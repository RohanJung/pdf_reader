from fastapi import APIRouter, UploadFile, File, Query
from fastapi.responses import JSONResponse
from services.ingestion import ingest_file
from models.responses import IngestionResponse

router = APIRouter()

@router.post("/", response_model=IngestionResponse)
async def ingest_document(
    file: UploadFile = File(...),
    chunking: str = Query("words", enum=["words", "sentences"])
) -> IngestionResponse:
    try:
        result = await ingest_file(file, chunking)
        return result
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)
