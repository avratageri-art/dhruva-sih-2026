"""
deepdarkcti.py — API router for deepdarkCTI integration

Exposes:
    GET  /api/deepdarkcti/status          — importer + scheduler status
    POST /api/deepdarkcti/refresh         — fetch/refresh sources from GitHub
    GET  /api/deepdarkcti/sources         — list discovered sources with state
    POST /api/deepdarkcti/sources/{id}/enable   — analyst enables a source
    POST /api/deepdarkcti/sources/{id}/disable  — analyst disables a source
    POST /api/deepdarkcti/collect         — trigger one collection cycle manually
    POST /api/deepdarkcti/scheduler/start — start background scheduler
    POST /api/deepdarkcti/scheduler/stop  — stop background scheduler
    GET  /api/deepdarkcti/scheduler/status — scheduler runtime state
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.intelligence import SeedSource, Observation, Alert

logger = logging.getLogger("DeepDarkCTI-API")
router = APIRouter(tags=["DeepDarkCTI Integration"])

# ─── In-memory importer state ─────────────────────────────────────
_IMPORT_STATE = {
    "last_refresh_at": None,
    "last_refresh_result": None,
    "is_refreshing": False,
}


@router.get("/status")
def get_deepdarkcti_status(db: Session = Depends(get_db)):
    """
    Overall status of the deepdarkCTI integration:
    - Importer refresh state
    - Scheduler state
    - Source counts by status
    - Recent collection summary
    """
    from app.services.crawler.deepdarkcti_collector import get_scheduler_state

    total     = db.query(SeedSource).filter(SeedSource.notes.like("%deepdarkCTI%")).count()
    discovered= db.query(SeedSource).filter(
        SeedSource.notes.like("%deepdarkCTI%"), SeedSource.status == "DISCOVERED"
    ).count()
    enabled   = db.query(SeedSource).filter(
        SeedSource.notes.like("%deepdarkCTI%"), SeedSource.authorized == 1,
        SeedSource.status.in_(["ENABLED", "REACHABLE", "CONTENT_OBSERVED"])
    ).count()
    reachable = db.query(SeedSource).filter(
        SeedSource.notes.like("%deepdarkCTI%"), SeedSource.status.in_(["REACHABLE", "CONTENT_OBSERVED"])
    ).count()
    unreachable=db.query(SeedSource).filter(
        SeedSource.notes.like("%deepdarkCTI%"), SeedSource.status == "UNREACHABLE"
    ).count()
    failed    = db.query(SeedSource).filter(
        SeedSource.notes.like("%deepdarkCTI%"), SeedSource.status == "FAILED"
    ).count()
    obs_count = db.query(Observation).filter(
        Observation.collection_method == "DeepDarkCTI-Collector"
    ).count()

    return {
        "integration": "deepdarkCTI",
        "catalogue_url": "https://github.com/fastfire/deepdarkCTI",
        "importer": {
            "last_refresh_at": _IMPORT_STATE["last_refresh_at"],
            "is_refreshing": _IMPORT_STATE["is_refreshing"],
            "last_result_summary": {
                "total_sources": _IMPORT_STATE["last_refresh_result"].get("total_sources") if _IMPORT_STATE["last_refresh_result"] else None,
                "by_category": {
                    k: v.get("count") for k, v in (_IMPORT_STATE["last_refresh_result"] or {}).get("by_category", {}).items()
                },
                "errors": (_IMPORT_STATE["last_refresh_result"] or {}).get("errors", []),
            } if _IMPORT_STATE["last_refresh_result"] else None,
        },
        "scheduler": get_scheduler_state(),
        "sources": {
            "total":       total,
            "discovered":  discovered,
            "enabled":     enabled,
            "reachable":   reachable,
            "unreachable": unreachable,
            "failed":      failed,
        },
        "observations": {
            "total_from_deepdarkcti": obs_count,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/refresh")
def refresh_sources(
    categories: Optional[List[str]] = Body(None, embed=True),
    db: Session = Depends(get_db),
):
    """
    Fetch/refresh deepdarkCTI source lists from GitHub.
    Upserts into SeedSource table with status=DISCOVERED (never auto-enables).
    Analyst must explicitly enable sources before collection starts.
    """
    from app.services.crawler.deepdarkcti_importer import refresh_all, upsert_sources_to_db, DEEPDARKCTI_FILES

    if _IMPORT_STATE["is_refreshing"]:
        raise HTTPException(status_code=409, detail="Refresh already in progress")

    _IMPORT_STATE["is_refreshing"] = True
    try:
        # Fetch from GitHub
        logger.info("[API] Starting deepdarkCTI refresh...")
        result = refresh_all(timeout=25)
        _IMPORT_STATE["last_refresh_at"] = result["fetched_at"]

        # Upsert into DB
        if result["sources"]:
            stats = upsert_sources_to_db(result["sources"], db, result["fetched_at"])
            result["db_stats"] = stats
        else:
            result["db_stats"] = {"created": 0, "updated": 0, "skipped": 0}

        _IMPORT_STATE["last_refresh_result"] = result

        return {
            "status": "refreshed",
            "fetched_at": result["fetched_at"],
            "total_sources_fetched": result["total_sources"],
            "db_created": result["db_stats"]["created"],
            "db_updated": result["db_stats"]["updated"],
            "by_category": {k: v["count"] for k, v in result["by_category"].items()},
            "errors": result["errors"],
            "note": (
                "Sources have been imported with status=DISCOVERED. "
                "Use POST /api/deepdarkcti/sources/{id}/enable to authorize collection. "
                "catalogue_status from deepdarkCTI does NOT automatically mean the source is reachable."
            ),
        }
    except Exception as e:
        logger.exception(f"[API] Refresh failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _IMPORT_STATE["is_refreshing"] = False


@router.get("/sources")
def list_sources(
    category: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    List all deepdarkCTI-sourced seeds with their DarkTrace collection state.
    Includes both catalogue_status (from deepdarkCTI) and collection_status (from DarkTrace).
    """
    import re
    q = db.query(SeedSource).filter(SeedSource.notes.like("%deepdarkCTI%"))
    if category:
        q = q.filter(SeedSource.category == category.upper())
    if status:
        q = q.filter(SeedSource.status == status.upper())

    total = q.count()
    seeds = q.order_by(SeedSource.last_seen.desc()).offset(offset).limit(limit).all()

    def parse_catalogue_status(notes: str) -> str:
        if not notes:
            return "UNKNOWN"
        m = re.search(r"catalogue_status=(\w+)", notes)
        return m.group(1) if m else "UNKNOWN"

    obs_counts = {}
    for s in seeds:
        obs_counts[s.id] = db.query(Observation).filter(
            Observation.seed_id == s.id
        ).count()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "sources": [{
            "id":                   s.id,
            "source_name":          s.name,
            "source_url":           s.reference,
            "category":             s.category,
            "is_onion":             ".onion" in (s.reference or ""),
            "catalogue_source":     "deepdarkCTI",
            "catalogue_status":     parse_catalogue_status(s.notes),
            "collection_status":    s.status,           # DarkTrace lifecycle
            "authorized":           bool(s.authorized),
            "collection_frequency": s.collection_frequency,
            "reliability":          s.reliability,
            "first_seen":           s.first_seen.isoformat() if s.first_seen else None,
            "last_seen":            s.last_seen.isoformat() if s.last_seen else None,
            "observation_count":    obs_counts.get(s.id, 0),
            "error_count":          s.error_count or 0,
            "notes":                s.notes,
        } for s in seeds]
    }


