# Vercel entry point for FastAPI
from web_app import app
from mangum import Mangum

# Mangum adapter for FastAPI on Vercel
handler = Mangum(app)
