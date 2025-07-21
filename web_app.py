from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import asyncio
from typing import Dict
import os
import uuid
import time

from ai_services import animal_info_service, image_generation_service
from config import config

# Initialize FastAPI app
app = FastAPI(
    title="Animal Explorer AI",
    description="Aplicación web para explorar animales con ChatGPT e Imagen 3",
    version="1.0.0"
)

# Setup templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
# Note: No uploads mount needed - using data URLs for images

# Store for session data with TTL (Time To Live)
sessions = {}
SESSION_TTL = 3600  # 1 hour in seconds

def cleanup_expired_sessions():
    """Remove expired sessions to prevent memory leaks"""
    current_time = time.time()
    expired_sessions = [
        session_id for session_id, data in sessions.items()
        if current_time - data.get('created_at', 0) > SESSION_TTL
    ]
    for session_id in expired_sessions:
        del sessions[session_id]

def get_session(session_id: str) -> Dict:
    """Get session data, cleaning up expired sessions first"""
    cleanup_expired_sessions()
    return sessions.get(session_id)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/research")
async def research_animal(request: Request, animal: str = Form(...)):
    """Research animal endpoint"""
    if not animal.strip():
        raise HTTPException(status_code=400, detail="Animal name is required")
    
    # Generate session ID
    session_id = str(uuid.uuid4())
    
    # Initialize session data with timestamp
    sessions[session_id] = {
        "animal": animal,
        "status": "processing",
        "info": None,
        "image": None,
        "errors": [],
        "created_at": time.time()
    }
    
    # Start background processing
    asyncio.create_task(process_animal_research(session_id, animal))
    
    return templates.TemplateResponse(
        "result.html", 
        {
            "request": request, 
            "session_id": session_id,
            "animal": animal
        }
    )

@app.get("/status/{session_id}")
async def get_status(session_id: str):
    """Get processing status"""
    session_data = get_session(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    return JSONResponse(session_data)

async def process_animal_research(session_id: str, animal: str):
    """Process animal research in background"""
    try:
        # Update status
        sessions[session_id]["status"] = "getting_info"
        
        # Step 1: Get animal information
        info_result = await animal_info_service.get_animal_info_async(animal)
        
        if not info_result.get('success'):
            sessions[session_id]["errors"].append(f"Info error: {info_result.get('error')}")
            sessions[session_id]["status"] = "error"
            return
        
        sessions[session_id]["info"] = info_result['content']
        
        # Update status
        sessions[session_id]["status"] = "generating_image"
        
        # Step 2: Generate image
        image_result = await image_generation_service.generate_image_async(animal)
        
        if not image_result.get('success'):
            sessions[session_id]["errors"].append(f"Image error: {image_result.get('error')}")
            sessions[session_id]["status"] = "error"
            return
            
        sessions[session_id]["image"] = image_result['image_data_url']
        
        # Complete
        sessions[session_id]["status"] = "completed"
        
    except Exception as e:
        sessions[session_id]["status"] = "error"
        sessions[session_id]["errors"].append(f"Unexpected error: {str(e)}")

@app.get("/api/animal/{animal}")
async def api_get_animal_info(animal: str):
    """API endpoint for getting animal info only"""
    result = await animal_info_service.get_animal_info_async(animal)
    if not result.get('success'):
        raise HTTPException(status_code=500, detail=result.get('error'))
    return result

@app.get("/api/image/{animal}")
async def api_generate_image(animal: str):
    """API endpoint for generating image only"""
    result = await image_generation_service.generate_image_async(animal)
    if not result.get('success'):
        raise HTTPException(status_code=500, detail=result.get('error'))
    return result

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Animal Explorer API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
