# Improved error handling utility for the FastAPI server
import asyncio
from async_transcript_service import AsyncTranscriptService, TranscriptResult
from typing import List

async def get_transcripts_with_retry(
    service: AsyncTranscriptService,
    video_ids: List[str], 
    language: str = "en", 
    retry_count: int = 2,
    show_progress: bool = False
) -> List[TranscriptResult]:
    """
    Process multiple videos with retry logic for each video
    
    Args:
        service: The transcript service instance
        video_ids: List of YouTube video IDs
        language: Target language code
        retry_count: Number of retries for each video
        show_progress: Whether to show progress output
    """
    if show_progress:
        print(f"Processing {len(video_ids)} videos concurrently with retry support...")
    
    # Function to process a single video with retries
    async def process_video(video_id):
        return await service.get_transcript_async(
            video_id, 
            language, 
            retry_count=retry_count
        )
    
    # Create tasks for all videos
    tasks = [process_video(vid) for vid in video_ids]
    
    # Process all concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle any unhandled exceptions
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
    
    # Status summary
    if show_progress:
        successful = len([r for r in final_results if r.status == "success"])
        failed = len(final_results) - successful
        print(f"Completed processing {len(video_ids)} videos")
        print(f"Successful: {successful}, Failed: {failed}")
    
    return final_results
