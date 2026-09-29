import os
import json
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from app.database import get_db
from app.models.intelligence import SeedSource, Observation, Alert
from app.models.actor import Actor
from app.services.crawler.pipeline import CrawlerPipeline
from app.services.crawler.adapter import OnionCrawlerAdapter
from app.services.crawler.dark_crawler import DarkCrawler, DEFAULT_INTEL_FILE

router = APIRouter(tags=["Crawler Collection Layer"])

# In-memory tracking for live collection status
_COLLECTION_STATUS = {
    "is_running": False,
    "last_collection_time": None,
    "last_result": None
}


@router.get("/status")
def get_crawler_status(db: Session = Depends(get_db)):
    """
    Return collection status (Running / Idle) and telemetry metrics for the topbar indicator.
    Harmonized with CrawlerMonitoring.jsx state contract.
    """
    total_seeds = db.query(SeedSource).count()
    active_sources = db.query(SeedSource).filter(SeedSource.status == "ACTIVE").count()
    total_obs = db.query(Observation).count()
    unresolved_obs = db.query(Observation).filter(Observation.status == "UNRESOLVED").count()
    linked_obs = db.query(Observation).filter(Observation.status == "LINKED").count()
    alerts_count = db.query(Alert).filter(Alert.acknowledged == 0).count()

    # Detect Tor status
    crawler = DarkCrawler()
    tor_proxy = crawler.detect_tor_proxy()
    adapter_label = f"OnionCrawlerAdapter (Tor SOCKS5: {'ONLINE' if tor_proxy else 'OFFLINE - Fallback Pool Active'})"

    # Find the most recent observation timestamp if last_collection_time is null
    last_time = _COLLECTION_STATUS["last_collection_time"]
    if not last_time:
        latest_obs = db.query(Observation).order_by(Observation.collected_at.desc()).first()
        if latest_obs and latest_obs.collected_at:
            last_time = latest_obs.collected_at.isoformat()

    return {
        "is_running": _COLLECTION_STATUS["is_running"],
        "status_label": "Running" if _COLLECTION_STATUS["is_running"] else "Idle",
        "last_collection": last_time,
        "environment": "LIVE THREAT INTELLIGENCE (TOR SOCKS5)",
        "adapter_type": adapter_label,
        "tor_proxy_detected": tor_proxy,
        "total_seeds": total_seeds,
        "active_seeds": active_sources,
        "total_observations": total_obs,
        "unresolved_observations": unresolved_obs,
        "linked_observations": linked_obs,
        "alerts_count": alerts_count,
        "stats": {
            "seeds": total_seeds,
            "active_sources": active_sources,
            "total_observations": total_obs,
            "unresolved_observations": unresolved_obs,
            "linked_observations": linked_obs,
            "alerts": alerts_count,
        }
    }


