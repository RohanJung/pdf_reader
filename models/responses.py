from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel

class AskResponse(BaseModel):
    session_id: str
    question: str
    answer: str
    context_used: List[str]
    has_history: bool

class BookingResponse(BaseModel):
    message: str
    booking_info: Dict[str, str]
    session_id: str

class ChatHistoryResponse(BaseModel):
    session_id: str
    history: List[Tuple[str, str]]
    total_messages: int

class SessionResponse(BaseModel):
    message: str
    session_id: str
    status: str

class CurrentSessionResponse(BaseModel):
    current_session: Optional[str]
    status: str

class IngestionResponse(BaseModel):
    session_id: str
    file_index: int
    filename: str
    num_chunks: int
    status: str
    created_at: Any