import uuid
import time
from utils.file_loader import extract_text
from utils.chunking import chunk_by_words, chunk_by_sentences
from utils.embeddings import generate_embedding
from services.store import upsert_vector
from db.crud import save_metadata
from datetime import datetime, timedelta, timezone
from qdrant_client import QdrantClient
from config import settings
import redis
from models.responses import IngestionResponse

qdrant_client = QdrantClient(
    url="https://77c5f8a3-9343-47e3-8cb3-651fc822ba5c.europe-west3-0.gcp.cloud.qdrant.io:6333",
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.jG1cN7xM_6AmCilYw-638ZOeAYq-3EJsGVC0kncTc9c",
)

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

def get_next_file_index() -> int:
    try:
        points, _ = qdrant_client.scroll(
            collection_name=settings.COLLECTION_NAME,
            with_payload=True,
            limit=10000
        )
        
        if not points:
            return 1
            
        max_index = max(
            (p.payload.get("file_index", 0) for p in points),
            default=0
        )
        return max_index + 1
    except Exception as e:
        print(f"Error getting next file_index: {e}")
        return 1

async def ingest_file(file, chunking: str) -> IngestionResponse:
    global file_counter

    session_id = str(uuid.uuid4())
    print('Session ID:', session_id)

    file_index = get_next_file_index()
    print('File Index:', file_index)

    timestamp = time.time()
    nepal_tz = timezone(timedelta(hours=5, minutes=45))
    readable_date = datetime.fromtimestamp(timestamp, tz=nepal_tz)
    file_created_at = readable_date

    text = await extract_text(file)

    if chunking == "words":
        chunks = chunk_by_words(text)
    else:
        chunks = chunk_by_sentences(text)

    for idx, chunk in enumerate(chunks):
        if not chunk.strip():
            continue

        vector = generate_embedding(chunk)
        upsert_vector(
            vector_id=str(uuid.uuid4()),
            session_id=session_id,
            vector=vector,
            metadata={
                "session_id": session_id,
                "file_index": file_index,
                "file_created_at": file_created_at,
                "filename": file.filename,
                "chunk_index": idx + 1,
                "text": chunk
            }
        )

        save_metadata(file.filename, idx + 1, chunk)
    
    redis_client.set("current_session", session_id, ex=86400)  

    return IngestionResponse(
        session_id=session_id,
        file_index=file_index,
        filename=file.filename,
        num_chunks=len(chunks),
        status="Stored successfully",
        created_at=file_created_at
    )