@router.post("/sources/{seed_id}/enable")
def enable_source(seed_id: int, db: Session = Depends(get_db)):
    """
    Analyst action: authorize and enable a deepdarkCTI source for real collection.
    Changes status DISCOVERED → ENABLED and sets authorized=1.
    This is the required human-in-the-loop gate before collection starts.
    """
    seed = db.query(SeedSource).filter(SeedSource.id == seed_id).first()
    if not seed:
        raise HTTPException(status_code=404, detail="Seed source not found")
    if "deepdarkCTI" not in (seed.notes or ""):
        raise HTTPException(status_code=400, detail="Not a deepdarkCTI source")

    seed.status = "ENABLED"
    seed.authorized = 1
    seed.collection_frequency = "1h"
    db.commit()

    return {
        "status": "enabled",
        "seed_id": seed_id,
        "source_url": seed.reference,
        "collection_status": seed.status,
        "note": "Source is now authorized for collection. It will be picked up in the next collection cycle.",
    }


@router.post("/sources/{seed_id}/disable")
def disable_source(seed_id: int, db: Session = Depends(get_db)):
    """Analyst action: disable a source from collection."""
    seed = db.query(SeedSource).filter(SeedSource.id == seed_id).first()
    if not seed:
        raise HTTPException(status_code=404, detail="Seed source not found")

    seed.status = "DISABLED"
    seed.authorized = 0
    db.commit()
    return {"status": "disabled", "seed_id": seed_id}


