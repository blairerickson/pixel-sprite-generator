"""
Simple test server to verify the backend works
"""
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pathlib import Path
import uvicorn

app = FastAPI()

@app.get("/")
async def root():
    """Serve the frontend HTML"""
    frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if frontend_path.exists():
        return FileResponse(frontend_path)
    return {"message": "Frontend not found"}

@app.get("/health")
async def health():
    return {"status": "healthy", "message": "Backend is running"}

@app.get("/models")
async def models():
    return {"models": ["test_model_1", "test_model_2"]}

if __name__ == "__main__":
    print("Starting simple test server...")
    uvicorn.run(app, host="127.0.0.1", port=8010, log_level="info")
