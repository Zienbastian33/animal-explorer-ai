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

    # OpenAI Settings
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = "gpt-4o-mini"

    # Image Generation Cloud Function
    image_generation_function_url: str = os.getenv("IMAGE_GENERATION_FUNCTION_URL", "")

    # Application Settings
    max_file_size: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB
    upload_dir: str = os.getenv("UPLOAD_DIR", "uploads")

    def __post_init__(self):
        """Validate and initialize configuration after creation."""
        # Debug logging for environment variables
        print(f"[CONFIG] OpenAI API Key set: {bool(self.openai_api_key)}")
        print(f"[CONFIG] OpenAI API Key length: {len(self.openai_api_key) if self.openai_api_key else 0}")
        print(f"[CONFIG] Image Function URL set: {bool(self.image_generation_function_url)}")
        
        # Show first/last 4 chars of API key for debugging (safely)
        if self.openai_api_key and len(self.openai_api_key) > 8:
            masked_key = f"{self.openai_api_key[:4]}...{self.openai_api_key[-4:]}"
            print(f"[CONFIG] OpenAI API Key preview: {masked_key}")
        
        # Validate required environment variables
        if not self.openai_api_key:
            print("[ERROR] OPENAI_API_KEY environment variable is missing or empty!")
            raise ValueError("OPENAI_API_KEY environment variable is required")
        if not self.image_generation_function_url:
            print("[ERROR] IMAGE_GENERATION_FUNCTION_URL environment variable is missing or empty!")
            raise ValueError("IMAGE_GENERATION_FUNCTION_URL environment variable is required")

        print("[CONFIG] Configuration validation passed!")
        # Note: No need to create upload directory - using data URLs for images

# Global config instance, ready to be imported by other modules
config = Config()
