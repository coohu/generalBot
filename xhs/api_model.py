from pydantic import BaseModel, EmailStr, Field, Json, ValidationError
from typing import List, Optional, Any

class UserCreate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    email: EmailStr = Field(..., max_length=100)
    passwd: str = Field(..., max_length=50)

class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = Field(None, max_length=100)
    passwd: Optional[str] = Field(None, max_length=50)
    config: Optional[Json[Any]] = Field(None)

class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1)
    sender_id: int
    receiver_id: int

class ArchiveCreate(BaseModel):
    file_type: str = Field(..., max_length=50)
    filemeta: Optional[dict]
    graph: Optional[dict]
    owner_id: int

class ArchiveUpdate(BaseModel):
    file_type: Optional[str] = Field(None, max_length=50)
    filemeta: Optional[dict]
    graph: Optional[dict]

class EmbedCreate(BaseModel):
    source_type: str
    source_id: int

class ChatCreate(BaseModel):
    msg: str = Field(..., min_length=1)
