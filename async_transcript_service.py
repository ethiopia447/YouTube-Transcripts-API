import asyncio
import time
from typing import List, Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor
from youtube_transcript_api._api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
from dataclasses import dataclass

@dataclass
class TranscriptResult:
    video_id: str
    status: str  # 'success', 'error', 'no_transcript'
    language: Optional[str] = None
    language_code: Optional[str] = None
    is_generated: bool = False
    is_translatable: bool = False
    transcript: Optional[List[Dict]] = None
    error: Optional[str] = None
    processing_time: float = 0.0
    
    def __post_init__(self):
        # Convert transcript to standard format if needed
        if self.transcript:
            try:
                # Convert each entry to a standard dictionary
                processed_transcript = []
                for entry in self.transcript:
                    if isinstance(entry, dict):
                        processed_transcript.append(entry)
                    else:
                        # Convert objects like FetchedTranscriptSnippet to dicts
                        processed_transcript.append({
                            "text": getattr(entry, "text", ""),
                            "start": getattr(entry, "start", 0.0),
                            "duration": getattr(entry, "duration", 0.0)
                        })
                self.transcript = processed_transcript
            except Exception as e:
                # Failed to convert, set to None and add error
                if not self.error:
                    self.error = f"Failed to process transcript format: {e}"
                self.transcript = None

