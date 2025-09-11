from typing import List, Optional
from fastapi import HTTPException
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue

from config import settings
from utils.embeddings import generate_embedding
from rag.memory import RedisMemory
from rag.pipeline import RAGPipeline
from services.session_manager import get_current_session, switch_to_latest_document
from services.booking import extract_booking_info, store_booking, format_booking_response


def search_relevant_chunks(
    question: str, 
    session_id: str, 
    qdrant_client: QdrantClient, 
    top_k: int
) -> List[str]:
    """Search for relevant document chunks using vector similarity"""
    question_vector = generate_embedding(question)
    
    session_vectors = qdrant_client.search(
        collection_name=settings.COLLECTION_NAME,
        query_vector=question_vector,
        limit=top_k,
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
    
    if not session_vectors:
        raise HTTPException(status_code=404, detail="No embeddings found for session.")
    
    return [hit.payload["text"] for hit in session_vectors if hit.payload.get("text")]


def process_rag_query(
    prompt: str,
    top_k: Optional[int],
    qdrant_client: QdrantClient,
    redis_memory: RedisMemory,
    pipeline: RAGPipeline
) -> tuple[str, str, List[str], bool]:
    """Process a RAG query and return session_id, answer, context, and history status"""
    
    # Get current session or switch to latest document
    session_id = get_current_session(redis_memory)
    if not session_id:
        session_id = switch_to_latest_document(qdrant_client, redis_memory)
        if not session_id:
            raise HTTPException(status_code=404, detail="No session found. Please ingest a file first.")

    # Search for relevant chunks
    top_chunks = search_relevant_chunks(
        prompt, 
        session_id, 
        qdrant_client, 
        top_k or settings.TOP_K
    )

    # Get chat history
    memory_rows = redis_memory.get(session_id)
    memory_text = RedisMemory.format_for_prompt(memory_rows) if memory_rows else None

    # Check for booking intent
    booking_info = extract_booking_info(prompt)
    if booking_info:
        booking_id = store_booking(session_id, booking_info, redis_memory)
        answer = f"{format_booking_response(booking_info)}\nBooking ID: {booking_id}"
    else:
        # Generate RAG response
        history_block = memory_text if memory_text else None
        rag_prompt = pipeline.llm.build_prompt(prompt, top_chunks, history_block)
        answer = pipeline.llm.generate(rag_prompt)

    # Store conversation in memory
    redis_memory.append(session_id, "user", prompt)
    redis_memory.append(session_id, "assistant", answer)

    return session_id, answer, top_chunks, bool(memory_rows)