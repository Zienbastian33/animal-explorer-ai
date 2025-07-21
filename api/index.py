# Vercel entry point for FastAPI
# Using direct FastAPI app export for Vercel
from web_app import app

# Export the app directly for Vercel
# Vercel will handle the ASGI adapter automatically
app = app
