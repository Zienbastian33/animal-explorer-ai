"""
Rate limiting service para Animal Explorer AI
Previene abuso de la API y controla costos de generación de imágenes
"""
import time
import json
from typing import Dict, Optional, Tuple
from session_service import session_service

class RateLimiter:
    def __init__(self):
        """Inicializar el rate limiter con configuración"""
        # Configuración de límites
        self.MINUTE_LIMIT = 5       # 5 consultas por minuto (aumentado de 1)
        self.HOUR_LIMIT = 20        # 20 consultas por hora  
        self.DAY_LIMIT = 60         # 60 consultas por día
        
        # TTL para las ventanas de tiempo
        self.MINUTE_TTL = 60        # 1 minuto
        self.HOUR_TTL = 3600        # 1 hora
        self.DAY_TTL = 86400        # 1 día
        self.BLACKLIST_TTL = 3600   # 1 hora de blacklist
        
        # Whitelist - IPs sin límites (para desarrollo/demos)
        self.WHITELIST_IPS = {
            "179.60.74.141",  # IP del desarrollador
            "127.0.0.1",      # localhost
            "::1"             # localhost IPv6
        }
        
        # Usar el mismo servicio de Redis que las sesiones
        self.redis_service = session_service
    
    def _get_client_ip(self, request) -> str:
        """Extraer IP real del cliente, considerando proxies"""
        # Vercel pasa la IP real en X-Forwarded-For
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            # Tomar la primera IP (cliente original)
            return forwarded_for.split(',')[0].strip()
        
        # Fallback a otras headers
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip.strip()
            
        # Último fallback
        return request.client.host if hasattr(request, 'client') else "unknown"
    
    def _get_rate_limit_key(self, ip: str, window: str) -> str:
        """Generar clave Redis para rate limiting"""
        return f"rate_limit:ip:{ip}:{window}"
    
    def _get_blacklist_key(self, ip: str) -> str:
        """Generar clave Redis para blacklist"""
        return f"blacklist:ip:{ip}"
    
    def _increment_counter(self, key: str, ttl: int) -> int:
        """Incrementar contador en Redis y devolver valor actual"""
        try:
            if self.redis_service.redis_client:
                # Usar Redis
                current = self.redis_service.redis_client.get(key)
                if current is None:
                    # Primera consulta en esta ventana
                    self.redis_service.redis_client.setex(key, ttl, "1")
                    return 1
                else:
                    # Incrementar contador existente
                    new_value = self.redis_service.redis_client.incr(key)
                    # Asegurar que el TTL no se perdió
                    self.redis_service.redis_client.expire(key, ttl)
                    return new_value
            else:
                # Fallback en memoria (no persistente, solo para desarrollo local)
                current_time = int(time.time())
                fallback_key = f"{key}:{current_time // ttl}"
                
                if fallback_key not in self.redis_service.fallback_sessions:
                    self.redis_service.fallback_sessions[fallback_key] = 1
                    return 1
                else:
                    self.redis_service.fallback_sessions[fallback_key] += 1
                    return self.redis_service.fallback_sessions[fallback_key]
                    
        except Exception as e:
            print(f"[ERROR] Rate limiter error: {e}")
            # En caso de error, permitir la consulta (fail-open)
            return 1
    
    def _get_counter(self, key: str) -> int:
        """Obtener valor actual del contador"""
        try:
            if self.redis_service.redis_client:
                current = self.redis_service.redis_client.get(key)
                return int(current) if current else 0
            else:
                # Fallback en memoria
                current_time = int(time.time())
                for window_ttl in [self.MINUTE_TTL, self.HOUR_TTL, self.DAY_TTL]:
                    fallback_key = f"{key}:{current_time // window_ttl}"
                    if fallback_key in self.redis_service.fallback_sessions:
                        return self.redis_service.fallback_sessions[fallback_key]
                return 0
        except Exception as e:
            print(f"[ERROR] Rate limiter get counter error: {e}")
            return 0
    
    def _is_blacklisted(self, ip: str) -> bool:
        """Verificar si la IP está en blacklist"""
        try:
            blacklist_key = self._get_blacklist_key(ip)
            if self.redis_service.redis_client:
                return bool(self.redis_service.redis_client.get(blacklist_key))
            else:
                # Fallback en memoria
                return blacklist_key in self.redis_service.fallback_sessions
        except Exception as e:
            print(f"[ERROR] Blacklist check error: {e}")
            return False
    
    def _add_to_blacklist(self, ip: str):
        """Agregar IP a blacklist temporal"""
        try:
            blacklist_key = self._get_blacklist_key(ip)
            if self.redis_service.redis_client:
                self.redis_service.redis_client.setex(blacklist_key, self.BLACKLIST_TTL, "blacklisted")
                print(f"[WARNING] IP {ip} blacklisted for {self.BLACKLIST_TTL} seconds")
            else:
                # Fallback en memoria
                self.redis_service.fallback_sessions[blacklist_key] = "blacklisted"
                print(f"[WARNING] IP {ip} blacklisted (memory fallback)")
        except Exception as e:
            print(f"[ERROR] Blacklist add error: {e}")
    
    def check_rate_limit(self, request) -> Tuple[bool, Dict]:
        """
        Verificar rate limits para una request
        Returns: (permitido: bool, info: dict)
        """
        client_ip = self._get_client_ip(request)
        
        # Whitelist - sin límites
        if client_ip in self.WHITELIST_IPS:
            print(f"[INFO] IP {client_ip} in whitelist, bypassing rate limits")
            return True, {"status": "whitelisted", "ip": client_ip}
        
        # Verificar blacklist
        if self._is_blacklisted(client_ip):
            print(f"[WARNING] IP {client_ip} is blacklisted")
            return False, {
                "status": "blacklisted",
                "error": "IP temporalmente bloqueada por exceso de consultas",
                "retry_after": self.BLACKLIST_TTL,
                "ip": client_ip
            }
        
        # Obtener claves para las ventanas de tiempo
        minute_key = self._get_rate_limit_key(client_ip, "minute")
        hour_key = self._get_rate_limit_key(client_ip, "hour")
        day_key = self._get_rate_limit_key(client_ip, "day")
        
        # Verificar límites ANTES de incrementar
        minute_count = self._get_counter(minute_key)
        hour_count = self._get_counter(hour_key)
        day_count = self._get_counter(day_key)
        
        # Verificar límite por minuto
        if minute_count >= self.MINUTE_LIMIT:
            return False, {
                "status": "rate_limited",
                "error": "Debes esperar 1 minuto entre consultas",
                "limit_type": "minute",
                "retry_after": 60,
                "current_count": minute_count,
                "limit": self.MINUTE_LIMIT,
                "ip": client_ip
            }
        
        # Verificar límite por hora
        if hour_count >= self.HOUR_LIMIT:
            return False, {
                "status": "rate_limited", 
                "error": f"Máximo {self.HOUR_LIMIT} consultas por hora alcanzado",
                "limit_type": "hour",
                "retry_after": 3600,
                "current_count": hour_count,
                "limit": self.HOUR_LIMIT,
                "ip": client_ip
            }
        
        # Verificar límite por día
        if day_count >= self.DAY_LIMIT:
            return False, {
                "status": "rate_limited",
                "error": f"Máximo {self.DAY_LIMIT} consultas por día alcanzado", 
                "limit_type": "day",
                "retry_after": 86400,
                "current_count": day_count,
                "limit": self.DAY_LIMIT,
                "ip": client_ip
            }
        
        # Todos los límites OK - incrementar contadores
        try:
            new_minute = self._increment_counter(minute_key, self.MINUTE_TTL)
            new_hour = self._increment_counter(hour_key, self.HOUR_TTL) 
            new_day = self._increment_counter(day_key, self.DAY_TTL)
            
            print(f"[INFO] Rate limit check passed for IP {client_ip}: minute={new_minute}, hour={new_hour}, day={new_day}")
            
            # Si alguien está cerca de los límites, monitorearlo
            if new_hour > (self.HOUR_LIMIT * 0.8) or new_day > (self.DAY_LIMIT * 0.8):
                print(f"[WARNING] IP {client_ip} approaching limits: hour={new_hour}/{self.HOUR_LIMIT}, day={new_day}/{self.DAY_LIMIT}")
            
            return True, {
                "status": "allowed",
                "ip": client_ip,
                "limits": {
                    "minute": {"current": new_minute, "limit": self.MINUTE_LIMIT},
                    "hour": {"current": new_hour, "limit": self.HOUR_LIMIT},
                    "day": {"current": new_day, "limit": self.DAY_LIMIT}
                }
            }
            
        except Exception as e:
            print(f"[ERROR] Rate limit increment error: {e}")
            # En caso de error, permitir la consulta (fail-open)
            return True, {"status": "error_fallback", "error": str(e)}
    
    def get_rate_limit_status(self, request) -> Dict:
        """Obtener estado actual de rate limits sin incrementar contadores"""
        client_ip = self._get_client_ip(request)
        
        if client_ip in self.WHITELIST_IPS:
            return {"status": "whitelisted", "ip": client_ip}
            
        if self._is_blacklisted(client_ip):
            return {"status": "blacklisted", "ip": client_ip}
        
        # Obtener contadores actuales
        minute_key = self._get_rate_limit_key(client_ip, "minute")
        hour_key = self._get_rate_limit_key(client_ip, "hour")
        day_key = self._get_rate_limit_key(client_ip, "day")
        
        minute_count = self._get_counter(minute_key)
        hour_count = self._get_counter(hour_key)
        day_count = self._get_counter(day_key)
        
        return {
            "status": "info",
            "ip": client_ip,
            "limits": {
                "minute": {"current": minute_count, "limit": self.MINUTE_LIMIT, "remaining": max(0, self.MINUTE_LIMIT - minute_count)},
                "hour": {"current": hour_count, "limit": self.HOUR_LIMIT, "remaining": max(0, self.HOUR_LIMIT - hour_count)},
                "day": {"current": day_count, "limit": self.DAY_LIMIT, "remaining": max(0, self.DAY_LIMIT - day_count)}
            }
        }

# Instancia global del rate limiter
rate_limiter = RateLimiter()