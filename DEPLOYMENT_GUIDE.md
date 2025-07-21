# Guía de Despliegue - Animal Explorer AI

## Problema Resuelto

Se ha solucionado el **error 404 persistente** en el endpoint `/status/{session_id}` que causaba polling infinito en producción (Vercel).

### Causa Raíz Identificada
- **Sesiones en memoria**: Se perdían entre invocaciones serverless
- **Arquitectura serverless**: Cada request se ejecuta en un contenedor independiente
- **Estado no persistente**: Los datos se almacenaban en `sessions = {}` que se reiniciaba

### Solución Implementada
- **Almacenamiento persistente**: Redis como backend de sesiones
- **Fallback robusto**: Sistema en memoria para desarrollo local
- **Gestión automática**: TTL, extensión y limpieza de sesiones

## Cambios Realizados

### 1. Nuevo Servicio de Sesiones (`session_service.py`)
```python
from session_service import session_service

# Crear sesión
session_service.create_session(session_id, data)

# Obtener sesión
session_data = session_service.get_session(session_id)

# Actualizar sesión
session_service.update_session(session_id, data)
```

### 2. Dependencias Actualizadas (`requirements.txt`)
```txt
# Session storage
redis==5.0.1
```

### 3. Configuración Vercel (`vercel.json`)
```json
{
  "env": {
    "REDIS_URL": "$REDIS_URL"
  }
}
```

### 4. Endpoints Optimizados (`web_app.py`)
- ✅ `POST /research`: Usa sesiones persistentes
- ✅ `GET /status/{session_id}`: Lee desde Redis/fallback
- ✅ `process_animal_research`: Actualiza estado persistente

## Configuración de Redis

### Opción 1: Redis Cloud (Recomendado para producción)
1. Crear cuenta en [Redis Cloud](https://redis.com/try-free/)
2. Crear una base de datos gratuita
3. Copiar la URL de conexión
4. Configurar en Vercel:
```bash
vercel env add REDIS_URL
# Pegar: redis://default:password@host:port
```

### Opción 2: Upstash Redis (Recomendado para serverless)
1. Crear cuenta en [Upstash](https://upstash.com/)
2. Clic en "Create Database"
3. Seleccionar región más cercana
4. **IMPORTANTE**: Copiar la **"Redis URL"** (NO la "REST URL")
   - ✅ Correcto: `redis://default:password@host:6379`
   - ❌ Incorrecto: `https://host.upstash.io` (REST URL)
5. Configurar en Vercel Dashboard:
   - Settings → Environment Variables → Add New
   - Name: `REDIS_URL`
   - Value: [La Redis URL copiada]

### Opción 3: Sin Redis (Solo desarrollo)
- La aplicación funciona sin Redis usando fallback en memoria
- **ADVERTENCIA**: Las sesiones se perderán entre deployments

## Pasos de Despliegue

### 1. Configurar Variables de Entorno en Vercel
```bash
# Variables existentes
vercel env add OPENAI_API_KEY
vercel env add IMAGE_GENERATION_FUNCTION_URL

# Nueva variable para sesiones
vercel env add REDIS_URL
```

### 2. Desplegar la Aplicación
```bash
vercel --prod
```

### 3. Verificar Funcionamiento
1. Abrir la URL de producción
2. Buscar un animal (ej: "león")
3. Verificar que el polling funciona correctamente
4. Confirmar que no aparece error 404

## Pruebas Locales

### Probar el Servicio de Sesiones
```bash
python test_sessions.py
```

### Ejecutar la Aplicación Localmente
```bash
python web_app.py
```

## Monitoreo y Debugging

### Logs de Vercel
```bash
vercel logs --follow
```

### Logs de Sesiones
- `[INFO] Redis connected successfully` - Redis funcionando
- `[WARNING] Redis connection failed` - Usando fallback
- `[DEBUG] Session {id} status: {status}` - Estado de sesiones

### Métricas de Redis
- Usar dashboard de Redis Cloud/Upstash
- Monitorear conexiones y uso de memoria
- Configurar alertas si es necesario

## Beneficios de la Solución

### ✅ Compatibilidad Total con Vercel
- Funciona en arquitectura serverless
- No depende del sistema de archivos
- Escalable automáticamente

### ✅ Robustez
- Fallback automático a memoria local
- Manejo de errores de conexión
- TTL automático para limpieza

### ✅ Rendimiento
- Sesiones persistentes entre requests
- Extensión automática de TTL
- Polling eficiente sin pérdida de estado

### ✅ Mantenimiento
- Limpieza automática de sesiones expiradas
- Logs detallados para debugging
- Configuración flexible

## Troubleshooting

### Error: "Redis connection failed"
- Verificar `REDIS_URL` en variables de entorno
- Confirmar que la URL incluye credenciales
- Probar conexión desde terminal local

### Error: "Session not found"
- Verificar que Redis está funcionando
- Confirmar que la sesión no ha expirado (1 hora TTL)
- Revisar logs para errores de conexión

### Polling Infinito
- Verificar que `/status/{session_id}` retorna 200
- Confirmar que el `session_id` es válido
- Revisar logs del navegador para errores

## Próximos Pasos Opcionales

1. **Monitoreo Avanzado**: Integrar con Sentry o similar
2. **Caché de Resultados**: Cachear respuestas de ChatGPT/Vertex AI
3. **Rate Limiting**: Implementar límites por IP
4. **Analytics**: Tracking de uso y métricas

---

**¡El error 404 en `/status/{session_id}` ha sido completamente resuelto!** 🎉
