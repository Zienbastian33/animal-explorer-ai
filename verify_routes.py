#!/usr/bin/env python3
"""
Script para verificar que todas las rutas de FastAPI estén funcionando correctamente
Útil para testing local antes del despliegue a Vercel
"""

import asyncio
import aiohttp
import json
from typing import Dict, List

# Configuración del servidor
BASE_URL = "http://127.0.0.1:8000"  # Para testing local
# BASE_URL = "https://tu-app.vercel.app"  # Para testing en producción

async def test_route(session: aiohttp.ClientSession, method: str, path: str, data: Dict = None) -> Dict:
    """Testear una ruta específica"""
    url = f"{BASE_URL}{path}"
    
    try:
        if method.upper() == "GET":
            async with session.get(url) as response:
                status = response.status
                content_type = response.headers.get('content-type', '')
                
                if 'application/json' in content_type:
                    content = await response.json()
                else:
                    content = await response.text()
                    
        elif method.upper() == "POST":
            if data:
                async with session.post(url, data=data) as response:
                    status = response.status
                    content = await response.text()
            else:
                return {"error": "POST requires data"}
                
        return {
            "status": status,
            "content": content[:200] if isinstance(content, str) else content,
            "success": 200 <= status < 400
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "success": False
        }

async def main():
    """Función principal para testear todas las rutas"""
    
    # Rutas a testear
    routes_to_test = [
        {"method": "GET", "path": "/", "description": "Página principal"},
        {"method": "GET", "path": "/health", "description": "Health check"},
        {"method": "POST", "path": "/research", "data": {"animal": "león"}, "description": "Iniciar investigación"},
        {"method": "GET", "path": "/status/test-session-id", "description": "Status endpoint (debería dar 404 para sesión inexistente)"},
        {"method": "GET", "path": "/api/animal/león", "description": "API info de animal"},
        {"method": "GET", "path": "/static/style.css", "description": "Archivo estático CSS"},
        {"method": "GET", "path": "/static/script.js", "description": "Archivo estático JS"},
    ]
    
    print("🧪 Verificando rutas de Animal Explorer AI...")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        for route in routes_to_test:
            print(f"\n📍 Testeando: {route['method']} {route['path']}")
            print(f"   Descripción: {route['description']}")
            
            result = await test_route(
                session, 
                route['method'], 
                route['path'], 
                route.get('data')
            )
            
            if result.get('success'):
                print(f"   ✅ Status: {result['status']}")
                if 'content' in result:
                    content_preview = str(result['content'])[:100]
                    print(f"   📄 Content: {content_preview}...")
            else:
                print(f"   ❌ Error: {result.get('error', 'Unknown error')}")
                if 'status' in result:
                    print(f"   📊 Status: {result['status']}")
    
    print("\n" + "=" * 60)
    print("🏁 Verificación completada")
    
    print("\n💡 Notas:")
    print("- Si ves errores 404 en /status/, es normal para sesiones inexistentes")
    print("- Si ves errores en /research POST, verifica que el servidor esté corriendo")
    print("- Para testing en producción, cambia BASE_URL en este script")

if __name__ == "__main__":
    print("🚀 Iniciando verificación de rutas...")
    asyncio.run(main())
