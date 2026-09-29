from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON
from datetime import datetime
from app.database import Base

class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    type = Column(String)
    reference = Column(String)
    reliability = Column(Float)
    collected_at = Column(DateTime, default=datetime.utcnow)

class Relationship(Base):
    __tablename__ = "relationships"

    id = Column(Integer, primary_key=True, index=True)
    source_entity_type = Column(String)
    source_entity_id = Column(Integer)
    relationship_type = Column(String)
    target_entity_type = Column(String)
    target_entity_id = Column(Integer)
    confidence = Column(Float)
    evidence = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class AttributionAssessment(Base):
    __tablename__ = "attribution_assessments"

    id = Column(Integer, primary_key=True, index=True)
    actor_a = Column(Integer, ForeignKey("actors.id"))
    actor_b = Column(Integer, ForeignKey("actors.id"))
    score = Column(Float)
    confidence_level = Column(String)
    evidence_json = Column(JSON)
    negative_evidence_json = Column(JSON)
    explanation = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
