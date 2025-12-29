"""
MongoDB client for the Deep Research Agent system.
"""

import os
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from datetime import datetime

from ..models.models import QueryRecord, ChatSession
from ..utils.logging import BaseLogger
from ..custom_errors import DeepResearchError

class DatabaseError(DeepResearchError):
    """Database operation error"""
    pass

class DatabaseClient:

    def __init__(self, mongo_uri:str=None):
        if not mongo_uri:
            mongo_uri = os.getenv("MONGO_URI")
        self.mongo_uri = mongo_uri
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self.queries_collection: Optional[AsyncIOMotorCollection] = None
        self.sessions_collection: Optional[AsyncIOMotorCollection] = None
        self.logger = BaseLogger.get_logger()

    async def connect(self) -> None:
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(self.mongo_uri)
            self.db = self.client[os.getenv("MONGO_DB")]
            self.queries_collection = self.db["DR_chats"]
            self.sessions_collection = self.db["chat_sessions"]

            # Test connection
            await self.client.admin.command('ping')
            self.logger.info("Connected to MongoDB successfully")

        except Exception as e:
            self.logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise DatabaseError(f"Failed to connect to MongoDB: {str(e)}")

    async def disconnect(self) -> None:
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            self.logger.info("Disconnected from MongoDB")

    async def save_query_record(self, query_record: QueryRecord) -> str:
        """Save a query record to database"""
        try:
            if self.queries_collection is None:
                raise DatabaseError("Database connection not established")

            document = query_record.to_dict()
            result = await self.queries_collection.insert_one(document)
            return str(result.inserted_id)

        except Exception as e:
            self.logger.error(f"Failed to save query record: {str(e)}")
            raise DatabaseError(f"Failed to save query record: {str(e)}")

    async def get_query_records(self,
                                session_id:Optional[str]=None,
                                limit: int = 100)-> List[Dict[str, Any]]:
        """Get query records from database, optionally filtered by session_id"""
        try:
            if self.queries_collection is None:
                raise DatabaseError("Database connection not established")

            query = {}
            if session_id:
                query["session_id"] = session_id

            cursor = self.queries_collection.find(query).sort("created_at", -1).limit(limit)
            records = await cursor.to_list(length=limit)

            for record in records:
                record['_id'] = str(record['_id'])

            return records
        except Exception as e:
            self.logger.error(f"Failed to get query records: {str(e)}")
            raise DatabaseError(f"Failed to get query records: {str(e)}")

    async def get_token_dashboard_data(self) -> List[Dict[str, Any]]:
        """Get all query records with token information for dashboard"""
        try:
            if self.queries_collection is None:
                raise DatabaseError("Database connection not established")
            projection = {
                "query_id": 1,
                "session_id": 1,
                "user_query": 1,
                "token_info": 1,
                "created_at": 1
            }
            cursor = self.queries_collection.find({}, projection).sort("created_at", -1)
            records = await cursor.to_list(length=None)

            # Convert ObjectId to string and format for dashboard
            dashboard_data = []
            for record in records:
                record['_id'] = str(record['_id'])
                token_info = record.get("token_info", {})
                dashboard_record = {
                    "query_id": record["query_id"],
                    "session_id": record["session_id"],
                    "user_query": record["user_query"][:100] + "..." if len(record["user_query"]) > 100 else record[
                        "user_query"],
                    "main_llm_input_tokens": token_info.get("main_llm_usage", {}).get("input_tokens", 0),
                    "main_llm_output_tokens": token_info.get("main_llm_usage", {}).get("output_tokens", 0),
                    "main_llm_cost": token_info.get("main_llm_usage", {}).get("cost", 0.0),
                    "context_input_tokens": token_info.get("context_summarization_usage", {}).get("input_tokens", 0),
                    "context_output_tokens": token_info.get("context_summarization_usage", {}).get("output_tokens", 0),
                    "context_cost": token_info.get("context_summarization_usage", {}).get("cost", 0.0),
                    "search_count": token_info.get("search_usage", {}).get("search_count", 0),
                    "search_cost": token_info.get("search_usage", {}).get("cost", 0.0),
                    "total_cost": token_info.get("total_cost", 0.0),
                    "created_at": record["created_at"]
                }
                dashboard_data.append(dashboard_record)

            return dashboard_data

        except Exception as e:
            self.logger.error(f"Failed to get token dashboard data: {str(e)}")
            raise DatabaseError(f"Failed to get token dashboard data: {str(e)}")

    async def save_chat_session(self, session: ChatSession) -> str:
        """Save or update a chat session"""
        try:
            if self.sessions_collection is None:
                raise DatabaseError("Database connection not established")

            document = session.to_dict()

            # Upsert the session
            result = await self.sessions_collection.replace_one(
                {"session_id": session.session_id},
                document,
                upsert=True
            )
            self.logger.info(f"Saved chat session: {session.session_id}")
            return session.session_id
        except Exception as e:
            self.logger.error(f"Failed to save chat session: {str(e)}")
            raise DatabaseError(f"Failed to save chat session: {str(e)}")

    async def get_chat_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a chat session by session_id"""
        try:
            if self.sessions_collection is None:
                raise DatabaseError("Database connection not established")

            document = await self.sessions_collection.find_one({"session_id": session_id})
            if not document:
                return None

            session = ChatSession(
                session_id=document["session_id"],
                messages=document["messages"],
                created_at=document["created_at"],
                updated_at=document["updated_at"]
            )
            return session
        except Exception as e:
            self.logger.error(f"Failed to get chat session: {str(e)}")
            raise DatabaseError(f"Failed to get chat session: {str(e)}")

    async def update_session_with_summary(
            self,
            session_id: str,
            summary: str,
            keep_recent_count: int = 2
    ) -> None:
        """Update session by replacing old messages with summary"""
        try:
            session = await self.get_chat_session(session_id)
            if not session:
                return

            # Keep only the most recent messages
            recent_messages = session.messages[-keep_recent_count:] if len(
                session.messages) > keep_recent_count else session.messages

            # Create new message list with summary + recent messages
            new_messages = [
                {
                    "role": "system",
                    "content": f"Previous conversation summary: {summary}",
                    "timestamp": datetime.now().isoformat()
                }
            ]
            new_messages.extend(recent_messages)

            session.messages = new_messages
            session.updated_at = datetime.now()

            await self.save_chat_session(session)
            self.logger.debug(f"Updated session {session_id} with summary")

        except Exception as e:
            self.logger.error(f"Failed to update session with summary: {str(e)}")
            raise DatabaseError(f"Failed to update session with summary: {str(e)}")


# Global database client instance
db_client: Optional[DatabaseClient] = None


async def get_database_client() -> DatabaseClient:
    """Get or create database client"""
    global db_client

    if db_client is None:
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        db_client = DatabaseClient(mongo_uri)
        await db_client.connect()

    return db_client


async def close_database_client() -> None:
    """Close database client"""
    global db_client

    if db_client:
        await db_client.disconnect()
        db_client = None


