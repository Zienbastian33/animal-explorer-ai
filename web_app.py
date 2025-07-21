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
from rate_limiter import rate_limiter
import re

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
from typing import Optional, Tuple

def is_valid_animal(animal_info: str) -> Tuple[bool, str, list]:
    """
    Check if animal is valid based on OpenAI response
    Returns: (is_valid, reason, suggestions)
    """
    try:
        # Check for validity marker
        valid_match = re.search(r'\*\*VALIDO:\*\*\s*([^\n\r]+)', animal_info, re.IGNORECASE)
        
        if valid_match:
            validity = valid_match.group(1).strip().upper()
            
            if validity == "SI":
                return True, "", []
            elif validity == "NO":
                # Extract reason and suggestions
                reason_match = re.search(r'\*\*Razón:\*\*\s*([^\n\r]+)', animal_info, re.IGNORECASE)
                suggestions_match = re.search(r'\*\*Sugerencias:\*\*\s*([^\n\r]+)', animal_info, re.IGNORECASE)
                
                reason = reason_match.group(1).strip() if reason_match else "No es un animal válido"
                suggestions_text = suggestions_match.group(1).strip() if suggestions_match else ""
                
                # Parse suggestions - clean up brackets and split by comma
                if suggestions_text:
                    # Remove brackets if present
                    suggestions_text = suggestions_text.strip('[]')
                    # Split by comma and clean each suggestion
                    suggestions = [s.strip().strip('[]"\'') for s in suggestions_text.split(',') if s.strip()]
                else:
                    suggestions = []
                
                return False, reason, suggestions
        
        # Fallback: if no validity marker found, assume invalid
        print("[WARNING] No validity marker found in OpenAI response")
        return False, "Respuesta inesperada del sistema", []
        
    except Exception as e:
        print(f"[ERROR] Error validating animal: {e}")
        return False, "Error de validación", []

def extract_english_name(animal_info: str) -> str:
    """Extract English animal name from OpenAI response for image generation"""
    try:
        # Look for the "Nombre_EN:" field in the response
        match = re.search(r'\*\*Nombre_EN:\*\*\s*([^\n\r]+)', animal_info, re.IGNORECASE)
        
        if match:
            english_name = match.group(1).strip()
            # Clean up any markdown or extra formatting
            english_name = re.sub(r'[\*\[\]_]', '', english_name)
            english_name = english_name.strip()
            
            print(f"[DEBUG] Extracted English name: '{english_name}'")
            return english_name
        else:
            print(f"[WARNING] Could not find 'Nombre_EN:' in response")
            print(f"[DEBUG] Response content: {animal_info[:200]}...")
            return ""
            
    except Exception as e:
        print(f"[ERROR] Error extracting English name: {e}")
        return ""

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/research")
async def research_animal(request: Request, animal: str = Form(...)):
    """Research animal endpoint with rate limiting"""
    if not animal.strip():
        raise HTTPException(status_code=400, detail="Animal name is required")
    
    # 🛡️ RATE LIMITING CHECK
    allowed, limit_info = rate_limiter.check_rate_limit(request)
    
    if not allowed:
        print(f"[RATE_LIMIT] Blocked request: {limit_info}")
        
        # Preparar mensaje de error para el usuario
        error_message = limit_info.get('error', 'Rate limit exceeded')
        retry_after = limit_info.get('retry_after', 60)
        limit_type = limit_info.get('limit_type', 'unknown')
        
        # Mensaje específico según el tipo de límite
        if limit_type == "minute":
            user_message = "⏱️ Debes esperar 1 minuto entre consultas. Por favor, espera antes de intentar nuevamente."
        elif limit_type == "hour":
            user_message = f"📊 Has alcanzado el límite de 20 consultas por hora. Inténtalo en {retry_after // 60} minutos."
        elif limit_type == "day":
            user_message = f"📅 Has alcanzado el límite de 60 consultas diarias. Inténtalo mañana."
        elif limit_info.get('status') == 'blacklisted':
            user_message = "🚫 IP temporalmente bloqueada por exceso de consultas. Inténtalo más tarde."
        else:
            user_message = error_message
        
        # Crear sesión de error para mostrar el mensaje
        session_id = str(uuid.uuid4())
        error_session_data = {
            "animal": animal,
            "status": "rate_limited",
            "info": None,
            "image": None,
            "errors": [user_message],
            "rate_limit_info": limit_info
        }
        
        session_service.create_session(session_id, error_session_data)
        
        # Retornar página de resultado con error
        return templates.TemplateResponse(
            "result.html",
            {
                "request": request,
                "session_id": session_id,
                "animal": animal,
                "rate_limited": True,
                "rate_limit_message": user_message
            }
        )
    
    print(f"[RATE_LIMIT] Request allowed: {limit_info}")
    
    # Generar ID de sesión
    session_id = str(uuid.uuid4())
    
    # Inicializar datos de sesión
    session_data = {
        "animal": animal,
        "status": "processing",
        "info": None,
        "image": None,
        "errors": [],
        "rate_limit_info": limit_info  # Información para debugging
    }
    
    # Crear sesión persistente
    success = session_service.create_session(session_id, session_data)
    if not success:
        raise HTTPException(status_code=500, detail="Error al crear sesión")
    
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
    
    try:
        # Obtener datos de la sesión persistente
        session_data = session_service.get_session(session_id)
        print(f"[DEBUG] Session data retrieved: {session_data is not None}")
        
        if session_data:
            print(f"[DEBUG] Session status: {session_data.get('status')}")
        else:
            print(f"[DEBUG] No session data found for {session_id}")
    except Exception as e:
        print(f"[ERROR] Error getting session data: {e}")
        return JSONResponse({"error": "Session retrieval error", "details": str(e)}, status_code=500)
    
    # Si no hay datos de sesión
    if not session_data:
        print(f"[DEBUG] Session {session_id} not found")
        raise HTTPException(status_code=404, detail="Sesión no encontrada o expirada")
    
    print(f"[DEBUG] Session {session_id} status: {session_data.get('status')}")
    
    # ✅ NEW SERVERLESS PATTERN: Process when first status call is made
    if session_data.get("status") == "processing":
        print(f"[INFO] Starting processing for session {session_id}")
        try:
            # Process the animal research synchronously
            await process_animal_research_sync(session_id, session_data["animal"])
            print(f"[INFO] Processing completed for session {session_id}")
        except Exception as e:
            print(f"[ERROR] Processing failed for session {session_id}: {e}")
            # Update session with error
            session_data["status"] = "error"
            session_data["errors"] = [f"Processing error: {str(e)}"]
            session_service.update_session(session_id, session_data)
            return JSONResponse(session_data)
        
        # Get updated session data
        session_data = session_service.get_session(session_id)
        if not session_data:
            print(f"[ERROR] Session data lost after processing for {session_id}")
            raise HTTPException(status_code=500, detail="Processing failed - session lost")
    
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
        
        # Step 1.5: Validate if it's a real animal BEFORE generating expensive image
        is_valid, invalid_reason, suggestions = is_valid_animal(info_result['content'])
        
        if not is_valid:
            print(f"[VALIDATION] Invalid animal detected: {animal} - {invalid_reason}")
            
            # Create user-friendly error message
            error_message = f"🚫 '{animal}' no es un animal válido"
            if invalid_reason:
                error_message += f": {invalid_reason}"
            
            if suggestions:
                suggestions_text = ", ".join(suggestions[:3])  # Limit to 3 suggestions
                error_message += f"\n\n💡 ¿Quizás buscabas uno de estos?: {suggestions_text}"
            
            error_message += "\n\n🔍 Intenta con el nombre de un animal real (ej: león, elefante, águila)"
            
            session_data["status"] = "invalid_animal"
            session_data["errors"] = [error_message]
            session_data["invalid_reason"] = invalid_reason
            session_data["suggestions"] = suggestions
            session_service.update_session(session_id, session_data)
            
            print(f"[INFO] Validation complete - animal rejected: {animal}")
            return  # Stop processing here - no image generation
        
        # Animal is valid - proceed with processing
        print(f"[VALIDATION] Animal validated successfully: {animal}")
        session_data["info"] = info_result['content']
        
        # Extract English name for image generation
        english_name = extract_english_name(info_result['content'])
        if not english_name:
            print(f"[WARNING] Could not extract English name, using original: {animal}")
            english_name = animal
        else:
            print(f"[INFO] Using English name for image: '{english_name}'")
        
        # Update status: generating image (only for valid animals)
        session_data["status"] = "generating_image"
        session_service.update_session(session_id, session_data)
        
        # Step 2: Generate image with English name (cost incurred only for valid animals)
        image_result = await image_generation_service.generate_image_async(english_name)
        
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

