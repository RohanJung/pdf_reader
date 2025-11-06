from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    #qdrant
    # VECTOR_DB_HOST: str = "localhost"
    # VECTOR_DB_PORT: int = 6333
    COLLECTION_NAME: str = "document"

    #Postgres 
    POSTGRES_USER: str = "rag"
    POSTGRES_PASSWORD: str = "rag"
    POSTGRES_DB: str = "ragdb"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    #Embedding model
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    #Redis 
    REDIS_URL: str = "redis://default:9bVYBKvlGatr3XkEZUF1KXKKbrQSvCMP@redis-16235.c335.europe-west2-1.gce.redns.redis-cloud.com:16235"

    #LLM 
    GOOGLE_API_KEY: str = "AIzaSyDeIOgouRSK0-ok3LNrVZt3o9oVT__4qfw"

    #Retrieval settings
    TOP_K: int = 3
    CHUNK_SIZE_WORDS: int = 100

    @property
    def POSTGRES_URL(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/"
            f"{self.POSTGRES_DB}"
        )

    @property
    def QDRANT_URL(self) -> str:
        return f"http://{self.VECTOR_DB_HOST}:{self.VECTOR_DB_PORT}"


settings = Settings()
