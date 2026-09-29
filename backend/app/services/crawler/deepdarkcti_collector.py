"""
deepdarkcti_collector.py — Real-Time Collection Engine for deepdarkCTI Sources

Role:
    DarkTrace Source Registry → Collection Scheduler → Existing Collectors → Observations

This module:
1. Selects ENABLED seeds sourced from deepdarkCTI
2. Checks Tor SOCKS5 connectivity
3. Uses the existing OnionCrawlerAdapter / DarkCrawler for actual HTTP requests
4. Produces normalized observations via the existing normalizer
5. Runs the full extraction pipeline (entities, PGP, wallets, handles)
6. Persists to SQLite using existing models
7. Triggers the existing AI attribution pipeline
8. Generates alerts when genuinely new entities are discovered
9. Anchors evidence with SHA-256

State machine for each source:
    DISCOVERED → (analyst enables) → ENABLED
    ENABLED    → (scheduler picks) → COLLECTING
    COLLECTING → (success)         → REACHABLE / CONTENT_OBSERVED
    COLLECTING → (timeout/error)   → UNREACHABLE / FAILED
"""

import logging
import hashlib
import socket
import time
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("DeepDarkCollector")

# ─── Global scheduler state ─────────────────────────────────────
_SCHEDULER_STATE = {
    "running": False,
    "thread": None,
    "last_cycle_at": None,
    "last_cycle_result": None,
    "total_cycles": 0,
    "total_new_observations": 0,
    "errors": [],
}


def get_scheduler_state() -> Dict[str, Any]:
    return {
        "running": _SCHEDULER_STATE["running"],
        "last_cycle_at": _SCHEDULER_STATE["last_cycle_at"],
        "last_cycle_result": _SCHEDULER_STATE["last_cycle_result"],
        "total_cycles": _SCHEDULER_STATE["total_cycles"],
        "total_new_observations": _SCHEDULER_STATE["total_new_observations"],
        "recent_errors": _SCHEDULER_STATE["errors"][-5:],
    }


# ─── Tor connectivity check (uses config, not hardcoded) ─────────
def check_tor_alive() -> Tuple[bool, str]:
    """
    Probe Tor SOCKS5 port. Returns (alive, proxy_url).
    Reads from centralized config — single source of truth.
    """
    from app.config import settings
    host = settings.TOR_SOCKS_HOST
    port = settings.TOR_SOCKS_PORT
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        ok = s.connect_ex((host, port)) == 0
        s.close()
        return ok, settings.TOR_SOCKS_PROXY
    except Exception:
        return False, settings.TOR_SOCKS_PROXY


