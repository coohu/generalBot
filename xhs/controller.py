from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import text, inspect, create_engine, func, Float
from sqlalchemy.ext.declarative import declarative_base
from fastapi import HTTPException, Security, Request
from sqlalchemy.orm import Session, sessionmaker
from fastapi.responses import StreamingResponse
from passlib.context import CryptContext
from datetime import datetime, timedelta
from collections import namedtuple
from typing import List, Optional
from utils import extract_domain
from openai import OpenAI
from api_model import *
from prompts import *
from time import time
import requests, json
import asyncio
import pprint
import model
import env
import jwt

engine = create_engine(env.pgVector)
def get_db():
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    with engine.connect() as conn:
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            print("pgvector EXTENSION inited.")
        except Exception as e:
            print(e)
    db = SessionLocal()
    model.Base.metadata.create_all(bind=engine)
    try:
        return db
    finally:
        db.close()

db = get_db()

revoked_tokens = set()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def create_jwt_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=env.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, env.secret_key, algorithm=env.ALGORITHM)

# Authorization 和 Bearer 大小写敏感， 
async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    if token in revoked_tokens:
        raise HTTPException(status_code=401, detail="Token 已失效")
    try:
        payload = jwt.decode(token, env.secret_key, algorithms=[env.ALGORITHM])
        user = get_user_by_email(payload.get("sub").get("email"))
        if not user:
            raise HTTPException(status_code=401, detail="用户不存在")
        if not glb_cache.get(user.id):
            print('get_current_user.user_cache()')
            await user_cache(user)
        else:
            glb_cache[user.id]['ts'] = time()
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token 过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token 无效")

def get_user(user_id: int):
    return db.query(model.User).filter(model.User.id == user_id).first()

def get_user_by_email(email: str):
    return db.query(model.User).filter(model.User.email == email).first()

def get_users(skip: int = 0, limit: int = 100):
    return db.query(model.User).offset(skip).limit(limit).all()

