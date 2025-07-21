# Vercel entry point para FastAPI
# Punto de entrada optimizado para el entorno serverless de Vercel

import sys
import os
from pathlib import Path

# Configurar el path para importaciones
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Asegurar que las variables de entorno estén disponibles
os.environ.setdefault('PYTHONPATH', str(root_dir))

try:
    # Importar la aplicación FastAPI
    from web_app import app as fastapi_app
    
    # Verificar que la app se importó correctamente
    print(f"FastAPI app imported successfully. Routes: {len(fastapi_app.routes)}")
    
    # Listar rutas disponibles para debugging
    for route in fastapi_app.routes:
        if hasattr(route, 'path'):
            print(f"Route: {route.path} - Methods: {getattr(route, 'methods', 'N/A')}")
            
except Exception as import_error:
    print(f"Error importing FastAPI app: {import_error}")
    # Crear una app básica de fallback
    from fastapi import FastAPI
    fastapi_app = FastAPI()
    
    @fastapi_app.get("/")
    async def fallback_root():
        return {"error": "Failed to import main app", "details": str(import_error)}

# Para Vercel, necesitamos exportar la app con el nombre correcto
# Vercel espera que la variable se llame exactamente 'app'
app = fastapi_app
