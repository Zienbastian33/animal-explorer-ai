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
        Eres un experto en zoología. Cuando te den el nombre de un animal, 
        responde EXACTAMENTE en este formato:

        **Nombre:** [Nombre del animal]
        **Clase:** [Vertebrado o Invertebrado]
        **Grupo:** [Mamífero/Ave/Reptil/Anfibio/Pez/Insecto/etc.]
        **Cubierta:** [Piel desnuda/Pelo/Plumas/Escamas/Caparazón/etc.]
        **Dato:** [Un dato interesante sobre el animal].
        **Dato2:** [Otro dato interesante sobre el animal].


        Responde solo en este formato, sin texto adicional.
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
            
            return {
                "success": True,
                "content": content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            
        except Exception as e:
            return {"success": False, "error": "API Error", "details": str(e)}


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
            
            # Save base64 image locally
            image_base64 = result['image_base64']
            filename = result['filename']
            
            # Decode and save image
            image_data = base64.b64decode(image_base64)
            filepath = os.path.join(config.upload_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            return {
                "success": True,
                "image_path": filepath,
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
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {"animal": animal_name}
                
                response = await client.post(
                    self.cloud_function_url,
                    json=payload,
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
                
                # Save base64 image locally
                image_base64 = result['image_base64']
                filename = result['filename']
                
                # Decode and save image
                image_data = base64.b64decode(image_base64)
                filepath = os.path.join(config.upload_dir, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(image_data)
                
                return {
                    "success": True,
                    "image_path": filepath,
                    "filename": filename,
                    "prompt": result.get('prompt', '')
                }
                
        except httpx.TimeoutException:
            return {"success": False, "error": "Request timeout", "details": "Cloud Function took too long to respond"}
        except httpx.ConnectError:
            return {"success": False, "error": "Connection error", "details": "Could not connect to Cloud Function"}
        except Exception as e:
            return {"success": False, "error": "Unexpected error", "details": str(e)}


# Service instances
animal_info_service = AnimalInfoService()
<<<<<<< HEAD
image_generation_service = ImageGenerationService()
=======
image_generation_service = ImageGenerationService()
>>>>>>> d8c5f21840aaa5dcdf9c7a83abf6e7dbc04b23a5
