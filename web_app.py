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
from cache_service import cache_service
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
    Check if animal is valid based on Gemini response
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
                
                # Parse suggestions - extract animal names from the response
                suggestions = []
                if suggestions_text:
                    # Remove everything before and including brackets/dashes
                    clean_text = suggestions_text.split(' - ')[0] if ' - ' in suggestions_text else suggestions_text
                    clean_text = clean_text.strip('[]')
                    
                    # Split by comma and clean each suggestion
                    raw_suggestions = clean_text.split(',')
                    
                    for suggestion in raw_suggestions:
                        # Clean up each suggestion extensively
                        clean_suggestion = suggestion.strip().strip('[]"\'')
                        
                        # Remove common unwanted phrases
                        unwanted_phrases = [
                            'como el ', 'como la ', 'el ', 'la ', 'un ', 'una ',
                            'Busca información sobre animales reales como el ',
                            'Busca información sobre el ', 'Busca información sobre ',
                            'información sobre ', 'animales reales como ',
                        ]
                        
                        for phrase in unwanted_phrases:
                            clean_suggestion = clean_suggestion.replace(phrase, '')
                        
                        # Remove quotes and extra whitespace
                        clean_suggestion = clean_suggestion.replace('"', '').replace("'", "").strip()
                        
                        # Only keep if it's a reasonable animal name
                        if clean_suggestion and len(clean_suggestion.strip()) > 1 and not any(x in clean_suggestion.lower() for x in ['busca', 'información', 'sobre']):
                            suggestions.append(clean_suggestion.strip())
                
                return False, reason, suggestions
        
        # Fallback: if no validity marker found, assume invalid
        print("[WARNING] No validity marker found in Gemini response")
        return False, "Respuesta inesperada del sistema", []
        
    except Exception as e:
        print(f"[ERROR] Error validating animal: {e}")
        return False, "Error de validación", []

def extract_english_name(animal_info: str) -> str:
    """Extract English animal name from Gemini response for image generation"""
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
    """Process animal research synchronously for serverless compatibility with intelligent caching"""
    try:
        # Obtener datos actuales de la sesión
        session_data = session_service.get_session(session_id)
        if not session_data:
            print(f"[ERROR] Session {session_id} not found during processing")
            return
        
        # 🚀 CACHE CHECK: Verificar si tenemos datos completos en caché
        print(f"[CACHE] Checking cache for animal: {animal}")
        cached_data = cache_service.get_complete_cached_animal(animal)
        
        if cached_data:
            print(f"[CACHE HIT] Complete data found for {animal}")
            # Usar datos cacheados - súper rápido!
            session_data["status"] = "completed"
            session_data["info"] = cached_data['info']
            session_data["image"] = cached_data['image']
            session_data["from_cache"] = True
            session_data["cached_at"] = cached_data['cached_at']
            
            # Actualizar sesión y trackear búsqueda
            session_service.update_session(session_id, session_data)
            cache_service.track_animal_search(animal)
            
            print(f"[CACHE] Served {animal} from cache - ultra fast response!")
            return
        
        # 📊 ANALYTICS: Trackear búsqueda aunque no esté en caché
        cache_service.track_animal_search(animal)
        
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
        print(f"[DEBUG] Starting validation for: {animal}")
        print(f"[DEBUG] Gemini response length: {len(info_result['content'])}")
        print(f"[DEBUG] Gemini response preview: {info_result['content'][:200]}...")
        
        is_valid, invalid_reason, suggestions = is_valid_animal(info_result['content'])
        print(f"[DEBUG] Validation result: valid={is_valid}, reason='{invalid_reason}', suggestions={suggestions}")
        
        if not is_valid:
            print(f"[VALIDATION] Invalid animal detected: {animal} - {invalid_reason}")
            print(f"[VALIDATION] Suggestions: {suggestions}")
            
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
            
            print(f"[DEBUG] Updating session with invalid_animal status")
            update_success = session_service.update_session(session_id, session_data)
            print(f"[DEBUG] Session update success: {update_success}")
            
            # Verify the session was updated
            updated_session = session_service.get_session(session_id)
            if updated_session:
                print(f"[DEBUG] Updated session status: {updated_session.get('status')}")
            else:
                print(f"[ERROR] Failed to retrieve updated session!")
            
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
        print(f"[INFO] Starting image generation for: {english_name}")
        print(f"[INFO] Timestamp: {time.time()}")
        
        try:
            # Set timeout for image generation (50 seconds to account for Vercel limits)
            image_result = await asyncio.wait_for(
                image_generation_service.generate_image_async(english_name),
                timeout=50.0
            )
            print(f"[INFO] Image generation completed at: {time.time()}")
        except asyncio.TimeoutError:
            print(f"[ERROR] Image generation timed out after 50 seconds for: {english_name}")
            image_result = {
                "success": False,
                "error": "Image generation timeout",
                "details": "The image generation took too long. This may be a temporary issue. Please try again."
            }
        except Exception as gen_error:
            print(f"[ERROR] Image generation exception: {gen_error}")
            image_result = {
                "success": False,
                "error": "Image generation error",
                "details": str(gen_error)
            }
        
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
        
        # 💾 CACHE STORAGE: Guardar datos para futuras consultas
        print(f"[CACHE] Storing data for future use: {animal}")
        
        # Cachear información del animal
        info_cached = cache_service.cache_animal_info(
            animal=animal,
            info_data=session_data["info"],
            english_name=english_name
        )
        
        # Cachear imagen del animal
        image_cached = cache_service.cache_animal_image(
            animal=animal,
            image_data_url=session_data["image"],
            english_name=english_name
        )
        
        print(f"[CACHE] Info cached: {info_cached}, Image cached: {image_cached}")
        
        # Complete
        session_data["status"] = "completed"
        session_data["cached"] = info_cached and image_cached  # Indicar si se guardó en caché
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

