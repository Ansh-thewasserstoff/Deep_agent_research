from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import datetime as datetimem
from typing import List, Optional
import os
from pydantic import BaseModel, Field

MONGO_URI = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME")

class Message(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.now(datetimem.UTC))

class SessionSummary(BaseModel):
    id: str = Field(alias="_id")
    title: str
    created_at: datetime

class MongoService:
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[DB_NAME]
        self.collection = self.db["sessions"]

    async def create_session(self, user_id:str, session_id:str, title:str = "New Chat"):
        document = {
            "_id": session_id,
            "user_id": user_id,
            "title": title,
            "created_at": datetime.now(datetimem.UTC),
            "updated_at": datetime.now(datetimem.UTC),
            "messages": []
        }

    async def add_message(self, user_id: str, session_id: str, role: str, content: str):
        """
        Uses $push to append a message atomically without fetching the whole doc.
        """
        new_message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow()
        }

        result = await self.collection.update_one(
            {"_id": session_id, "user_id": user_id},  # Security Check
            {
                "$push": {"messages": new_message},
                "$set": {"updated_at": datetime.utcnow()}  # Update timestamp
            }
        )
        return result.modified_count > 0

    # 3. Get Full Chat History (For the Chat Window)
    async def get_session_history(self, user_id: str, session_id: str):
        """
        Fetches the full conversation.
        """
        session = await self.collection.find_one(
            {"_id": session_id, "user_id": user_id}
        )
        return session

    # 4. Get List of Sessions (For the Sidebar)
    async def list_user_sessions(self, user_id: str, limit: int = 20) -> List[SessionSummary]:
        """
        Fetches ONLY metadata (id, title, date) for the sidebar.
        Does NOT fetch the heavy 'messages' array to save bandwidth.
        """
        cursor = self.collection.find(
            {"user_id": user_id},
            {"messages": 0}  # Projection: Exclude messages field
        ).sort("updated_at", -1).limit(limit)

        sessions = await cursor.to_list(length=limit)
        return sessions

    # 5. Delete Session
    async def delete_session(self, user_id: str, session_id: str):
        await self.collection.delete_one({"_id": session_id, "user_id": user_id})


# Singleton Instance
mongo_service = MongoService()