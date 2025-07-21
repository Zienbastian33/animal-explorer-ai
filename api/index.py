# Vercel entry point for FastAPI
# Fixed merge conflicts and syntax errors
from web_app import app
from mangum import Mangum

# Mangum adapter for FastAPI on Vercel
handler = Mangum(app)
