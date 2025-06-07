# YouTube Transcripts API 🎥📜

![YouTube Transcripts API](https://img.shields.io/badge/YouTube%20Transcripts%20API-v1.0-blue.svg)
![Python](https://img.shields.io/badge/Python-3.8%2B-green.svg)
![Docker](https://img.shields.io/badge/Docker-Enabled-blue.svg)
![Async](https://img.shields.io/badge/Async-Enabled-orange.svg)

Welcome to the **YouTube Transcripts API**! This high-performance, asynchronous API allows you to fetch YouTube video transcripts effortlessly. With features like adaptive rate limiting, Docker support, and robust error handling, this API is designed to meet your needs efficiently.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Rate Limiting](#rate-limiting)
- [Error Handling](#error-handling)
- [Docker Support](#docker-support)
- [Contributing](#contributing)
- [License](#license)
- [Releases](#releases)

## Features

- **High Performance**: Built with FastAPI, this API handles multiple requests seamlessly.
- **Asynchronous**: Designed for efficiency, it uses Python's `asyncio` to manage I/O-bound tasks.
- **Adaptive Rate Limiting**: Automatically adjusts request limits based on server load.
- **Robust Error Handling**: Provides meaningful error messages and HTTP status codes.
- **Docker Support**: Easy to deploy using Docker, ensuring a consistent environment.

## Installation

To get started with the YouTube Transcripts API, follow these steps:

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/ethiopia447/YouTube-Transcripts-API.git
   cd YouTube-Transcripts-API
   ```

2. **Install Dependencies**:
   Make sure you have Python 3.8 or higher installed. You can create a virtual environment and install the required packages:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   pip install -r requirements.txt
   ```

3. **Run the API**:
   You can start the API using the command:
   ```bash
   uvicorn main:app --reload
   ```

## Usage

After installation, you can access the API at `http://localhost:8000`. Use any HTTP client to make requests. Here’s a quick example using `curl`:

```bash
curl -X GET "http://localhost:8000/transcript?video_id=YOUR_VIDEO_ID"
```

Replace `YOUR_VIDEO_ID` with the ID of the YouTube video you want to fetch the transcript for.

## API Endpoints

### Get Transcript

- **Endpoint**: `/transcript`
- **Method**: `GET`
- **Query Parameters**:
  - `video_id`: The ID of the YouTube video.

**Example**:
```bash
GET /transcript?video_id=dQw4w9WgXcQ
```

### Get Supported Languages

- **Endpoint**: `/languages`
- **Method**: `GET`

This endpoint returns a list of languages supported by the API for fetching transcripts.

## Rate Limiting

The API implements adaptive rate limiting to optimize performance. If the server experiences high load, it will automatically reduce the number of allowed requests. You will receive a `429 Too Many Requests` status if you exceed the limit. 

## Error Handling

The API provides clear error messages to help you troubleshoot issues. Here are some common responses:

- **400 Bad Request**: The request was invalid. Check your parameters.
- **404 Not Found**: The requested resource could not be found.
- **500 Internal Server Error**: An unexpected error occurred on the server.

## Docker Support

You can easily run the YouTube Transcripts API using Docker. Here’s how:

1. **Build the Docker Image**:
   ```bash
   docker build -t youtube-transcripts-api .
   ```

2. **Run the Docker Container**:
   ```bash
   docker run -d -p 8000:8000 youtube-transcripts-api
   ```

The API will be available at `http://localhost:8000`.

## Contributing

We welcome contributions to improve the YouTube Transcripts API. To contribute:

1. Fork the repository.
2. Create a new branch.
3. Make your changes and commit them.
4. Push to your fork and create a pull request.

Please ensure that your code follows the existing style and includes tests where applicable.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Releases

You can find the latest releases of the YouTube Transcripts API [here](https://github.com/ethiopia447/YouTube-Transcripts-API/releases). Download the latest version and follow the installation instructions to get started.

## Conclusion

The YouTube Transcripts API offers a reliable and efficient way to fetch transcripts for YouTube videos. With its asynchronous design, adaptive rate limiting, and Docker support, it stands out as a powerful tool for developers. 

For any questions or issues, feel free to check the [Releases](https://github.com/ethiopia447/YouTube-Transcripts-API/releases) section or reach out to the community.

Happy coding!