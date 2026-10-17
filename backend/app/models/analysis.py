from sqlalchemy import Boolean, Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON
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


class EvidenceItem(Base):
    """Atomic evidence with provenance and lineage for independent corroboration."""
    __tablename__ = "evidence_items"

    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(String, unique=True, index=True)
    assessment_id = Column(Integer, ForeignKey("attribution_assessments.id"), index=True)
    evidence_type = Column(String, index=True)
    subject_a = Column(String)
    subject_b = Column(String)
    value = Column(Text)
    source_id = Column(String, index=True)
    observed_at = Column(DateTime, nullable=True)
    first_seen = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, nullable=True)
    content_hash = Column(String, index=True)
    origin_id = Column(String, index=True)
    is_derived = Column(Boolean, default=False)
    raw_ref = Column(String, nullable=True)
    direction = Column(String, default="support")
    weight = Column(Float, default=0.0)
    details_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class AssessmentAuditLog(Base):
    __tablename__ = "assessment_audit_log"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("attribution_assessments.id"), index=True)
    action = Column(String, index=True)
    user = Column(String, default="system")
    reason = Column(Text, nullable=True)
    details_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
