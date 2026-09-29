"""
ingestion_worker.py — Background Ingestion Worker for DarkTrace
Runs forum parsing, breach correlation, and Tor crawling as background tasks,
merging discovered entities into the primary persistence layer without duplication.
Designed to be non-blocking so the Streamlit/FastAPI dashboard stays responsive.
"""

import os
import sys
import json
import hashlib
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

# Ensure imports work
_current_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.abspath(os.path.join(_current_dir, "..", "..", ".."))
_project_root = os.path.abspath(os.path.join(_backend_dir, ".."))
for _p in [_backend_dir, _project_root]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

logger = logging.getLogger("IngestionWorker")

# Global worker state
_WORKER_STATUS = {
    "is_running": False,
    "last_run": None,
    "last_result": None,
    "forum_posts_ingested": 0,
    "breach_correlations_found": 0,
    "total_runs": 0,
    "errors": [],
}

_worker_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()


def get_worker_status() -> Dict[str, Any]:
    """Return current background worker status."""
    return dict(_WORKER_STATUS)


def run_forum_ingestion(db_session) -> Dict[str, Any]:
    """
    Parse all forum data files and ingest posts as Observations.
    Each post is:
    1. Entity-extracted (handles, wallets, PGP, etc.)
    2. Breach-correlated (handles/emails checked against breaches.db)
    3. Deduplicated (hash-checked against existing observations)
    4. Actor-resolved (matched against known actors in DB)
    5. Persisted as Observation records with extracted_entities
    """
    from app.services.crawler.forum_parser import scan_forum_directory, normalize_forum_post
    from app.services.crawler.breach_engine import enrich_entities_with_breaches
    from app.services.crawler.pipeline import extract_entities_from_text, CrawlerPipeline
    from app.models.intelligence import Observation, Alert
    from app.models.actor import Actor

    result = {
        "posts_parsed": 0,
        "observations_created": 0,
        "duplicates_skipped": 0,
        "breach_correlations": 0,
        "alerts_generated": 0,
        "errors": [],
    }

    try:
        posts = scan_forum_directory()
        result["posts_parsed"] = len(posts)

        if not posts:
            logger.info("[ForumIngestion] No forum posts found to ingest.")
            return result

        pipeline = CrawlerPipeline(db_session)
        now = datetime.now(timezone.utc)

        for post in posts:
            try:
                norm = normalize_forum_post(post)
                raw_ref = norm["raw_reference"]

                # Deduplication check
                existing = db_session.query(Observation).filter(
                    Observation.raw_reference == raw_ref
                ).first()
                if existing:
                    result["duplicates_skipped"] += 1
                    continue

                # Extract entities from content
                content_text = norm["content"] + " " + (norm.get("title") or "")
                entities = extract_entities_from_text(content_text)

                # Inject author as handle if present
                author = post.get("author", "")
                if author and author.startswith("@"):
                    if author not in entities["handles"]:
                        entities["handles"].insert(0, author)

                # Inject author PGP if present
                author_pgp = post.get("author_pgp", "")
                if author_pgp and len(author_pgp) in [32, 40]:
                    if author_pgp not in entities["pgps"]:
                        entities["pgps"].append(author_pgp)
                    if author_pgp not in entities["pgp_keys"]:
                        entities["pgp_keys"].append(author_pgp)

                # Breach correlation
                entities = enrich_entities_with_breaches(entities)
                breach_data = entities.get("breach_correlations", {})
                if breach_data.get("total_matches", 0) > 0:
                    result["breach_correlations"] += breach_data["total_matches"]

                # Actor resolution
                candidate_id, conf, notes, evidence = pipeline._resolve_against_actors(
                    norm, entities
                )

                # Parse timestamp safely
                obs_timestamp = now
                ts_str = norm.get("timestamp", "")
                if ts_str:
                    try:
                        raw_ts = str(ts_str).strip().rstrip("Z")
                        if "+00:00" in raw_ts:
                            raw_ts = raw_ts.split("+00:00")[0]
                        obs_timestamp = datetime.fromisoformat(raw_ts)
                    except Exception:
                        obs_timestamp = now

                # Create observation
                obs = Observation(
                    source_name="ForumParser",
                    source_type="forum-post",
                    service=norm["service"],
                    title=norm.get("title"),
                    content=norm["content"],
                    raw_reference=raw_ref,
                    collection_method="ForumParserModule",
                    reliability=norm.get("reliability", 0.82),
                    timestamp=obs_timestamp,
                    collected_at=now,
                    metadata_json=norm.get("metadata", {}),
                    extracted_entities=entities,
                    status="LINKED" if candidate_id and conf >= 0.85 else "UNRESOLVED",
                    candidate_actor_id=candidate_id,
                    candidate_confidence=conf if candidate_id else None,
                    candidate_notes=notes,
                )
                db_session.add(obs)
                db_session.flush()
                result["observations_created"] += 1

                # Generate alert for high-confidence matches
                if candidate_id and conf >= 0.70:
                    actor = db_session.query(Actor).filter(Actor.id == candidate_id).first()
                    actor_name = actor.actor_name if actor else f"Actor #{candidate_id}"

                    alert_type = "FORUM_INTEL_MATCH"
                    severity = "HIGH"
                    if "PGP" in notes:
                        alert_type = "SHARED_PGP"
                        severity = "CRITICAL"
                    elif conf >= 0.85:
                        alert_type = "HIGH_ATTRIBUTION"
                        severity = "CRITICAL"

                    # Add breach context to alert if available
                    breach_note = ""
                    if breach_data.get("total_matches", 0) > 0:
                        breach_note = f" | Breach correlations: {breach_data['total_matches']} records across {len(breach_data.get('matched_breaches', []))} breaches"
                        severity = "CRITICAL"

                    alert = Alert(
                        alert_type=alert_type,
                        title=f"Forum Intel: {actor_name} on {norm['service']}",
                        description=(
                            f"Forum post on {norm['service']} matched {actor_name} "
                            f"({conf*100:.1f}% confidence). {notes}{breach_note}"
                        ),
                        severity=severity,
                        actor_id=candidate_id,
                        observation_id=obs.id,
                        entity_type="ForumPost",
                        entity_value=norm["service"],
                        confidence=conf,
                        created_at=now,
                        acknowledged=0,
                    )
                    db_session.add(alert)
                    result["alerts_generated"] += 1

            except Exception as e:
                err_msg = f"Error processing forum post: {e}"
                logger.error(err_msg)
                result["errors"].append(err_msg)

        db_session.commit()
        logger.info(
            f"[ForumIngestion] Complete: {result['observations_created']} new observations, "
            f"{result['duplicates_skipped']} duplicates, {result['breach_correlations']} breach correlations, "
            f"{result['alerts_generated']} alerts"
        )

    except Exception as e:
        db_session.rollback()
        err_msg = f"Forum ingestion error: {e}"
        logger.error(err_msg)
        result["errors"].append(err_msg)

    return result


