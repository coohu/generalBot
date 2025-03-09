async def main():
    MongoDB.init_db(uri="mongodb://localhost:27017", db_name="chat_app")
    
    await User.create_indexes()
    await Message.create_indexes()

    alice = User(name="Alice", age=30, email="alice@example.com")
    await alice.save()
    bob = User(name="Bob", age=25, email="bob@example.com")
    await bob.save()

    msg1 = Message(sender_id=alice.id, receiver_id=bob.id, content="Hello Bob!")
    await msg1.save()
    msg2 = Message(sender_id=bob.id, receiver_id=alice.id, content="Hi Alice!")
    await msg2.save()

    conversation = await Message.find_conversation(alice.id, bob.id)
    print(f"Conversation between Alice and Bob: {conversation}")

    adults = await User.find_adults(min_age=20)
    print(f"Adult users: {adults}")


async def demo_soft_delete():
    MongoDB.init_db("mongodb://localhost:27017", "test_db")
    
    user = User(name="Charlie", age=28, email="charlie@example.com")
    await user.save()
    print("User Created:", user)

    await user.delete()
    print("User Soft-Deleted:", user.is_deleted, user.deleted_at)

    found_user = await User.get(user.id)
    print("Found User (default):", found_user)  # 输出 None

    found_user = await User.get(user.id, include_deleted=True)
    print("Found User (include_deleted):", found_user)

    await user.restore()
    print("User Restored:", user.is_deleted)

    await User.hard_delete(user.id)
    print("User Hard-Deleted")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())





from datetime import datetime
from typing import List, Optional, Union
from pydantic import BaseModel, EmailStr, Field, validator

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

为这个model.py 模块写一个 fastapi  crud 接口模块  main.py 目标数据库为pgvector