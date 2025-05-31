from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from contextlib import asynccontextmanager
import asyncio
import time
from async_transcript_service import AsyncTranscriptService, TranscriptResult
from transcript_utils import get_transcripts_with_retry

# Global transcript service
transcript_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global transcript_service
    transcript_service = AsyncTranscriptService(max_workers=20)
    print("🚀 Transcript service initialized")
    yield
    # Shutdown
    if transcript_service:
        transcript_service.close()
    print("🔄 Transcript service closed")

app = FastAPI(
    title="YouTube Transcript API",
    description="Fast async API for fetching YouTube video transcripts with concurrent processing",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API
class TranscriptRequest(BaseModel):
    video_id: str = Field(..., description="YouTube video ID")
    language: str = Field("en", description="Target language code")

class BatchTranscriptRequest(BaseModel):
    video_ids: List[str] = Field(..., description="List of YouTube video IDs")
    language: str = Field("en", description="Target language code")

class TranscriptEntry(BaseModel):
    start: float
    text: str
    duration: Optional[float] = None

class TranscriptResponse(BaseModel):
    video_id: str
    status: str
    language: Optional[str] = None
    language_code: Optional[str] = None
    is_generated: bool = False
    is_translatable: bool = False
    transcript: Optional[List[dict]] = None
    error: Optional[str] = None
    processing_time: float = 0.0

class BatchResponse(BaseModel):
    total_processed: int
    successful: int
    failed: int
    results: List[TranscriptResponse]
    total_processing_time: float

# API Routes
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "YouTube Transcript API",
        "status": "running",
        "version": "1.0.0",
        "features": [
            "Single video transcript fetching",
            "Batch processing with concurrency",
            "Auto-translation support",
            "Multiple language support",
            "Fast async processing"
        ],        "endpoints": {
            "single": "/transcript",
            "batch": "/transcripts/batch", 
            "get_by_query": "/transcript?video_id={video_id}&language={language}",
            "text_only": "/transcript?video_id={video_id}&language={language}&format=text",
            "text_only_alt": "/transcript/text?video_id={video_id}&language={language}",
            "docs": "/docs"
        }
    }

@app.post("/transcript", response_model=TranscriptResponse)
async def get_single_transcript(request: TranscriptRequest):
    """
    Get transcript for a single video
    
    - **video_id**: YouTube video ID (11 characters)
    - **language**: Target language code (default: en)
    """
    if not transcript_service:
        raise HTTPException(status_code=503, detail="Service not available")
    
    try:
        # Use retry logic (3 attempts) to handle intermittent "no element found" errors
        result = await transcript_service.get_transcript_async(
            request.video_id, 
            request.language,
            retry_count=2  # Original attempt + 2 retries
        )
        
        return TranscriptResponse(
            video_id=result.video_id,
            status=result.status,
            language=result.language,
            language_code=result.language_code,
            is_generated=result.is_generated,
            is_translatable=result.is_translatable,
            transcript=result.transcript,
            error=result.error,
            processing_time=result.processing_time
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/transcripts/batch", response_model=BatchResponse)
async def get_batch_transcripts(request: BatchTranscriptRequest):
    """
    Get transcripts for multiple videos concurrently (max 50 videos)
    
    - **video_ids**: List of YouTube video IDs
    - **language**: Target language code (default: en)
    
    This endpoint processes all videos simultaneously for maximum speed.
    """
    if len(request.video_ids) > 50:
        raise HTTPException(
            status_code=400, 
            detail="Maximum 50 videos per batch request"
        )
    
    if not transcript_service:
        raise HTTPException(status_code=503, detail="Service not available")
    
    try:
        import time
        start_time = time.time()
        
        # Use the utility function to process all videos with retry logic
        results = await get_transcripts_with_retry(
            service=transcript_service,
            video_ids=request.video_ids,
            language=request.language,
            retry_count=2,  # Original attempt + 2 retries
            show_progress=False
        )
        
        total_time = time.time() - start_time
        
        # Convert results to response format
        response_results = [
            TranscriptResponse(
                video_id=result.video_id,
                status=result.status,
                language=result.language,
                language_code=result.language_code,
                is_generated=result.is_generated,
                is_translatable=result.is_translatable,
                transcript=result.transcript,
                error=result.error,
                processing_time=result.processing_time
            )
            for result in results
        ]
        
        successful = len([r for r in results if r.status == 'success'])
        failed = len(results) - successful
        
        return BatchResponse(
            total_processed=len(results),
            successful=successful,
            failed=failed,
            results=response_results,
            total_processing_time=total_time
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/transcript")
async def get_transcript_by_query(
    video_id: str, 
    language: str = "en", 
    format: str = "full"
):
    """
    Get transcript for a video by ID using GET method with query parameters
    
    - **video_id**: YouTube video ID (as query parameter)
    - **language**: Target language code (query parameter)
    - **format**: Output format - "full" (default, with timing) or "text" (text only)
    
    Example: /transcript?video_id=MbAojJGuds4&language=en&format=text
    """
    if not transcript_service:
        raise HTTPException(status_code=503, detail="Service not available")
    try:
        # Use retry logic (3 attempts) to handle intermittent "no element found" errors
        result = await transcript_service.get_transcript_async(video_id, language, retry_count=2)
        
        if format.lower() == "text":
            # Return text-only format
            if result.status != "success" or not result.transcript:
                return {
                    "video_id": video_id,
                    "language": result.language,
                    "text": "",
                    "error": result.error or "No transcript available"
                }
            
            # Extract and join all text entries
            full_text = " ".join([entry.get("text", "") for entry in result.transcript])
            
            return {
                "video_id": video_id,
                "language": result.language,
                "text": full_text
            }
            
        # Default full format
        return TranscriptResponse(
            video_id=result.video_id,
            status=result.status,
            language=result.language,
            language_code=result.language_code,
            is_generated=result.is_generated,
            is_translatable=result.is_translatable,
            transcript=result.transcript,
            error=result.error,
            processing_time=result.processing_time
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "YouTube Transcript API",
        "async_workers": transcript_service.executor._max_workers if transcript_service else 0
    }

@app.get("/transcript/text")
async def get_transcript_text_only(video_id: str, language: str = "en"):
    """
    Get only the transcript text content as a single string, without timing information
    
    - **video_id**: YouTube video ID (as query parameter)
    - **language**: Target language code (query parameter)
    
    Example: /transcript/text?video_id=MbAojJGuds4&language=en
    
    Returns: {"video_id": "...", "language": "...", "text": "Full transcript text..."}
    """
    if not transcript_service:
        raise HTTPException(status_code=503, detail="Service not available")
    
    try:
        # Use retry logic (3 attempts) to handle intermittent "no element found" errors
        result = await transcript_service.get_transcript_async(video_id, language, retry_count=2)
        
        if result.status != "success" or not result.transcript:
            return {
                "video_id": video_id,
                "language": result.language,
                "text": "",
                "error": result.error or "No transcript available"
            }
        
        # Extract and join all text entries into a single string
        full_text = " ".join([entry.get("text", "") for entry in result.transcript])
        
        return {
            "video_id": video_id,
            "language": result.language,
            "text": full_text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("Starting YouTube Transcript API...")
    print("API will be available at: http://localhost:5681")
    print("Interactive docs: http://localhost:5681/docs")
    print("ReDoc: http://localhost:5681/redoc")
    print("\nTo enable auto-reload, use:")
    print("uvicorn fastapi_server:app --reload --host 0.0.0.0 --port 5681")
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=5681,
        log_level="info"
    )
