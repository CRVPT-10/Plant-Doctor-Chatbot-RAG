import os
import shutil
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from utils.config import config
from utils.logger import get_logger
from pipeline.document_loader import DocumentLoader
from pipeline.chunker import DocumentChunker
from pipeline.embedder import CachedEmbeddings
from pipeline.vector_store import VectorStoreManager
from pipeline.ingest import ingest_directory
from rag.llm_client import OllamaClient
from rag.memory import ConversationMemory
from rag.rag_chain import RAGChain
from voice.asr import SpeechToTextManager
from voice.translator import LanguageTranslator
from voice.tts import TextToSpeechManager

logger = get_logger("api_server")

app = FastAPI(
    title="Plant Doctor Chatbot API",
    description="Backend API for multilingual, voice-enabled agricultural RAG chatbot",
    version="1.0.0"
)

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG Pipeline components
logger.info("Initializing global pipeline managers...")
embeddings = CachedEmbeddings()
vector_store = VectorStoreManager(embeddings=embeddings)
llm_client = OllamaClient()
memory = ConversationMemory()
rag_chain = RAGChain(vector_store_manager=vector_store, llm_client=llm_client, memory=memory)

# Initialize Voice components
asr_manager = SpeechToTextManager()
translator = LanguageTranslator(vector_store_manager=vector_store)
tts_manager = TextToSpeechManager()

