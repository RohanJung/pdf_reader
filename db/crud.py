from db.db import SessionLocal
from db.models import DocumentMetadata

def save_metadata(filename: str, chunk_index: int, text: str):
    db = SessionLocal()
    doc = DocumentMetadata(filename=filename, chunk_index=chunk_index, text=text)
    db.add(doc)
    db.commit()
    db.close()

def get_all_metadata():
    """
    Fetch all document chunks from Postgres.
    """
    db = SessionLocal()
    try:
        results = db.query(DocumentMetadata).all()
        return [
            {
                "filename": r.filename,
                "chunk_index": r.chunk_index,
                "text": r.text
            } for r in results
        ]
    finally:
        db.close()

