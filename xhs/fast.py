from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
import model  # 导入原模型模块
from controller import * as ctl
from database import SessionLocal, engine

# 创建FastAPI应用
app = FastAPI()

# 数据库依赖
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 定义输入模型（用于创建和更新操作）
class UserCreate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    email: EmailStr = Field(..., max_length=100)

class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = Field(None, max_length=100)

class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1)
    sender_id: int
    receiver_id: int

class MessageUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1)

class ArchiveCreate(BaseModel):
    file_type: str = Field(..., max_length=50)
    metadata: dict
    graph: dict
    owner_id: int

class ArchiveUpdate(BaseModel):
    file_type: Optional[str] = Field(None, max_length=50)
    metadata: Optional[dict]
    graph: Optional[dict]

class EmbedCreate(BaseModel):
    source_type: str
    source_id: int
    embedding: List[float]

class EmbedUpdate(BaseModel):
    embedding: Optional[List[float]]

# 用户相关接口
@app.post("/users/", response_model=model.UserBase)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = ctl.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return ctl.create_user(db=db, user=user)

@app.get("/users/", response_model=List[model.UserBase])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = ctl.get_users(db, skip=skip, limit=limit)
    return users

@app.get("/users/{user_id}", response_model=model.UserBase)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = ctl.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.put("/users/{user_id}", response_model=model.UserBase)
def update_user(user_id: int, user: UserUpdate, db: Session = Depends(get_db)):
    db_user = ctl.get_user(db, user_id=user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email:
        existing_user = ctl.get_user_by_email(db, email=user.email)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(status_code=400, detail="Email already in use")
    return ctl.update_user(db=db, user_id=user_id, user=user)

@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = ctl.get_user(db, user_id=user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    ctl.delete_user(db=db, user_id=user_id)
    return {"detail": "User deleted"}

# 用户关注相关接口
@app.post("/users/{user_id}/follow/{follower_id}", response_model=model.UserBase)
def follow_user(user_id: int, follower_id: int, db: Session = Depends(get_db)):
    if user_id == follower_id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    user = ctl.get_user(db, user_id)
    follower = ctl.get_user(db, follower_id)
    if not user or not follower:
        raise HTTPException(status_code=404, detail="User not found")
    return ctl.follow_user(db, user_id, follower_id)

@app.delete("/users/{user_id}/follow/{follower_id}", response_model=model.UserBase)
def unfollow_user(user_id: int, follower_id: int, db: Session = Depends(get_db)):
    user = ctl.get_user(db, user_id)
    follower = ctl.get_user(db, follower_id)
    if not user or not follower:
        raise HTTPException(status_code=404, detail="User not found")
    return ctl.unfollow_user(db, user_id, follower_id)

@app.get("/users/{user_id}/followers", response_model=List[model.UserBase])
def get_followers(user_id: int, db: Session = Depends(get_db)):
    user = ctl.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.followers

@app.get("/users/{user_id}/following", response_model=List[model.UserBase])
def get_following(user_id: int, db: Session = Depends(get_db)):
    user = ctl.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.following

# 消息相关接口
@app.post("/messages/", response_model=model.MessageBase)
def create_message(message: MessageCreate, db: Session = Depends(get_db)):
    sender = ctl.get_user(db, message.sender_id)
    receiver = ctl.get_user(db, message.receiver_id)
    if not sender or not receiver:
        raise HTTPException(status_code=404, detail="User not found")
    return ctl.create_message(db=db, message=message)

@app.get("/messages/", response_model=List[model.MessageBase])
def read_messages(
    skip: int = 0,
    limit: int = 100,
    sender_id: Optional[int] = None,
    receiver_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    return ctl.get_messages(
        db, 
        skip=skip, 
        limit=limit,
        sender_id=sender_id,
        receiver_id=receiver_id
    )

@app.get("/messages/{message_id}", response_model=model.MessageBase)
def read_message(message_id: int, db: Session = Depends(get_db)):
    db_message = ctl.get_message(db, message_id=message_id)
    if db_message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    return db_message

@app.put("/messages/{message_id}", response_model=model.MessageBase)
def update_message(
    message_id: int, 
    message: MessageUpdate, 
    db: Session = Depends(get_db)
):
    db_message = ctl.get_message(db, message_id=message_id)
    if not db_message:
        raise HTTPException(status_code=404, detail="Message not found")
    return ctl.update_message(db=db, message_id=message_id, message=message)

@app.delete("/messages/{message_id}")
def delete_message(message_id: int, db: Session = Depends(get_db)):
    db_message = ctl.get_message(db, message_id=message_id)
    if not db_message:
        raise HTTPException(status_code=404, detail="Message not found")
    ctl.delete_message(db=db, message_id=message_id)
    return {"detail": "Message deleted"}

# 归档文件相关接口
@app.post("/archives/", response_model=model.ArchiveBase)
def create_archive(archive: ArchiveCreate, db: Session = Depends(get_db)):
    owner = ctl.get_user(db, archive.owner_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    return ctl.create_archive(db=db, archive=archive)

@app.get("/archives/", response_model=List[model.ArchiveBase])
def read_archives(
    skip: int = 0,
    limit: int = 100,
    owner_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    return ctl.get_archives(
        db, 
        skip=skip, 
        limit=limit,
        owner_id=owner_id
    )

@app.get("/archives/{archive_id}", response_model=model.ArchiveBase)
def read_archive(archive_id: int, db: Session = Depends(get_db)):
    db_archive = ctl.get_archive(db, archive_id=archive_id)
    if not db_archive:
        raise HTTPException(status_code=404, detail="Archive not found")
    return db_archive

@app.put("/archives/{archive_id}", response_model=model.ArchiveBase)
def update_archive(
    archive_id: int, 
    archive: ArchiveUpdate, 
    db: Session = Depends(get_db)
):
    db_archive = ctl.get_archive(db, archive_id=archive_id)
    if not db_archive:
        raise HTTPException(status_code=404, detail="Archive not found")
    return ctl.update_archive(db=db, archive_id=archive_id, archive=archive)

@app.delete("/archives/{archive_id}")
def delete_archive(archive_id: int, db: Session = Depends(get_db)):
    db_archive = ctl.get_archive(db, archive_id=archive_id)
    if not db_archive:
        raise HTTPException(status_code=404, detail="Archive not found")
    ctl.delete_archive(db=db, archive_id=archive_id)
    return {"detail": "Archive deleted"}

# 嵌入相关接口
@app.post("/embeds/", response_model=model.EmbedBase)
def create_embed(embed: EmbedCreate, db: Session = Depends(get_db)):
    # 验证source存在性
    if embed.source_type == "message":
        source = ctl.get_message(db, embed.source_id)
    elif embed.source_type == "archive":
        source = ctl.get_archive(db, embed.source_id)
    else:
        raise HTTPException(status_code=400, detail="Invalid source_type")
    
    if not source:
        raise HTTPException(
            status_code=404,
            detail=f"{embed.source_type} with id {embed.source_id} not found"
        )
    return ctl.create_embed(db=db, embed=embed)

@app.get("/embeds/", response_model=List[model.EmbedBase])
def read_embeds(
    skip: int = 0,
    limit: int = 100,
    source_type: Optional[str] = None,
    source_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    return ctl.get_embeds(
        db,
        skip=skip,
        limit=limit,
        source_type=source_type,
        source_id=source_id
    )

@app.get("/embeds/{embed_id}", response_model=model.EmbedBase)
def read_embed(embed_id: int, db: Session = Depends(get_db)):
    db_embed = ctl.get_embed(db, embed_id=embed_id)
    if not db_embed:
        raise HTTPException(status_code=404, detail="Embed not found")
    return db_embed

@app.put("/embeds/{embed_id}", response_model=model.EmbedBase)
def update_embed(
    embed_id: int,
    embed: EmbedUpdate,
    db: Session = Depends(get_db)
):
    db_embed = ctl.get_embed(db, embed_id=embed_id)
    if not db_embed:
        raise HTTPException(status_code=404, detail="Embed not found")
    return ctl.update_embed(db=db, embed_id=embed_id, embed=embed)

@app.delete("/embeds/{embed_id}")
def delete_embed(embed_id: int, db: Session = Depends(get_db)):
    db_embed = ctl.get_embed(db, embed_id=embed_id)
    if not db_embed:
        raise HTTPException(status_code=404, detail="Embed not found")
    ctl.delete_embed(db=db, embed_id=embed_id)
    return {"detail": "Embed deleted"}