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
from session_service import session_service

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

# Importaciones adicionales para manejo de sesiones
import json
from fastapi.responses import JSONResponse
from fastapi import Cookie
from typing import Optional

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/research")
async def research_animal(request: Request, animal: str = Form(...)):
    """Research animal endpoint"""
    if not animal.strip():
        raise HTTPException(status_code=400, detail="Animal name is required")
    
    # Generar ID de sesión
    session_id = str(uuid.uuid4())
    
    # Inicializar datos de sesión
    session_data = {
        "animal": animal,
        "status": "processing",
        "info": None,
        "image": None,
        "errors": []
    }
    
    # Crear sesión persistente
    success = session_service.create_session(session_id, session_data)
    if not success:
        raise HTTPException(status_code=500, detail="Error al crear sesión")
    
    # Iniciar procesamiento en background
    asyncio.create_task(process_animal_research(session_id, animal))
    
    # Crear respuesta con plantilla
    response = templates.TemplateResponse(
        "result.html", 
        {
            "request": request, 
            "session_id": session_id,
            "animal": animal
        }
    )
    
    return response

@app.get("/status/{session_id}")
async def get_status(session_id: str):
    """Obtener estado del procesamiento"""
    print(f"[DEBUG] Status request for session_id: {session_id}")
    
    # Obtener datos de la sesión persistente
    session_data = session_service.get_session(session_id)
    
    # Si no hay datos de sesión
    if not session_data:
        print(f"[DEBUG] Session {session_id} not found")
        raise HTTPException(status_code=404, detail="Sesión no encontrada o expirada")
    
    print(f"[DEBUG] Session {session_id} status: {session_data.get('status')}")
    
    # Extender TTL de la sesión si está activa
    if session_data.get("status") not in ["completed", "error"]:
        session_service.extend_session(session_id)
    
    # Crear respuesta con los datos actuales
    return JSONResponse(session_data)

async def process_animal_research(session_id: str, animal: str):
    """Process animal research in background"""
    try:
        # Obtener datos actuales de la sesión
        session_data = session_service.get_session(session_id)
        if not session_data:
            print(f"[ERROR] Session {session_id} not found during processing")
            return
        
        # Update status: getting info
        session_data["status"] = "getting_info"
        session_service.update_session(session_id, session_data)
        
        # Step 1: Get animal information
        info_result = await animal_info_service.get_animal_info_async(animal)
        
        # Obtener datos actualizados
        session_data = session_service.get_session(session_id)
        if not session_data:
            return
            
        if not info_result.get('success'):
            session_data["errors"].append(f"Info error: {info_result.get('error')}")
            session_data["status"] = "error"
            session_service.update_session(session_id, session_data)
            return
        
        session_data["info"] = info_result['content']
        
        # Update status: generating image
        session_data["status"] = "generating_image"
        session_service.update_session(session_id, session_data)
        
        # Step 2: Generate image
        image_result = await image_generation_service.generate_image_async(animal)
        
        # Obtener datos actualizados nuevamente
        session_data = session_service.get_session(session_id)
        if not session_data:
            return
            
        if not image_result.get('success'):
            session_data["errors"].append(f"Image error: {image_result.get('error')}")
            session_data["status"] = "error"
            session_service.update_session(session_id, session_data)
            return
            
        session_data["image"] = image_result['image_data_url']
        
        # Complete
        session_data["status"] = "completed"
        session_service.update_session(session_id, session_data)
        
        print(f"[INFO] Successfully completed research for session {session_id}")
        
    except Exception as e:
        print(f"[ERROR] Unexpected error in session {session_id}: {str(e)}")
        # Intentar actualizar el estado de error
        session_data = session_service.get_session(session_id)
        if session_data:
            session_data["status"] = "error"
            session_data["errors"].append(f"Unexpected error: {str(e)}")
            session_service.update_session(session_id, session_data)

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
