from config import settings
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct

client = QdrantClient(host=settings.VECTOR_DB_HOST, port=settings.VECTOR_DB_PORT)

def upsert_vector(vector_id: str, session_id: str , vector: list, metadata: dict):
    payload = metadata.copy()
    payload["session_id"] = session_id  
    print('Sucess')

    client.upsert(
        collection_name=settings.COLLECTION_NAME,
        points=[PointStruct(id=vector_id, vector=vector, payload=payload)]
    )
    return {"status": "success" }
