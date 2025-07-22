# Animal Explorer AI

Aplicación web inteligente que proporciona información detallada de animales y genera imágenes fotorealistas usando IA.

## ✨ Características Principales

- 🤖 **OpenAI GPT-4o-mini**: Información detallada y validación de animales reales
- 🎨 **Google Vertex AI Imagen 3**: Generación de imágenes fotorealistas
- 🌍 **Soporte Bilingüe**: Manejo automático español/inglés
- 🛡️ **Rate Limiting**: Control de costos y prevención de abuso
- 🔍 **Validación Inteligente**: Rechaza términos inválidos antes de generar imágenes
- ⚡ **Arquitectura Serverless**: Desplegado en Vercel con Redis persistence

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
- Cuenta OpenAI con API key
- Google Cloud Project con Vertex AI habilitado
- Redis instance (Upstash recomendado)

### Configuración
1. **Clonar repositorio**
   ```bash
   git clone <repository-url>
   cd animal-explorer-ai
   ```

2. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

3. **Variables de entorno** (Vercel Dashboard)
   - `OPENAI_API_KEY`: Tu clave de OpenAI
   - `IMAGE_GENERATION_FUNCTION_URL`: URL de Google Cloud Function
   - `REDIS_URL`: URL de conexión Redis

4. **Ejecutar localmente**
   ```bash
   python web_app.py
   ```

## 🌐 Despliegue en Producción

La aplicación está configurada para Vercel:

1. **Google Cloud Function** (generar imágenes)
   ```bash
   cd cloud_function
   ./deploy.sh
   ```

2. **Vercel Deployment**
   ```bash
   vercel --prod
   ```

## 🧪 Endpoints de Prueba

- `/test/config` - Verificar configuración
- `/test/openai` - Probar conexión OpenAI
- `/test/validation/{animal}` - Probar validación de animales
- `/api/rate-limits` - Estado de límites del usuario
- `/api/cache/stats` - Estadísticas del sistema de caché
- `/api/popular-animals` - Animales más buscados
- `/api/cache/upstash-stats` - Métricas de eficiencia Redis

## 📁 Estructura del Proyecto

```
animal-explorer-ai/
├── web_app.py              # Aplicación FastAPI principal
├── ai_services.py          # Servicios OpenAI y validación
├── cache_service.py        # Sistema de caché inteligente Redis
├── rate_limiter.py         # Sistema de límites por IP
├── session_service.py      # Persistencia Redis
├── static/                 # Frontend moderno (JS, CSS con animaciones)
├── templates/              # HTML templates responsive
├── cloud_function/         # Google Cloud Function para imágenes
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



## 💡 Desarrollado con

- FastAPI + Jinja2
- OpenAI GPT-4o-mini API
- Google Cloud Vertex AI
- Redis para persistencia
- Vercel para deployment