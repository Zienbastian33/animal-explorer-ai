# Animal Explorer AI

Aplicación completa en Python que permite consultar información de animales usando ChatGPT 4o-mini y generar imágenes usando Google Vertex AI Imagen 3.

## Características

- 🤖 **ChatGPT 4o-mini**: Información detallada de animales
- 🎨 **Google Imagen 3**: Generación de imágenes fotorealistas
- 🖥️ **Interfaz Desktop**: Aplicación tkinter moderna
- 🌐 **Aplicación Web**: FastAPI con interfaz responsive
- ⚡ **Procesamiento Asíncrono**: Experiencia fluida del usuario
- 🔒 **Manejo de Errores**: Gestión robusta de errores y autenticación

## Instalación

### 1. Clonar repositorio
```bash
git clone <repository-url>
cd animal-ai-app
```

### 2. Crear entorno virtual
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Crea un archivo `.env` a partir de `.env.example` y añade tus credenciales:

```
OPENAI_API_KEY="tu_clave_de_openai"
GOOGLE_APPLICATION_CREDENTIALS="ruta/a/tus/credenciales.json"
GOOGLE_CLOUD_PROJECT_ID="tu_id_de_proyecto_gcp"
```

## Uso

### Aplicación de Escritorio

```bash
python tkinter_app.py
```

### Aplicación Web

```bash
python web_app.py
# o con uvicorn para desarrollo
uvicorn web_app:app --reload
```

Luego, abre tu navegador en `http://127.0.0.1:8000`.

## Estructura del Proyecto

```
animal_ai_app/
├── .env.example
├── README.md
├── ai_services.py
├── config.py
├── requirements.txt
├── tkinter_app.py
├── web_app.py
├── static/
│   ├── script.js
│   └── style.css
├── templates/
│   ├── index.html
│   └── result.html
├── api/
│   └── index.py          # Punto de entrada para Vercel
├── verify_routes.py       # Script de verificación de rutas
├── vercel.json           # Configuración de despliegue
└── uploads/
    └── (imágenes generadas)
```

## Debugging y Verificación

### Verificar Rutas Localmente

Antes de desplegar, puedes verificar que todas las rutas funcionen correctamente:

```bash
# Iniciar el servidor local
python web_app.py

# En otra terminal, ejecutar el script de verificación
python verify_routes.py
```

### Debugging en Vercel

Si experimentas errores 404 en producción:

1. **Verificar logs de Vercel:**
   ```bash
   vercel logs
   ```

2. **Verificar variables de entorno:**
   - `OPENAI_API_KEY`
   - `IMAGE_GENERATION_FUNCTION_URL`

3. **Rutas críticas a verificar:**
   - `GET /` - Página principal
   - `POST /research` - Iniciar investigación
   - `GET /status/{session_id}` - Polling de estado
   - `GET /health` - Health check

### Solución de Problemas Comunes

- **Error 404 en `/status/`**: Verificar que `vercel.json` tenga las rutas correctas
- **Sesiones perdidas**: Normal en serverless, se maneja con cookies
- **Timeouts**: Verificar que `maxDuration` esté configurado en `vercel.json`
