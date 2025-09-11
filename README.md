## 🏗️ Architecture

```
├── routes/           # API endpoints (modular)
├── services/         # Business logic
├── rag/             # RAG pipeline components
├── utils/           # Utility functions
├── db/              # Database models and operations
├── models/          # Pydantic response models
└── config.py        # Configuration settings
```
## 📋 Prerequisites

- Python 3.8+
- Redis Server
- PostgreSQL
- Qdrant Vector Database
- Google Gemini API Key

##  Installation

### 1. Clone Repository
```bash
git clone 
cd pdf_reader_custom_rag
```

### 2. Create Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Infrastructure

#### Redis (Windows)
```bash

docker run -d -p 6379:6379 redis:alpine
```

#### PostgreSQL
```bash
createdb ragdb
```

#### Qdrant
```bash
docker run -p 6333:6333 qdrant/qdrant
```

### 5. Configuration

Update `config.py` with your settings:

```python
class Settings(BaseSettings):
    # Vector DB (Qdrant)
    VECTOR_DB_HOST: str = "localhost"
    VECTOR_DB_PORT: int = 6333
    
    # PostgreSQL
    POSTGRES_USER: str = "your_user"
    POSTGRES_PASSWORD: str = "your_password"
    POSTGRES_DB: str = "ragdb"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Google Gemini API
    GOOGLE_API_KEY: str = "your_api_key_here"
```

### 6. Initialize Database
```bash
python -c "from db.migrations import create_tables; create_tables()"
```

### 7. Run Application
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## 📚 API Documentation

### Base URL: `http://localhost:8000`

## 🔗 API Endpoints

### 1. Ingestion Module (`/ingestion`)

#### Upload Document
```http
POST /ingestion/


Parameters:
- file: PDF or TXT file
- chunking: "words" | "sentences"
```

**Response:**
```json
{
  "session_id": "uuid",
  "file_index": 1,
  "filename": "document.pdf",
  "num_chunks": 25,
  "status": "Stored successfully",
  "created_at": "2024-01-01T10:00:00"
}
```

### 2. Query Module (`/rag`)

#### Ask Question
```http
POST /rag/ask
Content-Type: application/json

{
  "prompt": "What is the main topic?",
  "top_k": 3  // optional
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "question": "What is the main topic?",
  "answer": "The main topic is...",
  "context_used": ["chunk1", "chunk2", "chunk3"],
  "has_history": true
}
```

### 3. Booking Module (`/rag`)

#### Create Booking
```http
POST /rag/book
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john@example.com",
  "date": "2024-01-15",
  "time": "10:30 AM",
  "message": "Optional message"
}
```

**Response:**
```json
{
  "message": "Booking request submitted successfully with ID: 1",
  "booking_info": {
    "name": "John Doe",
    "email": "john@example.com",
    "date": "2024-01-15",
    "time": "10:30 AM",
    "message": "Optional message"
  },
  "session_id": "uuid"
}
```

#### Get All Bookings
```http
GET /rag/bookings
```

**Response:**
```json
{
  "bookings": [
    ["1", "session_id", "John Doe", "john@example.com", "2024-01-15", "10:30 AM", "Optional message"],
    ["2", "session_id2", "Jane Smith", "jane@example.com", "2024-01-16", "2:00 PM", ""]
  ],
  "total_count": 2
}
```

#### Get Booking by ID
```http
GET /rag/bookings/{booking_id}
```

**Response:**
```json
["1", "session_id", "John Doe", "john@example.com", "2024-01-15", "10:30 AM", "Optional message"]
```

### 4. History Module (`/rag`)

#### Get Chat History
```http
GET /rag/history/{session_id}?limit=10
```

**Response:**
```json
{
  "session_id": "uuid",
  "history": [
    ["user", "What is this about?"],
    ["assistant", "This document is about..."]
  ],
  "total_messages": 4
}
```

#### Clear Chat History
```http
DELETE /rag/history/{session_id}
```

**Response:**
```json
{
  "message": "Chat history cleared for session uuid"
}
```

## 🧪 Testing

### Using Postman

1. Import `postman_collection_v2.json`
2. Set `base_url` variable to `http://localhost:8000`
3. Follow the test sequence:
   - **Document Upload**: Upload a document
   - **Query**: Ask questions about the document
   - **History**: Check conversation history
   - **Booking**: Test booking functionality

### Test Workflow

1. **Upload Document**
   ```bash
   curl -X POST "http://localhost:8000/ingestion/" \
     -F "file=@sample.pdf" \
     -F "chunking=words"
   ```

2. **Ask Question**
   ```bash
   curl -X POST "http://localhost:8000/rag/ask" \
     -H "Content-Type: application/json" \
     -d '{"prompt": "What is this document about?"}'
   ```

3. **Check History**
   ```bash
   curl "http://localhost:8000/rag/history/{session_id}"
   ```

