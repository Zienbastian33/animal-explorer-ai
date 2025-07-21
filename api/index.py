# Vercel entry point para FastAPI
# Necesitamos importar directamente todos los módulos necesarios aquí
import sys
import os

# Agregar el directorio principal al path para permitir importaciones
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar la app
from web_app import app as application

# Exportar la app con el nombre que Vercel espera
app = application
