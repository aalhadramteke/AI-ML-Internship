import os
import shutil
import tempfile
from typing import List, Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException, status
from pydantic import BaseModel, Field
import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
from transformers import pipeline
import PyPDF2

# --- Configuration ---
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {".pdf", ".txt"}
ALLOWED_MIME_TYPES = {"application/pdf", "text/plain"}
CHUNK_SIZE = 600  # Smaller chunks are often more precise for RAG
CHUNK_OVERLAP = 100

# Initialize FastAPI
app = FastAPI(title="Production RAG API v2")

# --- AI Models ---
# 1. High-quality lightweight embedding model from Hugging Face
EMBEDDING_MODEL_NAME = 'all-mpnet-base-v2'
emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL_NAME)

# 2. Extremely lightweight Generative model for answering questions
# flan-t5-small is an encoder-decoder model. In newer transformers, we use "text2text-generation"
# but some versions require specific handling. Let's use a more robust loading method.
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

model_name = "google/flan-t5-small"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

def generate_answer(prompt):
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(**inputs, max_new_tokens=128)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

# Initialize Vector Store
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# --- DATABASE RESET ---
# This ensures that when you restart the server, old embeddings from different
# models are cleared to prevent irrelevant results.
try:
    chroma_client.delete_collection(name="rag_collection")
except:
    pass

collection = chroma_client.get_or_create_collection(name="rag_collection", embedding_function=emb_fn)

# --- Schemas ---
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, example="What is the main topic of the document?")

class QueryResponse(BaseModel):
    answer: str
    sources: List[str]

# --- Utilities ---
def extract_text(file_path: str, filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".txt":
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    elif ext == ".pdf":
        text = ""
        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text
    else:
        raise ValueError("Unsupported file extension")

def split_text_smart(text: str) -> List[str]:
    """Splits text by paragraphs first to keep semantic meaning together."""
    paragraphs = text.split('\n')
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para: continue

        if len(current_chunk) + len(para) <= CHUNK_SIZE:
            current_chunk += para + " "
        else:
            chunks.append(current_chunk.strip())
            current_chunk = para + " "

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

# --- Endpoints ---

@app.post("/ingest", status_code=status.HTTP_201_CREATED)
async def ingest_file(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Allowed: {ALLOWED_EXTENSIONS}")

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"Allowed: {ALLOWED_MIME_TYPES}")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(content)
            temp_path = tmp.name

        text = extract_text(temp_path, file.filename)
        if not text.strip():
            raise HTTPException(status_code=400, detail="No extractable text")

        chunks = split_text_smart(text)
        ids = [f"{file.filename}_{i}" for i in range(len(chunks))]
        metadatas = [{"source": file.filename} for i in range(len(chunks))]

        collection.add(documents=chunks, ids=ids, metadatas=metadatas)
        return {"message": f"Ingested {len(chunks)} semantic chunks from {file.filename}"}

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    try:
        # 1. Retrieve most relevant chunks
        results = collection.query(query_texts=[request.query], n_results=3)
        docs = results.get("documents", [[]])[0]

        if not docs:
            return QueryResponse(answer="I couldn't find any relevant information in the documents.", sources=[])

        # 2. Build a prompt for the lightweight LLM
        # We combine the retrieved chunks into a context block
        context = " ".join(docs)
        prompt = f"Question: {request.query} Context: {context} Answer:"

        # 3. Generate a natural language answer
        answer = generate_answer(prompt)

        return QueryResponse(answer=answer, sources=docs)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
