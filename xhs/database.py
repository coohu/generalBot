from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Optional, ClassVar, List, Dict, TypeVar, Generic, Type, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from bson import ObjectId
from neo4j import AsyncGraphDatabase
from neo4j.exceptions import Neo4jError
import logging

logger = logging.getLogger(__name__)
T = TypeVar('T', bound='Database')

class Database(BaseModel, Generic[T]):
    # MongoDB 字段
    id: Optional[str] = Field(default=None, alias="_id")
    
    # MongoDB 类变量
    _mongo_collection_name: ClassVar[str] = None
    _mongo_indexes: ClassVar[List[Dict]] = []
    _mongo_client: ClassVar[Optional[AsyncIOMotorClient]] = None
    _mongo_db_name: ClassVar[Optional[str]] = None
    
    # Neo4j 类变量
    _neo4j_driver: ClassVar[Optional[AsyncGraphDatabase.driver]] = None
    _neo4j_config: ClassVar[Dict] = {}

    # 初始化 MongoDB
    @classmethod
    def init_mongodb(cls, uri: str, db_name: str) -> None:
        cls._mongo_client = AsyncIOMotorClient(uri)
        cls._mongo_db_name = db_name
        logger.info(f"Initialized MongoDB connection to {db_name}")

    # 初始化 Neo4j
    @classmethod
    def init_neo4j(cls, uri: str, auth: tuple, **kwargs) -> None:
        cls._neo4j_driver = AsyncGraphDatabase.driver(uri, auth=auth, **kwargs)
        logger.info(f"Initialized Neo4j connection to {uri}")

    # 获取 MongoDB 集合
    @classmethod
    def _get_mongo_collection(cls) -> AsyncIOMotorCollection:
        if not cls._mongo_collection_name:
            raise NotImplementedError("Subclass must define _mongo_collection_name")
        return cls._mongo_client[cls._mongo_db_name][cls._mongo_collection_name]

    # 创建 MongoDB 索引
    @classmethod
    async def create_mongo_indexes(cls) -> None:
        if cls._mongo_indexes:
            await cls._get_mongo_collection().create_indexes(cls._mongo_indexes)
            logger.info(f"Created MongoDB indexes for {cls._mongo_collection_name}")

    # MongoDB 保存
    async def save_to_mongo(self: T) -> T:
        data = self.dict(by_alias=True, exclude={"id"})
        if self.id:
            await self._get_mongo_collection().update_one(
                {"_id": ObjectId(self.id)}, {"$set": data}
            )
        else:
            result = await self._get_mongo_collection().insert_one(data)
            self.id = str(result.inserted_id)
        return self

    # Neo4j 保存
    async def save_to_neo4j(self: T) -> T:
        if not self.id:
            raise ValueError("MongoDB ID is required for Neo4j synchronization")

        query = """
        MERGE (u:User {id: $id})
        SET u.name = $name, u.email = $email, u.age = $age
        """
        params = {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "age": self.age
        }
        
        async with self._neo4j_driver.session() as session:
            await session.run(query, params)
        return self

    # 双数据库保存
    async def save(self: T) -> T:
        await self.save_to_mongo()
        await self.save_to_neo4j()
        return self

    # 其他 MongoDB 操作...
    
class User(Database['User']):
    _mongo_collection_name = "users"
    _mongo_indexes = [
        {"name": "email_unique", "key": [("email", 1)], "unique": True}
    ]

    name: str
    age: int
    email: EmailStr
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # 社交关系方法
    async def follow(self, target: 'User'):
        """关注另一个用户"""
        if not self.id or not target.id:
            raise ValueError("Both users must be persisted")

        query = """
        MATCH (a:User {id: $user_id}), (b:User {id: $target_id})
        MERGE (a)-[r:FOLLOWS]->(b)
        """
        params = {"user_id": self.id, "target_id": target.id}

        async with self._neo4j_driver.session() as session:
            await session.run(query, params)

    async def unfollow(self, target: 'User'):
        """取消关注"""
        query = """
        MATCH (a:User {id: $user_id})-[r:FOLLOWS]->(b:User {id: $target_id})
        DELETE r
        """
        params = {"user_id": self.id, "target_id": target.id}

        async with self._neo4j_driver.session() as session:
            await session.run(query, params)

    async def get_followers(self) -> List['User']:
        """获取粉丝列表"""
        query = """
        MATCH (u:User {id: $user_id})<-[:FOLLOWS]-(follower:User)
        RETURN follower
        """
        params = {"user_id": self.id}

        async with self._neo4j_driver.session() as session:
            result = await session.run(query, params)
            return [await self._neo4j_node_to_user(record["follower"]) async for record in result]

    async def get_following(self) -> List['User']:
        """获取关注列表"""
        query = """
        MATCH (u:User {id: $user_id})-[:FOLLOWS]->(following:User)
        RETURN following
        """
        params = {"user_id": self.id}

        async with self._neo4j_driver.session() as session:
            result = await session.run(query, params)
            return [await self._neo4j_node_to_user(record["following"]) async for record in result]

    async def get_mutuals(self) -> List['User']:
        """获取互相关注的用户"""
        query = """
        MATCH (u:User {id: $user_id})-[:FOLLOWS]->(m:User),
              (m)-[:FOLLOWS]->(u)
        RETURN m
        """
        params = {"user_id": self.id}

        async with self._neo4j_driver.session() as session:
            result = await session.run(query, params)
            return [await self._neo4j_node_to_user(record["m"]) async for record in result]

    @classmethod
    async def _neo4j_node_to_user(cls, node) -> 'User':
        """将 Neo4j 节点转换为 User 实例"""
        properties = dict(node.items())
        return cls(
            id=properties["id"],
            name=properties["name"],
            email=properties["email"],
            age=properties["age"]
        )

# 初始化数据库连接
User.init_mongodb("mongodb://localhost:27017", "social_network")
User.init_neo4j("bolt://localhost:7687", ("neo4j", "password"))

# 使用示例
async def main():
    # 创建用户
    user1 = User(name="Alice", age=30, email="alice@example.com")
    await user1.save()

    user2 = User(name="Bob", age=25, email="bob@example.com")
    await user2.save()

    # 建立关注关系
    await user1.follow(user2)
    await user2.follow(user1)

    # 查询关系
    print("Alice 的关注:", [u.name for u in await user1.get_following()])
    print("Bob 的粉丝:", [u.name for u in await user2.get_followers()])
    print("互相关注:", [u.name for u in await user1.get_mutuals()])

    # 双数据库查询
    db_user = await User.find_by_email("alice@example.com")
    print("MongoDB 用户:", db_user.dict())