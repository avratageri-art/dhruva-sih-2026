from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Actor(Base):
    __tablename__ = "actors"

    id = Column(Integer, primary_key=True, index=True)
    actor_name = Column(String, index=True)
    category = Column(String)
    description = Column(Text)
    status = Column(String)
    first_seen = Column(DateTime)
    last_seen = Column(DateTime)
    confidence = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    handles = relationship("Handle", back_populates="actor")
    pgp_identifiers = relationship("PGPIdentifier", back_populates="actor")
    wallets = relationship("Wallet", back_populates="actor")

class Handle(Base):
    __tablename__ = "handles"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("actors.id"))
    handle = Column(String, index=True)
    platform = Column(String)
    first_seen = Column(DateTime)
    last_seen = Column(DateTime)
    source_id = Column(Integer, ForeignKey("sources.id"))

    actor = relationship("Actor", back_populates="handles")

class PGPIdentifier(Base):
    __tablename__ = "pgp_identifiers"

    id = Column(Integer, primary_key=True, index=True)
    fingerprint = Column(String, index=True)
    actor_id = Column(Integer, ForeignKey("actors.id"))
    source_id = Column(Integer, ForeignKey("sources.id"))
    first_seen = Column(DateTime)
    last_seen = Column(DateTime)

    actor = relationship("Actor", back_populates="pgp_identifiers")

class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, index=True)
    address = Column(String, index=True)
    blockchain = Column(String)
    actor_id = Column(Integer, ForeignKey("actors.id"))
    source_id = Column(Integer, ForeignKey("sources.id"))
    first_seen = Column(DateTime)
    last_seen = Column(DateTime)

    actor = relationship("Actor", back_populates="wallets")
