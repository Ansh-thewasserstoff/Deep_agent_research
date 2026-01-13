import uuid
from fastapi import HTTPException

from modules.services.mongodb import mongo_service
from modules.services.redis import redis_service
from modules.server.types import SessionResponse

async def create_new_session(user_id:str, title: str) -> SessionResponse:
    session_id = str(uuid.uuid4())
    doc = await mongo_service.create_session(user_id, session_id, title)

    return SessionResponse(
        session_id=session_id,
        title=title,
        created_at=doc["created_at"]
    )

async def queue_agent_task(session_id: str, query: str):
    pass

async def get_history(user_id: str, session_id: str):
    """
    Fetches history from Mongo (persistent) OR Redis (active cache).
    """
    # Try Mongo first for full history
    session = await mongo_service.get_session_history(user_id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session