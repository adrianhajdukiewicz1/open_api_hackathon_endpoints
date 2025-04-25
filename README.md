# Instagram API Endpoints

A FastAPI application that provides endpoints for retrieving Instagram image URLs and other functionality.

## Features

- `get_instagram_imgs_urls` endpoint to fetch Instagram image URLs
- `second_endpoint` for demonstration purposes
- Fully typed with Pydantic models
- Error handling and logging

## Requirements

- Python 3.11+
- Rye for dependency management

## Installation

### Using Rye (Recommended)

1. Clone the repository:

```bash
git clone <repository-url>
cd open_api_hackathon_endpoints
```

2. Install dependencies using Rye:

```bash
# Install Rye if you don't have it yet
# macOS/Linux
curl -sSf https://rye-up.com/get | bash

# Install project dependencies
rye sync
```

### Running the Application

You can run the application using the provided run script:

```bash
# Make the script executable
chmod +x run.sh

# Run the server
./run.sh
```

The server will start using the Python interpreter from the Rye virtual environment:
```bash
./.venv/bin/python -m uvicorn src.app:app --host 0.0.0.0 --port 8080
```

The API will be available at http://localhost:8080


## API Endpoints

### GET /api/get_instagram_imgs_urls

Retrieves Instagram image URLs for a given username.

**Parameters:**
- `username` (required): Instagram username to fetch images from
- `limit` (optional, default=10): Maximum number of images to return

**Example Request:**
```
GET /api/get_instagram_imgs_urls?username=instagram&limit=5
```

**Example Response:**
```json
{
  "urls": [
    {
      "url": "https://instagram.com/instagram/image_1.jpg",
      "alt_text": "Image 1 for instagram"
    },
    {
      "url": "https://instagram.com/instagram/image_2.jpg",
      "alt_text": "Image 2 for instagram"
    },
    ...
  ],
  "count": 5
}
```

### GET /api/second_endpoint

A demonstration endpoint that returns status information.

**Parameters:**
- `param1` (required): First parameter
- `param2` (optional): Second parameter

**Example Request:**
```
GET /api/second_endpoint?param1=hello&param2=world
```

**Example Response:**
```json
{
  "message": "Processed request with param1: hello, param2: world",
  "status": "success",
  "timestamp": "2025-04-25T12:34:56.789123"
}
```



## Example API Calls

You can call the endpoints using curl:

```bash
# Get Instagram image URLs for a username
curl "http://localhost:8080/api/get_instagram_imgs_urls?username=instagram&limit=3"

# Call the second endpoint
curl "http://localhost:8080/api/second_endpoint?param1=hello&param2=world"
```

