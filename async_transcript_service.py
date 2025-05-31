import asyncio
import time
from typing import List, Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor
from youtube_transcript_api._api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
from dataclasses import dataclass
import random
import math
from collections import deque
from datetime import datetime, timedelta

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
                    try:
                        if isinstance(entry, dict):
                            processed_transcript.append(entry)
                        else:
                            # Convert objects like FetchedTranscriptSnippet to dicts
                            processed_transcript.append({
                                "text": getattr(entry, "text", ""),
                                "start": getattr(entry, "start", 0.0),
                                "duration": getattr(entry, "duration", 0.0)
                            })
                    except Exception as e:
                        print(f"Warning: Failed to process transcript entry in post_init: {e}")
                        continue
                
                # Only update transcript if we have valid entries
                if processed_transcript:
                    self.transcript = processed_transcript
                else:
                    self.transcript = None
                    if not self.error:
                        self.error = "No valid transcript entries found after processing"
            except Exception as e:
                # Failed to convert, set to None and add error
                if not self.error:
                    self.error = f"Failed to process transcript format: {e}"
                self.transcript = None

class AdaptiveRateLimiter:
    def __init__(
        self,
        initial_rate: int = 30,
        min_rate: int = 5,
        max_rate: int = 50,
        window_size: int = 60,
        backoff_factor: float = 1.5,
        recovery_factor: float = 0.8,
        max_consecutive_failures: int = 5
    ):
        self.initial_rate = initial_rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.window_size = window_size
        self.backoff_factor = backoff_factor
        self.recovery_factor = recovery_factor
        self.max_consecutive_failures = max_consecutive_failures
        
        # Request tracking
        self.request_timestamps = deque(maxlen=1000)  # Store last 1000 requests
        self.success_timestamps = deque(maxlen=1000)  # Store last 1000 successes
        self.failure_timestamps = deque(maxlen=1000)  # Store last 1000 failures
        
        # State tracking
        self.current_rate = initial_rate
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.last_failure_time = None
        self.last_success_time = None
        self.lock = asyncio.Lock()
        
        # Performance metrics
        self.total_requests = 0
        self.total_successes = 0
        self.total_failures = 0
        
    def _calculate_dynamic_rate(self) -> int:
        """Calculate the current rate limit based on recent performance"""
        now = time.time()
        window_start = now - self.window_size
        
        # Count recent requests
        recent_requests = sum(1 for ts in self.request_timestamps if ts > window_start)
        recent_successes = sum(1 for ts in self.success_timestamps if ts > window_start)
        recent_failures = sum(1 for ts in self.failure_timestamps if ts > window_start)
        
        # Calculate success rate
        success_rate = recent_successes / max(1, recent_requests)
        
        # Base rate on success rate
        if success_rate > 0.95:  # Very high success rate
            target_rate = min(self.max_rate, int(self.current_rate * 1.2))
        elif success_rate > 0.8:  # Good success rate
            target_rate = min(self.max_rate, int(self.current_rate * 1.1))
        elif success_rate < 0.5:  # Poor success rate
            target_rate = max(self.min_rate, int(self.current_rate * 0.7))
        else:  # Moderate success rate
            target_rate = self.current_rate
            
        return target_rate
    
    def _calculate_backoff_time(self) -> float:
        """Calculate backoff time using exponential backoff with jitter"""
        base_delay = self.backoff_factor ** self.consecutive_failures
        jitter = random.uniform(0, 0.1 * base_delay)  # 10% jitter
        return base_delay + jitter
    
    async def acquire(self):
        """Acquire permission to make a request with adaptive rate limiting"""
        async with self.lock:
            now = time.time()
            
            # Update current rate based on recent performance
            self.current_rate = self._calculate_dynamic_rate()
              # Calculate time window
            window_start = now - self.window_size
            recent_requests = [ts for ts in self.request_timestamps if ts > window_start]
            
            if len(recent_requests) >= self.current_rate and recent_requests:
                # Calculate wait time - add safety check for empty list
                oldest_request = recent_requests[0]
                wait_time = self.window_size - (now - oldest_request)
                
                if wait_time > 0:
                    # Add jitter to prevent thundering herd
                    jitter = random.uniform(0, 0.1 * wait_time)
                    wait_time += jitter
                    
                    # Apply additional backoff if we've had recent failures
                    if self.consecutive_failures > 0:
                        wait_time *= self._calculate_backoff_time()
                    
                    await asyncio.sleep(wait_time)
            
            self.request_timestamps.append(now)
            self.total_requests += 1
    
    def record_success(self):
        """Record a successful request"""
        now = time.time()
        self.success_timestamps.append(now)
        self.last_success_time = now
        self.consecutive_successes += 1
        self.consecutive_failures = 0
        self.total_successes += 1
        
        # Gradually increase rate on success
        if self.consecutive_successes >= 3:
            self.current_rate = min(self.max_rate, int(self.current_rate * self.recovery_factor))
    
    def record_failure(self):
        """Record a failed request"""
        now = time.time()
        self.failure_timestamps.append(now)
        self.last_failure_time = now
        self.consecutive_failures += 1
        self.consecutive_successes = 0
        self.total_failures += 1
        
        # Aggressively reduce rate on failure
        if self.consecutive_failures >= self.max_consecutive_failures:
            self.current_rate = max(self.min_rate, int(self.current_rate * 0.5))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current rate limiter statistics"""
        return {
            "current_rate": self.current_rate,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "total_requests": self.total_requests,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
            "success_rate": self.total_successes / max(1, self.total_requests)
        }

class AsyncTranscriptService:
    def __init__(
        self,
        max_workers: int = 30,
        initial_rate: int = 30,
        min_rate: int = 5,
        max_rate: int = 50,
        request_timeout: float = 10.0  # Add timeout support
    ):
        """
        Initialize the async transcript service with adaptive rate limiting
        
        Args:
            max_workers: Maximum number of concurrent transcript fetches
            initial_rate: Initial requests per minute
            min_rate: Minimum requests per minute
            max_rate: Maximum requests per minute
            request_timeout: Timeout for individual requests in seconds
        """
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.request_timeout = request_timeout
        self.rate_limiter = AdaptiveRateLimiter(
            initial_rate=initial_rate,
            min_rate=min_rate,
            max_rate=max_rate
        )
        # Cache for recent successful requests to avoid duplicate API calls
        self._cache = {}
        self._cache_timeout = 300  # 5 minutes cache
    
    async def get_transcript_async(self, video_id: str, target_language: str = "en", retry_count: int = 2) -> TranscriptResult:
        """
        Async wrapper for getting transcript with adaptive rate limiting, timeout, and caching
        """
        start_time = time.time()
        
        # Check cache first
        cache_key = f"{video_id}:{target_language}"
        now = time.time()
        if cache_key in self._cache:
            cached_result, cache_time = self._cache[cache_key]
            if now - cache_time < self._cache_timeout:
                print(f"Cache hit for {video_id}")
                # Return cached result but update processing time
                cached_result.processing_time = time.time() - start_time
                return cached_result
        
        loop = asyncio.get_event_loop()
        
        # Apply rate limiting
        await self.rate_limiter.acquire()
        
        try:
            # Add timeout to prevent hanging requests
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    self.executor, 
                    self._get_transcript_sync, 
                    video_id, 
                    target_language
                ),
                timeout=self.request_timeout
            )
            
            # Record success
            self.rate_limiter.record_success()
            
            # Handle "no element found" error with adaptive backoff
            if (result.status == "error" and 
                "no element found" in str(result.error) and 
                retry_count > 0):
                # Calculate adaptive backoff time
                backoff_time = min(self.rate_limiter._calculate_backoff_time(), 2.0)  # Cap at 2 seconds
                await asyncio.sleep(backoff_time)
                print(f"Retrying transcript fetch for {video_id}, attempts left: {retry_count}")
                result = await self.get_transcript_async(
                    video_id, 
                    target_language, 
                    retry_count - 1
                )
            
            result.processing_time = time.time() - start_time
              # Cache successful results
            if result.status == "success":
                self._cache[cache_key] = (result, now)
                # Clean old cache entries
                self._clean_cache()
            
            return result
            
        except asyncio.TimeoutError:
            # Record failure
            self.rate_limiter.record_failure()
            return TranscriptResult(
                video_id=video_id,
                status="error",
                error=f"Request timeout after {self.request_timeout} seconds",
                processing_time=time.time() - start_time
            )
        except Exception as e:
            # Record failure
            self.rate_limiter.record_failure()
            return TranscriptResult(
                video_id=video_id,
                status="error",
                error=f"Unexpected error: {str(e)}",
                processing_time=time.time() - start_time
            )
    
    def _get_transcript_sync(self, video_id: str, target_language: str = "en") -> TranscriptResult:
        """
        Optimized transcript fetching logic with proper list index error handling
        """
        try:
            # First try direct method for speed
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[target_language])
                if not transcript or not isinstance(transcript, list):
                    return TranscriptResult(
                        video_id=video_id,
                        status="error",
                        error="Invalid transcript format received"
                    )
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
                    if not transcript_data or not isinstance(transcript_data, list):
                        return TranscriptResult(
                            video_id=video_id,
                            status="error",
                            error=f"Invalid transcript data format for {target_language}"
                        )
                    # Convert FetchedTranscriptSnippet objects to dicts
                    transcript_dicts = []
                    for entry in transcript_data:
                        if isinstance(entry, dict):
                            transcript_dicts.append(entry)
                        else:
                            try:
                                transcript_dicts.append({
                                    "text": getattr(entry, "text", ""),
                                    "start": getattr(entry, "start", 0.0),
                                    "duration": getattr(entry, "duration", 0.0)
                                })
                            except Exception as e:
                                print(f"Warning: Failed to process transcript entry: {e}")
                                continue
                    
                    if not transcript_dicts:
                        return TranscriptResult(
                            video_id=video_id,
                            status="error",
                            error=f"No valid transcript entries found for {target_language}"
                        )
                    
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
                    if not original_data or not isinstance(original_data, list):
                        return TranscriptResult(
                            video_id=video_id,
                            status="error",
                            error="Invalid original transcript data format"
                        )
                    
                    # Try to translate
                    try:
                        translated = translatable_transcript.translate(target_language)
                        translated_data = list(translated.fetch())
                        if not translated_data or not isinstance(translated_data, list):
                            # Use original data if translation is empty
                            transcript_dicts = []
                            for entry in original_data:
                                if isinstance(entry, dict):
                                    transcript_dicts.append(entry)
                                else:
                                    try:
                                        transcript_dicts.append({
                                            "text": getattr(entry, "text", ""),
                                            "start": getattr(entry, "start", 0.0),
                                            "duration": getattr(entry, "duration", 0.0)
                                        })
                                    except Exception as e:
                                        print(f"Warning: Failed to process original transcript entry: {e}")
                                        continue
                            
                            if not transcript_dicts:
                                return TranscriptResult(
                                    video_id=video_id,
                                    status="error",
                                    error="No valid transcript entries found in original language"
                                )
                            
                            return TranscriptResult(
                                video_id=video_id,
                                status="success",
                                language=translatable_transcript.language,
                                language_code=translatable_transcript.language_code,
                                is_generated=translatable_transcript.is_generated,
                                is_translatable=True,
                                transcript=transcript_dicts,
                                error="Translation returned empty data. Using original transcript."
                            )
                        
                        # Convert FetchedTranscriptSnippet objects to dicts
                        translated_dicts = []
                        for entry in translated_data:
                            if isinstance(entry, dict):
                                translated_dicts.append(entry)
                            else:
                                try:
                                    translated_dicts.append({
                                        "text": getattr(entry, "text", ""),
                                        "start": getattr(entry, "start", 0.0),
                                        "duration": getattr(entry, "duration", 0.0)
                                    })
                                except Exception as e:
                                    print(f"Warning: Failed to process translated transcript entry: {e}")
                                    continue
                        
                        if not translated_dicts:
                            return TranscriptResult(
                                video_id=video_id,
                                status="error",
                                error="No valid transcript entries found in translation"
                            )
                        
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
                        transcript_dicts = []
                        for entry in original_data:
                            if isinstance(entry, dict):
                                transcript_dicts.append(entry)
                            else:
                                try:
                                    transcript_dicts.append({
                                        "text": getattr(entry, "text", ""),
                                        "start": getattr(entry, "start", 0.0),
                                        "duration": getattr(entry, "duration", 0.0)
                                    })
                                except Exception as e:
                                    print(f"Warning: Failed to process original transcript entry: {e}")
                                    continue
                        
                        if not transcript_dicts:
                            return TranscriptResult(
                                video_id=video_id,
                                status="error",
                                error="No valid transcript entries found in original language"
                            )
                        
                        return TranscriptResult(
                            video_id=video_id,
                            status="success",
                            language=translatable_transcript.language,
                            language_code=translatable_transcript.language_code,
                            is_generated=translatable_transcript.is_generated,
                            is_translatable=True,
                            transcript=transcript_dicts,
                            error=f"Translation failed: {e}. Using original transcript."
                        )
                except Exception as e:
                    return TranscriptResult(
                        video_id=video_id,
                        status="error",
                        error=f"Error fetching transcript: {e}"
                    )
            
            # Fall back to first available transcript - THIS IS WHERE THE LIST INDEX ERROR LIKELY OCCURS
            try:
                if not transcripts or len(transcripts) == 0:  # FIXED: Check both conditions
                    return TranscriptResult(
                        video_id=video_id,
                        status="error",
                        error="No transcripts available"
                    )
                    
                selected_transcript = transcripts[0]  # This was causing list index out of range
                transcript_data = list(selected_transcript.fetch())
                if not transcript_data or not isinstance(transcript_data, list):
                    return TranscriptResult(
                        video_id=video_id,
                        status="error",
                        error="Invalid transcript data format"
                    )
                    
                transcript_dicts = []
                for entry in transcript_data:
                    if isinstance(entry, dict):
                        transcript_dicts.append(entry)
                    else:
                        try:
                            transcript_dicts.append({
                                "text": getattr(entry, "text", ""),
                                "start": getattr(entry, "start", 0.0),
                                "duration": getattr(entry, "duration", 0.0)
                            })
                        except Exception as e:
                            print(f"Warning: Failed to process transcript entry: {e}")
                            continue
                
                if not transcript_dicts:
                    return TranscriptResult(
                        video_id=video_id,
                        status="error",
                        error="No valid transcript entries found"
                    )
                
                return TranscriptResult(
                    video_id=video_id,
                    status="success",
                    language=selected_transcript.language,
                    language_code=selected_transcript.language_code,
                    is_generated=selected_transcript.is_generated,
                    is_translatable=selected_transcript.is_translatable,
                    transcript=transcript_dicts
                )
            except IndexError as e:
                return TranscriptResult(
                    video_id=video_id,
                    status="error",
                    error=f"List index out of range - no transcripts available: {e}"
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
                status="error",                error=f"An error occurred: {e}"
            )
    
    def _clean_cache(self):
        """Remove expired cache entries to prevent memory leaks"""
        now = time.time()
        expired_keys = []
        
        for key, (result, cache_time) in self._cache.items():
            if now - cache_time > self._cache_timeout:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
        
        # Optionally limit cache size to prevent unbounded growth
        max_cache_size = 1000
        if len(self._cache) > max_cache_size:
            # Remove oldest entries
            sorted_items = sorted(self._cache.items(), key=lambda x: x[1][1])
            items_to_remove = len(self._cache) - max_cache_size
            for i in range(items_to_remove):
                key = sorted_items[i][0]
                del self._cache[key]
    
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
