from fastapi import FastAPI, HTTPException
from typing import Dict, Any
import os
from app.schemas.request import AIProcessRequest
from app.graph.pipeline import execute_pipeline

app = FastAPI(title="Smart Inbox Assistant - AI Service", version="2.0.0")

MODEL_NAME = os.getenv("AI_MODEL_NAME", "Qwen3-VL-2B-Instruct")

@app.get("/health")
def health_check():
    return {
        "status": "UP",
        "service": "ai-service",
        "model": MODEL_NAME
    }

@app.post("/ai/process")
def process_document(request: AIProcessRequest):
    try:
        response = execute_pipeline(request)
        if not response:
            raise HTTPException(status_code=500, detail="Pipeline execution failed to produce a response.")
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
