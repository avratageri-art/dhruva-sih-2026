from app.database import Base
from .actor import Actor, Handle, PGPIdentifier, Wallet
from .intelligence import Post, OnionService, Domain, InfrastructureIndicator
from .analysis import Source, Relationship, AttributionAssessment

# This allows Base.metadata.create_all() to see all models