@app.get("/api/rate-limits")
async def get_rate_limits(request: Request):
    """Obtener estado actual de rate limits para el usuario"""
    try:
        status = rate_limiter.get_rate_limit_status(request)
        return JSONResponse(status)
    except Exception as e:
        return JSONResponse({
            "error": "Failed to get rate limit status",
            "details": str(e)
        }, status_code=500)

@app.get("/test/translation/{animal}")
async def test_translation(animal: str):
    """Test bilingual animal translation and English name extraction"""
    try:
        print(f"[DEBUG] Testing translation for: {animal}")
        
        # Get animal info with new bilingual prompt
        info_result = await animal_info_service.get_animal_info_async(animal)
        
        if info_result.get('success'):
            content = info_result['content']
            english_name = extract_english_name(content)
            
            return {
                "status": "success",
                "original_input": animal,
                "openai_response": content,
                "extracted_english_name": english_name,
                "extraction_successful": bool(english_name),
                "recommended_for_image": english_name if english_name else animal
            }
        else:
            return {
                "status": "error",
                "error": info_result.get('error'),
                "details": info_result.get('details')
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/test/validation/{animal}")
async def test_animal_validation(animal: str):
    """Test animal validation with enhanced info and validation logic"""
    try:
        print(f"[DEBUG] Testing validation for: {animal}")
        
        # Get animal info with validation
        info_result = await animal_info_service.get_animal_info_async(animal)
        
        if info_result.get('success'):
            content = info_result['content']
            is_valid, reason, suggestions = is_valid_animal(content)
            english_name = extract_english_name(content) if is_valid else ""
            
            return {
                "status": "success",
                "original_input": animal,
                "is_valid_animal": is_valid,
                "validation_reason": reason if not is_valid else "Animal válido",
                "suggestions": suggestions,
                "english_name": english_name,
                "openai_full_response": content,
                "would_generate_image": is_valid,
                "cost_savings": "No image generation cost" if not is_valid else "Image will be generated"
            }
        else:
            return {
                "status": "error",
                "error": info_result.get('error'),
                "details": info_result.get('details')
            }
            
    except Exception as e:
        return {
            "status": "error", 
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
