from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from rag.memory import RedisMemory
from qdrant_client import QdrantClient
from services.dependencies import get_qdrant_client, get_redis_memory
from services.session_manager import get_latest_session_id
from services.booking import store_booking, get_all_bookings, get_booking_by_id
from models.responses import BookingResponse, AllBookingsResponse, BookingData

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
        
        booking_id = store_booking(session_id, booking_info, redis_memory)
        
        return BookingResponse(
            message=f"Booking request submitted successfully with ID: {booking_id}",
            booking_info=booking_info,
            session_id=session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bookings", response_model=AllBookingsResponse)
def get_all_booking_data(
    redis_memory: RedisMemory = Depends(get_redis_memory)
) -> AllBookingsResponse:
    """Get all booking data as arrays"""
    try:
        bookings_data = get_all_bookings(redis_memory)
        bookings_arrays = []
        for booking in bookings_data:
            booking_array = [
                booking.get('booking_id', ''),
                booking.get('session_id', ''),
                booking.get('name', ''),
                booking.get('email', ''),
                booking.get('date', ''),
                booking.get('time', ''),
                booking.get('message', '')
            ]
            bookings_arrays.append(booking_array)
        
        return AllBookingsResponse(
            bookings=bookings_arrays,
            total_count=len(bookings_arrays)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bookings/{booking_id}")
def get_booking_data(
    booking_id: str,
    redis_memory: RedisMemory = Depends(get_redis_memory)
):
    """Get specific booking by ID as array"""
    try:
        booking_data = get_booking_by_id(booking_id, redis_memory)
        if not booking_data:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        booking_array = [
            booking_data.get('booking_id', ''),
            booking_data.get('session_id', ''),
            booking_data.get('name', ''),
            booking_data.get('email', ''),
            booking_data.get('date', ''),
            booking_data.get('time', ''),
            booking_data.get('message', '')
        ]
        
        return booking_array
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))