from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from loguru import logger

app = FastAPI(title="Instagram API Endpoints", 
              description="API endpoints for Instagram data retrieval",
              version="1.0.0")

# Models
class InstagramImageUrl(BaseModel):
    url: str
    alt_text: Optional[str] = None

class InstagramImageResponse(BaseModel):
    urls: List[InstagramImageUrl]
    count: int

class SecondEndpointResponse(BaseModel):
    message: str
    status: str
    timestamp: str

@app.get("/")
async def root():
    return {"message": "Welcome to Instagram API Endpoints"}

@app.get("/api/get_instagram_imgs_urls", response_model=InstagramImageResponse)
async def get_instagram_imgs_urls(username: str, limit: Optional[int] = 10):
    """
    Retrieve Instagram image URLs for a given username.
    
    Args:
        username: Instagram username to fetch images from
        limit: Maximum number of images to return (default: 10)
    
    Returns:
        A list of image URLs and related metadata
    """
    try:
        logger.info(f"Fetching Instagram images for username: {username}, limit: {limit}")
        
        # This is a mock implementation. In a real application, you would connect to 
        # Instagram's API or use a scraping library to get actual data
        mock_urls = [
            InstagramImageUrl(url=f"https://instagram.com/{username}/image_{i}.jpg", 
                             alt_text=f"Image {i} for {username}")
            for i in range(1, min(limit + 1, 21))
        ]
        
        return InstagramImageResponse(urls=mock_urls, count=len(mock_urls))
    
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