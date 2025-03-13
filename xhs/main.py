from fastapi import Depends, FastAPI, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, EmailStr, Field, Json, ValidationError
from contextlib import asynccontextmanager
from typing import List, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime
import controller as ctl
from api_model import *
from time import time
import asyncio
import pprint
import model  
import env

@asynccontextmanager
async def lifespan(app: FastAPI):
    while True:
        now = time()
        print('lifespan  ->  cleanup_expired_cache(): ', now)
        keys = list(ctl.glb_cache.keys())
        for key in keys:
            if key in ctl.glb_cache:
                if (now - ctl.glb_cache[key]['ts']) > env.CACHE_TIMEOUT_SECONDS :
                    del ctl.glb_cache[key]
        await asyncio.sleep(env.CACHE_CLEANUP_INTERVAL_SECONDS)

app = FastAPI()

@app.get("/")
def index():
    return {"detail":"hi"}

@app.post("/register", response_model=model.UserBase)
def register(user: UserCreate):
    db_user = ctl.get_user_by_email(email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email 已经注册！")
    return ctl.create_user(user)

@app.post("/login")
async def login(user: UserCreate):
    db_user = ctl.get_user_by_email(email=user.email)
    if not db_user or not ctl.pwd_context.verify(user.passwd, db_user.passwd):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    asyncio.create_task(ctl.user_cache(db_user))
    token = ctl.create_jwt_token({"sub": {"email":db_user.email,"id":db_user.id}})
    return {"access_token": token, "token_type": "Bearer"}

@app.post("/logout")
def logout(user: dict = Depends(ctl.get_current_user)):
    token = ctl.create_jwt_token({"sub": {"email":user.email,"id":user.id}})  
    ctl.revoked_tokens.add(token)  
    if user.id in ctl.users_ctx:
        del ctl.users_ctx[user.id]
    return {"detail": "退出成功"}

@app.get("/users", response_model=List[model.UserBase])
def read_users(skip: int = 0, limit: int = 100, user: dict = Depends(ctl.get_current_user)):
    users = ctl.get_users(skip=skip, limit=limit)
    return users

@app.get("/users/{user_id}", response_model=model.UserBase)
def read_user(user_id: int, user: dict = Depends(ctl.get_current_user)):
    db_user = ctl.get_user(user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.put("/users/{user_id}", response_model=model.UserBase)
def update_user(user_id: int, user: UserUpdate, auth: dict = Depends(ctl.get_current_user)):
    db_user = ctl.get_user(user_id=user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email:
        existing_user = ctl.get_user_by_email(email=user.email)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(status_code=400, detail="Email already in use")
    return ctl.update_user(user=db_user, user_data=user)

@app.delete("/users/{user_id}")
def delete_user(user_id: int, auth: dict = Depends(ctl.get_current_user)):
    db_user = ctl.get_user(user_id=user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="未找到该用户！")
    if user_id != auth.get("id"):
        raise HTTPException(status_code=403, detail="权限不足！")
    ctl.delete_user(user_id=user_id)
    return {"detail": "User deleted"}

@app.post("/users/{user_id}/follow/{follower_id}", response_model=model.UserBase)
def follow_user(user_id: int, follower_id: int, user: dict = Depends(ctl.get_current_user)):
    if user_id == follower_id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    user = ctl.get_user(user_id)
    follower = ctl.get_user(follower_id)
    if not user or not follower:
        raise HTTPException(status_code=404, detail="User not found")
    return ctl.follow_user(user_id, follower_id)

@app.delete("/users/{user_id}/follow/{follower_id}", response_model=model.UserBase)
def unfollow_user(user_id: int, follower_id: int, user: dict = Depends(ctl.get_current_user)):
    user = ctl.get_user(user_id)
    follower = ctl.get_user(follower_id)
    if not user or not follower:
        raise HTTPException(status_code=404, detail="User not found")
    return ctl.unfollow_user(user_id, follower_id)

@app.get("/users/{user_id}/followers", response_model=List[model.UserBase])
def get_followers(user_id: int, user: dict = Depends(ctl.get_current_user)):
    user = ctl.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.followers

@app.get("/users/{user_id}/following", response_model=List[model.UserBase])
def get_following(user_id: int, user: dict = Depends(ctl.get_current_user)):
    user = ctl.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.following

@app.post("/messages", response_model=model.MessageBase)
def create_message(message: MessageCreate, user: dict = Depends(ctl.get_current_user)):
    sender = ctl.get_user(message.sender_id)
    receiver = ctl.get_user(message.receiver_id)
    if not sender or not receiver:
        raise HTTPException(status_code=404, detail="User not found")
    return ctl.create_message(message=message)

@app.get("/messages", response_model=List[model.MessageBase])
def read_messages(
    skip: int = 0,
    limit: int = 100,
    sender_id: Optional[int] = None,
    receiver_id: Optional[int] = None,
    user: dict = Depends(ctl.get_current_user),
):
    return ctl.get_messages(skip=skip, limit=limit,sender_id=sender_id,receiver_id=receiver_id)

@app.get("/messages/{message_id}", response_model=model.MessageBase)
def read_message(message_id: int, user: dict = Depends(ctl.get_current_user)):
    db_message = ctl.get_message(message_id=message_id)
    if db_message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    return db_message

@app.delete("/messages/{message_id}")
def delete_message(message_id: int, user: dict = Depends(ctl.get_current_user)):
    db_message = ctl.get_message(message_id=message_id)
    if not db_message:
        raise HTTPException(status_code=404, detail="Message not found")
    ctl.delete_message(message_id=message_id)
    return {"detail": "Message deleted!"}

@app.post("/archives", response_model=model.ArchiveBase)
def create_archive(archive: ArchiveCreate, user: dict = Depends(ctl.get_current_user)):
    owner = ctl.get_user(archive.owner_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    return ctl.create_archive(archive=archive)

@app.get("/archives", response_model=List[model.ArchiveBase])
def read_archives(skip: int = 0,limit: int = 100,owner_id: Optional[int] = None, user: dict = Depends(ctl.get_current_user)):
    return ctl.get_archives(skip=skip, limit=limit,owner_id=owner_id)

@app.get("/archives/{archive_id}", response_model=model.ArchiveBase)
def read_archive(archive_id: int, user: dict = Depends(ctl.get_current_user)):
    db_archive = ctl.get_archive(archive_id=archive_id)
    if not db_archive:
        raise HTTPException(status_code=404, detail="Archive not found")
    return db_archive

@app.put("/archives/{archive_id}", response_model=model.ArchiveBase)
def update_archive(archive_id: int, archive: ArchiveUpdate, user: dict = Depends(ctl.get_current_user)):
    db_archive = ctl.get_archive(archive_id=archive_id)
    if not db_archive:
        raise HTTPException(status_code=404, detail="Archive not found")
    return ctl.update_archive(archive_id=archive_id, archive=archive)

@app.delete("/archives/{archive_id}")
def delete_archive(archive_id: int, user: dict = Depends(ctl.get_current_user)):
    db_archive = ctl.get_archive(archive_id=archive_id)
    if not db_archive:
        raise HTTPException(status_code=404, detail="Archive not found")
    ctl.delete_archive(archive_id=archive_id)
    return {"detail": "Archive deleted"}

@app.post("/embeds")
async def create_embed(embed: EmbedCreate, auth: dict = Depends(ctl.get_current_user)):
    if embed.source_type == "message":
        source = ctl.get_message(embed.source_id)
    elif embed.source_type == "archive":
        source = ctl.get_archive(embed.source_id)
    else:
        raise HTTPException(status_code=400, detail="Invalid source_type")
    
    if not source:
        raise HTTPException(
            status_code=404,
            detail=f"{embed.source_type} with id {embed.source_id} not found"
        )

    asyncio.create_task(ctl.create_embed( embed_data=source, auth=auth ))
    return {"detail": "Embedding task append!"}

@app.get("/embeds", response_model=List[int])
def query_embeds(source_type: str,content: str, limit:Optional[int] = 10, user: dict = Depends(ctl.get_current_user)):
    if source_type not in ['message','archive']:
        raise ValueError("Must specify source_type for embedding queries")
    return ctl.query_embeds(limit=limit, source_type=source_type, content=content, auth=user)

@app.get("/embeds/{embed_id}", response_model=model.EmbedBase)
def read_embed(embed_id: int, user: dict = Depends(ctl.get_current_user)):
    db_embed = ctl.get_embed(embed_id=embed_id)
    if not db_embed:
        raise HTTPException(status_code=404, detail="Embed not found")
    return db_embed

@app.delete("/embeds/{embed_id}")
def delete_embed(embed_id: int, user: dict = Depends(ctl.get_current_user)):
    db_embed = ctl.get_embed(embed_id=embed_id)
    if not db_embed:
        raise HTTPException(status_code=404, detail="Embed not found")
    ctl.delete_embed(embed_id=embed_id)
    return {"detail": "Embed deleted"}

@app.post("/chat")
async def chat(cc: ChatCreate, auth: dict = Depends(ctl.get_current_user)):
    return await ctl.Chat(cc.msg, auth)
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run('main:app', host="0.0.0.0", port=8000, log_level="debug")
    # uvicorn.run('main:app', host="0.0.0.0", port=8000, log_level="debug", reload=True)