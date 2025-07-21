"""
Script de prueba para verificar el funcionamiento del servicio de sesiones
"""
import asyncio
import uuid
from session_service import session_service

async def test_session_service():
    """Probar el servicio de sesiones"""
    print("=== PRUEBA DEL SERVICIO DE SESIONES ===\n")
    
    # Test 1: Crear sesión
    session_id = str(uuid.uuid4())
    test_data = {
        "animal": "león",
        "status": "processing",
        "info": None,
        "image": None,
        "errors": []
    }
    
    print(f"1. Creando sesión {session_id[:8]}...")
    success = session_service.create_session(session_id, test_data)
    print(f"   Resultado: {'✅ Éxito' if success else '❌ Error'}")
    
    # Test 2: Obtener sesión
    print(f"\n2. Obteniendo sesión {session_id[:8]}...")
    retrieved_data = session_service.get_session(session_id)
    if retrieved_data:
        print(f"   Resultado: ✅ Éxito")
        print(f"   Animal: {retrieved_data.get('animal')}")
        print(f"   Status: {retrieved_data.get('status')}")
    else:
        print(f"   Resultado: ❌ Error - Sesión no encontrada")
    
    # Test 3: Actualizar sesión
    print(f"\n3. Actualizando sesión {session_id[:8]}...")
    if retrieved_data:
        retrieved_data["status"] = "getting_info"
        retrieved_data["info"] = "El león es el rey de la selva..."
        success = session_service.update_session(session_id, retrieved_data)
        print(f"   Resultado: {'✅ Éxito' if success else '❌ Error'}")
    
    # Test 4: Verificar actualización
    print(f"\n4. Verificando actualización {session_id[:8]}...")
    updated_data = session_service.get_session(session_id)
    if updated_data and updated_data.get("status") == "getting_info":
        print(f"   Resultado: ✅ Éxito")
        print(f"   Nuevo status: {updated_data.get('status')}")
        print(f"   Info: {updated_data.get('info')[:30]}...")
    else:
        print(f"   Resultado: ❌ Error - Actualización no funcionó")
    
    # Test 5: Extender TTL
    print(f"\n5. Extendiendo TTL de sesión {session_id[:8]}...")
    success = session_service.extend_session(session_id)
    print(f"   Resultado: {'✅ Éxito' if success else '❌ Error'}")
    
    # Test 6: Contar sesiones
    print(f"\n6. Contando sesiones activas...")
    count = session_service.get_session_count()
    print(f"   Sesiones activas: {count}")
    
    # Test 7: Eliminar sesión
    print(f"\n7. Eliminando sesión {session_id[:8]}...")
    success = session_service.delete_session(session_id)
    print(f"   Resultado: {'✅ Éxito' if success else '❌ Error'}")
    
    # Test 8: Verificar eliminación
    print(f"\n8. Verificando eliminación {session_id[:8]}...")
    deleted_data = session_service.get_session(session_id)
    if not deleted_data:
        print(f"   Resultado: ✅ Éxito - Sesión eliminada correctamente")
    else:
        print(f"   Resultado: ❌ Error - Sesión aún existe")
    
    print(f"\n=== PRUEBA COMPLETADA ===")

if __name__ == "__main__":
    asyncio.run(test_session_service())
