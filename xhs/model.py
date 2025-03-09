from datetime import datetime
from typing import List, Optional, Union
from pydantic import BaseModel, EmailStr, Field, validator
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSONB, CheckConstraint, Table
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.declarative import declared_attr
from pgvector.sqlalchemy import Vector

Base = declarative_base()

user_followers = Table(
    "user_followers",
    Base.metadata,
    Column("follower_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("followed_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("created_at", DateTime, default=datetime.utcnow)
)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=True)
    email = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系定义
    sent_messages = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender")
    received_messages = relationship("Message", foreign_keys="Message.receiver_id", back_populates="receiver")
    archives = relationship("Archive", back_populates="owner")
    followers = relationship(
        "User",
        secondary=user_followers,
        primaryjoin="User.id == user_followers.c.followed_id",
        back_populates="following"
    )
    following = relationship(
        "User",
        secondary=user_followers,
        primaryjoin="User.id == user_followers.c.follower_id",
        back_populates="followers"
    )

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="received_messages")

class Archive(Base):
    __tablename__ = "archives"
    
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_type = Column(String(50), nullable=False)
    path = Column(Text)
    metadata = Column(JSONB)
    graph = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="archives")

class EmbedFactory:
    @staticmethod
    def create_embed_model(dimension: int):
        class Embed(Base):
            __tablename__ = f"embed_{dimension}"
            
            id = Column(Integer, primary_key=True)
            source_type = Column(String(20), nullable=False)  # 'message' 或 'archive'
            source_id = Column(Integer, nullable=False)
            embedding = Column(Vector(dimension))
            created_at = Column(DateTime, default=datetime.utcnow)

            __table_args__ = (
                CheckConstraint(
                    "source_type IN ('message', 'archive')",
                    name=f"check_source_type_{dimension}"
                ),
                Index(f"idx_source_{dimension}", "source_type", "source_id")
            )

            @declared_attr
            def message_id(cls):
                return Column(Integer, ForeignKey("messages.id")) if dimension == 1024 else None  # 示例条件

            @declared_attr
            def archive_id(cls):
                return Column(Integer, ForeignKey("archives.id")) if dimension == 768 else None  # 示例条件

        return Embed

# 示例：创建不同维度的表
# Embed1024 = EmbedFactory.create_embed_model(1024)
# Embed768 = EmbedFactory.create_embed_model(768)

class UserBase(BaseModel):
    id: int
    name: str = Field(default=None, max_length=50)
    email: EmailStr = Field(..., max_length=100)
    created_at: datetime
    updated_at: datetime
    followers: List['User'] = []
    following: List['User'] = []

    class Config:
        orm_mode = True

class MessageBase(BaseModel):
    id: int
    content: str = Field(..., min_length=1)
    sender_id: int
    receiver_id: int
    created_at: datetime

    class Config:
        orm_mode = True

class ArchiveBase(BaseModel):
    id: int
    file_type: str = Field(..., max_length=50)
    metadata: dict
    graph: dict
    owner_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class EmbedBase(BaseModel):
    id: int
    source_type: str
    source_id: int
    embedding: List[float]
    created_at: datetime

    @validator('source_type')
    def validate_source_type(cls, v):
        if v not in ('message', 'archive'):
            raise ValueError("source_type must be 'message' or 'archive'")
        return v

    @validator('embedding')
    def validate_embedding(cls, v, values):
        if 'source_type' in values and values['source_type'] == 'message' and len(v) != 1024:
            raise ValueError("Message embedding must be 1024-dimensional")
        if 'source_type' in values and values['source_type'] == 'archive' and len(v) != 768:
            raise ValueError("Archive embedding must be 768-dimensional")
        return v

    class Config:
        orm_mode = True