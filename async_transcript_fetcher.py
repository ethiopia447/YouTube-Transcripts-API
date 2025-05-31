import asyncio
from async_transcript_service import AsyncTranscriptService, display_result

async def single_video_mode():
    """Interactive mode for single video processing"""
    print("YouTube Transcript Fetcher (Async)")
    print("-" * 40)
    video_id = input("Enter YouTube Video ID: ")
    target_language = input("Enter target language (default: en): ").strip() or 'en'
    
    service = AsyncTranscriptService(max_workers=5)
    
    try:
        print(f"\nFetching transcript for {video_id}...")
        result = await service.get_transcript_async(video_id, target_language)
        display_result(result)
    finally:
        service.close()

async def batch_mode():
    """Batch processing mode for multiple videos"""
    print("YouTube Transcript Fetcher - Batch Mode (Async)")
    print("-" * 50)
    
    video_input = input("Enter YouTube Video IDs (comma-separated): ")
    video_ids = [vid.strip() for vid in video_input.split(',') if vid.strip()]
    
    if not video_ids:
        print("No valid video IDs provided.")
        return
    
    target_language = input("Enter target language (default: en): ").strip() or 'en'
    
    service = AsyncTranscriptService(max_workers=min(len(video_ids), 10))
    
    try:
        print(f"\nProcessing {len(video_ids)} videos concurrently...")
        print("This will be much faster than processing them one by one!\n")
        
        results = await service.get_multiple_transcripts(video_ids, target_language)
        
        # Display summary
        print(f"\n{'='*60}")
        print("BATCH PROCESSING SUMMARY")
        print(f"{'='*60}")
        
        successful = [r for r in results if r.status == 'success']
        failed = [r for r in results if r.status != 'success']
        
        print(f"Total videos processed: {len(results)}")
        print(f"Successful: {len(successful)}")
        print(f"Failed: {len(failed)}")
        
        if successful:
            avg_time = sum(r.processing_time for r in successful) / len(successful)
            print(f"Average processing time: {avg_time:.2f}s")
        
        # Display detailed results
        print(f"\n{'='*60}")
        print("DETAILED RESULTS")
        print(f"{'='*60}")
        
        for result in results:
            display_result(result)
    finally:
        service.close()

async def demo_mode():
    """Demo mode with sample video IDs"""
    print("YouTube Transcript Fetcher - Demo Mode (Async)")
    print("-" * 50)
    
    # Sample video IDs for demonstration
    demo_videos = [
        "dQw4w9WgXcQ",  # Rick Astley - Never Gonna Give You Up
        "jNQXAC9IVRw",  # Me at the zoo (first YouTube video)
        "kJQP7kiw5Fk",  # Luis Fonsi - Despacito
    ]
    
    print("Demo videos:")
    for i, vid in enumerate(demo_videos, 1):
        print(f"{i}. {vid}")
    
    confirm = input("\nProcess these demo videos? (y/n): ").lower()
    if confirm != 'y':
        return
    
    service = AsyncTranscriptService(max_workers=len(demo_videos))
    
    try:
        print(f"\nProcessing {len(demo_videos)} demo videos concurrently...")
        results = await service.get_multiple_transcripts(demo_videos)
        
        for result in results:
            display_result(result)
    finally:
        service.close()

def show_performance_comparison():
    """Show estimated performance improvement"""
    print("\n" + "="*60)
    print("PERFORMANCE COMPARISON")
    print("="*60)
    print("Synchronous (current): Process videos one by one")
    print("- 10 videos × 2s each = 20 seconds total")
    print()
    print("Asynchronous (new): Process videos concurrently")
    print("- 10 videos processed simultaneously = ~2-3 seconds total")
    print()
    print("Speed improvement: 7-10x faster! 🚀")
    print("="*60)

async def main():
    """Main async function"""
    show_performance_comparison()
    
    print("\nChoose mode:")
    print("1. Single video")
    print("2. Batch processing (multiple videos)")
    print("3. Demo mode (sample videos)")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == '1':
        await single_video_mode()
    elif choice == '2':
        await batch_mode()
    elif choice == '3':
        await demo_mode()
    else:
        print("Invalid choice. Please run again and select 1, 2, or 3.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