@router.post("/collect")
def trigger_collection(
    max_sources: int = Body(3, embed=True),
    categories: Optional[List[str]] = Body(None, embed=True),
    db: Session = Depends(get_db),
):
    """
    Manually trigger one deepdarkCTI collection cycle.
    Only collects ENABLED (analyst-authorized) sources.
    Performs real HTTP requests through existing DarkCrawler.
    """
    from app.services.crawler.deepdarkcti_collector import run_collection_cycle

    logger.info(f"[API] Manual collection triggered: max_sources={max_sources}")
    result = run_collection_cycle(db, max_sources=max_sources, categories=categories)

    return {
        "status": "completed",
        "cycle": result,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/scheduler/start")
def start_scheduler(interval_seconds: int = Body(300, embed=True)):
    """Start the background collection scheduler."""
    from app.services.crawler.deepdarkcti_collector import start_scheduler as _start

    ok = _start(interval_seconds=interval_seconds)
    if not ok:
        raise HTTPException(status_code=409, detail="Scheduler already running")
    return {
        "status": "started",
        "interval_seconds": interval_seconds,
        "note": f"Scheduler will run collection cycles every {interval_seconds}s for ENABLED deepdarkCTI sources.",
    }


@router.post("/scheduler/stop")
def stop_scheduler():
    """Stop the background collection scheduler."""
    from app.services.crawler.deepdarkcti_collector import stop_scheduler as _stop
    _stop()
    return {"status": "stop_requested"}


@router.get("/scheduler/status")
def scheduler_status():
    """Get real-time scheduler state."""
    from app.services.crawler.deepdarkcti_collector import get_scheduler_state
    return get_scheduler_state()


@router.get("/sources/{seed_id}/observations")
def get_source_observations(seed_id: int, limit: int = 20, db: Session = Depends(get_db)):
    """Get observations collected from a specific deepdarkCTI source."""
    seed = db.query(SeedSource).filter(SeedSource.id == seed_id).first()
    if not seed:
        raise HTTPException(status_code=404, detail="Seed not found")

    obs_list = db.query(Observation).filter(
        Observation.seed_id == seed_id
    ).order_by(Observation.collected_at.desc()).limit(limit).all()

    return {
        "seed_id": seed_id,
        "source_url": seed.reference,
        "source_name": seed.name,
        "collection_status": seed.status,
        "observations": [{
            "id": o.id,
            "collected_at": o.collected_at.isoformat() if o.collected_at else None,
            "status": o.status,
            "content_sha256": o.content_sha256,
            "blockchain_tx_hash": o.blockchain_tx_hash,
            "entities_summary": {
                k: len(v) for k, v in (o.extracted_entities or {}).items()
                if isinstance(v, list) and v
            },
            "candidate_actor_id": o.candidate_actor_id,
            "candidate_confidence": o.candidate_confidence,
            "collection_method": o.collection_method,
        } for o in obs_list]
    }
