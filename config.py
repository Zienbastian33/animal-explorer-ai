import os
import json
import tempfile
from dataclasses import dataclass
from typing import Optional

# Only load .env file in local development, not in production
# Vercel provides environment variables directly, .env files are ignored
try:
    from dotenv import load_dotenv
    load_dotenv()  # This only works locally
except ImportError:
    # dotenv not available in production, that's fine
    pass

@dataclass
class Config:
    """Application configuration"""

    # Gemini API Settings
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "REDACTED_API_KEY")
    gemini_text_model: str = "gemini-3-flash-preview"  # Para información de animales
    gemini_image_model: str = "gemini-3-pro-image-preview"  # Para generación de imágenes

    # Application Settings
    max_file_size: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB
    upload_dir: str = os.getenv("UPLOAD_DIR", "uploads")

    def __post_init__(self):
        """Validate and initialize configuration after creation."""
        # Debug logging for environment variables
        print(f"[CONFIG] Gemini API Key set: {bool(self.gemini_api_key)}")
        print(f"[CONFIG] Gemini API Key length: {len(self.gemini_api_key) if self.gemini_api_key else 0}")
        
        # Show first/last 4 chars of API key for debugging (safely)
        if self.gemini_api_key and len(self.gemini_api_key) > 8:
            masked_key = f"{self.gemini_api_key[:4]}...{self.gemini_api_key[-4:]}"
            print(f"[CONFIG] Gemini API Key preview: {masked_key}")
        
        # Validate required environment variables
        if not self.gemini_api_key:
            print("[ERROR] GEMINI_API_KEY environment variable is missing or empty!")
            raise ValueError("GEMINI_API_KEY environment variable is required")

        print(f"[CONFIG] Using Gemini Text model: {self.gemini_text_model}")
        print(f"[CONFIG] Using Gemini Image model: {self.gemini_image_model}")
        print("[CONFIG] Configuration validation passed!")
        # Note: No need to create upload directory - using data URLs for images

# Global config instance, ready to be imported by other modules
config = Config()