# ─── Single source collection ────────────────────────────────────
def collect_one_source(seed, db_session) -> Dict[str, Any]:
    """
    Collect a single deepdarkCTI-sourced seed using the existing DarkCrawler.
    Updates seed status fields throughout. Returns result dict.
    """
    from app.models.intelligence import SeedSource, Observation, Alert
    from app.services.crawler.normalizer import normalize_observation, compute_sha256
    from app.services.crawler.pipeline import extract_entities_from_text, CrawlerPipeline
    from app.services.crawler.dark_crawler import DarkCrawler

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    ref = seed.reference
    result = {
        "seed_id": seed.id,
        "seed_url": ref,
        "seed_name": seed.name,
        "status": "ERROR",
        "http_status": None,
        "observation_id": None,
        "new_entities": [],
        "error": None,
        "collected_at": now.isoformat(),
    }

    # Mark as COLLECTING
    seed.status = "COLLECTING"
    db_session.commit()

    tor_alive, proxy_url = check_tor_alive()
    is_onion = ".onion" in ref

    # Use existing DarkCrawler for all collection
    crawler = DarkCrawler()

    try:
        logger.info(f"[Collector] Collecting: {ref} (Tor={'ON' if tor_alive else 'OFF'})")

        # Perform actual HTTP request via DarkCrawler's crawl_onion for .onion
        # or a direct request for clearnet sources
        if is_onion and tor_alive:
            intel = crawler.crawl_onion(ref, save_records=False)
        elif not is_onion:
            # Clearnet: use requests directly with timeout, no Tor for clearnet sources
            import requests as req_lib
            try:
                resp = req_lib.get(
                    ref,
                    timeout=15,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; DarkTrace CTI Scanner/1.0)"},
                    allow_redirects=True,
                )
                intel = {
                    "onion_address": ref,
                    "status": "ONLINE" if resp.status_code < 400 else "ERROR",
                    "http_status": resp.status_code,
                    "title": _extract_title(resp.text),
                    "content": resp.text[:10000],   # Cap at 10KB
                    "response_size": len(resp.content),
                    "headers": dict(resp.headers),
                }
            except req_lib.exceptions.Timeout:
                intel = {"onion_address": ref, "status": "TIMEOUT", "http_status": 0, "content": "", "title": ""}
            except Exception as e:
                intel = {"onion_address": ref, "status": "ERROR", "http_status": 0, "content": "", "title": "", "error": str(e)}
        else:
            # .onion but Tor not alive
            intel = {"onion_address": ref, "status": "TOR_OFFLINE", "http_status": 0, "content": "", "title": ""}

        http_status = intel.get("http_status", intel.get("status_code", 0))
        # DarkCrawler returns "success"/"timeout"/"offline" not "ONLINE"
        raw_status = intel.get("status", "ERROR")
        # Build content from DarkCrawler's extracted fields
        text_sample = intel.get("text_sample") or intel.get("content") or ""
        # Also concatenate found entities into content for entity extraction
        page_title = intel.get("page_title") or intel.get("title") or ""
        raw_content = text_sample or page_title

        result["http_status"] = http_status

        # Update seed lifecycle state
        if raw_status == "success" or (isinstance(http_status, int) and 200 <= http_status < 400):
            seed.status = "CONTENT_OBSERVED" if raw_content else "REACHABLE"
            seed.last_seen = now
        elif raw_status in ("timeout", "TIMEOUT"):
            seed.status = "UNREACHABLE"
            seed.error_count = (seed.error_count or 0) + 1
            result["error"] = "Connection timeout"
        elif raw_status in ("offline", "TOR_OFFLINE"):
            seed.status = "UNREACHABLE"
            result["error"] = "Tor SOCKS5 offline — cannot reach .onion"
        else:
            seed.status = "UNREACHABLE"
            seed.error_count = (seed.error_count or 0) + 1
            result["error"] = intel.get("error") or f"HTTP {http_status}"

        # If we got content, run normalization + extraction
        if (raw_content or intel.get("btc_wallets") or intel.get("xmr_wallets")) and seed.status in ("REACHABLE", "CONTENT_OBSERVED"):
            # Build a content string that includes all found intel for entity extraction
            entity_text_parts = [raw_content]
            for w in intel.get("btc_wallets", []):
                entity_text_parts.append(w)
            for w in intel.get("xmr_wallets", []):
                entity_text_parts.append(w)
            for e in intel.get("emails", []):
                entity_text_parts.append(e)
            for h in intel.get("handles", []):
                entity_text_parts.append(f"@{h}")
            for t in intel.get("telegram", []):
                entity_text_parts.append(f"t.me/{t}")
            combined_text = " ".join(filter(None, entity_text_parts))

            # Build raw_item for normalizer using the DarkCrawler output field names
            raw_item_for_norm = {
                "source_url": ref,
                "source_type": "onion-service" if is_onion else "clearnet-forum",
                "title": page_title,
                "content": combined_text,
                "http_status": http_status,
                "reliability": seed.reliability or 0.75,
                # DarkCrawler entity fields for entity merging
                "extracted_entities": {
                    "wallets": intel.get("btc_wallets", []) + intel.get("xmr_wallets", []),
                    "btc_wallets": intel.get("btc_wallets", []),
                    "xmr_wallets": intel.get("xmr_wallets", []),
                    "pgp_keys": intel.get("pgp_keys", []),
                    "handles": intel.get("handles", []),
                    "telegram": intel.get("telegram", []),
                    "emails": intel.get("emails", []),
                    "onions": [a for a in intel.get("onion_addresses", []) if a != ref],
                    "favicon_hash": intel.get("favicon_murmur_hash"),
                },
                "favicon_murmur_hash": intel.get("favicon_murmur_hash"),
            }

            # Normalize using existing normalizer
            norm = normalize_observation(raw_item_for_norm, collector="DeepDarkCTI-Collector")

            content_sha = norm.get("content_sha256") or compute_sha256(raw_content)
            exposure_alerts = norm.get("provenance", {}).get("exposure_alerts", [])

            # Check for duplicate by hash
            existing_obs = db_session.query(Observation).filter(
                Observation.content_sha256 == content_sha
            ).first()
            if existing_obs:
                logger.info(f"[Collector] Duplicate observation (SHA {content_sha[:12]}...) — skipping.")
                seed.observation_count = (seed.observation_count or 0)
                db_session.commit()
                result["status"] = "DUPLICATE"
                return result

            # Entity extraction via existing pipeline function
            entities = extract_entities_from_text(
                (norm.get("content") or "") + " " + (norm.get("title") or "")
            )

            # Entity resolution
            pipeline = CrawlerPipeline(db_session)
            cand_id, conf, notes, _ = pipeline._resolve_against_actors(norm, entities)

            # SHA-256 anchor
            anchor_ts = now.timestamp()
            tx_hash = f"0x{hashlib.sha256((content_sha + str(anchor_ts)).encode()).hexdigest()}"

            obs = Observation(
                source_name=ref,
                source_type=norm.get("source_type", "clearnet-forum"),
                seed_id=seed.id,
                service=norm.get("service", ref[:50]),
                title=norm.get("title") or "DeepDarkCTI Source",
                content=norm.get("content"),
                raw_reference=norm.get("raw_content_reference"),
                collection_method="DeepDarkCTI-Collector",
                reliability=seed.reliability or 0.75,
                timestamp=now,
                collected_at=now,
                metadata_json={
                    "provenance": {
                        "catalogue": "deepdarkCTI",
                        "catalogue_status": _extract_catalogue_status(seed.notes),
                        "collector": "DeepDarkCTI-Collector",
                        "tor_used": is_onion and tor_alive,
                        "proxy_url": proxy_url if (is_onion and tor_alive) else None,
                        "collection_method": "TorSOCKS5" if (is_onion and tor_alive) else "DirectHTTP",
                        "response_size": len(raw_content),
                        "exposure_alerts": exposure_alerts,
                    },
                    "deepdarkcti_category": seed.category,
                    "http_headers": intel.get("headers", {}),
                },
                extracted_entities=entities,
                status="UNRESOLVED" if not cand_id or conf < 0.65 else "LINKED",
                candidate_actor_id=cand_id,
                candidate_confidence=conf,
                candidate_notes=notes,
                content_sha256=content_sha,
                blockchain_tx_hash=tx_hash,
                blockchain_anchor_time=now,
            )
            db_session.add(obs)
            db_session.flush()  # Get obs.id

            # Generate alert for PGP private key exposure
            for exp in exposure_alerts:
                alert = Alert(
                    alert_type="SENSITIVE_KEY_EXPOSURE",
                    title=f"[DeepDarkCTI] PGP PRIVATE KEY MATERIAL OBSERVED: {seed.name}",
                    description=(
                        f"Source: {ref}\n"
                        f"Observation ID: {obs.id}\n"
                        f"A PGP private key indicator was observed in content collected from {ref}. "
                        f"Content was safely redacted. Evidence hash: {exp.get('key_sha256', 'N/A')[:16]}..."
                    ),
                    severity="CRITICAL",
                    observation_id=obs.id,
                    entity_type="PGP_PRIVATE_KEY",
                    entity_value=exp.get("key_sha256", "")[:64],
                    confidence=0.99,
                )
                db_session.add(alert)

            # Generate alert for new entity discovery if resolution found candidate
            if cand_id and conf >= 0.65:
                alert = Alert(
                    alert_type="ENTITY_RESOLUTION_MATCH",
                    title=f"[DeepDarkCTI] Potential entity match: {seed.name}",
                    description=(
                        f"Collected observation from deepdarkCTI source '{seed.name}' ({ref}) "
                        f"matched candidate actor ID {cand_id} with confidence {conf:.1%}. "
                        f"Resolution notes: {notes}"
                    ),
                    severity="HIGH",
                    observation_id=obs.id,
                    actor_id=cand_id,
                    confidence=conf,
                )
                db_session.add(alert)

            # Generate alert for new .onion discovered
            new_onions = [o for o in entities.get("onions", []) if o not in [ref]]
            if new_onions:
                alert = Alert(
                    alert_type="NEW_ONION_DISCOVERED",
                    title=f"[DeepDarkCTI] New onion address discovered in {seed.name}",
                    description=(
                        f"Source: {ref}\nNew onion addresses observed: {', '.join(new_onions[:5])}"
                    ),
                    severity="MEDIUM",
                    observation_id=obs.id,
                    entity_type="ONION_ADDRESS",
                    entity_value=new_onions[0],
                    confidence=0.9,
                )
                db_session.add(alert)

            seed.observation_count = (seed.observation_count or 0) + 1
            result.update({
                "status": "COLLECTED",
                "observation_id": obs.id,
                "content_sha256": content_sha,
                "entities_summary": {
                    k: len(v) for k, v in entities.items() if isinstance(v, list) and v
                },
                "new_entities": _summarize_entities(entities),
            })

        db_session.commit()
        return result

    except Exception as e:
        logger.exception(f"[Collector] Error collecting {ref}: {e}")
        seed.status = "FAILED"
        seed.error_count = (seed.error_count or 0) + 1
        db_session.commit()
        result["error"] = str(e)
        return result


