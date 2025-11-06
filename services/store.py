from config import settings
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct

client = QdrantClient(
    url="https://77c5f8a3-9343-47e3-8cb3-651fc822ba5c.europe-west3-0.gcp.cloud.qdrant.io:6333", 
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.jG1cN7xM_6AmCilYw-638ZOeAYq-3EJsGVC0kncTc9c",
)

def upsert_vector(vector_id: str, session_id: str , vector: list, metadata: dict):
    payload = metadata.copy()
    payload["session_id"] = session_id  
    print('Sucess')

    client.upsert(
        collection_name=settings.COLLECTION_NAME,
        points=[PointStruct(id=vector_id, vector=vector, payload=payload)]
    )
    return {"status": "success" }
