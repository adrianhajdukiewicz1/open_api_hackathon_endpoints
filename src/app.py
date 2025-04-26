from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from loguru import logger
from src.clients.instagram.client import get_instagram_images_urls

    
import asyncio

from .chatbot import QueueCallbackHandler, agent_executor
from fastapi.responses import StreamingResponse
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

class InvokeRequest(BaseModel):
    content: str

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
    
# initializing our application
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# streaming function
async def token_generator(content: str, streamer: QueueCallbackHandler):
    task = asyncio.create_task(agent_executor.invoke(
        input=content,
        streamer=streamer,
        verbose=True  # set to True to see verbose output in console
    ))
    # initialize various components to stream
    async for token in streamer:
        try:
            if token == "<<STEP_END>>":
                # send end of step token
                # yield "</step>"
                pass
            elif tool_calls := token.message.additional_kwargs.get("tool_calls"):
                if tool_name := tool_calls[0]["function"]["name"]:
                    # send start of step token followed by step name tokens
                    # yield f"<step><step_name>{tool_name}</step_name>"
                    pass
                if tool_args := tool_calls[0]["function"]["arguments"]:
                    # tool args are streamed directly, ensure it's properly encoded
                    yield tool_args
        except Exception as e:
            print(f"Error streaming token: {e}")
            continue
    await task

# invoke function
@app.post("/api/invoke")
async def invoke(request: InvokeRequest):
    queue: asyncio.Queue = asyncio.Queue()
    streamer = QueueCallbackHandler(queue)
    # return the streaming response
    return StreamingResponse(
        token_generator(request.content, streamer),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )