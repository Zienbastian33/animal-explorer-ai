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

# En Vercel, necesitamos una solución más resistente para las sesiones en serverless
# Usaremos cadenas JSON en cookies para almacenar datos entre solicitudes
import json
from fastapi.responses import JSONResponse
from fastapi import Cookie
from typing import Optional

# Constantes para las cookies
SESSION_COOKIE = "animal_explorer_session"
SESSION_TTL = 3600  # 1 hora en segundos

# Almacenamiento temporal en memoria (sigue siendo útil para operaciones dentro de una misma función)
sessions = {}

def set_session_cookie(response: JSONResponse, session_id: str, data: dict):
    """Establece una cookie con los datos de sesión"""
    # Crear una versión simplificada para la cookie (solo lo necesario)
    cookie_data = {
        "id": session_id,
        "status": data.get("status", "unknown"),
        "created_at": data.get("created_at", time.time())
    }
    # Si hay imagen o info disponible, marcarlos
    if data.get("info"):
        cookie_data["has_info"] = True
    if data.get("image"):
        cookie_data["has_image"] = True
    
    # Establecer cookie (no incluir la imagen completa para evitar cookies enormes)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=json.dumps(cookie_data),
        max_age=SESSION_TTL,
        httponly=True,
        samesite="lax"
    )
    return response

def get_session(session_id: str) -> Dict:
    """Obtiene datos de sesión de la memoria temporal"""
    # Si existe en memoria local, usarlo
    if session_id in sessions:
        return sessions[session_id]
    
    # Sino, crear uno vacío
    return None

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
    
    # Inicializar datos de sesión con timestamp
    session_data = {
        "animal": animal,
        "status": "processing",
        "info": None,
        "image": None,
        "errors": [],
        "created_at": time.time()
    }
    
    # Guardar en memoria local (útil para procesamiento inmediato)
    sessions[session_id] = session_data
    
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
    
    # Establecer cookie inicial (para tracking)
    response = set_session_cookie(response, session_id, session_data)
    
    return response

@app.get("/status/{session_id}")
async def get_status(
    session_id: str,
    session_cookie: Optional[str] = Cookie(None, alias=SESSION_COOKIE)
):
    """Obtener estado del procesamiento"""
    print(f"[DEBUG] Status request for session_id: {session_id}")
    print(f"[DEBUG] Available sessions: {list(sessions.keys())}")
    print(f"[DEBUG] Session cookie: {session_cookie[:50] if session_cookie else 'None'}...")
    
    # Intentar obtener datos de la sesión en memoria
    session_data = get_session(session_id)
    
    # Si no se encuentra en memoria, pero existe una cookie, crear respuesta especial
    if not session_data and session_cookie:
        try:
            # Intentar cargar los datos de la cookie
            cookie_data = json.loads(session_cookie)
            if cookie_data.get("id") == session_id:
                # Si la sesión ya estaba completa, devolver un estado especial
                if cookie_data.get("status") == "completed":
                    return JSONResponse({
                        "status": "reload_required",
                        "message": "Tu sesión está completa pero se ha perdido. Recarga la página."
                    })
        except:
            pass
    
    # Si no hay datos de sesión
    if not session_data:
        raise HTTPException(status_code=404, detail="Sesión no encontrada o expirada")
    
    # Crear respuesta con los datos actuales
    response = JSONResponse(session_data)
    
    # Si la sesión está completa o tiene un error, almacenar en cookie
    if session_data.get("status") in ["completed", "error"]:
        response = set_session_cookie(response, session_id, session_data)
        
    return response

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