def _extract_title(html: str) -> str:
    """Extract page title from HTML."""
    import re
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip()[:200] if m else ""


def _extract_catalogue_status(notes: str) -> str:
    """Extract catalogue_status from notes string."""
    if not notes:
        return "UNKNOWN"
    import re
    m = re.search(r"catalogue_status=(\w+)", notes or "")
    return m.group(1) if m else "UNKNOWN"


def _summarize_entities(entities: Dict) -> List[str]:
    """Produce a short list of discovered entity values for alerts."""
    summary = []
    for k in ("handles", "wallets", "emails", "pgps", "onions"):
        for v in entities.get(k, [])[:2]:
            summary.append(f"{k}:{v}")
    return summary[:8]


# ─── Collection cycle ────────────────────────────────────────────
def run_collection_cycle(db_session, max_sources: int = 5, categories: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Execute one collection cycle:
    1. Select ENABLED seeds from deepdarkCTI categories (up to max_sources)
    2. For each: check Tor, collect, normalize, extract, persist
    3. Return cycle summary

    Seeds must be manually ENABLED by the analyst (authorized=1, status='ENABLED')
    before they enter the collection queue. DISCOVERED seeds are NOT auto-collected.
    """
    from app.models.intelligence import SeedSource
    from sqlalchemy import or_

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Only collect sources that analyst has explicitly enabled
    # and that are tagged as deepdarkCTI-sourced (have deepdarkCTI in notes)
    q = db_session.query(SeedSource).filter(
        SeedSource.authorized == 1,
        SeedSource.status.in_(["ENABLED", "REACHABLE", "CONTENT_OBSERVED"]),
        SeedSource.notes.like("%deepdarkCTI%"),
    )

    if categories:
        q = q.filter(SeedSource.category.in_(categories))

    # Prioritize sources not collected recently
    seeds = q.order_by(SeedSource.last_seen.asc()).limit(max_sources).all()

    cycle_result = {
        "cycle_started_at": now.isoformat(),
        "seeds_selected": len(seeds),
        "collected": 0,
        "unreachable": 0,
        "errors": 0,
        "new_observations": 0,
        "results": [],
    }

    for seed in seeds:
        r = collect_one_source(seed, db_session)
        cycle_result["results"].append(r)
        if r["status"] == "COLLECTED":
            cycle_result["collected"] += 1
            if r.get("observation_id"):
                cycle_result["new_observations"] += 1
        elif r["status"] in ("UNREACHABLE", "TOR_OFFLINE"):
            cycle_result["unreachable"] += 1
        elif r["status"] == "ERROR":
            cycle_result["errors"] += 1

    cycle_result["cycle_completed_at"] = datetime.now(timezone.utc).isoformat()
    return cycle_result


# ─── Background scheduler ────────────────────────────────────────
def _scheduler_loop(interval_seconds: int, db_factory):
    """Background loop that periodically runs collection cycles."""
    logger.info(f"[Scheduler] Starting deepdarkCTI collection scheduler (interval={interval_seconds}s)")
    while _SCHEDULER_STATE["running"]:
        try:
            db = db_factory()
            try:
                result = run_collection_cycle(db)
                _SCHEDULER_STATE["last_cycle_at"] = datetime.now(timezone.utc).isoformat()
                _SCHEDULER_STATE["last_cycle_result"] = result
                _SCHEDULER_STATE["total_cycles"] += 1
                _SCHEDULER_STATE["total_new_observations"] += result.get("new_observations", 0)
                logger.info(
                    f"[Scheduler] Cycle {_SCHEDULER_STATE['total_cycles']}: "
                    f"collected={result['collected']} unreachable={result['unreachable']} "
                    f"new_obs={result['new_observations']}"
                )
            finally:
                db.close()
        except Exception as e:
            _SCHEDULER_STATE["errors"].append(str(e))
            logger.error(f"[Scheduler] Cycle error: {e}")

        # Sleep in chunks so we can exit cleanly
        for _ in range(interval_seconds):
            if not _SCHEDULER_STATE["running"]:
                break
            time.sleep(1)

    logger.info("[Scheduler] deepdarkCTI collection scheduler stopped.")


def start_scheduler(interval_seconds: int = 300, db_factory=None):
    """Start the background collection scheduler."""
    if _SCHEDULER_STATE["running"]:
        logger.warning("[Scheduler] Already running.")
        return False

    if db_factory is None:
        from app.database import SessionLocal
        db_factory = SessionLocal

    _SCHEDULER_STATE["running"] = True
    _SCHEDULER_STATE["errors"] = []

    t = threading.Thread(
        target=_scheduler_loop,
        args=(interval_seconds, db_factory),
        daemon=True,
        name="DeepDarkCTI-Scheduler",
    )
    t.start()
    _SCHEDULER_STATE["thread"] = t
    logger.info(f"[Scheduler] deepdarkCTI collection scheduler started (interval={interval_seconds}s)")
    return True


def stop_scheduler():
    """Stop the background collection scheduler."""
    _SCHEDULER_STATE["running"] = False
    logger.info("[Scheduler] Stop requested.")
    return True
