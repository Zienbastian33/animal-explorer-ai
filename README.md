# Animal Explorer AI

Aplicación web inteligente que proporciona información detallada de animales y genera imágenes fotorealistas usando **100% Google Gemini AI**.

> **🔄 Última actualización**: El proyecto ha sido completamente migrado de OpenAI + Vertex AI a **Google Gemini 3** (Flash + Pro Image) para simplificar la arquitectura y mejorar el rendimiento. Ahora usa una sola API key y dos modelos de vanguardia de Google.

## ✨ Características Principales

- 🤖 **Gemini 3 Flash Preview**: Información detallada y validación de animales reales (rápido y eficiente)
- 🎨 **Gemini 3 Pro Image (Nano Banana Pro)**: Generación de imágenes fotorealistas de alta calidad con razonamiento avanzado
- 🌍 **Soporte Bilingüe**: Manejo automático español/inglés
- 🛡️ **Rate Limiting**: Control de costos y prevención de abuso
- 🔍 **Validación Inteligente**: Rechaza términos inválidos antes de generar imágenes
- ⚡ **Arquitectura Serverless**: Desplegado en Vercel con Redis persistence
- 📸 **Imágenes 2K**: Generación en alta resolución con modelo de última generación
- 🚀 **100% Gemini**: Una sola API key, arquitectura simplificada, mejor integración

## 🚀 Información de Animales

La aplicación proporciona:
- **Clasificación**: Clase, grupo, cubierta corporal
- **Ecología**: Hábitat natural y dieta específica
- **Biometría**: Tamaño promedio y esperanza de vida
- **Conservación**: Estado actual de conservación
- **Datos Fascinantes**: Comportamientos únicos y características especiales

## 🛠️ Desarrollo Local

### Prerrequisitos
- Python 3.9+
- Google Gemini API key
- Redis instance (Upstash recomendado)

### Configuración
1. **Clonar repositorio**
   ```bash
   git clone <repository-url>
   cd animal-explorer-ai
   ```

2. **Crear entorno virtual**
   ```bash
   python -m venv venv
   # Windows
   .\venv\Scripts\Activate.ps1
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar API Key de Gemini** 
   - Ve a: https://aistudio.google.com/apikey
   - Crea una nueva API key (es GRATIS)
   - Copia la clave (empieza con `AIza...`)
   - Edita el archivo `.env`:
   ```env
   GEMINI_API_KEY=tu_clave_aqui
   REDIS_URL=redis://localhost:6379  # Opcional
   ```

5. **Ejecutar localmente**
   ```bash
   python web_app.py
   ```
   
6. **Abrir en navegador**
   - URL: http://localhost:8080
   - ¡Listo para explorar animales! 🐾

## 🌐 Despliegue en Producción

La aplicación está configurada para Vercel:

**Variables de entorno requeridas:**
```bash
GEMINI_API_KEY=tu_clave_gemini_aqui
REDIS_URL=tu_url_redis_upstash  # Opcional pero recomendado
```

**Pasos:**

1. **Configurar en Vercel Dashboard**
   - Settings → Environment Variables
   - Agregar `GEMINI_API_KEY` con tu clave
   - Agregar `REDIS_URL` (opcional, para producción)

2. **Desplegar**
   ```bash
   vercel --prod
   ```

3. **Verificar**
   - Abrir URL de producción
   - Probar con un animal
   - Revisar `/health` endpoint

**Nota**: Sin Redis, el sistema usa fallback en memoria (funciona pero pierde sesiones entre deployments).

## 🧪 Endpoints de Prueba

- `/health` - Estado del servidor
- `/test/config` - Verificar configuración de Gemini
- `/test/gemini` - Probar conexión con Gemini 3 Flash
- `/test/validation/{animal}` - Probar validación de animales con Gemini
- `/test/gemini-only/{animal}` - Probar generación de imágenes directa
- `/test/image` - Probar servicio de generación de imágenes
- `/api/rate-limits` - Estado de límites del usuario
- `/api/cache/stats` - Estadísticas del sistema de caché
- `/api/popular-animals` - Animales más buscados
- `/api/cache/upstash-stats` - Métricas de eficiencia Redis

### Ejemplos de Uso

```bash
# Verificar salud del servidor
curl http://localhost:8080/health

# Probar Gemini
curl http://localhost:8080/test/gemini

# Validar un animal
curl http://localhost:8080/test/validation/leon

