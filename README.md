# Animal Explorer AI

<<<<<<< HEAD
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
└── uploads/
    └── (imágenes generadas)
```
=======
Aplicación híbrida que usa OpenAI para información de animales y Google Vertex AI para generar imágenes.

## Arquitectura

- **Frontend + OpenAI API**: Desplegado en Vercel
- **Generación de Imágenes**: Google Cloud Function con Vertex AI

## Tecnologías

- FastAPI
- OpenAI GPT-4
- Google Vertex AI (Imagen 3)
- Vercel
- Google Cloud Functions

## Despliegue

Ver `DEPLOYMENT_GUIDE.md` para instrucciones detalladas de despliegue.
>>>>>>> d8c5f21840aaa5dcdf9c7a83abf6e7dbc04b23a5
