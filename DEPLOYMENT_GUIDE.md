# 🚀 Guía de Despliegue - Animal Explorer AI (Arquitectura Híbrida)

## 📋 Resumen de la Arquitectura

Esta aplicación utiliza una **arquitectura híbrida** para optimizar costos y compatibilidad:

- **Frontend + OpenAI API**: Desplegado en **Vercel** (liviano, ~60MB)
- **Generación de Imágenes**: **Google Cloud Function** (pesado, con Vertex AI)

## 🔧 Paso 1: Desplegar Google Cloud Function

### Prerrequisitos:
1. **Google Cloud CLI** instalado y autenticado
2. **Proyecto de Google Cloud** con facturación habilitada
3. **Vertex AI API** habilitada

### Comandos:
```bash
# 1. Navegar a la carpeta de la función
cd cloud_function

# 2. Editar deploy.bat (Windows) o deploy.sh (Linux/Mac)
# Cambiar "your-google-project-id" por tu ID real de proyecto

# 3. Ejecutar despliegue
# En Windows:
deploy.bat

# En Linux/Mac:
chmod +x deploy.sh
./deploy.sh
```

### Resultado:
- Obtendrás una URL como: `https://us-central1-tu-proyecto.cloudfunctions.net/generate-animal-image`
- **¡GUARDA ESTA URL!** La necesitarás para Vercel.

## 🌐 Paso 2: Desplegar en Vercel

### Prerrequisitos:
1. Cuenta en **Vercel**
2. Repositorio en **GitHub** con tu código

### Configuración:
1. **Conecta tu repositorio** a Vercel
2. **Configura las variables de entorno** en Vercel:
   ```
   OPENAI_API_KEY=tu_clave_openai
   IMAGE_GENERATION_FUNCTION_URL=https://us-central1-tu-proyecto.cloudfunctions.net/generate-animal-image
   ```

### Despliegue:
- Vercel detectará automáticamente `vercel.json` y desplegará tu aplicación
- El peso total será ~60MB (compatible con Vercel)

## 🔑 Variables de Entorno Necesarias

### Para Vercel:
```env
OPENAI_API_KEY=sk-...
IMAGE_GENERATION_FUNCTION_URL=https://us-central1-tu-proyecto.cloudfunctions.net/generate-animal-image
```

### Para Google Cloud Function:
- Se configuran automáticamente durante el despliegue
- Usa las credenciales por defecto del proyecto

## 📊 Costos Estimados

### Vercel:
- **Gratis** hasta 100GB de ancho de banda
- **$20/mes** para uso comercial

### Google Cloud Function:
- **Gratis** hasta 2M invocaciones/mes
- **~$0.40** por cada 1M invocaciones adicionales
- **Vertex AI**: ~$0.02 por imagen generada

## 🔄 Flujo de Funcionamiento

1. Usuario visita tu app en Vercel
2. Introduce nombre de animal
3. Vercel obtiene info del animal (OpenAI)
4. Vercel llama a Cloud Function para generar imagen
5. Cloud Function usa Vertex AI y devuelve imagen
6. Usuario ve resultado completo

## 🐛 Solución de Problemas

### Error: "Cloud Function not found"
- Verifica que la URL en `IMAGE_GENERATION_FUNCTION_URL` sea correcta
- Asegúrate de que la función esté desplegada y sea pública

### Error: "Authentication failed" en Cloud Function
- Verifica que Vertex AI API esté habilitada
- Confirma que el proyecto tenga facturación activa

### Error: "Module not found" en Vercel
- Verifica que `requirements.txt` no tenga dependencias pesadas
- Solo debe tener: openai, fastapi, httpx, etc.

## ✅ Verificación de Despliegue

### Cloud Function:
```bash
curl -X POST https://tu-cloud-function-url \
  -H "Content-Type: application/json" \
  -d '{"animal": "león"}'
```

### Vercel:
- Visita tu URL de Vercel
- Prueba generar información de un animal

## 🎯 Ventajas de esta Arquitectura

✅ **Compatible con Vercel** (sin límites de peso)  
✅ **Mantiene Google Vertex AI** (aprovecha tus créditos)  
✅ **Escalable** (cada parte escala independientemente)  
✅ **Costo-efectivo** (paga solo por uso)  
✅ **Fácil mantenimiento** (separación clara de responsabilidades)

## 📞 Soporte

Si tienes problemas durante el despliegue, verifica:
1. Todas las variables de entorno están configuradas
2. Las APIs necesarias están habilitadas
3. Los permisos de Google Cloud son correctos

¡Tu Animal Explorer AI estará funcionando en minutos! 🎉
