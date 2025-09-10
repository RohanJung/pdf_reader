from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from rag.memory import RedisMemory
from qdrant_client import QdrantClient
from services.dependencies import get_qdrant_client, get_redis_memory
from services.session_manager import get_latest_session_id
from services.booking import store_booking
from models.responses import BookingResponse

router = APIRouter()


class BookingRequest(BaseModel):
    name: str
    email: str
    date: str
    time: str
    message: Optional[str] = None


@router.post("/book", response_model=BookingResponse)
def book_interview(
    req: BookingRequest,
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
    redis_memory: RedisMemory = Depends(get_redis_memory)
) -> BookingResponse:
    """Direct booking endpoint"""
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