@app.get("/test/gemini")
async def test_gemini():
    """Test Gemini API connectivity"""
    try:
        print("[DEBUG] Testing Gemini API connection...")
        result = await animal_info_service.get_animal_info_async("león")
        print(f"[DEBUG] Gemini test result: {result.get('success')}")
        
        if result.get('success'):
            return {
                "status": "success",
                "message": "Gemini API is working",
                "sample_response": result.get('content', '')[:100] + "..."
            }
        else:
            return {
                "status": "error",
                "message": "Gemini API failed",
                "error": result.get('error'),
                "details": result.get('details')
            }
    except Exception as e:
        print(f"[ERROR] Gemini test failed: {str(e)}")
        return {
            "status": "error",
            "message": "Gemini test failed",
            "error": str(e)
        }

@app.get("/test/config")
async def test_config():
    """Test configuration and environment variables"""
    import os
    
    # Get raw environment variables
    raw_gemini_key = os.getenv("GEMINI_API_KEY")
    raw_redis_url = os.getenv("REDIS_URL")
    
    return {
        "raw_env_vars": {
            "GEMINI_API_KEY_set": bool(raw_gemini_key),
            "GEMINI_API_KEY_length": len(raw_gemini_key) if raw_gemini_key else 0,
            "GEMINI_API_KEY_preview": f"{raw_gemini_key[:4]}...{raw_gemini_key[-4:]}" if raw_gemini_key and len(raw_gemini_key) > 8 else "INVALID_OR_MISSING",
            "REDIS_URL_set": bool(raw_redis_url)
        },
        "config_vars": {
            "gemini_key_set": bool(config.gemini_api_key),
            "gemini_key_length": len(config.gemini_api_key) if config.gemini_api_key else 0,
            "gemini_text_model": config.gemini_text_model,
            "gemini_image_model": config.gemini_image_model
        },
        "environment": os.getenv("VERCEL_ENV", "development")
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

# 📊 CACHE AND ANALYTICS ENDPOINTS

@app.get("/api/cache/stats")
async def get_cache_stats():
    """Obtener estadísticas del sistema de caché"""
    try:
        stats = cache_service.get_cache_stats()
        return JSONResponse(stats)
    except Exception as e:
        return JSONResponse({
            "error": "Failed to get cache stats",
            "details": str(e)
        }, status_code=500)

@app.get("/api/popular-animals")
async def get_popular_animals(limit: int = 10):
    """Obtener animales más buscados"""
    try:
        # Limitar el número para no sobrecargar
        limit = min(limit, 50)  # Máximo 50
        popular = cache_service.get_popular_animals(limit)
        
        return JSONResponse({
            "popular_animals": popular,
            "total_count": len(popular),
            "limit_applied": limit
        })
    except Exception as e:
        return JSONResponse({
            "error": "Failed to get popular animals",
            "details": str(e)
        }, status_code=500)

@app.get("/api/cache/health")
async def cache_health_check():
    """Verificar salud del sistema de caché"""
    try:
        # Test básico de lectura/escritura
        test_key = "health_check_test"
        test_data = {"timestamp": int(time.time()), "test": True}
        
        # Intentar escribir
        cache_service._set_cache(f"test:{test_key}", test_data, 60)
        
        # Intentar leer
        retrieved = cache_service._get_cache(f"test:{test_key}")
        
        # Limpiar
        if cache_service.redis_service.redis_client:
            cache_service.redis_service.redis_client.delete(f"test:{test_key}")
        
        return JSONResponse({
            "cache_healthy": retrieved is not None,
            "redis_available": bool(cache_service.redis_service.redis_client),
            "test_successful": retrieved == test_data if retrieved else False,
            "timestamp": int(time.time())
        })
    except Exception as e:
        return JSONResponse({
            "cache_healthy": False,
            "error": str(e)
        }, status_code=500)

@app.get("/api/cache/upstash-stats")
async def get_upstash_efficiency():
    """Obtener estadísticas de eficiencia específicas para Upstash"""
    try:
        stats = cache_service.get_upstash_efficiency_stats()
        return JSONResponse(stats)
    except Exception as e:
        return JSONResponse({
            "error": "Failed to get Upstash efficiency stats",
            "details": str(e)
        }, status_code=500)

@app.delete("/api/cache/clear")
async def clear_cache_endpoint():
    """Limpiar caché expirado (solo para desarrollo/mantenimiento)"""
    try:
        result = cache_service.clear_expired_cache()
        return JSONResponse({
            "message": "Cache cleanup completed",
            "cleared_items": result["cleared_items"],
            "timestamp": result["timestamp"]
        })
    except Exception as e:
        return JSONResponse({
            "error": "Failed to clear cache",
            "details": str(e)
        }, status_code=500)

@app.get("/test/gemini-only/{animal}")
async def test_gemini_only(animal: str):
    """
    🧪 Endpoint de prueba: Genera imagen solo con Gemini (sin OpenAI)
    Útil para verificar que Gemini funciona mientras configuras OpenAI
    """
    try:
        print(f"[TEST] Generando imagen solo con Gemini para: {animal}")
        
        # Generar imagen directamente con Gemini
        result = await image_generation_service.generate_image_async(animal)
        
        if result.get('success'):
            return {
                "success": True,
                "message": f"✅ Gemini generó imagen para '{animal}' correctamente",
                "animal": animal,
                "model": result.get('model'),
                "image_url": result.get('image_data_url'),
                "filename": result.get('filename'),
                "note": "Esta prueba solo usa Gemini. Para usar el sistema completo, configura OPENAI_API_KEY"
            }
        else:
            return {
                "success": False,
                "message": "❌ Error al generar imagen con Gemini",
                "error": result.get('error'),
                "details": result.get('details'),
                "animal": animal
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "animal": animal
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
