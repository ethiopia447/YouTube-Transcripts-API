# YouTube Transcript API

A high-performance, asynchronous API for fetching YouTube video transcripts with advanced rate limiting and IP protection mechanisms.

## Features

- 🚀 Asynchronous processing with concurrent request handling
- 🔄 Adaptive rate limiting with exponential backoff
- 🌐 Multiple language support
- 📦 Docker containerization
- 🔒 IP protection mechanisms
- 📊 Real-time statistics and monitoring
- 🏥 Health check endpoints
- 📝 Comprehensive API documentation

## Quick Start

### Using Docker (Recommended)

1. Clone the repository:

```bash
git clone https://github.com/devtitus/YouTube-Transcripts-API.git
cd youtube-transcript-api
```

2. Create environment configuration:

```bash
cp .env.example .env
# Edit .env with your preferred settings
```

3. Start the service:

```bash
docker-compose up -d
```

The API will be available at `http://localhost:5681`

### Manual Installation

1. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create environment configuration:

```bash
cp .env.example .env
# Edit .env with your preferred settings
```

4. Start the server:

```bash
python fastapi_server.py
```

## Environment Configuration

Create a `.env` file in the project root with the following structure:

```ini
# API Configuration
API_HOST=0.0.0.0
API_PORT=5681
API_WORKERS=4
API_RELOAD=false

# Rate Limiting Configuration
MAX_WORKERS=20
INITIAL_RATE=20
MIN_RATE=5
MAX_RATE=30
BACKOFF_FACTOR=1.5
RECOVERY_FACTOR=0.8
MAX_CONSECUTIVE_FAILURES=3

# CORS Configuration
CORS_ORIGINS=["*"]
CORS_METHODS=["GET", "POST", "OPTIONS"]
CORS_HEADERS=["*"]

# Logging Configuration
LOG_LEVEL=info
ENABLE_ACCESS_LOG=true

# Health Check Configuration
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_TIMEOUT=10
HEALTH_CHECK_RETRIES=3
HEALTH_CHECK_START_PERIOD=40

# Docker Configuration
DOCKER_CONTAINER_NAME=youtube-transcript-api
DOCKER_RESTART_POLICY=unless-stopped
```

## API Endpoints

### Single Transcript

```http
POST /transcript
Content-Type: application/json

{
    "video_id": "dQw4w9WgXcQ",
    "language": "en"
}
```

### Batch Transcripts

```http
POST /transcripts/batch
Content-Type: application/json

{
    "video_ids": ["dQw4w9WgXcQ", "another_video_id"],
    "language": "en"
}
```

### Text-Only Transcript

```http
GET /transcript/text?video_id=dQw4w9WgXcQ&language=en
```

### Health Check

```http
GET /health
```

### Statistics

```http
GET /stats
```

## Rate Limiting

The API implements adaptive rate limiting with the following features:

- Dynamic rate adjustment based on success/failure patterns
- Exponential backoff for failed requests
- Concurrent request management
- Automatic recovery mechanisms

## Docker Support

### Building the Image

```bash
docker build -t youtube-transcript-api .
```

### Running with Docker Compose

```bash
docker-compose up -d
```

### Viewing Logs

```bash
docker-compose logs -f
```

## Development

### Running Tests

```bash
pytest
```

### Code Style

```bash
black .
flake8
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [youtube-transcript-api](https://pypi.org/project/youtube-transcript-api/) for the base transcript functionality
- FastAPI for the web framework
- Docker for containerization

## Support

For support, please open an issue in the GitHub repository or contact the maintainers.

---

**Note**: This API is designed to respect YouTube's terms of service and implements rate limiting to prevent IP flagging. Please use responsibly.
