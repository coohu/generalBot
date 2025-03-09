from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from typing import Generic, TypeVar, ClassVar, Optional, Any, List, Dict
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from bson import ObjectId
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
T = TypeVar('T', bound='MongoDB')

class MongoDB(BaseModel, Generic[T]):

    id: Optional[str] = Field(default=None, alias="_id")
    _collection_name: ClassVar[str]
    _indexes: ClassVar[List[Dict]] = []
    _client: ClassVar[Optional[AsyncIOMotorClient]] = None
    _db_name: ClassVar[Optional[str]] = None

    @classmethod
    def init_db(cls, uri: str, db_name: str) -> None:
        cls._client = AsyncIOMotorClient(uri)
        cls._db_name = db_name
        logger.info(f"Initialized MongoDB connection to {db_name}")

    @classmethod
    def _get_collection(cls) -> AsyncIOMotorCollection:
        if not cls._collection_name:
            raise NotImplementedError("Subclass must define _collection_name")
        return cls._client[cls._db_name][cls._collection_name]

    @classmethod
    async def create_indexes(cls) -> None:
        if cls._indexes:
            await cls._get_collection().create_indexes(cls._indexes)
            logger.info(f"Created indexes for {cls._collection_name}: {cls._indexes}")

    async def save(self: T) -> T:
        await self.pre_save()
        data = self.dict(by_alias=True, exclude={"id"})
        if self.id:
            await self._get_collection().update_one(
                {"_id": ObjectId(self.id)}, {"$set": data}
            )
            logger.debug(f"Updated document {self.id} in {self._collection_name}")
        else:
            result = await self._get_collection().insert_one(data)
            self.id = str(result.inserted_id)
            logger.debug(f"Inserted new document {self.id} into {self._collection_name}")
        return self

    async def delete(self) -> bool:
        if not self.id:
            return False
        result = await self._get_collection().delete_one({"_id": ObjectId(self.id)})
        deleted = result.deleted_count > 0
        if deleted:
            logger.debug(f"Deleted document {self.id} from {self._collection_name}")
        return deleted

    @classmethod
    async def get(cls: type[T], id: str) -> Optional[T]:
        data = await cls._get_collection().find_one({"_id": ObjectId(id)})
        return cls(**cls._to_mongo(data)) if data else None

    @classmethod
    async def find(cls: type[T], filter: Dict = None, skip: int = 0, limit: int = 100) -> List[T]:
        """通用查询方法（支持分页）"""
        filter = filter or {}
        cursor = cls._get_collection().find(filter).skip(skip).limit(limit)
        return [cls(**cls._to_mongo(data)) async for data in cursor]

    @classmethod
    def _to_mongo(cls, data: Dict) -> Dict:
        """转换 MongoDB 数据到 Pydantic 模型"""
        if data and "_id" in data:
            data["id"] = str(data["_id"])
        return data

    async def pre_save(self):
        print("pre_save() hooks!")

class SoftDeleteMixin(MongoDB):
    is_deleted: bool = Field(default=False)  # 软删除标记
    deleted_at: Optional[datetime] = None    # 删除时间

    async def delete(self) -> bool:
        """执行软删除（标记为已删除）"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        await self.save()
        return True

    @classmethod
    async def hard_delete(cls, id: str) -> bool:
        """物理删除文档（慎用）"""
        result = await cls._get_collection().delete_one({"_id": ObjectId(id)})
        return result.deleted_count > 0

    @classmethod
    async def find(
        cls: type[T],
        filter: Dict = None,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[T]:
        """查询文档（默认过滤已删除项）"""
        if not include_deleted:
            filter = filter or {}
            filter["is_deleted"] = False
        return await super().find(filter=filter, skip=skip, limit=limit)

    @classmethod
    async def get(
        cls: type[T], 
        id: str, 
        include_deleted: bool = False
    ) -> Optional[T]:
        """根据 ID 获取文档（默认过滤已删除项）"""
        doc = await super().get(id)
        if doc and (include_deleted or not doc.is_deleted):
            return doc
        return None

    @classmethod
    async def find_deleted(cls: type[T]) -> List[T]:
        """查询所有已删除的文档"""
        return await cls.find({"is_deleted": True}, include_deleted=True)

    async def restore(self) -> None:
        """恢复软删除的文档"""
        self.is_deleted = False
        self.deleted_at = None
        await self.save()

class AuditLog(SoftDeleteMixin, MongoDB['AuditLog']):
    _collection_name = "audit_logs"
    action: str
    target_id: str
    performed_by: str

    
class User(SoftDeleteMixin, MongoDB['User']):
    _collection_name = "users"
    _indexes = [
        {"name": "email_unique", "key": [("email", 1)], "unique": True}
    ]

    name: str
    age: int
    email: EmailStr
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    async def find_by_email(cls, email: str) -> Optional['User']:
        """根据邮箱查询用户"""
        data = await cls._get_collection().find_one({"email": email})
        return cls(**cls._convert_mongo_data(data)) if data else None

    @classmethod
    async def find_adults(cls, min_age: int = 18) -> List['User']:
        """查询成年用户"""
        return await cls.find({"age": {"$gte": min_age}})

class Message(MongoDB['Message']):
    _collection_name = "messages"
    _indexes = [
        {"name": "sender_index", "key": [("sender_id", 1)]},
        {"name": "receiver_index", "key": [("receiver_id", 1)]}
    ]

    sender_id: str  # 关联 User.id
    receiver_id: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    async def find_conversation(cls, user1_id: str, user2_id: str,limit: int = 100) -> List['Message']:
        """查询两个用户之间的对话"""
        return await cls.find({
            "$or": [
                {"sender_id": user1_id, "receiver_id": user2_id},
                {"sender_id": user2_id, "receiver_id": user1_id}
            ]
        }, limit=limit)

    async def transfer_message(sender: User, receiver: User, content: str):
        async with MongoDB._client.start_session() as session:
            async with session.start_transaction():
                msg = Message(sender_id=sender.id, receiver_id=receiver.id, content=content)
                await msg.save(session=session)