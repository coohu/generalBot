from sqlalchemy.orm import Session
from . import models
from .models import EmbedFactory
from typing import List, Optional
import datetime

# User 相关操作
def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: dict):
    db_user = models.User(
        name=user.name,
        email=user.email,
        created_at=datetime.datetime.utcnow(),
        updated_at=datetime.datetime.utcnow()
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user_data: dict):
    db_user = get_user(db, user_id)
    for key, value in user_data.dict(exclude_unset=True).items():
        if value is not None:
            setattr(db_user, key, value)
    db_user.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int):
    db_user = get_user(db, user_id)
    db.delete(db_user)
    db.commit()

# 关注关系操作
def follow_user(db: Session, user_id: int, follower_id: int):
    user = get_user(db, user_id)
    follower = get_user(db, follower_id)
    
    if follower not in user.followers:
        user.followers.append(follower)
        db.commit()
    return user

def unfollow_user(db: Session, user_id: int, follower_id: int):
    user = get_user(db, user_id)
    follower = get_user(db, follower_id)
    
    if follower in user.followers:
        user.followers.remove(follower)
        db.commit()
    return user

# Message 相关操作
def create_message(db: Session, message: dict):
    db_message = models.Message(
        content=message.content,
        sender_id=message.sender_id,
        receiver_id=message.receiver_id,
        created_at=datetime.datetime.utcnow()
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

def get_message(db: Session, message_id: int):
    return db.query(models.Message).filter(models.Message.id == message_id).first()

def get_messages(db: Session, skip: int = 0, limit: int = 100, 
                sender_id: Optional[int] = None, receiver_id: Optional[int] = None):
    query = db.query(models.Message)
    if sender_id:
        query = query.filter(models.Message.sender_id == sender_id)
    if receiver_id:
        query = query.filter(models.Message.receiver_id == receiver_id)
    return query.offset(skip).limit(limit).all()

def update_message(db: Session, message_id: int, message_data: dict):
    db_message = get_message(db, message_id)
    for key, value in message_data.dict(exclude_unset=True).items():
        setattr(db_message, key, value)
    db.commit()
    db.refresh(db_message)
    return db_message

def delete_message(db: Session, message_id: int):
    db_message = get_message(db, message_id)
    db.delete(db_message)
    db.commit()

# Archive 相关操作
def create_archive(db: Session, archive: dict):
    db_archive = models.Archive(
        owner_id=archive.owner_id,
        file_type=archive.file_type,
        metadata=archive.metadata,
        graph=archive.graph,
        created_at=datetime.datetime.utcnow(),
        updated_at=datetime.datetime.utcnow()
    )
    db.add(db_archive)
    db.commit()
    db.refresh(db_archive)
    return db_archive

def get_archive(db: Session, archive_id: int):
    return db.query(models.Archive).filter(models.Archive.id == archive_id).first()

def get_archives(db: Session, skip: int = 0, limit: int = 100, owner_id: Optional[int] = None):
    query = db.query(models.Archive)
    if owner_id:
        query = query.filter(models.Archive.owner_id == owner_id)
    return query.offset(skip).limit(limit).all()

def update_archive(db: Session, archive_id: int, archive_data: dict):
    db_archive = get_archive(db, archive_id)
    for key, value in archive_data.dict(exclude_unset=True).items():
        setattr(db_archive, key, value)
    db_archive.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(db_archive)
    return db_archive

def delete_archive(db: Session, archive_id: int):
    db_archive = get_archive(db, archive_id)
    db.delete(db_archive)
    db.commit()

# Embed 相关操作
def get_embed_model(source_type: str):
    """根据 source_type 获取对应的 Embed 模型"""
    dimension = 1024 if source_type == "message" else 768
    return EmbedFactory.create_embed_model(dimension)

def create_embed(db: Session, embed_data: dict):
    EmbedModel = get_embed_model(embed_data.source_type)
    
    # 设置外键字段
    extra_fields = {}
    if embed_data.source_type == "message":
        extra_fields["message_id"] = embed_data.source_id
    else:
        extra_fields["archive_id"] = embed_data.source_id
    
    db_embed = EmbedModel(
        source_type=embed_data.source_type,
        source_id=embed_data.source_id,
        embedding=embed_data.embedding,
        created_at=datetime.datetime.utcnow(),
        **extra_fields
    )
    db.add(db_embed)
    db.commit()
    db.refresh(db_embed)
    return db_embed

def get_embed(db: Session, embed_id: int, source_type: str):
    EmbedModel = get_embed_model(source_type)
    return db.query(EmbedModel).filter(EmbedModel.id == embed_id).first()

def get_embeds(db: Session, skip: int = 0, limit: int = 100,
              source_type: Optional[str] = None, source_id: Optional[int] = None):
    if not source_type:
        raise ValueError("Must specify source_type for embedding queries")
    
    EmbedModel = get_embed_model(source_type)
    query = db.query(EmbedModel)
    
    if source_id:
        query = query.filter(EmbedModel.source_id == source_id)
    
    return query.offset(skip).limit(limit).all()

def update_embed(db: Session, embed_id: int, source_type: str, embed_data: dict):
    EmbedModel = get_embed_model(source_type)
    db_embed = db.query(EmbedModel).filter(EmbedModel.id == embed_id).first()
    
    for key, value in embed_data.dict(exclude_unset=True).items():
        setattr(db_embed, key, value)
    
    db.commit()
    db.refresh(db_embed)
    return db_embed

def delete_embed(db: Session, embed_id: int, source_type: str):
    EmbedModel = get_embed_model(source_type)
    db_embed = db.query(EmbedModel).filter(EmbedModel.id == embed_id).first()
    db.delete(db_embed)
    db.commit()