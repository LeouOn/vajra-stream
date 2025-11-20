#!/usr/bin/env python3
"""
Minimal test server for RNG Attunement API
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import only the RNG endpoint
from backend.app.api.v1.endpoints import rng_attunement

# Create minimal FastAPI app
app = FastAPI(
    title="RNG Attunement Test API",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include RNG router
app.include_router(
    rng_attunement.router,
    prefix="/api/v1",
    tags=["rng-attunement"]
)

@app.get("/")
async def root():
    return {
        "message": "RNG Attunement Test API",
        "status": "running"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    print("Starting RNG Attunement Test Server...")
    print("API Documentation: http://localhost:8001/docs")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )
