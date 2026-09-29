import sys
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.intelligence import Intelligence
from app.models.actor import Actor

# Add ai module to path (lives at project root /ai/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

try:
    from ai.entity_extraction import extraction_pipeline
    _HAS_AI = True
except ImportError:
    _HAS_AI = False

router = APIRouter()

RANSOMWATCH_URL = "https://raw.githubusercontent.com/joshhighet/ransomwatch/main/posts.json"

@router.post("/live")
async def fetch_live_intelligence(db: Session = Depends(get_db)):
    """
    Fetches real-time intelligence from an open-source ransomware telemetry feed.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(RANSOMWATCH_URL, timeout=10.0)
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch live intel: {str(e)}")
        
    ingested_count = 0
    # Process the latest 20 posts to avoid overloading the DB
    for post in data[:20]:
        post_title = post.get("post_title", "")
        group_name = post.get("group_name", "Unknown")
        
        if not post_title:
            continue
            
        # Check if we already have this actor by name
        actor = db.query(Actor).filter(Actor.actor_name == group_name).first()
        if not actor:
            actor = Actor(actor_name=group_name, category="Ransomware Operator", status="ACTIVE")
            db.add(actor)
            db.commit()
            db.refresh(actor)
            
        # Extract entities from the post title
        entities = extraction_pipeline.extract_all(post_title) if _HAS_AI else []
        
        # Save intelligence
        intel = Intelligence(
            actor_id=actor.id,
            source_platform="Ransomwatch (Live)",
            raw_text=post_title,
            extracted_entities=entities
        )
        db.add(intel)
        ingested_count += 1
        
    db.commit()
    return {"status": "success", "ingested": ingested_count, "source": "Ransomwatch Live"}
