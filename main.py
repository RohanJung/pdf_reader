from fastapi import FastAPI
from routes.ingestion import router as ingestion_router
from routes.rag import router as rag_router
from db.migrations import create_tables

app = FastAPI(title="Document RAG API", version="1.0.0")

# Initialize database
create_tables()

# Include routers
app.include_router(ingestion_router, prefix="/ingestion", tags=["Ingestion"])
app.include_router(rag_router, prefix="/rag", tags=["RAG"])