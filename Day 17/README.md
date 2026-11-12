# Production Ready RAG API

This is a complete end-to-end Retrieval-Augmented Generation (RAG) API built with FastAPI, Sentence-Transformers, and ChromaDB.

## Features
- **Robust Ingestion**: Validates file extensions (.pdf, .txt), MIME types, file size (5MB limit), and non-empty content.
- **Text Processing**: Implements chunking with overlap to maintain context.
- **Vector Storage**: Uses ChromaDB for local persistent storage of embeddings.
- **Retrieval**: Efficient similarity search to retrieve the top $k$ most relevant context chunks.
- **Automated Testing**: Comprehensive pytest suite covering edge cases and robustness.

## Installation

1. **Navigate to the folder**:
   ```bash
   cd Day 17
   ```
2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   # Unix/macOS:
   source venv/bin/activate
   ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

Start the server using Uvicorn:
```bash
uvicorn main:app --reload
```
The API will be available at `http://127.0.0.1:8000`.

### API Endpoints
- `POST /ingest`: Upload a `.pdf` or `.txt` file to the vector store.
- `POST /query`: Provide a JSON payload `{"query": "your question"}` to retrieve relevant context.

## Executing the Test Suite

The project includes a robustness test suite to ensure stability:

```bash
pytest test_robustness.py
```

## Technical Stack
- **Framework**: FastAPI
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2`
- **Vector DB**: ChromaDB
- **PDF Parsing**: PyPDF2
- **Testing**: pytest, httpx
