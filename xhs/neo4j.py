from neomodel import (
    StructuredNode,
    StringProperty,
    UniqueIdProperty,
    RelationshipTo,
    RelationshipFrom,
    config,
)

config.DATABASE_URL = "bolt://neo4j:password@localhost:7687"
class User(StructuredNode):
    uid = UniqueIdProperty()
    name = StringProperty(required=True)
    email = StringProperty(unique_index=True, required=True)

    # 用户主动关注的人（关系方向：User → User，类型为 FOLLOW）
    following = RelationshipTo("User", "FOLLOW")
    # 关注该用户的人（反向关系：User ← User，类型为 FOLLOW）
    followers = RelationshipFrom("User", "FOLLOW")
    # 判断是否相互关注
    def is_mutual(self, other_user):
        return other_user in self.following and self in other_user.following
    # 获取相互关注的用户列表
    def mutuals(self):
        query = """
        MATCH (u:User {uid: $uid})-[:FOLLOW]->(target:User)
        WHERE (target)-[:FOLLOW]->(u)
        RETURN target
        """
        return self.cypher(query, {"uid": self.uid})[0]
