#!/bin/bash

# Deploy Google Cloud Function for image generation
# Make sure you have gcloud CLI installed and authenticated

# Set your project variables
PROJECT_ID="your-google-project-id"
FUNCTION_NAME="generate-animal-image"
REGION="us-central1"

echo "Deploying Cloud Function..."

gcloud functions deploy $FUNCTION_NAME \
  --gen2 \
  --runtime=python311 \
  --region=$REGION \
  --source=. \
  --entry-point=generate_animal_image \
  --trigger=http \
  --allow-unauthenticated \
  --memory=2GB \
  --timeout=300s \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=$REGION"

echo "Deployment complete!"
echo "Function URL will be displayed above. Copy it to your Vercel environment variables as IMAGE_GENERATION_FUNCTION_URL"
