"""
infra.py — Infrastructure Fingerprinting API for DarkTrace
Exposes real-time SSL/TLS cert scanning and shared-infra detection endpoints.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List

from app.database import get_db
from app.services.infra_scan import get_scanner

logger = logging.getLogger("InfraAPI")
router = APIRouter(tags=["Infrastructure Fingerprinting"])

# In-memory cache of recent scan results (host -> result)
_SCAN_CACHE: Dict[str, Any] = {}
_FINGERPRINT_REGISTRY: Dict[str, List[str]] = {}  # fingerprint -> [hosts]


@router.post("/scan")
def scan_host(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    """
    Perform a real-time SSL/TLS cert inspection + HTTP banner grab on a target host.
    Detects shared infrastructure by comparing cert fingerprints across actors.

    Body: {"host": "example.com", "port": 443}
    """
    host = payload.get("host", "").strip()
    if not host:
        raise HTTPException(status_code=400, detail="'host' field is required")

    # Sanitize: strip scheme, path
    host = host.replace("https://", "").replace("http://", "").split("/")[0]
    port = int(payload.get("port", 443))

    if port not in (80, 443):
        raise HTTPException(status_code=400, detail="Only ports 80 and 443 are allowed")

    try:
        scanner = get_scanner()
        result = scanner.scan_target(host, port)

        # Register fingerprint
        fp = result.get("fingerprint")
        if fp:
            if fp not in _FINGERPRINT_REGISTRY:
                _FINGERPRINT_REGISTRY[fp] = []
            if host not in _FINGERPRINT_REGISTRY[fp]:
                _FINGERPRINT_REGISTRY[fp].append(host)

            # Check for shared infrastructure
            result["shared_with"] = scanner.check_shared_infrastructure(fp, db)

            # Also check our in-memory registry for other scanned hosts sharing this cert
            other_hosts = [h for h in _FINGERPRINT_REGISTRY.get(fp, []) if h != host]
            if other_hosts:
                result["shared_hosts"] = other_hosts
                result["infrastructure_overlap"] = True
            else:
                result["infrastructure_overlap"] = False

        # Cache result
        _SCAN_CACHE[host] = result
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[InfraAPI] Scan error for {host}: {e}")
        return {
            "host": host,
            "port": port,
            "reachable": False,
            "error": str(e),
            "ssl": None,
            "banner": None,
            "fingerprint": None,
            "indicators": [],
            "infrastructure_overlap": False,
        }


@router.get("/fingerprints")
def get_fingerprints():
    """
    Return all SSL certificate fingerprints seen across scanned hosts.
    Hosts sharing a fingerprint are flagged as shared infrastructure.
    """
    result = []
    for fp, hosts in _FINGERPRINT_REGISTRY.items():
        result.append({
            "fingerprint": fp,
            "hosts": hosts,
            "host_count": len(hosts),
            "is_shared": len(hosts) > 1,
            "risk_level": "HIGH" if len(hosts) > 1 else "LOW",
        })

    result.sort(key=lambda x: x["host_count"], reverse=True)
    return {
        "total_fingerprints": len(result),
        "shared_fingerprints": sum(1 for r in result if r["is_shared"]),
        "fingerprints": result,
    }


@router.get("/shared")
def get_shared_infrastructure(db: Session = Depends(get_db)):
    """
    Return pairs of actors/hosts that share SSL certificate fingerprints
    (strong indicator of shared infrastructure / same operator).
    """
    shared_findings = []

    for fp, hosts in _FINGERPRINT_REGISTRY.items():
        if len(hosts) > 1:
            shared_findings.append({
                "fingerprint": fp,
                "shared_hosts": hosts,
                "finding_type": "SHARED_TLS_CERT",
                "confidence": 0.92,
                "description": (
                    f"{len(hosts)} hosts share SSL certificate fingerprint {fp[:16]}... "
                    f"— likely operated by the same entity."
                ),
            })

    return {
        "total_findings": len(shared_findings),
        "findings": shared_findings,
        "summary": (
            f"Found {len(shared_findings)} shared infrastructure finding(s) "
            f"across {sum(len(f['shared_hosts']) for f in shared_findings)} hosts."
        ),
    }


@router.get("/recent-scans")
def get_recent_scans():
    """Return all cached scan results from this session."""
    scans = list(_SCAN_CACHE.values())
    return {
        "total_scans": len(scans),
        "scans": scans,
    }


@router.get("/scan-targets")
def get_recommended_scan_targets(db: Session = Depends(get_db)):
    """
    Return a list of clearnet hosts worth scanning:
    - Domains from actor profiles
    - Known infrastructure indicators from the DB
    """
    try:
        from app.models.intelligence import Domain, InfrastructureIndicator

        domains = db.query(Domain).limit(20).all()
        indicators = db.query(InfrastructureIndicator).filter(
            InfrastructureIndicator.indicator_type == "DOMAIN"
        ).limit(10).all()

        targets = []
        seen = set()

        for d in domains:
            if d.domain and d.domain not in seen:
                seen.add(d.domain)
                targets.append({
                    "host": d.domain,
                    "source": "actor_domain",
                    "actor_id": d.actor_id,
                })

        for ind in indicators:
            if ind.value and ind.value not in seen:
                seen.add(ind.value)
                targets.append({
                    "host": ind.value,
                    "source": "infrastructure_indicator",
                    "confidence": ind.confidence,
                })

        # Always include well-known public hosts for SSL demo
        demo_targets = [
            {"host": "google.com", "source": "demo", "description": "Public reference"},
            {"host": "cloudflare.com", "source": "demo", "description": "Public reference"},
            {"host": "github.com", "source": "demo", "description": "Public reference"},
        ]
        targets = demo_targets + targets

        return {"targets": targets, "total": len(targets)}
    except Exception as e:
        return {
            "targets": [
                {"host": "google.com", "source": "demo"},
                {"host": "cloudflare.com", "source": "demo"},
            ],
            "total": 2,
            "note": str(e),
        }
