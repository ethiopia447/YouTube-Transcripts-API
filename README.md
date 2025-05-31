# YouTube Transcript API - Async Version

A fast, async-powered YouTube transcript fetcher with concurrent processing and FastAPI endpoints.

## 🚀 Features

- **Async Processing**: Handle multiple requests simultaneously
- **10x+ Performance**: Concurrent transcript fetching
- **FastAPI Integration**: RESTful API with automatic documentation
- **Batch Processing**: Process up to 50 videos at once
- **Auto-translation**: Automatic translation to target languages
- **Error Handling**: Robust error handling and fallbacks
- **Multiple Interfaces**: CLI, Python API, and REST API

## 📁 Project Structure

```
YouTube Transcripts API/
├── async_transcript_service.py    # Core async service
├── async_transcript_fetcher.py    # CLI interface
├── fastapi_server.py             # REST API server
├── performance_test.py           # Performance comparison
├── api_test_client.py            # API testing script
├── transcript_fetcher.py         # Original sync version
├── requirements.txt              # Dependencies
└── README.md                     # This file
```

## 🛠️ Installation

1. **Install dependencies**:

   ```powershell
   pip install -r requirements.txt
   ```

2. **Verify installation**:
   ```powershell
   python -c "import youtube_transcript_api; print('✅ Installation successful')"
   ```

## 🎯 Usage

### 1. CLI Interface (Interactive)

Run the async CLI version:

```powershell
python async_transcript_fetcher.py
```

Choose from:

- **Single video**: Process one video
- **Batch mode**: Process multiple videos concurrently
- **Demo mode**: Test with sample videos

### 2. FastAPI Server

Start the API server:

```powershell
python fastapi_server.py
```

The API will be available at:

- **API Base**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 3. API Endpoints

#### Single Transcript (POST)

```bash
curl -X POST "http://localhost:8000/transcript" \
     -H "Content-Type: application/json" \
     -d '{"video_id": "dQw4w9WgXcQ", "language": "en"}'
```

#### Batch Processing (POST)

```bash
curl -X POST "http://localhost:8000/transcripts/batch" \
     -H "Content-Type: application/json" \
     -d '{"video_ids": ["dQw4w9WgXcQ", "jNQXAC9IVRw"], "language": "en"}'
```

#### Query Parameter Endpoint (GET)

```bash
curl "http://localhost:8000/transcript?video_id=dQw4w9WgXcQ&language=en"
```

#### Text-Only Transcript (GET)

```bash
# Option 1: Using format parameter
curl "http://localhost:8000/transcript?video_id=dQw4w9WgXcQ&format=text"

# Option 2: Using dedicated endpoint
curl "http://localhost:8000/transcript/text?video_id=dQw4w9WgXcQ"
```

### 4. Python API

```python
import asyncio
from async_transcript_service import AsyncTranscriptService

async def main():
    service = AsyncTranscriptService(max_workers=10)

    # Single video
    result = await service.get_transcript_async("dQw4w9WgXcQ")
    print(f"Status: {result.status}")

    # Multiple videos (concurrent)
    video_ids = ["dQw4w9WgXcQ", "jNQXAC9IVRw", "kJQP7kiw5Fk"]
    results = await service.get_multiple_transcripts(video_ids)

    for result in results:
        print(f"{result.video_id}: {result.status}")

    service.close()

asyncio.run(main())
```

## 📊 Performance Testing

Run the performance comparison:

```powershell
python performance_test.py
```

This will compare sync vs async performance and show the speedup.

## 🧪 API Testing

Test the API endpoints:

```powershell
# Start the server first
python fastapi_server.py

# Then in another terminal
python api_test_client.py
```

## 🔧 Configuration

### AsyncTranscriptService Parameters

- `max_workers`: Number of concurrent workers (default: 10)

### API Limits

- Batch processing: Maximum 50 videos per request
- Concurrent workers: Configurable (default: 20 for API)

## 📈 Performance Improvements

### Before (Synchronous)

- Process videos one by one
- 10 videos × 2s each = 20 seconds

### After (Asynchronous)

- Process videos concurrently
- 10 videos simultaneously = ~2-3 seconds
- **7-10x faster!** 🚀

## 🛡️ Error Handling

The service handles various error cases:

- **No transcripts found**: Returns appropriate error message
- **Transcripts disabled**: Handles disabled transcripts
- **Translation failures**: Falls back to original transcript
- **API rate limits**: Respects YouTube's API limits
- **Network errors**: Proper timeout and retry handling
- **"No element found" errors**: Automatic retry mechanism (up to 3 attempts)

### Retry Mechanism

The service includes an automatic retry mechanism that helps with intermittent YouTube API issues:

- Retries on "no element found" errors that commonly occur on first requests
- Configurable retry count (default: up to 3 attempts - original + 2 retries)
- Small delay between retry attempts for better reliability
- Works across all endpoints including batch processing

## 📝 API Response Format

```json
{
  "video_id": "dQw4w9WgXcQ",
  "status": "success",
  "language": "English",
  "language_code": "en",
  "is_generated": false,
  "is_translatable": true,
  "transcript": [
    {
      "start": 0.0,
      "text": "We're no strangers to love",
      "duration": 3.5
    }
  ],
  "error": null,
  "processing_time": 1.23
}
```

## 🔄 Migration from Sync Version

Your original `transcript_fetcher.py` is preserved. The new async version:

1. Uses the same core logic
2. Adds concurrent processing
3. Provides better error handling
4. Includes API endpoints

## 🚀 Production Deployment

For production use:

1. Configure CORS properly in `fastapi_server.py`
2. Add authentication if needed
3. Set up proper logging
4. Use a production ASGI server like Gunicorn
5. Add rate limiting
6. Monitor performance and adjust `max_workers`

## 🐛 Troubleshooting

### Common Issues

1. **"No module named 'async_transcript_service'"**

   - Make sure you're in the correct directory
   - All files should be in the same folder

2. **"Connection refused" when testing API**

   - Start the FastAPI server first: `python fastapi_server.py`
   - Check if port 8000 is available

3. **"No transcripts found"**

   - Video might not have transcripts
   - Try with a popular video (like the demo videos)

4. **Slow performance**
   - Increase `max_workers` for more concurrency
   - Check your internet connection

## 📚 Dependencies

- `fastapi`: Web framework for the API
- `uvicorn`: ASGI server for FastAPI
- `youtube-transcript-api`: Core transcript fetching
- `pydantic`: Data validation and settings
- `python-multipart`: File upload support

## 🎉 Next Steps

1. **Run performance test**: See the speed improvement
2. **Try the CLI**: Test single and batch modes
3. **Start the API**: Access the interactive docs
4. **Test with your videos**: Use your own YouTube video IDs

Happy transcript fetching! 🎬✨
