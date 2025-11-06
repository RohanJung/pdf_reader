from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams
from config import settings

def ensure_collection_exists():

    client = QdrantClient(
    url="https://77c5f8a3-9343-47e3-8cb3-651fc822ba5c.europe-west3-0.gcp.cloud.qdrant.io:6333", 
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.jG1cN7xM_6AmCilYw-638ZOeAYq-3EJsGVC0kncTc9c",
)

    collection_name = settings.COLLECTION_NAME
    existing_collections = [c.name for c in client.get_collections().collections]
    
    if collection_name not in existing_collections:
        client.recreate_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance="Cosine")
        )
        print(f"Collection '{collection_name}' created successfully")
    else:
        print(f"Collection '{collection_name}' already exists")
