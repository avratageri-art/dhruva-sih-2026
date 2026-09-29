from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PostBase(BaseModel):
    platform: str
    content: str
    language: Optional[str] = None

class PostResponse(PostBase):
    id: int
    actor_id: Optional[int] = None
    timestamp: Optional[datetime] = None
    class Config:
        from_attributes = True

class OnionServiceBase(BaseModel):
    address: str
    title: Optional[str] = None
    status: Optional[str] = None

class OnionServiceResponse(OnionServiceBase):
    id: int
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    class Config:
        from_attributes = True
