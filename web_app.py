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
    """Research animal endpoint - SERVERLESS COMPATIBLE VERSION"""
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
    
    # ❌ OLD: Background task (doesn't work in serverless)
    # asyncio.create_task(process_animal_research(session_id, animal))
    
    # ✅ NEW: Process immediately and return loading page
    # The frontend will poll /status/{session_id} to get results
    
    # Start processing in a separate endpoint call pattern
    # For now, return the loading page and let frontend poll
    
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
    """Obtener estado del procesamiento - SERVERLESS COMPATIBLE VERSION"""
    print(f"[DEBUG] Status request for session_id: {session_id}")
    
    # Obtener datos de la sesión persistente
    session_data = session_service.get_session(session_id)
    
    # Si no hay datos de sesión
    if not session_data:
        print(f"[DEBUG] Session {session_id} not found")
        raise HTTPException(status_code=404, detail="Sesión no encontrada o expirada")
    
    print(f"[DEBUG] Session {session_id} status: {session_data.get('status')}")
    
    # ✅ NEW SERVERLESS PATTERN: Process when first status call is made
    if session_data.get("status") == "processing":
        print(f"[INFO] Starting processing for session {session_id}")
        # Process the animal research synchronously
        await process_animal_research_sync(session_id, session_data["animal"])
        # Get updated session data
        session_data = session_service.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=500, detail="Processing failed")
    
    # Extender TTL de la sesión si está activa
    if session_data.get("status") not in ["completed", "error"]:
        session_service.extend_session(session_id)
    
    # Crear respuesta con los datos actuales
    return JSONResponse(session_data)

async def process_animal_research_sync(session_id: str, animal: str):
    """Process animal research synchronously for serverless compatibility"""
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

@app.get("/test/openai")
async def test_openai():
    """Test OpenAI API connectivity"""
    try:
        print("[DEBUG] Testing OpenAI API connection...")
        result = await animal_info_service.get_animal_info_async("león")
        print(f"[DEBUG] OpenAI test result: {result.get('success')}")
        
        if result.get('success'):
            return {
                "status": "success",
                "message": "OpenAI API is working",
                "sample_response": result.get('content', '')[:100] + "..."
            }
        else:
            return {
                "status": "error",
                "message": "OpenAI API failed",
                "error": result.get('error'),
                "details": result.get('details')
            }
    except Exception as e:
        print(f"[ERROR] OpenAI test failed: {str(e)}")
        return {
            "status": "error",
            "message": "OpenAI test failed",
            "error": str(e)
        }

@app.get("/test/config")
async def test_config():
    """Test configuration and environment variables"""
    import os
    
    # Get raw environment variables
    raw_openai_key = os.getenv("OPENAI_API_KEY")
    raw_image_url = os.getenv("IMAGE_GENERATION_FUNCTION_URL")
    raw_redis_url = os.getenv("REDIS_URL")
    
    return {
        "raw_env_vars": {
            "OPENAI_API_KEY_set": bool(raw_openai_key),
            "OPENAI_API_KEY_length": len(raw_openai_key) if raw_openai_key else 0,
            "OPENAI_API_KEY_preview": f"{raw_openai_key[:4]}...{raw_openai_key[-4:]}" if raw_openai_key and len(raw_openai_key) > 8 else "INVALID_OR_MISSING",
            "IMAGE_GENERATION_FUNCTION_URL_set": bool(raw_image_url),
            "REDIS_URL_set": bool(raw_redis_url)
        },
        "config_vars": {
            "openai_key_set": bool(config.openai_api_key),
            "openai_key_length": len(config.openai_api_key) if config.openai_api_key else 0,
            "image_function_url_set": bool(config.image_generation_function_url),
            "openai_model": config.openai_model
        },
        "environment": os.getenv("VERCEL_ENV", "development")
    }

@app.get("/test/simple-openai")
async def test_simple_openai():
    """Simple OpenAI test without services wrapper"""
    import os
    from openai import AsyncOpenAI
    
    try:
        # Get API key directly
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            return {"error": "No API key found in environment"}
        
        # Create client directly
        client = AsyncOpenAI(api_key=api_key)
        
        # Make simple request
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "Say hello"}
            ],
            max_tokens=10
        )
        
        return {
            "success": True,
            "response": response.choices[0].message.content,
            "model": response.model
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": str(type(e))
        }

@app.get("/test/image")
async def test_image_generation():
    """Test image generation service directly"""
    try:
        print("[DEBUG] Testing image generation...")
        result = await image_generation_service.generate_image_async("león")
        print(f"[DEBUG] Image test result: {result.get('success')}")
        
        if result.get('success'):
            return {
                "status": "success",
                "message": "Image generation is working",
                "filename": result.get('filename'),
                "has_image": bool(result.get('image_data_url'))
            }
        else:
            return {
                "status": "error",
                "message": "Image generation failed",
                "error": result.get('error'),
                "details": result.get('details'),
                "url_used": result.get('url_used')
            }
    except Exception as e:
        print(f"[ERROR] Image test failed: {str(e)}")
        return {
            "status": "error",
            "message": "Image test failed",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
