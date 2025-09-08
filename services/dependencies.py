from functools import lru_cache
from qdrant_client import QdrantClient
import redis
from config import settings
from rag.pipeline import RAGPipeline
from rag.memory import RedisMemory

@lru_cache()
def get_qdrant_client() -> QdrantClient:
    return QdrantClient(host=settings.VECTOR_DB_HOST, port=settings.VECTOR_DB_PORT)

@lru_cache()
def get_redis_client() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL, decode_responses=True)

@lru_cache()
def get_redis_memory() -> RedisMemory:
    return RedisMemory()

@lru_cache()
def get_rag_pipeline() -> RAGPipeline:
    return RAGPipeline()