# Generar imagen directamente
curl http://localhost:8080/test/gemini-only/dolphin
```

## 📁 Estructura del Proyecto

```
animal-explorer-ai/
├── web_app.py              # Aplicación FastAPI principal
├── ai_services.py          # Servicios Gemini (texto e imágenes)
├── config.py               # Configuración de API keys y modelos
├── cache_service.py        # Sistema de caché inteligente Redis
├── rate_limiter.py         # Sistema de límites por IP
├── session_service.py      # Persistencia Redis
├── static/                 # Frontend moderno (JS, CSS con animaciones)
├── templates/              # HTML templates responsive
├── api/index.py           # Entry point Vercel
└── vercel.json            # Configuración deployment
```

## 🔧 Características Técnicas

- **🚀 Caché Inteligente**: Sistema Redis optimizado que acelera búsquedas repetidas
- **📊 Analytics en Tiempo Real**: Tracking de animales populares y tendencias
- **🛡️ Rate Limiting**: 1 min entre consultas, 20/hora, 60/día
- **💰 Validación de Costos**: Previene generación de imágenes para términos inválidos
- **🎨 UI/UX Moderna**: Animaciones fluidas, glassmorphism, responsive design
- **🔄 Sesiones Persistentes**: Redis con TTL automático
- **🌍 Soporte Bilingüe**: Traducción automática para precisión de imágenes
- **⚡ Arquitectura Serverless**: Compatible con Vercel Functions



## 💡 Tecnologías Utilizadas

- **Backend**: FastAPI + Jinja2
- **IA de Texto**: Google Gemini 3 Flash Preview (1M tokens de contexto)
- **IA de Imágenes**: Google Gemini 3 Pro Image Preview (Nano Banana Pro)
- **Caché**: Redis (Upstash) con fallback en memoria
- **Deployment**: Vercel Serverless Functions
- **Frontend**: HTML5, CSS3 (Glassmorphism), JavaScript Vanilla

## 🎯 Modelos de IA Gemini

### Gemini 3 Flash Preview
- **Uso**: Información y validación de animales
- **Características**: 
  - 1,048,576 tokens de entrada
  - 65,536 tokens de salida
  - Multimodal (texto, imágenes, video, audio, PDF)
  - Optimizado para velocidad y escala

### Gemini 3 Pro Image Preview (Nano Banana Pro)
- **Uso**: Generación de imágenes fotorealistas
- **Características**:
  - Resolución hasta 4K (configurado en 2K)
  - Razonamiento avanzado ("Thinking mode")
  - Renderizado de texto de alta fidelidad
  - Hasta 14 imágenes de referencia
  - Integración con Google Search para fundamentación

---

## 📝 Historial de Cambios

### v2.0.0 - Migración 100% Gemini (Febrero 2026)

#### 📊 Comparación v1.x vs v2.0

| Aspecto | v1.x (Anterior) | v2.0 (Actual) | Mejora |
|---------|----------------|---------------|---------|
| **IA de Texto** | OpenAI GPT-4o-mini | Gemini 3 Flash Preview | ✅ 8x más contexto (1M vs 128K tokens) |
| **IA de Imágenes** | Vertex AI Imagen 3 (Cloud Function) | Gemini 3 Pro Image (API directa) | ✅ Sin Cloud Functions |
| **API Keys** | 2 (OpenAI + Google Cloud) | 1 (solo Gemini) | ✅ Configuración más simple |
| **Dependencias** | openai + google-cloud-aiplatform | google-genai | ✅ Menos paquetes |
| **Infraestructura** | Cloud Functions + Vercel | Solo Vercel | ✅ Arquitectura simplificada |
| **Costo** | Doble servicio | Un solo servicio | ✅ Más económico |
| **Rendimiento** | Bueno | Excelente | ✅ Gemini Flash más rápido |
| **Mantenimiento** | Complejo | Simple | ✅ Menos componentes |

#### 🎯 Cambios Principales
1. **Eliminación de OpenAI GPT-4o-mini**
   - Reemplazado por **Gemini 3 Flash Preview**
   - Información de animales más rápida y eficiente
   - 1M tokens de contexto (vs 128K de GPT-4o-mini)

2. **Eliminación de Cloud Functions**
   - Generación de imágenes ahora directa vía API de Gemini
   - Sin necesidad de Google Cloud Functions separadas
   - Arquitectura simplificada y más mantenible

3. **API Key Unificada**
   - Solo requiere `GEMINI_API_KEY`
   - Menos configuración, más simple
   - Gratuita en AI Studio de Google

#### ✨ Mejoras
- ⚡ **Mejor rendimiento**: Gemini Flash es más rápido
- 💰 **Más económico**: Una sola API, mejor pricing
- 🔧 **Mantenimiento simple**: Menos dependencias
- 🌐 **Mejor integración**: Todo en ecosistema Google
- 📊 **Más capacidad**: 1M tokens de entrada

#### 🔄 Archivos Modificados
- `config.py` - Configuración unificada de Gemini
- `ai_services.py` - Reescrito para usar solo Gemini SDK
- `requirements.txt` - Removido OpenAI SDK
- `templates/` - Actualizadas referencias de UI
- `README.md` - Documentación completa actualizada
- `.env` - Simplificado a una sola API key

#### 📦 Dependencias Actualizadas
```python
# Antes
openai==1.54.3
google-cloud-aiplatform==1.40.0

# Después  
google-genai==0.5.0  # ✅ Solo esto
```

#### 🚀 Migrando desde v1.x
Si tienes una versión anterior:
1. Obtén API key de Gemini: https://aistudio.google.com/apikey
2. Actualiza `.env`: Solo `GEMINI_API_KEY` necesaria
3. Elimina `OPENAI_API_KEY` e `IMAGE_GENERATION_FUNCTION_URL`
4. Reinstala dependencias: `pip install -r requirements.txt`
5. ¡Listo! El proyecto funcionará con Gemini

---

## 👨‍💻 Desarrollado con ❤️

**Autor**: Bastian  
**Para**: Trini  
**Stack**: FastAPI + Google Gemini 3 + Redis + Vercel