# Ensure directories exist
DOCUMENTS_DIR = config.get_absolute_path("paths.documents_dir")
PROCESSED_DIR = os.path.join(config.base_dir, "data", "processed")
os.makedirs(DOCUMENTS_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# Mount the static directory to serve generated audio files
app.mount("/static", StaticFiles(directory=PROCESSED_DIR), name="static")

# Request Models
class ChatRequest(BaseModel):
    query: str
    session_id: str = "default_session"
    language: Optional[str] = None # Optional manual language override

@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...), 
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Upload an agricultural document (PDF, DOCX, TXT, MD).
    Saves it to documents directory and schedules ingestion.
    """
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".pdf", ".docx", ".txt", ".md"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format '{ext}'. Supported formats: PDF, DOCX, TXT, MD."
        )
        
    dest_path = os.path.join(DOCUMENTS_DIR, filename)
    
    try:
        # Save file to disk
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        logger.info(f"Uploaded file saved to {dest_path}")
        
        # Incremental Ingestion: Parse, Chunk, Embed, FAISS
        # Let's run this synchronously since users expect immediate index updating, 
        # or schedule background task. For instant UI feedback, we can run it.
        # Let's run load/chunk/add immediately:
        loader = DocumentLoader()
        chunker = DocumentChunker()
        
        docs = loader.load_file(dest_path)
        chunks = chunker.chunk_documents(docs)
        vector_store.add_documents(chunks)
        
        return {
            "status": "success",
            "message": f"Successfully uploaded and indexed document: {filename}",
            "chunks_created": len(chunks)
        }
    except Exception as e:
        logger.error(f"Error handling document upload: {e}")
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise HTTPException(status_code=500, detail=f"Inference/Ingestion error: {str(e)}")

@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Processes text query through RAG pipeline.
    Applies translation routing if a language is specified.
    """
    try:
        query = request.query
        session_id = request.session_id
        lang = request.language
        
        # If no language is manual, run simple routing
        if not lang:
            # Simple fallback: English
            lang = "en"
            
        # Route query through translator (Checks native vs translate logic)
        routing_info = translator.route_query(query, lang)
        routed_query = routing_info["query"]
        retrieve_lang = routing_info["retrieve_lang"]
        needs_translation = routing_info["needs_translation"]
        
        # Query the RAG chain
        result = rag_chain.query(
            user_query=routed_query, 
            session_id=session_id, 
            lang_filter=retrieve_lang
        )
        
        final_answer = result["answer"]
        
        # If query was translated, translate the response back to original language
        if needs_translation:
            final_answer = translator.translate(
                final_answer, 
                source_lang="en", 
                target_lang=lang
            )
            
        # Generate audio file path using TTS for the final answer
        audio_url = None
        try:
            audio_filepath = tts_manager.generate_speech(final_answer, lang=lang)
            audio_filename = os.path.basename(audio_filepath)
            audio_url = f"/static/{audio_filename}"
        except Exception as tts_err:
            logger.error(f"TTS generation error in chat endpoint: {tts_err}")
            
        return {
            "query": query,
            "translated_query": routed_query if needs_translation else None,
            "answer": final_answer,
            "audio_url": audio_url,
            "sources": result["sources"],
            "confidence": result["confidence"],
            "metrics": result["metrics"]
        }
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/voice")
async def voice_chat(
    file: UploadFile = File(...),
    session_id: str = Form("default_session"),
    language: Optional[str] = Form(None)
):
    """
    Receives voice audio file, transcribes (STT), routes adaptively (Translation),
    executes RAG, synthesizes response (TTS), and returns results with audio link.
    """
    # Create a temporary file to save the uploaded audio
    temp_audio_name = f"temp_{session_id}_{file.filename}"
    temp_audio_path = os.path.join(PROCESSED_DIR, temp_audio_name)
    
    try:
        with open(temp_audio_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 1. Speech-to-Text (ASR)
        transcription, detected_lang = asr_manager.transcribe(temp_audio_path, language=language)
        
        if not transcription.strip():
            return {
                "transcription": "",
                "answer": "I could not hear anything. Please try again.",
                "audio_url": None,
                "sources": [],
                "confidence": 0.0,
                "metrics": {}
            }
            
        # 2. Adaptive Routing (Translator)
        routing_info = translator.route_query(transcription, detected_lang)
        routed_query = routing_info["query"]
        retrieve_lang = routing_info["retrieve_lang"]
        needs_translation = routing_info["needs_translation"]
        
        # 3. Query RAG Chain
        result = rag_chain.query(
            user_query=routed_query, 
            session_id=session_id, 
            lang_filter=retrieve_lang
        )
        
        final_answer = result["answer"]
        
        # 4. Translate answer back if translation occurred
        if needs_translation:
            final_answer = translator.translate(
                final_answer, 
                source_lang="en", 
                target_lang=detected_lang
            )
            
        # 5. Text-to-Speech (TTS)
        # Generate audio file path
        audio_filepath = tts_manager.generate_speech(final_answer, lang=detected_lang)
        
        # Convert absolute local path to accessible URL path
        # StaticFiles mounts 'data/processed' at '/static'
        audio_filename = os.path.basename(audio_filepath)
        audio_url = f"/static/{audio_filename}"
        
        return {
            "transcription": transcription,
            "detected_language": detected_lang,
            "translated_query": routed_query if needs_translation else None,
            "answer": final_answer,
            "audio_url": audio_url,
            "sources": result["sources"],
            "confidence": result["confidence"],
            "metrics": result["metrics"]
        }
        
    except Exception as e:
        logger.error(f"Error in voice endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup uploaded temporary audio file
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

@app.post("/embed")
async def rebuild_index():
    """
    Manually triggers full vector store rebuild from local data/documents folder.
    """
    try:
        ingest_directory(force_rebuild=True)
        return {"status": "success", "message": "FAISS Index and SQLite database successfully rebuilt."}
    except Exception as e:
        logger.error(f"Error rebuilding index: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
async def get_history(session_id: str = Query("default_session")):
    """
    Retrieves conversational memory history list for session_id.
    """
    history_turns = memory.get_all_history(session_id)
    return {
        "session_id": session_id,
        "history": [{"farmer": q, "plant_doctor": a} for q, a in history_turns]
    }

@app.delete("/history")
async def delete_history(session_id: str = Query("default_session")):
    """
    Clears memory for session_id.
    """
    memory.clear_session(session_id)
    return {"status": "success", "message": f"Cleared session memory for {session_id}."}

@app.get("/health")
async def health_check():
    """
    Quick status report of index size, database counts, and model load flags.
    """
    indexed = vector_store.get_all_indexed_documents()
    ollama_ready = llm_client.is_available()
    return {
        "status": "healthy",
        "faiss_index_ready": vector_store.vector_store is not None,
        "ollama_ready": ollama_ready,
        "documents_indexed": indexed,
        "asr_ready": asr_manager.enabled
    }
