import os
import json
import tempfile
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Optional

# Load environment variables from .env file
load_dotenv()

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
        # Validate required environment variables
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        if not self.image_generation_function_url:
            raise ValueError("IMAGE_GENERATION_FUNCTION_URL environment variable is required")

        # Create upload directory if it doesn't exist
        os.makedirs(self.upload_dir, exist_ok=True)

# Global config instance, ready to be imported by other modules
config = Config()
