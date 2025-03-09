from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .model import Base, EmbedFactory
import os

# 数据库配置
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 初始化 pgvector 扩展
def enable_pgvector():
    with engine.connect() as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

# 动态创建 Embed 表
def create_dynamic_tables():
    # 创建标准表
    Base.metadata.create_all(bind=engine)
    
    # 创建不同维度的 Embed 表
    dimensions = [768, 1024]  # 根据需求添加更多维度
    for dim in dimensions:
        EmbedModel = EmbedFactory.create_embed_model(dim)
        EmbedModel.__table__.create(bind=engine, checkfirst=True)

# 初始化数据库
def init_db():
    enable_pgvector()
    create_dynamic_tables()

# 依赖注入
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()