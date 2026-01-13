from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# --- REQUEST MODELS ---
class CreateChatRequest(BaseModel):
    # Optional: If you want to allow naming the chat upfront
    title: Optional[str] = "New Conversation"

class ChatQueryRequest(BaseModel):
    query: str
    session_id: str

# --- RESPONSE MODELS ---
class SessionResponse(BaseModel):
    session_id: str
    title: str
    created_at: datetime

class Message(BaseModel):
    role: str
    content: str
    timestamp: datetime

class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: List[Message]