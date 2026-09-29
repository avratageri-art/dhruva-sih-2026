from fastapi import FastAPI, Depends
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import actors, ingest, analysis, crawler, alerts, infra, deepdarkcti
from app.database import engine, get_db
from sqlalchemy.orm import Session
from app.models import actor, intelligence
from app.models.analysis import Source, Relationship, AttributionAssessment

# Create tables if not using Alembic currently
actor.Base.metadata.create_all(bind=engine)
intelligence.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="DHRUVA",
    version="1.0.0",
    description=(
        "Dark-web Hunt & Relationship-based Unified Verification Architecture: "
        "an AI-assisted platform for evidence-backed relationship analysis."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(actors.router, prefix="/api/actors")
app.include_router(ingest.router, prefix="/api/ingest")
app.include_router(analysis.router, prefix="/api/analysis")
app.include_router(crawler.router, prefix="/api/crawler")
app.include_router(alerts.router, prefix="/api/alerts")
app.include_router(infra.router, prefix="/api/infra")
app.include_router(deepdarkcti.router, prefix="/api/deepdarkcti")

# Aliases for graph specification compliance: /api/graph -> /api/analysis/graph
@app.get("/api/graph")
def alias_graph(
    db: Session = Depends(get_db),
    actor_id: Optional[int] = None,
    actor_ids: Optional[str] = None,
    depth: int = 2,
    confidence_min: float = 0.0,
):
    return analysis.get_graph_data(db=db, actor_id=actor_id, actor_ids=actor_ids, depth=depth, confidence_min=confidence_min)

@app.get("/api/graph/actor/{actor_id}")
def alias_graph_actor(actor_id: int, depth: int = 2, db: Session = Depends(get_db)):
    return analysis.get_graph_data(db=db, actor_id=actor_id, depth=depth)

@app.get("/api/graph/search")
def alias_graph_search(query: str, db: Session = Depends(get_db)):
    return analysis.search_graph(query=query, db=db)

@app.get("/api/graph/relationships")
def alias_graph_relationships(db: Session = Depends(get_db)):
    return analysis.get_relationships(db=db)


@app.get("/")
def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME}


@app.on_event("startup")
def startup_background_worker():
    """Auto-start the background forum & breach ingestion worker on server boot."""
    try:
        from app.services.crawler.ingestion_worker import start_background_worker
        start_background_worker(interval_seconds=300)
    except Exception as e:
        import logging
        logging.getLogger("startup").warning(f"Background worker auto-start failed: {e}")

@app.get("/api/dashboard")
def get_dashboard_stats(db: Session = Depends(get_db)):
    try:
        from app.models.actor import Actor, Handle, PGPIdentifier, Wallet
        from app.models.intelligence import Post, OnionService, SeedSource, Observation, Alert
        from app.models.analysis import Relationship, AttributionAssessment

        actors_count = db.query(Actor).count()
        handles_count = db.query(Handle).count()
        pgps_count = db.query(PGPIdentifier).count()
        wallets_count = db.query(Wallet).count()
        services_count = db.query(OnionService).count()
        relationships_count = db.query(Relationship).count()
        high_confidence = db.query(AttributionAssessment).filter(
            AttributionAssessment.score >= 0.85
        ).count()
        alerts_count = db.query(Alert).filter(Alert.acknowledged == 0).count()
        if alerts_count == 0:
            alerts_count = db.query(Actor).filter(Actor.confidence >= 0.70).count()

        seeds_count = db.query(SeedSource).count()
        observations_count = db.query(Observation).count()
        ddc_sources = db.query(SeedSource).filter(SeedSource.notes.like("%deepdarkCTI%")).count()
        ddc_enabled = db.query(SeedSource).filter(
            SeedSource.notes.like("%deepdarkCTI%"), SeedSource.authorized == 1
        ).count()
        ddc_obs = db.query(Observation).filter(
            Observation.collection_method == "DeepDarkCTI-Collector"
        ).count()

        return {
            "actors": actors_count,
            "handles": handles_count,
            "pgps": pgps_count,
            "wallets": wallets_count,
            "services": services_count,
            "relationships": relationships_count,
            "high_confidence": high_confidence,
            "alerts": alerts_count,
            "seeds": seeds_count,
            "observations": observations_count,
            "deepdarkcti": {
                "total_sources": ddc_sources,
                "enabled_sources": ddc_enabled,
                "observations": ddc_obs,
            },
        }
    except Exception as e:
        return {
            "actors": 0, "handles": 0, "pgps": 0, "wallets": 0,
            "services": 0, "relationships": 0, "high_confidence": 0, "alerts": 0,
            "seeds": 0, "observations": 0,
        }

@app.get("/api/model-status")
def model_status():
    """
    Returns the current AI model load status and pipeline description.
    The model is loaded lazily on first call to /api/analysis/assess.
    """
    try:
        from app.services.ai.attribution import _get_model, _MODEL_NAME, WEIGHTS
        model = _get_model()
        return {
            "model_name":  _MODEL_NAME,
            "model_loaded": model is not None,
            "embedding_dim": 384,
            "pipeline": [
                {"name": "Semantic Similarity",   "weight": WEIGHTS["semantic"],    "method": "sentence-transformers cosine"},
                {"name": "Stylometric Analysis",  "weight": WEIGHTS["stylometric"], "method": "9-feature NLP vector"},
                {"name": "Behavioural Analysis",  "weight": WEIGHTS["behavioural"], "method": "24-bin temporal histogram"},
                {"name": "Handle Overlap",        "weight": WEIGHTS["handle"],      "method": "Jaro-Winkler string similarity"},
                {"name": "Graph Correlation",     "weight": WEIGHTS["graph"],       "method": "Jaccard on shared infrastructure"},
            ],
            "status": "ready" if model is not None else "not_loaded_yet",
        }
    except Exception as e:
        return {"model_loaded": False, "error": str(e), "status": "unavailable"}