class AsyncTranscriptService:
    def __init__(self, max_workers: int = 10):
        """
        Initialize the async transcript service
        
        Args:
            max_workers: Maximum number of concurrent transcript fetches
        """
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def get_transcript_async(self, video_id: str, target_language: str = "en", retry_count: int = 1) -> TranscriptResult:
        """
        Async wrapper for getting transcript with your existing logic
        
        Args:
            video_id: YouTube video ID
            target_language: Preferred language code (default: 'en')
            retry_count: Number of retry attempts for transient errors (default: 1)
        """
        start_time = time.time()
        loop = asyncio.get_event_loop()
        
        result = await loop.run_in_executor(
            self.executor, 
            self._get_transcript_sync, 
            video_id, 
            target_language
        )
        
        # Handle "no element found" error with retries
        if (result.status == "error" and 
            "no element found" in str(result.error) and 
            retry_count > 0):
            # Add a small delay before retrying
            await asyncio.sleep(0.5)
            print(f"Retrying transcript fetch for {video_id}, attempts left: {retry_count}")
            result = await self.get_transcript_async(
                video_id, 
                target_language, 
                retry_count - 1
            )
        
        result.processing_time = time.time() - start_time
        return result
        
    def _get_transcript_sync(self, video_id: str, target_language: str = "en") -> TranscriptResult:
        """
        Optimized transcript fetching logic
        """
        try:
            # First try direct method for speed
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[target_language])
                return TranscriptResult(
                    video_id=video_id,
                    status="success",
                    language=target_language.title(),
                    language_code=target_language,
                    transcript=transcript  # Already in list of dicts format
                )
            except NoTranscriptFound:
                pass  # Fall through to more detailed approach
                
            # Try listing all available transcripts
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            transcripts = list(transcript_list)
            
            if not transcripts:
                return TranscriptResult(
                    video_id=video_id,
                    status="no_transcript",
                    error="No transcripts found for this video in any language."
                )
            
            # Look for target language transcript first
            target_transcript = None
            for transcript in transcripts:
                if transcript.language_code == target_language:
                    target_transcript = transcript
                    break
            
            # If we found the target language
            if target_transcript:
                try:
                    transcript_data = list(target_transcript.fetch())
                    # Convert FetchedTranscriptSnippet objects to dicts
                    transcript_dicts = [
                        {
                            "text": getattr(entry, "text", ""),
                            "start": getattr(entry, "start", 0.0),
                            "duration": getattr(entry, "duration", 0.0)
                        } if not isinstance(entry, dict) else entry
                        for entry in transcript_data
                    ]
                    return TranscriptResult(
                        video_id=video_id,
                        status="success",
                        language=target_transcript.language,
                        language_code=target_transcript.language_code,
                        is_generated=target_transcript.is_generated,
                        is_translatable=target_transcript.is_translatable,
                        transcript=transcript_dicts
                    )
                except Exception as e:
                    return TranscriptResult(
                        video_id=video_id,
                        status="error",
                        error=f"Error fetching {target_language} transcript: {e}"
                    )
            
            # No target language found, look for translatable transcript
            translatable_transcript = None
            for transcript in transcripts:
                if transcript.is_translatable:
                    translatable_transcript = transcript
                    break
            
            # If we have a translatable transcript, try to translate it
            if translatable_transcript:
                try:
                    # First fetch original for fallback
                    original_data = list(translatable_transcript.fetch())
                    
                    # Try to translate
                    try:
                        translated = translatable_transcript.translate(target_language)
                        translated_data = list(translated.fetch())
                        
                        # Convert FetchedTranscriptSnippet objects to dicts
                        translated_dicts = [
                            {
                                "text": getattr(entry, "text", ""),
                                "start": getattr(entry, "start", 0.0),
                                "duration": getattr(entry, "duration", 0.0)
                            } if not isinstance(entry, dict) else entry
                            for entry in translated_data
                        ]
                        return TranscriptResult(
                            video_id=video_id,
                            status="success",
                            language=f"{target_language.title()} (Translated)",
                            language_code=target_language,
                            is_generated=translatable_transcript.is_generated,
                            is_translatable=True,
                            transcript=translated_dicts
                        )
                    except Exception as e:
                        # Translation failed, use original
                        return TranscriptResult(
                            video_id=video_id,
                            status="success",
                            language=translatable_transcript.language,
                            language_code=translatable_transcript.language_code,
                            is_generated=translatable_transcript.is_generated,
                            is_translatable=True,
                            transcript=[
                                {
                                    "text": getattr(entry, "text", ""),
                                    "start": getattr(entry, "start", 0.0),
                                    "duration": getattr(entry, "duration", 0.0)
                                } if not isinstance(entry, dict) else entry
                                for entry in original_data
                            ],
                            error=f"Translation failed: {e}. Using original transcript."
                        )
                except Exception as e:
                    return TranscriptResult(
                        video_id=video_id,
                        status="error",
                        error=f"Error fetching transcript: {e}"
                    )
            
            # Fall back to first available transcript
            try:
                selected_transcript = transcripts[0]
                transcript_data = list(selected_transcript.fetch())
                transcript_dicts = [
                    {
                        "text": getattr(entry, "text", ""),
                        "start": getattr(entry, "start", 0.0),
                        "duration": getattr(entry, "duration", 0.0)
                    } if not isinstance(entry, dict) else entry
                    for entry in transcript_data
                ]
                return TranscriptResult(
                    video_id=video_id,
                    status="success",
                    language=selected_transcript.language,
                    language_code=selected_transcript.language_code,
                    is_generated=selected_transcript.is_generated,
                    is_translatable=selected_transcript.is_translatable,
                    transcript=transcript_dicts
                )
            except Exception as e:
                return TranscriptResult(
                    video_id=video_id,
                    status="error",
                    error=f"Error fetching transcript: {e}"
                )
                
        except TranscriptsDisabled:
            return TranscriptResult(
                video_id=video_id,
                status="error",
                error="Transcripts are disabled for this video."
            )
        except Exception as e:
            return TranscriptResult(
                video_id=video_id,
                status="error",
                error=f"An error occurred: {e}"
            )
    
    async def get_multiple_transcripts(
        self, 
        video_ids: List[str], 
        target_language: str = "en",
        show_progress: bool = True
    ) -> List[TranscriptResult]:
        """
        Get transcripts for multiple videos concurrently
        
        Args:
            video_ids: List of YouTube video IDs
            target_language: Preferred language code
            show_progress: Whether to show progress updates
        """
        if show_progress:
            print(f"Processing {len(video_ids)} videos concurrently...")
        
        start_time = time.time()
        
        # Create tasks for all videos
        tasks = [
            self.get_transcript_async(video_id, target_language) 
            for video_id in video_ids
        ]
        
        # Process all concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(TranscriptResult(
                    video_id=video_ids[i],
                    status="error",
                    error=f"Unexpected error: {result}"
                ))
            else:
                final_results.append(result)
        
        total_time = time.time() - start_time
        
        if show_progress:
            successful = len([r for r in final_results if r.status == "success"])
            failed = len(final_results) - successful
            print(f"Completed in {total_time:.2f} seconds")
            print(f"Successful: {successful}, Failed: {failed}")
        
        return final_results
    
    def close(self):
        """Cleanup executor"""
        self.executor.shutdown(wait=True)

def display_transcript(transcript_data, language=None):
    """Display transcript in a readable format"""
    if not transcript_data:
        print(f"\nNo transcript data available for {language or 'Original'}")
        return
        
    print(f"\nTranscript ({language or 'Original'}):")
    print("-" * 50)
    
    # Display first entries
    display_count = min(10, len(transcript_data))
    for i in range(display_count):
        entry = transcript_data[i]
        print(f"[{entry['start']:.2f}s] {entry['text']}")
    
    if len(transcript_data) > 10:
        print(f"... and {len(transcript_data) - 10} more entries")
    
    print(f"\nTotal entries: {len(transcript_data)}")

def display_result(result: TranscriptResult):
    """Display a single transcript result"""
    print(f"\n{'='*60}")
    print(f"Video ID: {result.video_id}")
    print(f"Status: {result.status.upper()}")
    print(f"Processing time: {result.processing_time:.2f}s")
    
    if result.status == "success":
        print(f"Language: {result.language}")
        if result.is_generated:
            print("Type: Auto-generated")
        if result.is_translatable:
            print("Translatable: Yes")
        if result.error:
            print(f"Note: {result.error}")
        
        if result.transcript:
            display_transcript(result.transcript, result.language)
    else:
        print(f"Error: {result.error}")
