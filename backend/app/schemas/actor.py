from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class HandleBase(BaseModel):
    handle: str
    platform: Optional[str] = None
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None

class HandleResponse(HandleBase):
    id: int
    actor_id: Optional[int] = None
    class Config:
        from_attributes = True

class PGPIdentifierBase(BaseModel):
    fingerprint: str
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None

class PGPIdentifierResponse(PGPIdentifierBase):
    id: int
    actor_id: Optional[int] = None
    class Config:
        from_attributes = True

class WalletBase(BaseModel):
    address: str
    blockchain: Optional[str] = None
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None

class WalletResponse(WalletBase):
    id: int
    actor_id: Optional[int] = None
    class Config:
        from_attributes = True

class ActorBase(BaseModel):
    actor_name: str
    category: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    confidence: Optional[float] = None

class ActorResponse(ActorBase):
    id: int
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    handles: List[HandleResponse] = []
    pgp_identifiers: List[PGPIdentifierResponse] = []
    wallets: List[WalletResponse] = []
    
    class Config:
        from_attributes = True
