"""
Servicio de gestión de sesiones persistente para Vercel serverless
Usa Redis como almacenamiento backend para mantener sesiones entre invocaciones
"""
import json
import time
import os
from typing import Dict, Optional
import redis
from redis.exceptions import ConnectionError, TimeoutError

class SessionService:
    def __init__(self):
        """Inicializar el servicio de sesiones con Redis"""
        self.redis_url = os.getenv('REDIS_URL')
        self.session_ttl = 3600  # 1 hora
        self.redis_client = None
        self.fallback_sessions = {}  # Fallback en memoria para desarrollo local
        
        # Intentar conectar a Redis
        if self.redis_url:
            try:
                # Normalizar la URL de Redis
                normalized_url = self._normalize_redis_url(self.redis_url)
                print(f"[DEBUG] Connecting to Redis: {normalized_url[:40]}...")
                
                # Forzar conexión SSL para compatibilidad con Upstash/Vercel
                self.redis_client = redis.from_url(
                    normalized_url,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    retry_on_timeout=True,
                    # ssl=True,  # Deshabilitado para desarrollo local
                    # ssl_cert_reqs=None # Deshabilitar requerimientos de certificado SSL
                )
                # Test connection
                self.redis_client.ping()
                print("[INFO] Redis connected successfully")
            except (ConnectionError, TimeoutError) as e:
                print(f"[WARNING] Redis connection failed: {e}")
                print("[INFO] Falling back to in-memory sessions")
                self.redis_client = None
            except Exception as e:
                print(f"[ERROR] Redis setup error: {e}")
                print("[INFO] Falling back to in-memory sessions")
                self.redis_client = None
        else:
            print("[INFO] No REDIS_URL found, using in-memory sessions")
    
    def _normalize_redis_url(self, url: str) -> str:
        """Normalizar URL de Redis para diferentes proveedores"""
        # Si ya tiene el esquema correcto, devolverlo tal como está
        if url.startswith(('redis://', 'rediss://', 'unix://')):
            return url
        
        # Si es una URL HTTP/HTTPS (como Upstash REST), convertir a Redis
        if url.startswith(('http://', 'https://')):
            # Para Upstash, necesitamos usar la URL de Redis, no la REST
            print("[WARNING] HTTP URL detected. Para Upstash, usa la 'Redis URL', no la 'REST URL'")
            # Intentar convertir URL HTTP a Redis
            if 'upstash.io' in url:
                # Formato típico de Upstash: https://xxx.upstash.io
                # Necesitamos la Redis URL que es: redis://default:password@xxx.upstash.io:6379
                print("[ERROR] Upstash REST URL detected. Necesitas la 'Redis URL' de Upstash, no la 'REST URL'")
                raise ValueError("URL de Redis inválida. Usa la 'Redis URL' de Upstash, no la 'REST URL'")
            else:
                # Asumir que es una URL HTTP que necesita ser convertida
                return url.replace('http://', 'redis://').replace('https://', 'rediss://')
        
        # Si no tiene esquema, asumir redis://
        if '://' not in url:
            return f'redis://{url}'
        
        return url
    
    def _get_key(self, session_id: str) -> str:
        """Generar clave Redis para la sesión"""
        return f"session:{session_id}"
    
    def create_session(self, session_id: str, data: Dict) -> bool:
        """Crear una nueva sesión"""
        try:
            data['created_at'] = time.time()
            data['last_updated'] = time.time()
            
            if self.redis_client:
                # Usar Redis
                key = self._get_key(session_id)
                serialized_data = json.dumps(data)
                result = self.redis_client.setex(key, self.session_ttl, serialized_data)
                return result
            else:
                # Fallback en memoria
                self.fallback_sessions[session_id] = data
                return True
                
        except Exception as e:
            print(f"[ERROR] Failed to create session {session_id}: {e}")
            # Fallback en memoria
            self.fallback_sessions[session_id] = data
            return True
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Obtener datos de sesión"""
        try:
            if self.redis_client:
                # Usar Redis
                key = self._get_key(session_id)
                data = self.redis_client.get(key)
                if data:
                    return json.loads(data)
                return None
            else:
                # Fallback en memoria
                return self.fallback_sessions.get(session_id)
                
        except Exception as e:
            print(f"[ERROR] Failed to get session {session_id}: {e}")
            # Intentar fallback
            return self.fallback_sessions.get(session_id)
    
    def update_session(self, session_id: str, data: Dict) -> bool:
        """Actualizar datos de sesión"""
        try:
            data['last_updated'] = time.time()
            
            if self.redis_client:
                # Usar Redis
                key = self._get_key(session_id)
                serialized_data = json.dumps(data)
                result = self.redis_client.setex(key, self.session_ttl, serialized_data)
                return result
            else:
                # Fallback en memoria
                self.fallback_sessions[session_id] = data
                return True
                
        except Exception as e:
            print(f"[ERROR] Failed to update session {session_id}: {e}")
            # Fallback en memoria
            self.fallback_sessions[session_id] = data
            return True
    
    def delete_session(self, session_id: str) -> bool:
        """Eliminar sesión"""
        try:
            if self.redis_client:
                # Usar Redis
                key = self._get_key(session_id)
                result = self.redis_client.delete(key)
                return bool(result)
            else:
                # Fallback en memoria
                if session_id in self.fallback_sessions:
                    del self.fallback_sessions[session_id]
                    return True
                return False
                
        except Exception as e:
            print(f"[ERROR] Failed to delete session {session_id}: {e}")
            # Intentar fallback
            if session_id in self.fallback_sessions:
                del self.fallback_sessions[session_id]
            return False
    
    def extend_session(self, session_id: str) -> bool:
        """Extender TTL de la sesión"""
        try:
            if self.redis_client:
                # Usar Redis
                key = self._get_key(session_id)
                result = self.redis_client.expire(key, self.session_ttl)
                return result
            else:
                # En memoria no necesita extensión
                return session_id in self.fallback_sessions
                
        except Exception as e:
            print(f"[ERROR] Failed to extend session {session_id}: {e}")
            return False
    
    def cleanup_expired_sessions(self):
        """Limpiar sesiones expiradas (solo para fallback en memoria)"""
        if not self.redis_client:
            current_time = time.time()
            expired_sessions = []
            
            for session_id, data in self.fallback_sessions.items():
                if current_time - data.get('created_at', 0) > self.session_ttl:
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                del self.fallback_sessions[session_id]
            
            if expired_sessions:
                print(f"[INFO] Cleaned up {len(expired_sessions)} expired sessions")
    
    def get_session_count(self) -> int:
        """Obtener número de sesiones activas"""
        try:
            if self.redis_client:
                # Contar claves que empiecen con "session:"
                keys = self.redis_client.keys("session:*")
                return len(keys)
            else:
                return len(self.fallback_sessions)
        except Exception as e:
            print(f"[ERROR] Failed to get session count: {e}")
            return 0

# Instancia global del servicio
session_service = SessionService()
