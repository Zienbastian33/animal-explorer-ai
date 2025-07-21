import functions_framework
import os
import base64
from google.cloud import storage
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
from google.oauth2 import service_account
import json
from flask import jsonify

# Initialize Vertex AI
def initialize_vertex_ai():
    """Initialize Vertex AI with proper authentication"""
    try:
        # Get project ID from environment
        project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
        location = os.environ.get('GOOGLE_CLOUD_LOCATION', 'us-central1')
        
        vertexai.init(project=project_id, location=location)
        model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")
        return model
    except Exception as e:
        print(f"Error initializing Vertex AI: {e}")
        return None

@functions_framework.http
def generate_animal_image(request):
    """HTTP Cloud Function to generate animal images"""
    
    # Enable CORS
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    }
    
    try:
        # Validate request
        if request.method != 'POST':
            return jsonify({"error": "Only POST method allowed"}), 405, headers
        
        # Get request data
        request_json = request.get_json(silent=True)
        if not request_json or 'animal' not in request_json:
            return jsonify({"error": "Missing 'animal' parameter"}), 400, headers
        
        animal_name = request_json['animal'].strip()
        if not animal_name:
            return jsonify({"error": "Animal name cannot be empty"}), 400, headers
        
        # Initialize Vertex AI
        model = initialize_vertex_ai()
        if not model:
            return jsonify({"error": "Failed to initialize Vertex AI"}), 500, headers
        
        # Create detailed prompt
        prompt = f"""
        Photorealistic portrait of a single "{animal_name}". Focus on the animal's distinct features.
        Wildlife photography, natural environment, detailed, high resolution, professional photography.
        """
        
        # Generate image
        images = model.generate_images(
            prompt=prompt,
            number_of_images=1,
            language="en"
        )
        
        if not images:
            return jsonify({"error": "No image generated"}), 500, headers
        
        # Convert image to base64
        image_bytes = images[0]._image_bytes
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Create filename
        filename = f"{animal_name.replace(' ', '_').lower()}_generated.png"
        
        return jsonify({
            "success": True,
            "image_base64": image_base64,
            "filename": filename,
            "prompt": prompt
        }), 200, headers
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error generating image: {error_msg}")
        
        if "UNAUTHENTICATED" in error_msg:
            return jsonify({"error": "Authentication error", "details": "Check Google Cloud credentials"}), 401, headers
        elif "QUOTA_EXCEEDED" in error_msg:
            return jsonify({"error": "Quota exceeded", "details": "Check billing and API limits"}), 429, headers
        else:
            return jsonify({"error": "Image generation failed", "details": error_msg}), 500, headers
