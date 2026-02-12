import os
import base64
import asyncio
import time
import traceback
from typing import Dict, Optional, Tuple
from io import BytesIO
from PIL import Image
import httpx

from config import config

class AnimalInfoService:
    """Service for getting animal information from Gemini 3 Flash"""
    
    def __init__(self):
        try:
            from google import genai
            from google.genai import types
            
            self.genai = genai
            self.types = types
            self.client = genai.Client(api_key=config.gemini_api_key)
            self.model = config.gemini_text_model
            print(f"[INFO] Gemini Text Service initialized with model: {self.model}")
        except ImportError as e:
            print(f"[ERROR] Failed to import google-genai: {e}")
            raise
        except Exception as e:
            print(f"[ERROR] Failed to initialize Gemini text client: {e}")
            raise
        
        self.system_prompt = """
        Eres un experto en zoología. PRIMERO valida si el término corresponde a un animal real existente.

        SI ES UN ANIMAL REAL, responde EXACTAMENTE en este formato en ESPAÑOL:

        **VALIDO:** SI
        **Nombre:** [Nombre del animal en español]
        **Nombre_EN:** [Nombre del animal en inglés - para generación de imagen]
        **Clase:** [Vertebrado o Invertebrado]
        **Grupo:** [Mamífero/Ave/Reptil/Anfibio/Pez/Insecto/etc.]
        **Hábitat:** [Donde vive - bosques, océanos, desiertos, etc.]
        **Dieta:** [Carnívoro/Herbívoro/Omnívoro - qué come específicamente]
        **Tamaño:** [Tamaño promedio del animal]
        **Vida:** [Esperanza de vida promedio]
        **Conservación:** [Estado: Estable/Vulnerable/En peligro/Crítico]
        **Cubierta:** [Piel desnuda/Pelo/Plumas/Escamas/Caparazón/etc.]
        **Dato:** [Un dato fascinante y específico sobre el animal]
        **Dato2:** [Otro dato increíble sobre sus comportamientos únicos]

        SI NO ES UN ANIMAL REAL (ej: "pikachu", "cuchara", "asdhasjd"), responde:

        **VALIDO:** NO
        **Razón:** [Por qué no es válido - ej: "No es un animal real", "Es un objeto", "Es un personaje ficticio"]
        **Sugerencias:** [Animal1, Animal2, Animal3] - Solo nombres de animales separados por comas, sin explicaciones adicionales

        VALIDACIÓN ESTRICTA:
        - Solo acepta animales REALES que existan en la naturaleza
        - Rechaza: personajes ficticios, objetos, palabras sin sentido, plantas, etc.
        - Si hay duda, considera NO válido

        INSTRUCCIONES DE IDIOMA:
        - Si el usuario da un animal en español, traduce a inglés para "Nombre_EN"
        - Si el usuario da un animal en inglés, traduce a español para "Nombre"
        - El "Nombre_EN" es crucial para generar imágenes correctas

        Responde solo en el formato indicado, sin texto adicional.
        """
    
    def get_animal_info(self, animal_name: str) -> Dict[str, str]:
        """Get animal information synchronously using Gemini"""
        try:
            # Combinar system prompt con user message para Gemini
            full_prompt = f"{self.system_prompt}\n\nInformación sobre: {animal_name}"
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=full_prompt,
                config=self.types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=500,
                )
            )
            
            content = response.text
            
            return {
                "success": True,
                "content": content,
                "usage": {
                    "total_tokens": response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else 0
                }
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] Gemini text generation error: {error_msg}")
            
            if "API key not valid" in error_msg or "UNAUTHENTICATED" in error_msg:
                return {"success": False, "error": "Authentication failed", "details": "Invalid Gemini API key"}
            elif "QUOTA_EXCEEDED" in error_msg:
                return {"success": False, "error": "Rate limit exceeded", "details": str(e)}
            elif "PERMISSION_DENIED" in error_msg:
                return {"success": False, "error": "Connection failed", "details": "Permission denied for Gemini API"}
            else:
                return {"success": False, "error": "Unexpected error", "details": str(e)}
    
    async def get_animal_info_async(self, animal_name: str) -> Dict[str, str]:
        """Get animal information asynchronously using Gemini"""
        try:
            print(f"[DEBUG] Making Gemini request for animal: {animal_name}")
            print(f"[DEBUG] Using model: {self.model}")
            print(f"[DEBUG] API key present: {bool(config.gemini_api_key)}")
            
            # Gemini SDK no es completamente async, usar executor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.get_animal_info(animal_name)
            )
            
            if result.get('success'):
                print(f"[DEBUG] Gemini response successful, content length: {len(result['content'])}")
            else:
                print(f"[ERROR] Gemini request failed: {result.get('error')}")
            
            return result
            
        except Exception as e:
            print(f"[ERROR] Unexpected Gemini Error: {str(e)}")
            print(f"[ERROR] Error type: {type(e)}")
            return {"success": False, "error": "Unexpected API Error", "details": str(e)}


