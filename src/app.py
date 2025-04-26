from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from loguru import logger
from src.clients.instagram.client import get_instagram_images_urls
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Instagram API Endpoints", 
              description="API endpoints for Instagram data retrieval",
              version="1.0.0")

class InstagramImageResponse(BaseModel):
    urls: List[str]

class SecondEndpointResponse(BaseModel):
    message: str
    status: str
    timestamp: str

@app.get("/")
async def root():
    return {"message": "Welcome to Instagram API Endpoints"}

@app.get("/api/get_instagram_imgs_urls", response_model=InstagramImageResponse)
async def get_instagram_imgs_urls_endpoint(username: str, imgs_limit: Optional[int] = 2):
    """
    Retrieve Instagram image URLs for a given username.
    
    Args:
        username: Instagram username to fetch images from
        imgs_limit: Maximum number of images to return (default: 10)
    
    Returns:
        A list of image URLs
    """
    try:
        logger.info(f"Fetching Instagram images for username: {username}, limit: {imgs_limit}")
        
        # Call the actual implementation from the Instagram client
        image_urls = get_instagram_images_urls(username=username, imgs_limit=imgs_limit)
        
        return InstagramImageResponse(urls=image_urls)
    
    except Exception as e:
        logger.error(f"Error fetching Instagram images: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching Instagram images: {str(e)}")

@app.get("/api/second_endpoint", response_model=SecondEndpointResponse)
async def second_endpoint(param1: str, param2: Optional[str] = None):
    """
    Second endpoint for demonstration purposes.
    
    Args:
        param1: First parameter
        param2: Optional second parameter
    
    Returns:
        A response containing status information
    """
    import datetime
    
    try:
        logger.info(f"Second endpoint called with param1: {param1}, param2: {param2}")
        
        timestamp = datetime.datetime.now().isoformat()
        
        response = {
            "message": f"Processed request with param1: {param1}" + 
                      (f", param2: {param2}" if param2 else ""),
            "status": "success",
            "timestamp": timestamp
        }
        
        return response
    
    except Exception as e:
        logger.error(f"Error in second endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)