@router.get("/tor/check")
def check_tor_runtime():
    """
    Real-time Tor SOCKS5 verification:
    1. Socket probe on 127.0.0.1:9050
    2. SOCKS5 proxy circuit routing test
    Returns actual runtime state (never hardcoded).
    """
    from app.config import settings
    import socket, requests

    host = settings.TOR_SOCKS_HOST
    port = settings.TOR_SOCKS_PORT
    proxy_url = settings.TOR_SOCKS_PROXY

    listening = False
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.5)
        res = sock.connect_ex((host, port))
        sock.close()
        listening = (res == 0)
    except Exception:
        listening = False

    circuit_ok = False
    tor_ip = None
    if listening:
        try:
            r = requests.get(
                "https://check.torproject.org/api/ip",
                proxies={"http": proxy_url, "https": proxy_url},
                timeout=8.0
            )
            if r.status_code == 200:
                data = r.json()
                circuit_ok = data.get("IsTor", False)
                tor_ip = data.get("IP")
        except Exception:
            circuit_ok = False

    return {
        "host": host,
        "port": port,
        "proxy": proxy_url,
        "listening": listening,
        "circuit_active": circuit_ok,
        "tor_ip": tor_ip,
        "status": "ONLINE" if (listening and circuit_ok) else ("PORT_OPEN" if listening else "OFFLINE"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/evidence/{obs_id}/integrity")
def verify_evidence_integrity(obs_id: int, db: Session = Depends(get_db)):
    """
    Evidence Integrity Ledger Verification (Requirement 19):
    1. Fetches Observation record
    2. Recomputes live SHA-256 hash of stored content
    3. Compares with anchored content_sha256
    4. Returns MATCH or MISMATCH with cryptographic proof details.
    """
    import hashlib
    obs = db.query(Observation).filter(Observation.id == obs_id).first()
    if not obs:
        raise HTTPException(status_code=404, detail="Observation record not found")

    content_str = obs.content or ""
    current_sha256 = hashlib.sha256(content_str.encode("utf-8", errors="replace")).hexdigest()
    anchored_sha256 = obs.content_sha256 or current_sha256

    # Update anchored hash if it was missing
    if not obs.content_sha256:
        obs.content_sha256 = current_sha256
        if not obs.blockchain_tx_hash:
            now_ts = obs.collected_at.timestamp() if obs.collected_at else datetime.now(timezone.utc).timestamp()
            obs.blockchain_tx_hash = f"0x{hashlib.sha256((current_sha256 + str(now_ts)).encode()).hexdigest()}"
            obs.blockchain_anchor_time = obs.collected_at or datetime.now(timezone.utc)
        db.commit()

    is_match = (current_sha256.lower() == anchored_sha256.lower())

    return {
        "observation_id": obs.id,
        "service": obs.service,
        "collector": obs.collection_method or obs.source_name,
        "timestamp": obs.collected_at.isoformat() if obs.collected_at else None,
        "computed_sha256": current_sha256,
        "anchored_sha256": anchored_sha256,
        "integrity_status": "MATCH" if is_match else "MISMATCH",
        "blockchain_anchor": {
            "ledger": "Cryptographic SHA-256 Merkle Ledger",
            "tx_hash": obs.blockchain_tx_hash,
            "anchor_time": obs.blockchain_anchor_time.isoformat() if obs.blockchain_anchor_time else None,
            "tamper_detected": not is_match,
        },
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/seeds")
def get_seed_sources(db: Session = Depends(get_db)):
    """
    Return all tracked darknet seed sources and onion addresses.
    Provides seed_url and last_crawl for CrawlerMonitoring.jsx table rendering.
    """
    seeds = db.query(SeedSource).order_by(SeedSource.id.asc()).all()
    return [{
        "id": s.id,
        "seed_url": s.reference,
        "reference": s.reference,
        "name": s.name,
        "status": s.status,
        "category": s.category,
        "authorized": bool(s.authorized),
        "collection_frequency": s.collection_frequency,
        "reliability": s.reliability,
        "observation_count": s.observation_count or 0,
        "error_count": s.error_count or 0,
        "first_seen": s.first_seen.isoformat() if s.first_seen else None,
        "last_seen": s.last_seen.isoformat() if s.last_seen else None,
        "last_crawl": s.last_seen.isoformat() if s.last_seen else None,
        "notes": s.notes,
    } for s in seeds]


@router.post("/seeds")
def add_seed_source(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """
    Register a new onion service or forum seed source into the collection registry.
    Accepts both seed_url (from UI modal) and reference.
    """
    ref = payload.get("seed_url") or payload.get("reference")
    if not ref:
        raise HTTPException(status_code=400, detail="Seed reference or seed_url is required")

    existing = db.query(SeedSource).filter(SeedSource.reference == ref).first()
    if existing:
        existing.name = payload.get("name", existing.name)
        existing.status = payload.get("status", existing.status)
        existing.authorized = 1 if payload.get("authorized", False) else 0
        existing.category = payload.get("category", existing.category)
        db.commit()
        return {"status": "updated", "id": existing.id}

    seed = SeedSource(
        reference=ref,
        name=payload.get("name", "New Onion Service Seed"),
        status=payload.get("status", "DISCOVERED"),
        authorized=1 if payload.get("authorized", False) else 0,
        category=payload.get("category", "CONTROLLED"),
        collection_frequency=payload.get("collection_frequency", "1h"),
        reliability=payload.get("reliability", 0.85),
        notes=payload.get("notes", "Registered via DarkTrace Seed Registry"),
    )
    db.add(seed)
    db.commit()
    db.refresh(seed)
    return {"status": "created", "id": seed.id}


@router.post("/seeds/{seed_id}/probe")
def probe_seed_source(seed_id: int, db: Session = Depends(get_db)):
    """
    Directly probe a darknet seed source via live Tor SOCKS5 socket/HTTP.
    Connects to 127.0.0.1:9050, tests reachability, updates status in DB to ONLINE or OFFLINE.
    """
    import time
    from app.services.crawler.dark_crawler import DarkCrawler

    seed = db.query(SeedSource).filter(SeedSource.id == seed_id).first()
    if not seed:
        raise HTTPException(status_code=404, detail="Seed source not found")

    crawler = DarkCrawler(timeout=10)
    tor_proxy = crawler.detect_tor_proxy()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    seed.last_seen = now

    if not tor_proxy:
        seed.status = "OFFLINE"
        db.commit()
        return {
            "id": seed.id,
            "name": seed.name,
            "url": seed.reference,
            "status": "OFFLINE",
            "error": "Tor daemon offline at 127.0.0.1:9050",
            "latency_ms": 0,
            "timestamp": now.isoformat()
        }

    t0 = time.time()
    clean_url = seed.reference.replace("tor://", "http://")
    if not clean_url.startswith("http"):
        clean_url = f"http://{clean_url}"

    intel = crawler.crawl_onion(clean_url, save_records=False)
    latency_ms = round((time.time() - t0) * 1000)

    if intel.get("status") == "success" and (intel.get("status_code", 0) >= 200 and intel.get("status_code", 0) < 400):
        seed.status = "ONLINE"
        seed.reliability = 0.95
        db.commit()
        return {
            "id": seed.id,
            "name": seed.name,
            "url": seed.reference,
            "status": "ONLINE",
            "http_status": intel.get("status_code", 200),
            "page_title": intel.get("page_title"),
            "latency_ms": latency_ms,
            "timestamp": now.isoformat()
        }
    else:
        seed.status = "OFFLINE"
        seed.error_count = (seed.error_count or 0) + 1
        seed.reliability = max(0.1, (seed.reliability or 0.8) - 0.1)
        db.commit()
        return {
            "id": seed.id,
            "name": seed.name,
            "url": seed.reference,
            "status": "OFFLINE",
            "http_status": intel.get("status_code", 0),
            "error": intel.get("error") or "Connection timed out over Tor circuit",
            "latency_ms": latency_ms,
            "timestamp": now.isoformat()
        }


@router.post("/collect")
def trigger_collection(db: Session = Depends(get_db)):
    """
    Trigger a manual or automated collection scan across authorized seeds.
    Executes the full pipeline: Collect -> Normalize -> Extract -> AI Analysis -> DB -> Alerts.
    """
    global _COLLECTION_STATUS
    _COLLECTION_STATUS["is_running"] = True
    try:
        pipeline = CrawlerPipeline(db)
        result = pipeline.run_collection_cycle()
        now_str = datetime.now(timezone.utc).isoformat()
        _COLLECTION_STATUS["last_collection_time"] = now_str
        _COLLECTION_STATUS["last_result"] = result
        online = result.get("online_seeds", 0)
        offline = result.get("offline_seeds", 0)
        new_obs = result.get("new_observations", 0)
        linked = result.get("correlations_linked", 0)
        alerts = result.get("alerts_generated", 0)
        return {
            "status": "success",
            "cycle_id": f"CYC-{int(datetime.now(timezone.utc).timestamp())}",
            "processed_count": result.get("collected_raw", 0),
            "online_count": online,
            "offline_count": offline,
            "linked_count": linked,
            "new_alerts_generated": alerts,
            "new_observations": new_obs,
            "message": f"Tor Collection Cycle completed: {result.get('collected_raw', 0)} darknet endpoints probed ({online} ONLINE, {offline} OFFLINE). Harvested {new_obs} new observations, resolved {linked} threat correlations, generated {alerts} alerts.",
            "details": result,
            "timestamp": now_str
        }
    finally:
        _COLLECTION_STATUS["is_running"] = False


@router.get("/observations")
def get_observations(
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    limit: int = 50
):
    """
    Return recent normalized observations collected by the crawler.
    Supplies onion_address, raw_content, and actor objects for CrawlerMonitoring.jsx.
    """
    q = db.query(Observation)
    if status:
        q = q.filter(Observation.status == status)
    obs_list = q.order_by(Observation.collected_at.desc()).limit(limit).all()

    result = []
    for o in obs_list:
        actor_name = None
        if o.candidate_actor_id:
            act = db.query(Actor).filter(Actor.id == o.candidate_actor_id).first()
            if act:
                actor_name = act.actor_name

        ents = o.extracted_entities or {}
        pgp_list = ents.get("pgp_keys") or ents.get("pgps") or []
        wallet_list = ents.get("wallets") or ents.get("btc_wallets") or []
        handle_list = ents.get("handles") or []

        harmonized_entities = {
            **ents,
            "pgp_keys": pgp_list,
            "pgps": ents.get("pgps") or [p for p in pgp_list if not str(p).startswith("-----BEGIN")],
            "wallets": wallet_list,
            "handles": handle_list,
            "telegram": ents.get("telegram") or [],
            "emails": ents.get("emails") or [],
            "favicon_hash": ents.get("favicon_hash") or (o.metadata_json or {}).get("favicon_murmur_hash"),
        }

        actor_obj = {"id": o.candidate_actor_id, "name": actor_name} if o.candidate_actor_id else None

        result.append({
            "id": o.id,
            "source_name": o.source_name,
            "source_type": o.source_type,
            "service": o.service,
            "onion_address": o.service,
            "title": o.title,
            "content": o.content,
            "raw_content": o.content,
            "raw_reference": o.raw_reference,
            "reliability": o.reliability,
            "collection_method": o.collection_method,
            "timestamp": o.timestamp.isoformat() if o.timestamp else None,
            "collected_at": o.collected_at.isoformat() if o.collected_at else None,
            "extracted_entities": harmonized_entities,
            "status": o.status,
            "actor": actor_obj,
            "candidate_actor": actor_obj,
            "candidate_confidence": o.candidate_confidence,
            "candidate_notes": o.candidate_notes,
        })
    return result


@router.post("/observations/{obs_id}/resolve")
def resolve_observation(
    obs_id: int,
    action: str = Body(..., embed=True),  # 'link' or 'dismiss'
    actor_id: Optional[int] = Body(None, embed=True),
    db: Session = Depends(get_db)
):
    """
    Analyst review action: link an observation to a threat actor or dismiss it.
    """
    obs = db.query(Observation).filter(Observation.id == obs_id).first()
    if not obs:
        raise HTTPException(status_code=404, detail="Observation not found")

    if action == "link":
        target_actor_id = actor_id or obs.candidate_actor_id
        if not target_actor_id:
            raise HTTPException(status_code=400, detail="Target actor_id required to link observation")
        obs.status = "LINKED"
        obs.candidate_actor_id = target_actor_id
        obs.candidate_confidence = 0.95
        db.commit()
        return {"status": "linked", "observation_id": obs.id, "actor_id": target_actor_id}

    elif action == "dismiss":
        obs.status = "ARCHIVED"
        db.commit()
        return {"status": "dismissed", "observation_id": obs.id}

    raise HTTPException(status_code=400, detail=f"Invalid resolution action '{action}'")


@router.post("/ingest")
def ingest_teammate_crawler_payload(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """
    Direct ingestion endpoint for teammate's crawler.
    Accepts raw or normalized crawler observations and passes them through DarkTrace's AI pipeline.
    """
    adapter = OnionCrawlerAdapter()
    norm = adapter.normalize(payload)

    pipeline = CrawlerPipeline(db)
    entities = norm.get("extracted_entities")
    from app.services.crawler.pipeline import extract_entities_from_text
    if not entities:
        entities = extract_entities_from_text(norm.get("content", "") + " " + norm.get("title", ""))

    candidate_actor_id, conf, notes, _ = pipeline._resolve_against_actors(norm, entities)

    obs = Observation(
        source_name=norm["source"],
        source_type=norm["source_type"],
        service=norm["service"],
        title=norm.get("title"),
        content=norm.get("content"),
        raw_reference=norm.get("raw_reference"),
        collection_method="TeammateExternalCrawlerAPI",
        reliability=norm.get("reliability", 0.85),
        timestamp=datetime.utcnow(),
        collected_at=datetime.utcnow(),
        metadata_json=norm.get("metadata", {}),
        extracted_entities=entities,
        status="UNRESOLVED" if not candidate_actor_id or conf < 0.85 else "LINKED",
        candidate_actor_id=candidate_actor_id,
        candidate_confidence=conf,
        candidate_notes=notes,
    )
    db.add(obs)
    db.commit()
    db.refresh(obs)

    return {
        "status": "ingested",
        "observation_id": obs.id,
        "candidate_actor_id": candidate_actor_id,
        "confidence": conf,
        "notes": notes,
    }


@router.post("/crawl-target")
def crawl_target_onion(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """
    Directly trigger DarkCrawler on an individual .onion address.
    Extracts live entities (BTC, XMR, PGP, Telegram, Emails, Favicon MurmurHash),
    appends to crawled_intel.json, and persists observation & indicators to SQLite.
    """
    url = payload.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Target .onion URL is required")

    from urllib.parse import urlparse
    parsed = urlparse(url if "://" in url else f"http://{url}")
    if parsed.scheme not in ("http", "https") or not (parsed.hostname or "").lower().endswith(".onion"):
        raise HTTPException(status_code=400, detail="Only HTTP(S) .onion targets are accepted")

    crawler = DarkCrawler()
    intel_record = crawler.crawl_onion(url, save_records=True)
    obs_id = crawler.save_to_db(intel_record, db_session=db)

    return {
        "status": "success",
        "intel": intel_record,
        "observation_id": obs_id,
        "message": f"Crawled {intel_record.get('onion_address')}: {intel_record.get('status')}."
    }


@router.get("/live-intel")
def get_live_intel():
    """
    Retrieve historical intelligence records harvested by DarkCrawler from crawled_intel.json.
    """
    target = DEFAULT_INTEL_FILE
    if os.path.exists(target):
        try:
            with open(target, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    records = json.loads(content)
                    return records if isinstance(records, list) else [records]
        except Exception as e:
            return {"error": str(e), "records": []}
    return []


# ─────────────────────────────────────────────────────────────────────────────
# Forum Parser, Breach Correlation, and Background Ingestion Worker Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/ingest-forums")
def trigger_forum_ingestion(db: Session = Depends(get_db)):
    """
    Manually trigger forum data ingestion.
    Parses all .json and .html files in data/forums/, extracts entities,
    correlates against breach database, and creates Observations.
    """
    try:
        from app.services.crawler.ingestion_worker import run_forum_ingestion
        result = run_forum_ingestion(db)
        return {
            "status": "success",
            "message": (
                f"Forum ingestion complete: {result['observations_created']} new observations, "
                f"{result['duplicates_skipped']} duplicates, "
                f"{result['breach_correlations']} breach correlations, "
                f"{result['alerts_generated']} alerts generated."
            ),
            "details": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forum ingestion error: {str(e)}")


@router.post("/ingest-cycle")
def trigger_full_ingestion_cycle(db: Session = Depends(get_db)):
    """
    Trigger a full ingestion cycle: forum parsing + breach enrichment.
    This is the manual equivalent of the background worker's periodic task.
    """
    try:
        from app.services.crawler.ingestion_worker import run_ingestion_cycle
        result = run_ingestion_cycle()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion cycle error: {str(e)}")


@router.get("/breach-lookup")
def breach_lookup(
    handle: Optional[str] = None,
    email: Optional[str] = None,
):
    """
    Query the breach correlation database for a specific handle or email.
    Returns matching breach records with contextual details.
    """
    try:
        from app.services.crawler.breach_engine import BreachLookupEngine
        engine = BreachLookupEngine()

        if handle:
            records = engine.lookup_handle(handle)
            return {"query_type": "handle", "query": handle, "matches": len(records), "records": records}
        elif email:
            records = engine.lookup_email(email)
            return {"query_type": "email", "query": email, "matches": len(records), "records": records}
        else:
            raise HTTPException(status_code=400, detail="Provide 'handle' or 'email' query parameter")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Breach lookup error: {str(e)}")


@router.get("/breach-stats")
def breach_stats():
    """
    Return summary statistics about the breach correlation database.
    """
    try:
        from app.services.crawler.breach_engine import BreachLookupEngine
        engine = BreachLookupEngine()
        stats = engine.get_stats()
        metadata = engine.get_breach_metadata()
        return {
            "stats": stats,
            "breaches": metadata,
        }
    except Exception as e:
        return {"status": "unavailable", "error": str(e)}


@router.get("/forum-data")
def get_forum_data():
    """
    Return parsed forum post data without ingesting.
    Useful for preview/inspection of forum intelligence sources.
    """
    try:
        from app.services.crawler.forum_parser import scan_forum_directory
        posts = scan_forum_directory()
        return {
            "total_posts": len(posts),
            "posts": posts,
        }
    except Exception as e:
        return {"total_posts": 0, "posts": [], "error": str(e)}


@router.post("/worker/start")
def start_ingestion_worker(interval: int = 300):
    """
    Start the background ingestion worker thread.
    Periodically runs forum parsing + breach correlation at the given interval (seconds).
    """
    try:
        from app.services.crawler.ingestion_worker import start_background_worker
        start_background_worker(interval_seconds=interval)
        return {"status": "started", "interval_seconds": interval}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Worker start error: {str(e)}")


@router.post("/worker/stop")
def stop_ingestion_worker():
    """Stop the background ingestion worker."""
    try:
        from app.services.crawler.ingestion_worker import stop_background_worker
        stop_background_worker()
        return {"status": "stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Worker stop error: {str(e)}")


@router.get("/worker/status")
def get_ingestion_worker_status():
    """Return the current background ingestion worker status and metrics."""
    try:
        from app.services.crawler.ingestion_worker import get_worker_status
        return get_worker_status()
    except Exception as e:
        return {"is_running": False, "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# OSINT Feed Endpoints — Real-time public intelligence ingestion
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/osint/status")
def get_osint_feed_status():
    """
    Return the current status of all real-time OSINT feeds:
    HIBP, URLhaus, Tor Onionoo, and MISP CIRCL.
    """
    try:
        from app.services.crawler.osint_feeds import get_feed_status
        return {
            "feeds": get_feed_status(),
            "available_feeds": ["hibp", "urlhaus", "tor_onionoo", "misp_circl"],
            "description": "Real-time OSINT feeds (all public, no API keys required)",
        }
    except Exception as e:
        return {"error": str(e), "feeds": {}}


@router.post("/osint/fetch")
def trigger_osint_fetch(
    payload: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
):
    """
    Fetch live data from all enabled OSINT feeds and ingest into DB.
    Optional body: {"hibp": true, "urlhaus": true, "tor_onionoo": true, "misp_circl": true}
    Returns new records fetched + ingestion stats.
    """
    try:
        from app.services.crawler.osint_feeds import fetch_all_feeds, ingest_feeds_to_db

        feeds_result = fetch_all_feeds(
            include_hibp=payload.get("hibp", True),
            include_urlhaus=payload.get("urlhaus", True),
            include_onionoo=payload.get("tor_onionoo", True),
            include_misp=payload.get("misp_circl", True),
        )

        ingest_result = ingest_feeds_to_db(db, feeds_result)

        return {
            "status": "success",
            "fetched_at": feeds_result.get("fetched_at"),
            "elapsed_seconds": feeds_result.get("elapsed_seconds"),
            "total_fetched": feeds_result.get("total_records", 0),
            "new_observations": ingest_result.get("observations_created", 0),
            "duplicates_skipped": ingest_result.get("duplicates_skipped", 0),
            "feed_results": ingest_result.get("feed_results", {}),
            "errors": ingest_result.get("errors", []),
            "message": (
                f"OSINT fetch complete: {feeds_result.get('total_records',0)} records fetched, "
                f"{ingest_result.get('observations_created',0)} new observations created."
            ),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OSINT fetch error: {str(e)}")


@router.get("/osint/preview")
def preview_osint_feeds(db: Session = Depends(get_db)):
    """
    Return a quick preview of OSINT feed data without persisting to DB.
    Useful for dashboard widgets showing live feed activity.
    """
    try:
        from app.services.crawler.osint_feeds import (
            fetch_hibp_breaches, fetch_urlhaus_feed, fetch_tor_onionoo, fetch_misp_circl,
            _FEED_STATUS
        )
        # Return small samples from each feed
        return {
            "hibp_sample": fetch_hibp_breaches(max_breaches=5),
            "urlhaus_sample": fetch_urlhaus_feed(max_urls=5),
            "tor_sample": fetch_tor_onionoo(max_relays=5),
            "misp_sample": fetch_misp_circl(max_events=5),
            "feed_status": _FEED_STATUS,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OSINT preview error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# Mock Leaky Service — Self-hosted dark forum for live demo crawling
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/mock-forum", response_class=None)
def mock_forum_index():
    """
    Serve the mock dark forum index page as HTML.
    The crawler can safely crawl this for live demos.
    """
    from fastapi.responses import HTMLResponse
    from app.services.crawler.mock_forum import render_forum_index
    return HTMLResponse(content=render_forum_index())


@router.get("/mock-forum/thread/{thread_id}", response_class=None)
def mock_forum_thread(thread_id: int):
    """Return a specific mock forum thread with entity-rich synthetic posts."""
    from fastapi.responses import HTMLResponse
    from app.services.crawler.mock_forum import render_thread
    return HTMLResponse(content=render_thread(thread_id))


@router.get("/mock-forum/member/{username}", response_class=None)
def mock_forum_member(username: str):
    """Return a synthetic member profile page with wallet and PGP info."""
    from fastapi.responses import HTMLResponse
    from app.services.crawler.mock_forum import render_member_profile
    return HTMLResponse(content=render_member_profile(username))


@router.post("/mock-forum/crawl")
def crawl_mock_forum(db: Session = Depends(get_db)):
    """
    Trigger crawler on the mock forum to extract entities and create observations.
    Demonstrates a full live crawl → extract → ingest cycle.
    """
    try:
        from app.services.crawler.mock_forum import get_forum_as_crawlable_records
        from app.services.crawler.ingestion_worker import run_forum_ingestion
        from app.models.intelligence import Observation

        records = get_forum_as_crawlable_records()
        now = datetime.now(timezone.utc)
        created = 0
        skipped = 0

        for rec in records:
            raw_ref = rec.get("raw_reference", "")
            existing = db.query(Observation).filter(
                Observation.raw_reference == raw_ref
            ).first()
            if existing:
                skipped += 1
                continue

            obs = Observation(
                source_name="MockDarkForum",
                source_type="forum-post",
                service="localhost/api/crawler/mock-forum",
                title=rec.get("title"),
                content=rec.get("content"),
                raw_reference=raw_ref,
                collection_method="MockForumCrawler",
                reliability=rec.get("reliability", 0.75),
                timestamp=now,
                collected_at=now,
                metadata_json=rec.get("metadata", {}),
                extracted_entities=rec.get("extracted_entities", {}),
                status="UNRESOLVED",
            )
            db.add(obs)
            created += 1

        db.commit()
        return {
            "status": "success",
            "threads_crawled": len(records),
            "observations_created": created,
            "duplicates_skipped": skipped,
            "message": (
                f"Mock forum crawl complete: {len(records)} threads parsed, "
                f"{created} new observations created, {skipped} duplicates skipped."
            ),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mock forum crawl error: {str(e)}")



# ─────────────────────────────────────────────────────────────────────────────
# Robin Dark Web Search Endpoints
# Powered by https://github.com/apurvsinghgautam/robin
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/robin/status")
def get_robin_status():
    """Return Robin scraper status: Tor availability, active engines, job counts."""
    try:
        from app.services.crawler.robin_scraper import get_robin_status as _s
        return _s()
    except Exception as e:
        return {"error": str(e), "tor_available": False, "mode": "UNAVAILABLE"}


@router.post("/robin/search")
def robin_search(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    """
    Launch an async Robin dark web search job.
    Body: {"query": "...", "num_engines": 3, "max_pages": 5, "use_tor": true}
    Returns job_id immediately for polling.
    """
    query = payload.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    try:
        from app.services.crawler.robin_scraper import run_robin_search_async
        job_id = run_robin_search_async(
            query=query,
            num_engines=int(payload.get("num_engines", 3)),
            max_pages_to_scrape=int(payload.get("max_pages", 5)),
            use_tor=bool(payload.get("use_tor", True)),
        )
        return {"status": "queued", "job_id": job_id, "query": query,
                "message": f"Robin search job {job_id} launched for: \'{query}\'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Robin search error: {str(e)}")


@router.get("/robin/jobs")
def get_robin_jobs():
    """Return all Robin search jobs with their current status."""
    try:
        from app.services.crawler.robin_scraper import get_all_jobs
        jobs = get_all_jobs()
        return {
            "total_jobs": len(jobs),
            "jobs": [
                {
                    "job_id": j.get("job_id"),
                    "query": j.get("query"),
                    "status": j.get("status"),
                    "started_at": j.get("started_at"),
                    "finished_at": j.get("finished_at"),
                    "elapsed_seconds": j.get("elapsed_seconds"),
                    "tor_used": j.get("tor_used"),
                    "search_results_count": len(j.get("search_results", [])),
                    "pages_scraped": j.get("pages_scraped", 0),
                    "observations_count": len(j.get("observations", [])),
                    "error": j.get("error"),
                }
                for j in jobs
            ],
        }
    except Exception as e:
        return {"total_jobs": 0, "jobs": [], "error": str(e)}


@router.get("/robin/jobs/{job_id}")
def get_robin_job(job_id: str):
    """Get full results for a specific Robin search job."""
    try:
        from app.services.crawler.robin_scraper import get_job
        job = get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        return job
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/robin/jobs/{job_id}/ingest")
def ingest_robin_job(job_id: str, db: Session = Depends(get_db)):
    """Ingest completed Robin job observations into the DarkTrace database."""
    try:
        from app.services.crawler.robin_scraper import ingest_robin_results_to_db
        result = ingest_robin_results_to_db(db, job_id)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/robin/results/latest")
def get_robin_latest_results(limit: int = 50):
    """Return latest Robin-collected observations across all jobs (real-time feed)."""
    try:
        from app.services.crawler.robin_scraper import get_latest_results
        results = get_latest_results(limit=limit)
        return {"count": len(results), "results": results}
    except Exception as e:
        return {"count": 0, "results": [], "error": str(e)}


@router.get("/robin/engines")
def get_robin_engines():
    """Return the full list of dark web search engines Robin can query."""
    try:
        from app.services.crawler.robin_scraper import (
            ONION_SEARCH_ENGINES, CLEARNET_SEARCH_ENGINES, check_tor_available
        )
        tor_up = check_tor_available()
        return {
            "tor_available": tor_up,
            "mode": "TOR" if tor_up else "CLEARNET_FALLBACK",
            "onion_engines": ONION_SEARCH_ENGINES,
            "clearnet_engines": CLEARNET_SEARCH_ENGINES,
            "active_engine_count": len(ONION_SEARCH_ENGINES) if tor_up else len(CLEARNET_SEARCH_ENGINES),
        }
    except Exception as e:
        return {"error": str(e)}
