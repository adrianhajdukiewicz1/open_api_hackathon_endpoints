#!/usr/bin/env python3
"""
Run the Travel Planning API server using Uvicorn
"""

import uvicorn

if __name__ == "__main__":
    # Run the FastAPI application with Uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",  # Listen on all network interfaces
        port=8000,  # Port to listen on
        reload=True,  # Auto-reload on file changes (useful for development)
    )
