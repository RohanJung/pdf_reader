from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from rag.pipeline import RAGPipeline
from rag.memory import RedisMemory
from qdrant_client import QdrantClient
from services.dependencies import get_qdrant_client, get_redis_memory, get_rag_pipeline
from services.rag_query import process_rag_query
from models.responses import AskResponse

router = APIRouter()


class AskRequest(BaseModel):
    prompt: str
    top_k: Optional[int] = None


@router.post("/ask", response_model=AskResponse)
def ask(
    req: AskRequest,
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
    redis_memory: RedisMemory = Depends(get_redis_memory),
    pipeline: RAGPipeline = Depends(get_rag_pipeline)
) -> AskResponse:
    """Process user question using RAG pipeline"""
    try:
        session_id, answer, context_chunks, has_history = process_rag_query(
            req.prompt, req.top_k, qdrant_client, redis_memory, pipeline
        )
        
        return AskResponse(
            session_id=session_id,
            question=req.prompt,
            answer=answer,
            context_used=context_chunks[:3] if context_chunks else [],
            has_history=has_history
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))