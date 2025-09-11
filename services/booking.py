import uuid
import re
from typing import Dict, List
from rag.memory import RedisMemory


def extract_booking_info(text: str) -> Dict[str, str]:
    """Extract booking details from natural language text"""
    booking_keywords = ['book', 'schedule', 'appointment', 'meeting', 'interview']
    if not any(keyword in text.lower() for keyword in booking_keywords):
        return {}
    
    info = {}
    
    #email
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    if email_match:
        info['email'] = email_match.group()
    
    #name
    name_patterns = [r'my name is ([A-Za-z\s]+)', r'i am ([A-Za-z\s]+)', r'name: ([A-Za-z\s]+)']
    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            info['name'] = match.group(1).strip()
            break
    
    #date
    date_match = re.search(r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b', text)
    if date_match:
        info['date'] = date_match.group()
    
    #time
    time_match = re.search(r'\b(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)\b', text)
    if time_match:
        info['time'] = time_match.group()
    
    return info


def get_next_booking_id(redis_memory: RedisMemory) -> int:
    """Get next sequential booking ID"""
    return redis_memory.r.incr("booking_counter")


def store_booking(session_id: str, booking_info: Dict[str, str], redis_memory: RedisMemory) -> str:
    """Store booking information in Redis with 7-day expiry"""
    booking_id = get_next_booking_id(redis_memory)
    booking_key = f"booking:{session_id}:{booking_id}"
    redis_memory.r.hset(booking_key, mapping=booking_info)
    redis_memory.r.expire(booking_key, 86400 * 7)  # 7 days
    return str(booking_id)


def format_booking_response(booking_info: Dict[str, str]) -> str:
    """Format booking confirmation message"""
    return (
        f"Great! I've recorded your booking request:\n"
        f"Name: {booking_info.get('name', 'Not provided')}\n"
        f"Email: {booking_info.get('email', 'Not provided')}\n"
        f"Date: {booking_info.get('date', 'Not provided')}\n"
        f"Time: {booking_info.get('time', 'Not provided')}\n"
        "Someone will contact you soon to confirm."
    )


def get_all_bookings(redis_memory: RedisMemory) -> List[Dict[str, str]]:
    """Retrieve all booking data from Redis"""
    bookings = []
    for key in redis_memory.r.scan_iter(match="booking:*"):
        if key == "booking_counter":  # Skip the counter key
            continue
        booking_data = redis_memory.r.hgetall(key)
        if booking_data:  # Only process if data exists
            booking_data['booking_id'] = key.split(':')[-1]  # Extract numeric ID
            booking_data['session_id'] = key.split(':')[1]   # Extract session_id
            bookings.append(booking_data)
    return bookings


def get_booking_by_id(booking_id: str, redis_memory: RedisMemory) -> Dict[str, str]:
    """Retrieve specific booking by ID"""
    for key in redis_memory.r.scan_iter(match=f"booking:*:{booking_id}"):
        booking_data = redis_memory.r.hgetall(key)
        if booking_data:
            booking_data['booking_id'] = booking_id
            booking_data['session_id'] = key.split(':')[1]
            return booking_data
    return {}