class ImageGenerationService:
    """Service for generating images using Gemini 3 Pro Image (Nano Banana Pro)"""
    
    def __init__(self):
        try:
            from google import genai
            from google.genai import types
            
            self.genai = genai
            self.types = types
            self.client = genai.Client(api_key=config.gemini_api_key)
            self.model = config.gemini_image_model
            print(f"[INFO] Gemini Image Service initialized with model: {self.model}")
        except ImportError as e:
            print(f"[ERROR] Failed to import google-genai: {e}")
            print("[ERROR] Please install: pip install google-genai")
            raise
        except Exception as e:
            print(f"[ERROR] Failed to initialize Gemini client: {e}")
            raise
    
    def generate_image(self, animal_name: str) -> Dict[str, any]:
        """Generate image synchronously using Gemini 3 Pro Image"""
        try:
            # Create detailed photorealistic prompt for wildlife
            prompt = f"""Photorealistic portrait of a {animal_name} in its natural habitat. 
            Wildlife photography style, detailed features, professional quality, natural lighting, 
            4K resolution. Focus on the animal's distinctive characteristics and natural beauty."""
            
            print(f"[IMAGE] Generating image for: {animal_name}")
            print(f"[IMAGE] Using model: {self.model}")
            print(f"[IMAGE] API key configured: {bool(self.client)}")
            print(f"[IMAGE] Starting generation at: {time.time()}")
            
            # Generate image with Gemini 3 Pro Image
            try:
                # Intentar con ImageConfig si está disponible
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=self.types.GenerateContentConfig(
                        response_modalities=['IMAGE'],
                        image_config=self.types.ImageConfig(
                            aspect_ratio="1:1",
                            image_size="2K"  # High quality 2K resolution
                        ),
                    )
                )
            except (AttributeError, TypeError) as e:
                # Fallback: Si ImageConfig no está disponible, usar configuración simplificada
                print(f"[WARNING] ImageConfig not available, using simplified config: {e}")
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=self.types.GenerateContentConfig(
                        response_modalities=['IMAGE'],
                    )
                )
            
            # Extract image from response - usando el mismo método robusto
            print(f"[DEBUG] Response type in generate_image: {type(response)}")
            image_base64 = None
            
            # Intentar diferentes métodos de extracción
            if hasattr(response, 'parts'):
                for part in response.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        image_bytes = part.inline_data.data
                        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                        break
            elif hasattr(response, 'candidates'):
                for candidate in response.candidates:
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        for part in candidate.content.parts:
                            if hasattr(part, 'inline_data') and part.inline_data:
                                image_bytes = part.inline_data.data
                                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                                break
            
            if not image_base64:
                print("[ERROR] No image data found in response (generate_image)")
                print(f"[ERROR] Available attributes: {[a for a in dir(response) if not a.startswith('_')]}")
                return {
                    "success": False,
                    "error": "No image generated",
                    "details": "Gemini API did not return image data in expected format"
                }
            
            filename = f"{animal_name.replace(' ', '_').lower()}_gemini.png"
            data_url = f"data:image/png;base64,{image_base64}"
            
            print(f"[SUCCESS] Image generated successfully for {animal_name}")
            
            return {
                "success": True,
                "image_data_url": data_url,
                "image_base64": image_base64,
                "filename": filename,
                "prompt": prompt,
                "model": self.model
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] Image generation failed: {error_msg}")
            print(f"[ERROR] Error type: {type(e).__name__}")
            print(f"[ERROR] Full traceback available")
            import traceback
            traceback.print_exc()
            
            if "API key not valid" in error_msg or "UNAUTHENTICATED" in error_msg:
                return {"success": False, "error": "Authentication error", "details": "Invalid or expired Gemini API key"}
            elif "QUOTA_EXCEEDED" in error_msg or "quota" in error_msg.lower():
                return {"success": False, "error": "Quota exceeded", "details": "Gemini API quota limit reached"}
            elif "PERMISSION_DENIED" in error_msg:
                return {"success": False, "error": "Permission denied", "details": "API key does not have access to this model"}
            else:
                return {"success": False, "error": "Image generation failed", "details": error_msg}
    
    async def generate_image_async(self, animal_name: str) -> Dict[str, any]:
        """Generate image asynchronously using Gemini 3 Pro Image"""
        try:
            # Create detailed photorealistic prompt for wildlife
            prompt = f"""Photorealistic portrait of a {animal_name} in its natural habitat. 
            Wildlife photography style, detailed features, professional quality, natural lighting, 
            4K resolution. Focus on the animal's distinctive characteristics and natural beauty."""
            
            print(f"[DEBUG] Generating image async for: {animal_name}")
            print(f"[DEBUG] Using model: {self.model}")
            
            # Gemini SDK is not fully async, run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._generate_sync(animal_name, prompt)
            )
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] Async image generation failed: {error_msg}")
            
            if "API key not valid" in error_msg or "UNAUTHENTICATED" in error_msg:
                return {"success": False, "error": "Authentication error", "details": "Invalid or expired Gemini API key"}
            elif "QUOTA_EXCEEDED" in error_msg or "quota" in error_msg.lower():
                return {"success": False, "error": "Quota exceeded", "details": "Gemini API quota limit reached"}
            elif "PERMISSION_DENIED" in error_msg:
                return {"success": False, "error": "Permission denied", "details": "API key does not have access to this model"}
            else:
                return {"success": False, "error": "Image generation failed", "details": error_msg}
    
    def _generate_sync(self, animal_name: str, prompt: str) -> Dict[str, any]:
        """Internal synchronous generation method for async wrapper"""
        try:
            # Generate image with Gemini 3 Pro Image
            try:
                # Intentar con ImageConfig si está disponible
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=self.types.GenerateContentConfig(
                        response_modalities=['IMAGE'],
                        image_config=self.types.ImageConfig(
                            aspect_ratio="1:1",
                            image_size="2K"  # High quality 2K resolution
                        ),
                    )
                )
            except (AttributeError, TypeError) as e:
                # Fallback: Si ImageConfig no está disponible, usar configuración simplificada
                print(f"[WARNING] ImageConfig not available in _generate_sync, using simplified config: {e}")
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=self.types.GenerateContentConfig(
                        response_modalities=['IMAGE'],
                    )
                )
            
            # Debug: Ver estructura de la respuesta
            print(f"[DEBUG] Response type: {type(response)}")
            print(f"[DEBUG] Response attributes: {dir(response)}")
            
            # Extract image from response - manejo robusto de diferentes estructuras
            image_base64 = None
            
            # Método 1: Intentar acceder a parts (estructura antigua)
            if hasattr(response, 'parts'):
                print("[DEBUG] Response has 'parts' attribute")
                for part in response.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        image_bytes = part.inline_data.data
                        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                        print("[DEBUG] Image extracted from parts.inline_data")
                        break
            
            # Método 2: Intentar acceder directamente a candidates
            if not image_base64 and hasattr(response, 'candidates'):
                print("[DEBUG] Trying to extract from candidates")
                for candidate in response.candidates:
                    if hasattr(candidate, 'content'):
                        content = candidate.content
                        if hasattr(content, 'parts'):
                            for part in content.parts:
                                if hasattr(part, 'inline_data') and part.inline_data:
                                    image_bytes = part.inline_data.data
                                    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                                    print("[DEBUG] Image extracted from candidates.content.parts")
                                    break
            
            # Método 3: Intentar acceder a text o image directamente
            if not image_base64 and hasattr(response, 'image'):
                print("[DEBUG] Trying to extract from response.image")
                image_base64 = base64.b64encode(response.image).decode('utf-8')
                print("[DEBUG] Image extracted from response.image")
            
            # Método 4: Buscar en cualquier atributo que contenga 'data' o 'image'
            if not image_base64:
                print("[DEBUG] Searching for image in all response attributes")
                for attr_name in dir(response):
                    if not attr_name.startswith('_'):
                        attr_value = getattr(response, attr_name, None)
                        print(f"[DEBUG] Checking attribute: {attr_name} = {type(attr_value)}")
            
            if not image_base64:
                print("[ERROR] No image data found in response")
                print(f"[ERROR] Response content: {response}")
                return {
                    "success": False,
                    "error": "No image generated",
                    "details": "Gemini API did not return image data in expected format"
                }
            
            filename = f"{animal_name.replace(' ', '_').lower()}_gemini.png"
            data_url = f"data:image/png;base64,{image_base64}"
            
            print(f"[SUCCESS] Image generated successfully for {animal_name}")
            
            return {
                "success": True,
                "image_data_url": data_url,
                "image_base64": image_base64,
                "filename": filename,
                "prompt": prompt,
                "model": self.model
            }
            
        except Exception as e:
            print(f"[ERROR] Internal generation error: {e}")
            raise


# Service instances
animal_info_service = AnimalInfoService()
image_generation_service = ImageGenerationService()
