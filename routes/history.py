from typing import Optional, Dict
from fastapi import APIRouter, HTTPException, Depends

from rag.memory import RedisMemory
from services.dependencies import get_redis_memory
from models.responses import ChatHistoryResponse

router = APIRouter()


@router.get("/history/{session_id}", response_model=ChatHistoryResponse)
def get_chat_history(
    session_id: str, 
    limit: Optional[int] = None,
    redis_memory: RedisMemory = Depends(get_redis_memory)
) -> ChatHistoryResponse:
    """Get chat history for a session"""
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
    """Clear chat history for a session"""
    try:
        redis_memory.reset(session_id)
        return {"message": f"Chat history cleared for session {session_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))