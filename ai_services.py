import os
import base64
import asyncio
from typing import Dict, Optional, Tuple
from io import BytesIO
from PIL import Image
import httpx

# OpenAI
from openai import OpenAI, AsyncOpenAI
import openai

from config import config

class AnimalInfoService:
    """Service for getting animal information from ChatGPT"""
    
    def __init__(self):
        self.client = OpenAI(api_key=config.openai_api_key)
        self.async_client = AsyncOpenAI(api_key=config.openai_api_key)
        
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
        """Get animal information synchronously"""
        try:
            response = self.client.chat.completions.create(
                model=config.openai_model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Información sobre: {animal_name}"}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            content = response.choices[0].message.content
            
            return {
                "success": True,
                "content": content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            
        except openai.RateLimitError as e:
            return {"success": False, "error": "Rate limit exceeded", "details": str(e)}
        except openai.AuthenticationError as e:
            return {"success": False, "error": "Authentication failed", "details": str(e)}
        except openai.APIConnectionError as e:
            return {"success": False, "error": "Connection failed", "details": str(e)}
        except Exception as e:
            return {"success": False, "error": "Unexpected error", "details": str(e)}
    
    async def get_animal_info_async(self, animal_name: str) -> Dict[str, str]:
        """Get animal information asynchronously"""
        try:
            print(f"[DEBUG] Making OpenAI request for animal: {animal_name}")
            print(f"[DEBUG] Using model: {config.openai_model}")
            print(f"[DEBUG] API key present: {bool(config.openai_api_key)}")
            print(f"[DEBUG] API key length: {len(config.openai_api_key) if config.openai_api_key else 0}")
            
            response = await self.async_client.chat.completions.create(
                model=config.openai_model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Información sobre: {animal_name}"}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            content = response.choices[0].message.content
            print(f"[DEBUG] OpenAI response successful, content length: {len(content)}")
            
            return {
                "success": True,
                "content": content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            
        except openai.RateLimitError as e:
            print(f"[ERROR] OpenAI Rate Limit: {str(e)}")
            return {"success": False, "error": "Rate Limit Error", "details": str(e)}
        except openai.AuthenticationError as e:
            print(f"[ERROR] OpenAI Auth Error: {str(e)}")
            return {"success": False, "error": "Authentication Error - Check API Key", "details": str(e)}
        except openai.APIConnectionError as e:
            print(f"[ERROR] OpenAI Connection Error: {str(e)}")
            return {"success": False, "error": "Connection Error", "details": str(e)}
        except openai.BadRequestError as e:
            print(f"[ERROR] OpenAI Bad Request: {str(e)}")
            return {"success": False, "error": "Bad Request Error", "details": str(e)}
        except Exception as e:
            print(f"[ERROR] Unexpected OpenAI Error: {str(e)}")
            print(f"[ERROR] Error type: {type(e)}")
            return {"success": False, "error": "Unexpected API Error", "details": str(e)}


class ImageGenerationService:
    """Service for generating images using Google Cloud Function"""
    
    def __init__(self):
        self.cloud_function_url = config.image_generation_function_url
        self.timeout = 60  # seconds
    
    def generate_image(self, animal_name: str) -> Dict[str, any]:
        """Generate image synchronously via Cloud Function"""
        try:
            import requests
            
            payload = {"animal": animal_name}
            
            response = requests.post(
                self.cloud_function_url,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Cloud Function error: {response.status_code}",
                    "details": response.text
                }
            
            result = response.json()
            
            if not result.get('success'):
                return result
            
            # Return image as base64 data URL directly (no local storage)
            image_base64 = result['image_base64']
            filename = result['filename']
            
            # Create data URL for direct display
            data_url = f"data:image/png;base64,{image_base64}"
            
            return {
                "success": True,
                "image_data_url": data_url,
                "image_base64": image_base64,
                "filename": filename,
                "prompt": result.get('prompt', '')
            }
            
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Request timeout", "details": "Cloud Function took too long to respond"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Connection error", "details": "Could not connect to Cloud Function"}
        except Exception as e:
            return {"success": False, "error": "Unexpected error", "details": str(e)}
    
    async def generate_image_async(self, animal_name: str) -> Dict[str, any]:
        """Generate image asynchronously via Cloud Function"""
        try:
            print(f"[DEBUG] Making image generation request for: {animal_name}")
            print(f"[DEBUG] Cloud Function URL: {self.cloud_function_url}")
            print(f"[DEBUG] URL is set: {bool(self.cloud_function_url)}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {"animal": animal_name}
                print(f"[DEBUG] Payload: {payload}")
                
                response = await client.post(
                    self.cloud_function_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                print(f"[DEBUG] Response status: {response.status_code}")
                print(f"[DEBUG] Response headers: {dict(response.headers)}")
                
                if response.status_code != 200:
                    error_text = response.text
                    print(f"[ERROR] Cloud Function failed: {response.status_code}")
                    print(f"[ERROR] Response body: {error_text}")
                    return {
                        "success": False,
                        "error": f"Cloud Function error: {response.status_code}",
                        "details": error_text,
                        "url_used": self.cloud_function_url
                    }
                
                result = response.json()
                print(f"[DEBUG] Cloud Function response: {result}")
                
                if not result.get('success'):
                    print(f"[ERROR] Cloud Function returned error: {result}")
                    return result
                
                # Return image as base64 data URL directly (no local storage)
                image_base64 = result['image_base64']
                filename = result['filename']
                
                # Create data URL for direct display
                data_url = f"data:image/png;base64,{image_base64}"
                
                return {
                    "success": True,
                    "image_data_url": data_url,
                    "image_base64": image_base64,
                    "filename": filename,
                    "prompt": result.get('prompt', '')
                }
                
        except httpx.TimeoutException as e:
            print(f"[ERROR] Image generation timeout: {str(e)}")
            return {"success": False, "error": "Request timeout", "details": "Cloud Function took too long to respond"}
        except httpx.ConnectError as e:
            print(f"[ERROR] Image generation connection error: {str(e)}")
            return {"success": False, "error": "Connection error", "details": f"Could not connect to Cloud Function: {str(e)}"}
        except Exception as e:
            print(f"[ERROR] Unexpected image generation error: {str(e)}")
            return {"success": False, "error": "Unexpected error", "details": str(e)}


# Service instances
animal_info_service = AnimalInfoService()
image_generation_service = ImageGenerationService()
