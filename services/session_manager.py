from typing import Optional
from qdrant_client import QdrantClient
from rag.memory import RedisMemory
from config import settings


def get_current_session(redis_memory: RedisMemory) -> Optional[str]:
    """Get the current active session from Redis"""
    return redis_memory.r.get("current_session")


def set_current_session(session_id: str, redis_memory: RedisMemory) -> None:
    """Set the current active session"""
    redis_memory.r.set("current_session", session_id, ex=86400)  # 24 hours


def get_latest_session_id(qdrant_client: QdrantClient) -> Optional[str]:
    """Find the session ID of the latest uploaded document"""
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


def switch_to_latest_document(qdrant_client: QdrantClient, redis_memory: RedisMemory) -> Optional[str]:
    """Switch to the latest uploaded document's session"""
    latest_session = get_latest_session_id(qdrant_client)
    if latest_session:
        set_current_session(latest_session, redis_memory)
    return latest_session