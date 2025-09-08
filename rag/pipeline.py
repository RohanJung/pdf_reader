from typing import List
from config import settings
from rag.llm import GeminiLLM
from rag.memory import RedisMemory

class RAGPipeline:
    """Custom RAG pipeline with Google Gemini and Redis memory"""

    def __init__(self, top_k: int | None = None) -> None:
        self.top_k = top_k or settings.TOP_K
        self.memory = RedisMemory()
        self.llm = GeminiLLM()

    def reset(self, session_id: str) -> None:
        self.memory.reset(session_id)

    def history(self, session_id: str, limit: int | None = None) -> List[str]:
        return self.memory.get(session_id, limit=limit)
