from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float
from app.database import Base
from datetime import datetime

class Intelligence(Base):
    __tablename__ = "intelligence"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("actors.id"), nullable=True)
    source_platform = Column(String)
    raw_text = Column(Text)
    extracted_entities = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("actors.id"), nullable=True)
    handle_id = Column(Integer, ForeignKey("handles.id"), nullable=True)
    platform = Column(String, index=True)
    content = Column(Text)
    timestamp = Column(DateTime)
    language = Column(String)
    embedding_reference = Column(String)
    source_id = Column(Integer, ForeignKey("sources.id"))

class OnionService(Base):
    __tablename__ = "onion_services"

    id = Column(Integer, primary_key=True, index=True)
    address = Column(String, index=True)
    title = Column(String)
    first_seen = Column(DateTime)
    last_seen = Column(DateTime)
    status = Column(String)
    metadata_ = Column("metadata", JSON)
    source_id = Column(Integer, ForeignKey("sources.id"))

class Domain(Base):
    __tablename__ = "domains"

    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String, index=True)
    actor_id = Column(Integer, ForeignKey("actors.id"), nullable=True)
    source_id = Column(Integer, ForeignKey("sources.id"))

class InfrastructureIndicator(Base):
    __tablename__ = "infrastructure_indicators"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("onion_services.id"), nullable=True)
    indicator_type = Column(String)
    value = Column(String)
    confidence = Column(Float)
    observed_at = Column(DateTime, default=datetime.utcnow)
    source_id = Column(Integer, ForeignKey("sources.id"))

class SeedSource(Base):
    __tablename__ = "seed_sources"

    id = Column(Integer, primary_key=True, index=True)
    reference = Column(String, index=True)
    name = Column(String)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    # DarkTrace lifecycle: DISCOVERED|SELECTED|ENABLED|COLLECTING|REACHABLE|CONTENT_OBSERVED|UNREACHABLE|FAILED|DISABLED
    status = Column(String, default="ACTIVE")
    collection_frequency = Column(String, default="1h")
    authorized = Column(Integer, default=1)  # 1 for authorized/controlled, 0 for unauthorized
    category = Column(String, default="CONTROLLED")  # CONTROLLED, AUTHORIZED, SYNTHETIC, FORUM, MARKET, etc.
    reliability = Column(Float, default=0.85)
    notes = Column(Text, nullable=True)
    error_count = Column(Integer, default=0)
    observation_count = Column(Integer, default=0)
    # DeepDarkCTI integration fields (separate from DarkTrace collection status)
    catalogue_source = Column(String, nullable=True)   # e.g. "deepdarkCTI"
    catalogue_status = Column(String, nullable=True)   # ONLINE/OFFLINE from catalogue (NOT DarkTrace status)
    last_collection_attempt = Column(DateTime, nullable=True)
    last_collection_success = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)

class Observation(Base):
    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String, index=True)
    source_type = Column(String, default="onion-service")
    seed_id = Column(Integer, ForeignKey("seed_sources.id"), nullable=True)
    service = Column(String, index=True)
    title = Column(String, nullable=True)
    content = Column(Text, nullable=True)
    raw_reference = Column(String, nullable=True)
    collection_method = Column(String, default="OnionCrawlerAdapter")
    reliability = Column(Float, default=0.85)
    timestamp = Column(DateTime, default=datetime.utcnow)
    collected_at = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)
    extracted_entities = Column(JSON, nullable=True)
    content_sha256 = Column(String, index=True, nullable=True)
    blockchain_tx_hash = Column(String, nullable=True)
    blockchain_anchor_time = Column(DateTime, nullable=True)
    status = Column(String, default="UNRESOLVED")  # UNRESOLVED, LINKED, ARCHIVED
    candidate_actor_id = Column(Integer, ForeignKey("actors.id"), nullable=True)
    candidate_confidence = Column(Float, nullable=True)
    candidate_notes = Column(Text, nullable=True)

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String, index=True)
    title = Column(String)
    description = Column(Text)
    severity = Column(String, default="HIGH")  # CRITICAL, HIGH, MEDIUM, LOW
    actor_id = Column(Integer, ForeignKey("actors.id"), nullable=True)
    observation_id = Column(Integer, ForeignKey("observations.id"), nullable=True)
    entity_type = Column(String, nullable=True)
    entity_value = Column(String, nullable=True)
    confidence = Column(Float, default=0.85)
    created_at = Column(DateTime, default=datetime.utcnow)
    acknowledged = Column(Integer, default=0)