def run_breach_enrichment(db_session) -> Dict[str, Any]:
    """
    Scan existing UNRESOLVED observations and enrich their entities with breach data.
    Also re-check for actor correlation with the enriched data.
    """
    from app.services.crawler.breach_engine import enrich_entities_with_breaches
    from app.services.crawler.pipeline import CrawlerPipeline
    from app.models.intelligence import Observation

    result = {
        "observations_scanned": 0,
        "enriched": 0,
        "errors": [],
    }

    try:
        observations = db_session.query(Observation).filter(
            Observation.status == "UNRESOLVED"
        ).limit(100).all()

        result["observations_scanned"] = len(observations)

        for obs in observations:
            try:
                entities = obs.extracted_entities or {}
                handles = entities.get("handles", [])
                emails = entities.get("emails", [])

                if not handles and not emails:
                    continue

                # Check if already enriched
                if entities.get("breach_correlations"):
                    continue

                enriched = enrich_entities_with_breaches(entities)
                if enriched.get("breach_correlations", {}).get("total_matches", 0) > 0:
                    obs.extracted_entities = enriched
                    result["enriched"] += 1

            except Exception as e:
                result["errors"].append(f"Enrichment error for obs #{obs.id}: {e}")

        db_session.commit()
        logger.info(f"[BreachEnrichment] Enriched {result['enriched']} / {result['observations_scanned']} observations")

    except Exception as e:
        db_session.rollback()
        result["errors"].append(f"Breach enrichment error: {e}")

    return result


