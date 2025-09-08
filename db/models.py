from sqlalchemy import Column, Integer, String
from db.db import Base

class DocumentMetadata(Base):
    __tablename__ = "document_metadata"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    chunk_index = Column(Integer)
    text = Column(String)
