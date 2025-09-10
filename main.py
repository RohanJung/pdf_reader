from fastapi import FastAPI
from routes.ingestion import router as ingestion_router
from routes.query import router as query_router
from routes.booking import router as booking_router
from routes.history import router as history_router
from routes.session import router as session_router
from db.migrations import create_tables

app = FastAPI(title="Document RAG API")

create_tables()

app.include_router(ingestion_router, prefix="/ingestion", tags=["Ingestion"])
app.include_router(query_router, prefix="/rag", tags=["Query"])
app.include_router(booking_router, prefix="/rag", tags=["Booking"])
app.include_router(history_router, prefix="/rag", tags=["History"])
app.include_router(session_router, prefix="/rag", tags=["Session"])