def run_ingestion_cycle() -> Dict[str, Any]:
    """
    Execute one complete ingestion cycle:
    1. Forum parsing & ingestion
    2. Breach correlation enrichment for existing observations
    Returns combined results.
    """
    global _WORKER_STATUS

    try:
        from app.database import SessionLocal
        db_session = SessionLocal()
    except Exception as e:
        error = f"Could not create DB session: {e}"
        logger.error(error)
        return {"status": "error", "error": error}

    try:
        _WORKER_STATUS["is_running"] = True
        now = datetime.now(timezone.utc)

        # Step 1: Forum ingestion
        logger.info("[IngestionWorker] Starting forum ingestion...")
        forum_result = run_forum_ingestion(db_session)

        # Step 2: Breach enrichment
        logger.info("[IngestionWorker] Starting breach enrichment...")
        breach_result = run_breach_enrichment(db_session)

        # Step 3: Real-time OSINT feeds
        osint_result = {"observations_created": 0, "duplicates_skipped": 0, "errors": [], "feed_results": {}}
        try:
            logger.info("[IngestionWorker] Fetching real-time OSINT feeds...")
            from app.services.crawler.osint_feeds import fetch_all_feeds, ingest_feeds_to_db
            feeds_data = fetch_all_feeds()
            osint_result = ingest_feeds_to_db(db_session, feeds_data)
            logger.info(f"[IngestionWorker] OSINT feeds: {osint_result.get('observations_created',0)} new records")
        except Exception as e:
            logger.warning(f"[IngestionWorker] OSINT feed step failed (non-fatal): {e}")
            osint_result["errors"].append(str(e))

        # Step 4: Mock forum crawl disabled (synthetic data purged)
        mock_result = {"observations_created": 0, "duplicates_skipped": 0}

        combined = {
            "status": "success",
            "timestamp": now.isoformat(),
            "forum_ingestion": forum_result,
            "breach_enrichment": breach_result,
            "osint_feeds": osint_result,
            "mock_forum": mock_result,
            "summary": {
                "forum_posts_parsed": forum_result["posts_parsed"],
                "new_observations": forum_result["observations_created"],
                "duplicates_skipped": forum_result["duplicates_skipped"],
                "breach_correlations": forum_result["breach_correlations"],
                "alerts_generated": forum_result["alerts_generated"],
                "observations_enriched": breach_result["enriched"],
                "osint_new_records": osint_result.get("observations_created", 0),
                "mock_forum_records": mock_result.get("observations_created", 0),
            }
        }

        _WORKER_STATUS["last_run"] = now.isoformat()
        _WORKER_STATUS["last_result"] = combined
        _WORKER_STATUS["forum_posts_ingested"] += forum_result["observations_created"]
        _WORKER_STATUS["breach_correlations_found"] += forum_result["breach_correlations"]
        _WORKER_STATUS["total_runs"] += 1

        logger.info(f"[IngestionWorker] Cycle complete: {combined['summary']}")
        return combined

    except Exception as e:
        error = f"Ingestion cycle error: {e}"
        logger.error(error)
        _WORKER_STATUS["errors"].append(error)
        return {"status": "error", "error": error}
    finally:
        _WORKER_STATUS["is_running"] = False
        db_session.close()


def start_background_worker(interval_seconds: int = 300):
    """
    Start the background ingestion worker thread.
    Runs forum parsing + breach correlation on a configurable interval.
    """
    global _worker_thread, _stop_event

    if _worker_thread and _worker_thread.is_alive():
        logger.info("[IngestionWorker] Worker already running.")
        return

    _stop_event.clear()

    def worker_loop():
        logger.info(f"[IngestionWorker] Background worker started (interval: {interval_seconds}s)")
        while not _stop_event.is_set():
            try:
                result = run_ingestion_cycle()
                logger.info(f"[IngestionWorker] Cycle result: {result.get('status')}")
            except Exception as e:
                logger.error(f"[IngestionWorker] Worker loop error: {e}")

            _stop_event.wait(timeout=interval_seconds)

        logger.info("[IngestionWorker] Background worker stopped.")

    _worker_thread = threading.Thread(target=worker_loop, name="IngestionWorker", daemon=True)
    _worker_thread.start()


def stop_background_worker():
    """Stop the background ingestion worker."""
    global _stop_event
    _stop_event.set()
    logger.info("[IngestionWorker] Stop signal sent to background worker.")


# CLI entrypoint
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("\n" + "=" * 60)
    print("[*] DarkTrace Ingestion Worker — Manual Run")
    print("=" * 60)
    result = run_ingestion_cycle()
    print(json.dumps(result, indent=2, default=str))
