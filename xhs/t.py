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