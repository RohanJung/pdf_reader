from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import requests
import tempfile
import os
import uuid
from rag.pipeline import RAGPipeline
from rag.memory import RedisMemory
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams, Distance, PayloadSchemaType
from services.dependencies import get_qdrant_client, get_redis_memory, get_rag_pipeline
from services.rag_query import process_rag_query
from models.responses import AskResponse, IngestionResponse
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
from rag.llm import GeminiLLM  

router = APIRouter()

# ------------------------
# Models for requests
# ------------------------
class AskRequest(BaseModel):
    prompt: str
    top_k: Optional[int] = None

class MetaAskRequest(BaseModel):
    query: str
    business_id: str
    pdf_id: str
    sender_id: str
    top_k: Optional[int] = None

class UploadFromLinkRequest(BaseModel):
    link: str
    pdf_id: str
    chunk_size: int = 500
    chunk_overlap: int = 50

class ChatWithPdfRequest(BaseModel):
    user_id: str
    pdf_id: str
    query: str
    top_k: Optional[int] = 3

# ------------------------
# Initialize embedding model
# ------------------------
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# ------------------------
# Simple text splitter
# ------------------------
def split_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - chunk_overlap if chunk_overlap > 0 else end
    return chunks

# ------------------------
# Ask endpoint
# ------------------------
@router.post("/ask", response_model=AskResponse)
def ask(
    req: AskRequest,
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
    redis_memory: RedisMemory = Depends(get_redis_memory),
    pipeline: RAGPipeline = Depends(get_rag_pipeline)
) -> AskResponse:
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

# ------------------------
# Upload PDF from link
# ------------------------
@router.post("/upload_from_link", response_model=IngestionResponse)
def upload_from_link(
    req: UploadFromLinkRequest,
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
    collection_name: str = "document",
    pipeline: RAGPipeline = Depends(get_rag_pipeline)
) -> IngestionResponse:
    try:
        if not req.link.lower().startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="Invalid URL format")

        # Download PDF
        response = requests.get(req.link, timeout=20)
        response.raise_for_status()

        if "pdf" not in response.headers.get("Content-Type", "").lower():
            raise HTTPException(status_code=400, detail="Unsupported file type")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(response.content)
            temp_path = temp_file.name

        try:
            reader = PdfReader(temp_path)
            text = "".join([page.extract_text() or "" for page in reader.pages])
            if not text.strip():
                raise HTTPException(status_code=400, detail="PDF contains no text")

            chunks = split_text(text, req.chunk_size, req.chunk_overlap)
            embeddings = embedding_model.encode(chunks, show_progress_bar=True)

            # Create collection if missing
            try:
                qdrant_client.get_collection(collection_name)
            except Exception:
                qdrant_client.recreate_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=len(embeddings[0]),
                        distance=Distance.COSINE
                    )
                )

            # Ensure pdf_id index exists (important)
            try:
                qdrant_client.create_payload_index(
                    collection_name=collection_name,
                    field_name="pdf_id",
                    field_schema=PayloadSchemaType.KEYWORD
                )
            except Exception as e:
                print(f"Index creation skipped or exists: {e}")

            # Insert data
            points = [
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=emb.tolist(),
                    payload={
                        "pdf_id": req.pdf_id,
                        "text": chunk
                    },
                )
                for emb, chunk in zip(embeddings, chunks)
            ]

            qdrant_client.upsert(collection_name=collection_name, points=points)

            return IngestionResponse(
                pdf_id=req.pdf_id,
                chunks_ingested=len(chunks),
                message=f"Ingested {len(chunks)} chunks into '{collection_name}' collection."
            )
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch file: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------------
# Chat with PDF (search using pdf_id only)
# ------------------------
@router.post("/chat_with_pdf", response_model=AskResponse)
def chat_with_pdf(
    req: ChatWithPdfRequest,
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
    redis_memory: RedisMemory = Depends(get_redis_memory),
    pipeline: RAGPipeline = Depends(get_rag_pipeline)
) -> AskResponse:
    try:
        session_id = f"{req.user_id}_{req.pdf_id}"

        # Retrieve chat history
        history_rows = redis_memory.get(session_id)
        history_block = RedisMemory.format_for_prompt(history_rows) if history_rows else None

        # Embed the query and search relevant PDF chunks
        query_embedding = embedding_model.encode([req.query])[0]
        search_results = qdrant_client.search(
            collection_name="document",
            query_vector=query_embedding.tolist(),
            query_filter={"must":[{"key":"pdf_id","match":{"value":req.pdf_id}}]},
            limit=req.top_k
        )
        context_chunks = [hit.payload["text"] for hit in search_results if "text" in hit.payload]

        if not context_chunks:
            raise HTTPException(status_code=404, detail=f"No content found for pdf_id: {req.pdf_id}")

        # Build prompt using history + retrieved chunks
        from rag.llm import GeminiLLM
        llm = GeminiLLM()
        prompt = llm.build_prompt(req.query, context_chunks, history_block)
        answer = llm.generate(prompt)

        # Save user query and assistant answer to Redis
        redis_memory.append(session_id, "user", req.query)
        redis_memory.append(session_id, "assistant", answer)

        return AskResponse(
            session_id=session_id,
            question=req.query,
            answer=answer,
            context_used=context_chunks[:3],
            has_history=bool(history_rows)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
