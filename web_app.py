from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import asyncio
from typing import Dict
import os
import uuid

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
app.mount("/uploads", StaticFiles(directory=config.upload_dir), name="uploads")

# Store for session data (in production, use proper session management)
sessions = {}

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
    
    # Initialize session data
    sessions[session_id] = {
        "animal": animal,
        "status": "processing",
        "info": None,
        "image": None,
        "errors": []
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
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return JSONResponse(sessions[session_id])

async def process_animal_research(session_id: str, animal: str):
    """Process animal research in background"""
    try:
        # Update status
        sessions[session_id]["status"] = "getting_info"
        
        # Step 1: Get animal information
        info_result = await animal_info_service.get_animal_info_async(animal)
        
        if info_result.get('success'):
            sessions[session_id]["info"] = info_result['content']
        else:
            sessions[session_id]["errors"].append(f"Info error: {info_result.get('error')}")
        
        # Update status
        sessions[session_id]["status"] = "generating_image"
        
        # Step 2: Generate image
        image_result = await image_generation_service.generate_image_async(animal)
        
        if image_result.get('success'):
            sessions[session_id]["image"] = f"/uploads/{image_result['filename']}"
        else:
            sessions[session_id]["errors"].append(f"Image error: {image_result.get('error')}")
        
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
