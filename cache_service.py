"""
Cache Service para Animal Explorer AI
Sistema de caché inteligente que guarda resultados comunes en Redis
"""
import json
import time
import hashlib
from typing import Dict, Optional, Tuple, List
from session_service import session_service

class CacheService:
    def __init__(self):
        """Inicializar el servicio de caché optimizado para Upstash (256MB, 500k comandos/mes)"""
        # 🎯 CONFIGURACIÓN TTL OPTIMIZADA PARA UPSTASH
        self.ANIMAL_INFO_TTL = 86400 * 7  # 7 días - info básica dura más
        self.ANIMAL_IMAGE_TTL = 86400 * 14  # 14 días - imágenes son más costosas de regenerar
        self.POPULAR_ANIMALS_TTL = 3600 * 2  # 2 horas - suficiente para trends
        self.SEARCH_SUGGESTIONS_TTL = 86400  # 1 día - sugerencias cambian poco
        
        # 📊 CONFIGURACIÓN ANALYTICS OPTIMIZADA
        self.ANALYTICS_TTL = 86400 * 30  # 30 días para analytics principales
        self.DAILY_ANALYTICS_TTL = 86400 * 7  # 7 días para análisis diarios
        
        # Prefijos para diferentes tipos de caché
        self.INFO_PREFIX = "cache:animal_info:"
        self.IMAGE_PREFIX = "cache:animal_image:"
        self.POPULAR_PREFIX = "cache:popular_animals"
        self.SUGGESTIONS_PREFIX = "cache:suggestions:"
        self.ANALYTICS_PREFIX = "cache:analytics:"
        
        # Usar el mismo servicio Redis que las sesiones
        self.redis_service = session_service
        
    def _get_cache_key(self, prefix: str, identifier: str) -> str:
        """Generar clave de caché normalizada"""
        # Normalizar el identificador
        normalized = identifier.lower().strip()
        # Crear hash para evitar problemas con caracteres especiales
        hash_id = hashlib.md5(normalized.encode('utf-8')).hexdigest()
        return f"{prefix}{hash_id}"
    
    def _set_cache(self, key: str, data: Dict, ttl: int) -> bool:
        """Guardar datos en caché con TTL"""
        try:
            if self.redis_service.redis_client:
                serialized_data = json.dumps(data, ensure_ascii=False)
                self.redis_service.redis_client.setex(key, ttl, serialized_data)
                print(f"[CACHE] Stored: {key} (TTL: {ttl}s)")
                return True
            else:
                # Fallback en memoria (sin persistencia)
                self.redis_service.fallback_sessions[key] = {
                    'data': data,
                    'expires_at': time.time() + ttl
                }
                print(f"[CACHE] Stored in memory: {key}")
                return True
        except Exception as e:
            print(f"[CACHE ERROR] Failed to store {key}: {e}")
            return False
    
    def _get_cache(self, key: str) -> Optional[Dict]:
        """Obtener datos del caché"""
        try:
            if self.redis_service.redis_client:
                cached_data = self.redis_service.redis_client.get(key)
                if cached_data:
                    data = json.loads(cached_data)
                    print(f"[CACHE HIT] {key}")
                    return data
            else:
                # Fallback en memoria
                cached_item = self.redis_service.fallback_sessions.get(key)
                if cached_item:
                    # Verificar si ha expirado
                    if time.time() < cached_item['expires_at']:
                        print(f"[CACHE HIT] Memory: {key}")
                        return cached_item['data']
                    else:
                        # Eliminar si ha expirado
                        del self.redis_service.fallback_sessions[key]
            
            print(f"[CACHE MISS] {key}")
            return None
            
        except Exception as e:
            print(f"[CACHE ERROR] Failed to get {key}: {e}")
            return None
    
    def cache_animal_info(self, animal: str, info_data: str, english_name: str = "") -> bool:
        """Cachear información de un animal"""
        cache_key = self._get_cache_key(self.INFO_PREFIX, animal)
        
        cache_data = {
            'animal': animal.lower().strip(),
            'info': info_data,
            'english_name': english_name,
            'cached_at': int(time.time()),
            'cache_version': '1.0'
        }
        
        return self._set_cache(cache_key, cache_data, self.ANIMAL_INFO_TTL)
    
    def get_cached_animal_info(self, animal: str) -> Optional[Dict]:
        """Obtener información cacheada de un animal"""
        cache_key = self._get_cache_key(self.INFO_PREFIX, animal)
        cached_data = self._get_cache(cache_key)
        
        if cached_data:
            # Verificar que el caché tenga los campos necesarios
            if 'info' in cached_data and 'animal' in cached_data:
                return {
                    'info': cached_data['info'],
                    'english_name': cached_data.get('english_name', ''),
                    'cached_at': cached_data.get('cached_at', 0),
                    'from_cache': True
                }
        
        return None
    
    def cache_animal_image(self, animal: str, image_data_url: str, english_name: str = "") -> bool:
        """Cachear imagen de un animal"""
        cache_key = self._get_cache_key(self.IMAGE_PREFIX, animal)
        
        cache_data = {
            'animal': animal.lower().strip(),
            'image': image_data_url,
            'english_name': english_name,
            'cached_at': int(time.time()),
            'cache_version': '1.0'
        }
        
        return self._set_cache(cache_key, cache_data, self.ANIMAL_IMAGE_TTL)
    
    def get_cached_animal_image(self, animal: str) -> Optional[Dict]:
        """Obtener imagen cacheada de un animal"""
        cache_key = self._get_cache_key(self.IMAGE_PREFIX, animal)
        cached_data = self._get_cache(cache_key)
        
        if cached_data:
            if 'image' in cached_data and 'animal' in cached_data:
                return {
                    'image': cached_data['image'],
                    'english_name': cached_data.get('english_name', ''),
                    'cached_at': cached_data.get('cached_at', 0),
                    'from_cache': True
                }
        
        return None
    
    def get_complete_cached_animal(self, animal: str) -> Optional[Dict]:
        """Obtener información e imagen completa cacheada de un animal"""
        info_cache = self.get_cached_animal_info(animal)
        image_cache = self.get_cached_animal_image(animal)
        
        if info_cache and image_cache:
            return {
                'info': info_cache['info'],
                'image': image_cache['image'],
                'english_name': info_cache.get('english_name', ''),
                'from_cache': True,
                'cached_at': min(info_cache['cached_at'], image_cache['cached_at'])
            }
        elif info_cache:
            return {
                'info': info_cache['info'],
                'english_name': info_cache.get('english_name', ''),
                'from_cache': True,
                'partial_cache': True,
                'cached_at': info_cache['cached_at']
            }
        
        return None
    
    def track_animal_search(self, animal: str) -> bool:
        """Trackear búsqueda de animal para analytics"""
        try:
            analytics_key = f"{self.ANALYTICS_PREFIX}searches"
            current_time = int(time.time())
            
            if self.redis_service.redis_client:
                # Usar Redis sorted set para tracking
                self.redis_service.redis_client.zincrby(analytics_key, 1, animal.lower().strip())
                self.redis_service.redis_client.expire(analytics_key, self.ANALYTICS_TTL)
                
                # También trackear por día para tendencias
                daily_key = f"{self.ANALYTICS_PREFIX}daily:{int(current_time / 86400)}"
                self.redis_service.redis_client.zincrby(daily_key, 1, animal.lower().strip())
                self.redis_service.redis_client.expire(daily_key, self.DAILY_ANALYTICS_TTL)
                
            return True
            
        except Exception as e:
            print(f"[ANALYTICS ERROR] Failed to track search for {animal}: {e}")
            return False
    
    def get_popular_animals(self, limit: int = 10) -> List[Dict]:
        """Obtener animales más populares"""
        try:
            popular_key = f"{self.ANALYTICS_PREFIX}searches"
            
            if self.redis_service.redis_client:
                # Obtener top animales del sorted set
                top_animals = self.redis_service.redis_client.zrevrange(
                    popular_key, 0, limit - 1, withscores=True
                )
                
                return [
                    {
                        'animal': animal.decode('utf-8') if isinstance(animal, bytes) else animal,
                        'search_count': int(score)
                    }
                    for animal, score in top_animals
                ]
            
            return []
            
        except Exception as e:
            print(f"[ANALYTICS ERROR] Failed to get popular animals: {e}")
            return []
    
    def get_cache_stats(self) -> Dict:
        """Obtener estadísticas del caché"""
        try:
            stats = {
                'cached_animals_info': 0,
                'cached_animals_images': 0,
                'total_searches': 0,
                'cache_enabled': bool(self.redis_service.redis_client)
            }
            
            if self.redis_service.redis_client:
                # Contar claves de caché
                info_keys = self.redis_service.redis_client.keys(f"{self.INFO_PREFIX}*")
                image_keys = self.redis_service.redis_client.keys(f"{self.IMAGE_PREFIX}*")
                
                stats['cached_animals_info'] = len(info_keys)
                stats['cached_animals_images'] = len(image_keys)
                
                # Total de búsquedas
                analytics_key = f"{self.ANALYTICS_PREFIX}searches"
                if self.redis_service.redis_client.exists(analytics_key):
                    total_searches = sum(
                        score for _, score in 
                        self.redis_service.redis_client.zrange(analytics_key, 0, -1, withscores=True)
                    )
                    stats['total_searches'] = int(total_searches)
            
            return stats
            
        except Exception as e:
            print(f"[CACHE ERROR] Failed to get cache stats: {e}")
            return {'error': str(e), 'cache_enabled': False}
    
    def clear_expired_cache(self) -> Dict:
        """Limpiar caché expirado (Redis lo hace automáticamente, esto es para memoria)"""
        cleared = 0
        current_time = time.time()
        
        if not self.redis_service.redis_client:
            # Solo necesario para fallback en memoria
            expired_keys = []
            
            for key, data in self.redis_service.fallback_sessions.items():
                if key.startswith(('cache:', 'rate_limit:')):
                    if isinstance(data, dict) and 'expires_at' in data:
                        if current_time > data['expires_at']:
                            expired_keys.append(key)
            
            for key in expired_keys:
                del self.redis_service.fallback_sessions[key]
                cleared += 1
        
        return {
            'cleared_items': cleared,
            'timestamp': int(current_time)
        }
    
    def get_upstash_efficiency_stats(self) -> Dict:
        """Obtener estadísticas específicas para optimización de Upstash"""
        try:
            stats = {
                'upstash_limits': {
                    'max_storage_mb': 256,
                    'max_commands_monthly': 500000,
                    'estimated_usage': 'unknown'
                },
                'cache_efficiency': {
                    'total_animals_cached': 0,
                    'estimated_storage_mb': 0,
                    'cache_hit_potential': 0
                },
                'recommendations': []
            }
            
            if self.redis_service.redis_client:
                # Contar elementos cacheados
                info_keys = self.redis_service.redis_client.keys(f"{self.INFO_PREFIX}*")
                image_keys = self.redis_service.redis_client.keys(f"{self.IMAGE_PREFIX}*")
                
                total_cached = len(info_keys)
                total_images = len(image_keys)
                
                # Estimaciones de memoria (aproximadas)
                # Texto de info: ~2KB promedio, Imagen base64: ~150KB promedio
                estimated_info_mb = (total_cached * 2) / 1024
                estimated_images_mb = (total_images * 150) / 1024
                total_estimated_mb = estimated_info_mb + estimated_images_mb
                
                stats['cache_efficiency'] = {
                    'total_animals_cached': total_cached,
                    'total_images_cached': total_images,
                    'estimated_storage_mb': round(total_estimated_mb, 2),
                    'storage_usage_percent': round((total_estimated_mb / 256) * 100, 1),
                    'cache_hit_potential': self._calculate_cache_potential()
                }
                
                # Recomendaciones basadas en uso
                if total_estimated_mb > 200:  # 200MB+ de uso
                    stats['recommendations'].append("Considerar limpiar imágenes más antiguas")
                
                if total_cached < 10:
                    stats['recommendations'].append("El caché está subutilizado - más búsquedas generarán valor")
                elif total_cached > 1000:
                    stats['recommendations'].append("Excelente utilización del caché")
            
            return stats
            
        except Exception as e:
            return {
                'error': f"Error calculating Upstash stats: {e}",
                'upstash_limits': {'max_storage_mb': 256, 'max_commands_monthly': 500000}
            }
    
    def _calculate_cache_potential(self) -> float:
        """Calcular el potencial de cache hits basado en búsquedas repetidas"""
        try:
            if not self.redis_service.redis_client:
                return 0.0
                
            analytics_key = f"{self.ANALYTICS_PREFIX}searches"
            if not self.redis_service.redis_client.exists(analytics_key):
                return 0.0
            
            # Obtener todas las búsquedas con scores
            all_searches = self.redis_service.redis_client.zrange(analytics_key, 0, -1, withscores=True)
            
            if not all_searches:
                return 0.0
            
            total_searches = sum(score for _, score in all_searches)
            repeated_searches = sum(score - 1 for _, score in all_searches if score > 1)
            
            if total_searches == 0:
                return 0.0
                
            return round((repeated_searches / total_searches) * 100, 1)
            
        except Exception as e:
            print(f"[ERROR] Cache potential calculation failed: {e}")
            return 0.0

# Instancia global del servicio de caché
cache_service = CacheService()