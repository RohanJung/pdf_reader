from fastapi import APIRouter, HTTPException, Depends

from rag.memory import RedisMemory
from qdrant_client import QdrantClient
from services.dependencies import get_qdrant_client, get_redis_memory
from services.session_manager import get_current_session, switch_to_latest_document
from models.responses import SessionResponse, CurrentSessionResponse

router = APIRouter()


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