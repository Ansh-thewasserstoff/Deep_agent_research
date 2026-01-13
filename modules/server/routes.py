from fastapi import APIRouter, Header, Depends
from sse_starlette.sse import EventSourceResponse

from modules.server import types, functions
from modules.services.redis import redis_service

router = APIRouter()

# --- MOCK AUTH (Replace with your actual Middleware) ---
async def get_user_id(x_user_id: str = Header(..., alias="X-User-ID")):
    return x_user_id


@router.post("/chat/new", response_model=types.SessionResponse)
async def create_chat_endpoint(
        request: types.CreateChatRequest,
        user_id: str = Depends(get_user_id)
):
    return await functions.create_new_session(user_id, request.title)


@router.post("/chat/send")
async def send_message_endpoint(
        request: types.ChatQueryRequest,
        user_id: str = Depends(get_user_id)
):
    # Fire and forget (Async processing)
    await functions.queue_agent_task(request.session_id, request.query)
    return {"status": "queued"}


@router.get("/chat/stream/{session_id}")
async def stream_chat_endpoint(session_id: str):
    """
    SSE Endpoint: The frontend listens to this.
    """

    async def event_generator():
        async for message in redis_service.listen_to_session(session_id):
            # SSE Format is strict: "data: <payload>\n\n"
            yield f"data: {message}\n\n"

    return EventSourceResponse(event_generator())


@router.get("/chat/history")
async def list_chats_endpoint(user_id: str = Depends(get_user_id)):
    from modules.services.mongodb import mongo_service
    return await mongo_service.list_user_sessions(user_id)


@router.get("/chat/{session_id}/history")
async def get_chat_details_endpoint(
        session_id: str,
        user_id: str = Depends(get_user_id)
):
    return await functions.get_history(user_id, session_id)