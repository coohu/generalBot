from sqlalchemy import create_engine, Column, Integer, String, Text, TIMESTAMP, DateTime, ForeignKey, Enum
from sqlalchemy.orm import DeclarativeBase, relationship, Session
from sqlalchemy.types import UserDefinedType
from typing import Optional, List, Dict, Any
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import func
import json
import db.env as env

engine = create_engine(env.c['MARIADB_URL'])

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created = Column(DateTime, default=func.now(), nullable=False)
    updated = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

class IDMixin:
    id = Column(Integer, primary_key=True)

class CustomBase(Base):
    __abstract__ = True
    id = Column(Integer, primary_key=True, autoincrement=True)
    created = Column(DateTime, default=func.now(), nullable=False)
    updated = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

class VectorType(UserDefinedType):
    def __init__(self, dimensions):
        self.dimensions = dimensions
        
    def get_col_spec(self, **kw):
        return f"VECTOR({self.dimensions})"
    
    def bind_processor(self, dialect):
        def process(value):
            if value is None:
                return None
            if isinstance(value, (list, tuple)):
                json_str = json.dumps(value)
                return text(f"VEC_FromText('{json_str}')").execution_options(inline=True)

        return process
    
    def result_processor(self, dialect, coltype):
        def process(value):
            if value is None:
                return None
            # 这里可能需要根据实际情况转换返回的向量数据
            return value
        return process

# class User(Base, IDMixin, TimestampMixin):
class User(CustomBase):
    __tablename__ = 'user'
    wxid = Column(String(50), nullable=False, unique=True)
    last_run = Column(DateTime, nullable=True)

    customers = relationship("Customer", back_populates="user")
    posts = relationship("Post", back_populates="user")

    @classmethod
    def insert(cls, session: Session, 
        wxid: str = '',
        last_run: Optional[DateTime] = None) -> Optional['User']:
        """
        创建并插入一个新的用户记录
        
        Args:
            wxid: 微信 ID
            last_run: 上一次运行时间戳(可选)
            
        Returns:
            成功时返回新创建的 User 对象，失败时返回 None
        """
        try:
            user = cls(
                wxid=wxid,
                last_run=last_run
            )
            
            session.add(user)
            session.commit()
            return user
            
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Error inserting user: {str(e)}")
            return None

class Customer(CustomBase):
    __tablename__ = 'customer'
    user_id = Column(Integer, ForeignKey('user.id'), nullable=True)
    wxid = Column(String(50), nullable=True,unique=True)
    nick_name = Column(String(50), nullable=True)
    ps = Column(String(50), nullable=True)
    addr = Column(String(150),nullable=True)
    permission = Column(String(150), nullable=True)
    status = Column(String(150), nullable=True)
    source = Column(String(50), nullable=True)
    tags = Column(String(255), nullable=True)

    user = relationship("User", back_populates="customers")
    posts = relationship("Post", back_populates="customer")

    @classmethod
    async def insert_async(cls, async_session, **kwargs):
        try:
            customer = cls(**kwargs)
            async_session.add(customer)
            await async_session.commit()
            return customer
        except SQLAlchemyError as e:
            await async_session.rollback()
            print(f"Error inserting customer: {str(e)}")
            return None

    @classmethod
    def insert(cls, session: Session, 
        user_id: Optional[int] = None,
        wxid: Optional[str] = None,
        nick_name: Optional[str] = None,
        ps: Optional[str] = None,
        addr: Optional[str] = None,
        permission: Optional[str] = None,
        status: Optional[str] = None,
        source: Optional[str] = None,
        tags: Optional[str] = None) -> Optional['Customer']:
        """
        创建并插入一个新的客户记录
        
        Args:
            session: SQLAlchemy 会话对象
            user_id: 关联的用户 ID（可选）
            wxid: 微信 ID
            nick_name: 昵称
            ps: 备注
            addr: 地址
            permission: 权限
            status: 状态
            source: 来源
            tags: 标签列表
            
        Returns:
            成功时返回新创建的 Customer 对象，失败时返回 None
        """
        try:
            customer = cls(
                user_id=user_id,
                wxid=wxid,
                nick_name=nick_name,
                ps=ps,
                addr=addr,
                permission=permission,
                status=status,
                source=source,
                tags=tags
            )
            
            session.add(customer)
            session.commit()
            return customer
            
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Error inserting customer: {str(e)}")
            return None

class Post(CustomBase):
    __tablename__ = 'post'
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    customer_id = Column(Integer, ForeignKey('customer.id'), nullable=False)
    post_type = Column(Enum('post', 'msg'), nullable=False, default='post')
    md5 = Column(String(50), nullable=True, unique=True)
    headline = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)
    embedding = Column(VectorType(768), nullable=True) 

    user = relationship("User", back_populates="posts")
    customer = relationship("Customer", back_populates="posts")
    images = relationship("Image", back_populates="post")

    @classmethod
    def insert(cls, session: Session,
        user_id:int = None,
        customer_id: int = None,
        post_type:str = 'post',
        md5:str = None,
        headline: Optional[str] = None,
        tags: Optional[str] = None,
        embedding: Optional[VectorType(768)] = None) -> Optional['Post']:
        try:
            post = cls(user_id=user_id, 
                customer_id=customer_id,
                post_type=post_type, 
                md5=md5, 
                headline=headline,
                tags=tags,
                embedding=embedding)
            session.add(post)
            session.commit()
            return post
            
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Error inserting post: {str(e)}")
            return None

class Image(CustomBase):
    __tablename__ = 'image'
    post_id = Column(Integer, ForeignKey('post.id'), nullable=False)
    img = Column(String(255), nullable=True)
    ocr_text = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)
    embedding = Column(VectorType(768), nullable=True) 

    post = relationship("Post", back_populates="images")

    @classmethod
    def insert(cls, session: Session, 
        post_id: int = None,
        img: Optional[str] = None,
        ocr_text: Optional[str] = None,
        tags: Optional[str] = None,
        embedding: Optional[VectorType(768)] = None) -> Optional['Image']:
        try:
            img = cls(post_id=post_id,img=img,ocr_text=ocr_text,tags=tags,embedding=embedding)
            session.add(img)
            session.commit()
            return img
            
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Error inserting post: {str(e)}")
            return None

# Base.registry.configure()
Base.metadata.create_all(engine)


print("Table 'user','customer', 'post', 'image' created successfully!")