def create_user(user: dict):
    dbu = get_user_by_email(email=user.email)
    if dbu:
        return dbu

    db_user = model.User(
        name=user.name,
        email=user.email,
        passwd=pwd_context.hash(user.passwd),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(user: dict, user_data: dict):
    for key, value in user_data.dict(exclude_unset=True).items():
        if key=="config" and value =={}:
            setattr(user, key, None)
            continue
        if key=="passwd":
            setattr(user, key, pwd_context.hash(value))
            continue
        if value is not None:
            setattr(user, key, value)
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user

def delete_user(user_id: int):
    db_user = get_user(user_id)
    db.delete(db_user)
    db.commit()

def follow_user(user_id: int, follower_id: int):
    user = get_user(user_id)
    follower = get_user(follower_id)
    
    if follower not in user.followers:
        user.followers.append(follower)
        db.commit()
    return user

def unfollow_user(user_id: int, follower_id: int):
    user = get_user(user_id)
    follower = get_user(follower_id)
    
    if follower in user.followers:
        user.followers.remove(follower)
        db.commit()
    return user

def create_message(message: dict):
    db_message = model.Message(
        content=message.content,
        sender_id=message.sender_id,
        receiver_id=message.receiver_id,
        created_at=datetime.utcnow()
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

def get_message(message_id: int):
    return db.query(model.Message).filter(model.Message.id == message_id).first()

def get_messages(skip: int = 0, limit: int = 100, 
        sender_id: Optional[int] = None, receiver_id: Optional[int] = None):
    query = db.query(model.Message)
    if sender_id:
        query = query.filter(model.Message.sender_id == sender_id)
    if receiver_id:
        query = query.filter(model.Message.receiver_id == receiver_id)
    return query.offset(skip).limit(limit).all()

def delete_message(message_id: int):
    db_message = get_message(db, message_id)
    db.delete(db_message)
    db.commit()

def create_archive(archive: dict):
    db_archive = model.Archive(
        owner_id=archive.owner_id,
        file_type=archive.file_type,
        filemeta=archive.filemeta,
        graph=archive.graph,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(db_archive)
    db.commit()
    db.refresh(db_archive)
    return db_archive

def get_archive(archive_id: int):
    return db.query(model.Archive).filter(model.Archive.id == archive_id).first()

def get_archives(skip: int = 0, limit: int = 100, owner_id: Optional[int] = None):
    query = db.query(model.Archive)
    if owner_id:
        query = query.filter(model.Archive.owner_id == owner_id)
    return query.offset(skip).limit(limit).all()

def update_archive(archive_id: int, archive: dict):
    db_archive = get_archive(archive_id)
    for key, value in archive.dict(exclude_unset=True).items():
        setattr(db_archive, key, value)
    db_archive.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_archive)
    return db_archive

def delete_archive(archive_id: int):
    db_archive = get_archive(archive_id)
    db.delete(db_archive)
    db.commit()

def get_embed_model(uid:int):
    openaiEmbed = None 
    apiEmbed = None
    EmbedAPI = glb_cache[uid]['embed']
    if type(EmbedAPI['api']) == OpenAI:
        openaiEmbed = EmbedAPI
    else:
        apiEmbed = EmbedAPI
    EmbedDim = EmbedAPI.get('dim')
    if not EmbedDim:
        if type(EmbedAPI['api']) == OpenAI:
            res =EmbedAPI['api'].embeddings.create(input='get the embedmodel dim', model=EmbedAPI['model'])
            EmbedDim = len(res.data[0].embedding)
            EmbedAPI['dim'] = EmbedDim
            
        # todo other style api
    ebd = model.EmbedFactory.create_embed_model(EmbedDim)
    if f"embed_{EmbedDim}" not in inspect(engine).get_table_names():
        model.Base.metadata.create_all(bind=engine, tables=[ebd.__table__])
    return (ebd, openaiEmbed, apiEmbed)

async def create_embed(embed_data: dict, auth: dict):
    EmbedModel = get_embed_model(auth.id)[0]
    extra_fields = {}
    if embed_data.source_type == "message":
        extra_fields["message_id"] = embed_data.source_id
    else:
        extra_fields["archive_id"] = embed_data.source_id
    
    db_embed = EmbedModel(
        source_type=embed_data.source_type,
        source_id=embed_data.source_id,
        embedding=embed_data.embedding,
        created_at=datetime.utcnow(),
        **extra_fields
    )
    db.add(db_embed)
    db.commit()
    db.refresh(db_embed)

def query_embeds(source_type:str, content: str,  limit: int, auth:dict, threshold:float=0):
    if source_type not in ['message','archive']:
        return []
    (EmbedModel, embed, _) = get_embed_model(auth.id)
    res = embed['api'].embeddings.create(input=content, model=embed['model'])
    qv = res.data[0].embedding
    results = db.query(
        EmbedModel.source_id,
        (1 - func.cast(EmbedModel.embedding.cosine_distance(qv), Float)).label("similarity")
    ).filter(
        EmbedModel.source_type == source_type
    ).filter(
        EmbedModel.user_id == auth.id
    ).order_by(
        EmbedModel.embedding.cosine_distance(qv) 
    ).limit(limit).all()
    return [sid for (sid, n) in results if n > threshold]

def delete_embed(embed_id: int, source_type: str):
    EmbedModel = get_embed_model(source_type)
    db_embed = db.query(EmbedModel).filter(EmbedModel.id == embed_id).first()
    db.delete(db_embed)
    db.commit()

async def embed_msgs(msgs, uid):
    (EmbedModel, EmbedAPI, _) = get_embed_model(uid)
    ChatAPI = glb_cache[uid]['chat']
    chat = UserCreate(
        name=ChatAPI['model'], 
        email=f'{ChatAPI['model']}@{ChatAPI['vendor']}',
        passwd="",
    )
    ChatUser = create_user(chat)

    for msg in msgs:
        if msg['role'] == 'system':
            continue
        sender_id=uid 
        receiver_id=ChatUser.id
        if msg['role'] != 'user':
            sender_id=ChatUser.id
            receiver_id=uid
        m = MessageCreate(
            content=msg['content'],
            sender_id=sender_id,
            receiver_id=receiver_id,
        )
        dbm = create_message(m)
        if msg['role'] == 'user':
            res =EmbedAPI['api'].embeddings.create(input=msg['content'], model=EmbedAPI['model'])
            db_embed = EmbedModel(
                source_type='message',
                source_id=dbm.id,
                user_id = uid,
                embedding=res.data[0].embedding,
                created_at=datetime.utcnow(),
            )
            db.add(db_embed)
    db.commit()
    db.refresh(db_embed)

async def query_msgs(topic, gud, auth):
    mids = query_embeds('message', topic, 16, auth, 0.7)
    results = db.query(model.Message.content).filter(model.Message.id.in_(mids)).all()
    return [content for (content, ) in results]

glb_cache = {}

async def Chat(msg: str, auth: dict, memble=True, topicble=False):
    print(f'ctl.Chat({msg})')
    gud = glb_cache.get(auth.id)
    if not gud:
        print('Chat.user_cache()')
        await user_cache(auth)
        gud = glb_cache.get(auth.id)

    gud['ctx'].append({'role':'user','content':msg})
    gud['ctx'] = gud['ctx'][-10:]
    print('ctl.Chat() glb_cache loaded!')
    sys_pps = []

    if gud['mem'] and memble:
        sys_pps.append( gud['mem'] )

    if not topicble:
        tpc = await query_msgs(msg, gud, auth)
        print("\n向量搜索结果:\n")
        pprint.pp(tpc)
        if len(tpc):
            sys_pps.append( '\n'.join(tpc) )
        # sys_pps.append( PERFUNCTORY )


    msgs = gud.get('ctx')
    if len(sys_pps):
        mps = MEMORY_ANSWER_PROMPT.format('\n'.join(sys_pps))
        msgs = [{'role':'system','content':mps}] + msgs

    print("\n会话上下文:\n")
    pprint.pp(msgs)
    chat_api = gud.get('chat').get('api')
    if type(chat_api)== OpenAI:
        res = chat_api.chat.completions.create(
            model= gud.get('chat').get('model'),
            messages= msgs,
            stream= True,
        )
        async def generate():
            rsc = ''
            dpb = False
            for chunk in res:
                if chunk.choices[0].delta.content:  
                    text=chunk.choices[0].delta.content
                    if '<think>' in text:
                        dpb = True
                        continue
                    if '</think>' in text:
                        dpb = False
                        continue
                    if not dpb:
                        # print(chunk.choices[0].delta.content, end="", flush=True)
                        rsc += text
                        yield text
            # print()
            gud['ctx'].append({'role':'assistant','content':rsc})
            asyncio.create_task(embed_msgs(gud['ctx'][-2:], auth.id))
        return StreamingResponse(generate(), media_type="text/plain")

def Generate(msg: str, sys:str, archive):
    msgs = [
        {'role':'system','content':sys},
        {'role':'user','content':msg},
    ]
    archive_api = archive['api']
    if type(archive_api) == OpenAI:
        res = archive_api.chat.completions.create(
            model=archive.get('model'),
            messages=msgs,
            stream=False,
        )
        return res.choices[0].message.content
    return ''

async def user_cache(auth):
    if glb_cache.get(auth.id):
        return 
    rts = {}
    for key in auth.config.keys():
        it = auth.config.get(key)
        key = str(key).lower()
        if type(it) is dict and set(it.keys()) == {'name', 'url', 'protocol','key'} and key not in ['ctx','mem']: 
            if it['protocol'] == 'openai':
                rts[key] = {"api": OpenAI(api_key=it['key'], base_url=it['url']), 
                    "model": it['name'], 'vendor':extract_domain(it['url'])}
            if it['protocol'] == 'api':
                req = requests.Request(
                    method='POST',
                    url= it['url'],
                    headers={'Authorization': f'Bearer {it['key']}'},  
                )
                rts[key] = {"api":req, "model":it['name'], 'vendor':extract_domain(it['url'])}

    dft_vendor = 'relay.shengsuanyun.com'
    dft = {
        "ctx":[],
        "mem":'',
        "chat": {'api':OpenAI(api_key=env.key, base_url=env.url),"model": 'shengsuanyun/DeepSeek-R1','vendor':dft_vendor},
        "embed":{'api':OpenAI(api_key=env.key, base_url=env.url),"model": 'text-embedding-v3','vendor':dft_vendor},
        "archive":{'api':OpenAI(api_key=env.key, base_url=env.url),"model": 'qwen-turbo','vendor':dft_vendor},
        "ts": time(),
    }
    glb_cache[auth.id] = {**dft, **rts}

    msgs = get_messages(skip=0, limit=1000, sender_id=auth.id)
    hst = "\n".join([it.content for it in msgs])
    mem = Generate(hst, FACT_RETRIEVAL_PROMPT, glb_cache[auth.id]['archive'])
    glb_cache[auth.id]['mem'] = mem
    print("\n历史会话汇总:\n")
    print(mem)

async def mem_load(uid):
    pass


