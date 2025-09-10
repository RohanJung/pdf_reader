import uuid
import re
from typing import Dict
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


def store_booking(session_id: str, booking_info: Dict[str, str], redis_memory: RedisMemory) -> None:
    """Store booking information in Redis with 7-day expiry"""
    booking_key = f"booking:{session_id}:{uuid.uuid4()}"
    redis_memory.r.hset(booking_key, mapping=booking_info)
    redis_memory.r.expire(booking_key, 86400 * 7)  # 7 days


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