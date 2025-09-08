from typing import Optional, Dict, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import uuid
import re

from rag.pipeline import RAGPipeline
from rag.memory import RedisMemory
from config import settings
from qdrant_client import QdrantClient
from utils.embeddings import generate_embedding
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
from services.dependencies import get_qdrant_client, get_redis_memory, get_rag_pipeline
from models.responses import (
    AskResponse, BookingResponse, ChatHistoryResponse, 
    SessionResponse, CurrentSessionResponse
)

router = APIRouter()


# --- Request model ---
class AskRequest(BaseModel):
    prompt: str
    top_k: Optional[int] = None  # override default top_k

class BookingRequest(BaseModel):
    name: str
    email: str
    date: str
    time: str
    message: Optional[str] = None




# Booking functionality - extracts booking details from natural language
def extract_booking_info(text: str) -> Dict[str, str]:
    import re
    booking_keywords = ['book', 'schedule', 'appointment', 'meeting', 'interview']
    if not any(keyword in text.lower() for keyword in booking_keywords):
        return {}
    
    info = {}
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    if email_match:
        info['email'] = email_match.group()
    
    name_patterns = [r'my name is ([A-Za-z\s]+)', r'i am ([A-Za-z\s]+)', r'name: ([A-Za-z\s]+)']
    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            info['name'] = match.group(1).strip()
            break
    
    date_match = re.search(r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b', text)
    if date_match:
        info['date'] = date_match.group()
    
    time_match = re.search(r'\b(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)\b', text)
    if time_match:
        info['time'] = time_match.group()
    
    return info

def store_booking(session_id: str, booking_info: Dict[str, str], redis_memory: RedisMemory) -> None:
    booking_key = f"booking:{session_id}:{uuid.uuid4()}"
    redis_memory.r.hset(booking_key, mapping=booking_info)
    redis_memory.r.expire(booking_key, 86400 * 7)

# Session management - handles multi-document chat sessions
def get_current_session(redis_memory: RedisMemory) -> Optional[str]:
    """Get the current active session from Redis"""
    return redis_memory.r.get("current_session")

def set_current_session(session_id: str, redis_memory: RedisMemory) -> None:
    """Set the current active session"""
    redis_memory.r.set("current_session", session_id, ex=86400)  # 24 hours

def switch_to_latest_document(qdrant_client: QdrantClient, redis_memory: RedisMemory) -> Optional[str]:
    """Switch to the latest uploaded document's session"""
    latest_session = get_latest_session_id(qdrant_client)
    if latest_session:
        set_current_session(latest_session, redis_memory)
    return latest_session


# Vector DB session retrieval - finds latest uploaded document
def get_latest_session_id(qdrant_client: QdrantClient) -> Optional[str]:
    try:
        points, _ = qdrant_client.scroll(
            collection_name=settings.COLLECTION_NAME,
            with_payload=True,
            limit=10000
        )
        
        if not points:
            return None
            
        # Filter points that have file_index and find max
        valid_points = [p for p in points if p.payload.get("file_index") is not None]
        if not valid_points:
            return None
            
        latest_point = max(
            valid_points, 
            key=lambda p: p.payload.get("file_index", 0)
        )
        
        return latest_point.payload.get("session_id")
    except Exception as e:
        print(f"Error fetching latest session_id: {e}")
        return None

@router.post("/ask", response_model=AskResponse)
def ask(
    req: AskRequest,
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
    redis_memory: RedisMemory = Depends(get_redis_memory),
    pipeline: RAGPipeline = Depends(get_rag_pipeline)
) -> AskResponse:
    try:
        # 1️⃣ Get current session or switch to latest document
        session_id = get_current_session(redis_memory)
        if not session_id:
            session_id = switch_to_latest_document(qdrant_client, redis_memory)
            if not session_id:
                raise HTTPException(status_code=404, detail="No session found. Please ingest a file first.")

        # 2️⃣ Generate embedding for user prompt (no chunking)
        question_vector = generate_embedding(req.prompt)

        #fetch vector according to session id
        session_vectors = qdrant_client.search(
            collection_name=settings.COLLECTION_NAME,
            query_vector=question_vector,
            limit=req.top_k or settings.TOP_K,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="session_id",
                        match=MatchValue(value=session_id)
                    )
                ]
            ),
            with_payload=True
        )
        print(session_vectors)

        if not session_vectors:
            raise HTTPException(status_code=404, detail="No embeddings found for session.")

        # 4️⃣ Extract context chunks
        top_chunks = [hit.payload["text"] for hit in session_vectors if hit.payload.get("text")]

        # 5️⃣ Get chat history from Redis
        memory_rows = redis_memory.get(session_id)
        memory_text = RedisMemory.format_for_prompt(memory_rows) if memory_rows else None

        # 6️⃣ Check for booking intent
        booking_info = extract_booking_info(req.prompt)
        if booking_info:
            store_booking(session_id, booking_info, redis_memory)
            answer = f"Great! I've recorded your booking request:\n" + \
                    f"Name: {booking_info.get('name', 'Not provided')}\n" + \
                    f"Email: {booking_info.get('email', 'Not provided')}\n" + \
                    f"Date: {booking_info.get('date', 'Not provided')}\n" + \
                    f"Time: {booking_info.get('time', 'Not provided')}\n" + \
                    "Someone will contact you soon to confirm."
        else:
            # 7️⃣ Build prompt with context and memory
            history_block = memory_text if memory_text else None
            prompt = pipeline.llm.build_prompt(req.prompt, top_chunks, history_block)
            
            # 8️⃣ Generate answer
            answer = pipeline.llm.generate(prompt)

        # 9️⃣ Store in memory
        redis_memory.append(session_id, "user", req.prompt)
        redis_memory.append(session_id, "assistant", answer)

        return AskResponse(
            session_id=session_id,
            question=req.prompt,
            answer=answer,
            context_used=top_chunks[:3] if top_chunks else [],
            has_history=bool(memory_rows)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/book", response_model=BookingResponse)
def book_interview(
    req: BookingRequest,
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
    redis_memory: RedisMemory = Depends(get_redis_memory)
) -> BookingResponse:
    try:
        session_id = get_latest_session_id(qdrant_client)
        if not session_id:
            raise HTTPException(status_code=404, detail="No session found.")
        
        booking_info = {
            "name": req.name,
            "email": req.email,
            "date": req.date,
            "time": req.time,
            "message": req.message or ""
        }
        
        store_booking(session_id, booking_info, redis_memory)
        
        return BookingResponse(
            message="Booking request submitted successfully",
            booking_info=booking_info,
            session_id=session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{session_id}", response_model=ChatHistoryResponse)
def get_chat_history(
    session_id: str, 
    limit: Optional[int] = None,
    redis_memory: RedisMemory = Depends(get_redis_memory)
) -> ChatHistoryResponse:
    try:
        history = redis_memory.get(session_id, limit)
        pairs = RedisMemory.as_pairs(history)
        return ChatHistoryResponse(
            session_id=session_id,
            history=pairs,
            total_messages=len(history)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/history/{session_id}", response_model=Dict[str, str])
def clear_chat_history(
    session_id: str,
    redis_memory: RedisMemory = Depends(get_redis_memory)
) -> Dict[str, str]:
    try:
        redis_memory.reset(session_id)
        return {"message": f"Chat history cleared for session {session_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/switch-document", response_model=SessionResponse)
def switch_document(
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
    redis_memory: RedisMemory = Depends(get_redis_memory)
) -> SessionResponse:
    """Switch to chat with the latest uploaded document"""
    try:
        session_id = switch_to_latest_document(qdrant_client, redis_memory)
        if not session_id:
            raise HTTPException(status_code=404, detail="No documents found")
        
        return SessionResponse(
            message="Switched to latest document",
            session_id=session_id,
            status="ready_to_chat"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/current-session", response_model=CurrentSessionResponse)
def get_current_session_info(
    redis_memory: RedisMemory = Depends(get_redis_memory)
) -> CurrentSessionResponse:
    """Get info about current active session"""
    try:
        session_id = get_current_session(redis_memory)
        if not session_id:
            return CurrentSessionResponse(current_session=None, status="no_active_session")
        
        return CurrentSessionResponse(
            current_session=session_id,
            status="active"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
