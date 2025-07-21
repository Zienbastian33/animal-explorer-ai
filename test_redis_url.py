"""
Script para probar la normalización de URLs de Redis
"""
from session_service import SessionService
import os

def test_redis_url_normalization():
    """Probar diferentes formatos de URL de Redis"""
    print("=== PRUEBA DE NORMALIZACIÓN DE URLs REDIS ===\n")
    
    # Crear instancia temporal para acceder al método
    service = SessionService()
    
    test_urls = [
        # URLs válidas
        ("redis://localhost:6379", "URL Redis estándar"),
        ("rediss://user:pass@host:6379", "URL Redis con SSL"),
        ("redis://default:password@host.upstash.io:6379", "URL Redis de Upstash"),
        
        # URLs que necesitan normalización
        ("localhost:6379", "Host sin esquema"),
        ("user:pass@host:6379", "Host con credenciales sin esquema"),
        
        # URLs problemáticas
        ("https://host.upstash.io", "REST URL de Upstash (debería fallar)"),
        ("http://localhost:8080", "URL HTTP genérica"),
    ]
    
    for url, description in test_urls:
        print(f"Probando: {description}")
        print(f"  Input:  {url}")
        
        try:
            normalized = service._normalize_redis_url(url)
            print(f"  Output: {normalized}")
            print(f"  ✅ Éxito\n")
        except Exception as e:
            print(f"  ❌ Error: {e}\n")

def test_with_env_var():
    """Probar con variable de entorno"""
    print("=== PRUEBA CON VARIABLE DE ENTORNO ===\n")
    
    # Probar sin variable de entorno
    print("1. Sin REDIS_URL:")
    service1 = SessionService()
    print()
    
    # Probar con URL válida
    print("2. Con REDIS_URL válida:")
    os.environ['REDIS_URL'] = 'redis://localhost:6379'
    service2 = SessionService()
    print()
    
    # Probar con URL inválida
    print("3. Con REDIS_URL inválida:")
    os.environ['REDIS_URL'] = 'https://invalid.upstash.io'
    service3 = SessionService()
    print()
    
    # Limpiar variable de entorno
    if 'REDIS_URL' in os.environ:
        del os.environ['REDIS_URL']

if __name__ == "__main__":
    test_redis_url_normalization()
    test_with_env_var()
    print("=== PRUEBAS COMPLETADAS ===")
