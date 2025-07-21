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
    from web_app import app
    
    # Verificar que la app se importó correctamente
    print(f"FastAPI app imported successfully. Routes: {len(app.routes)}")
    
    # Listar rutas disponibles para debugging
    for route in app.routes:
        if hasattr(route, 'path'):
            print(f"Route: {route.path} - Methods: {getattr(route, 'methods', 'N/A')}")
            
except Exception as e:
    print(f"Error importing FastAPI app: {e}")
    # Crear una app básica de fallback
    from fastapi import FastAPI
    app = FastAPI()
    
    @app.get("/")
    async def fallback_root():
        return {"error": "Failed to import main app", "details": str(e)}

# Exportar la app para Vercel
# Vercel espera que la variable se llame 'app'
handler = app
