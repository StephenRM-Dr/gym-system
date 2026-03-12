import requests
from database import get_connection
from datetime import datetime

# URL del Gateway de Node.js que ya tienes corriendo
NODE_API_URL = "http://localhost:3000/send-message"

def run_audit_and_notify():
    conn = get_connection()
    if not conn:
        return

    try:
        cur = conn.cursor()
        
        # Buscamos miembros que vencen en exactamente 3 días
        query = """
            SELECT full_name, phone_number, expiration_date 
            FROM members 
            WHERE expiration_date = CURRENT_DATE + INTERVAL '3 days'
            AND status = true;
        """
        cur.execute(query)
        results = cur.fetchall()

        if not results:
            print("🔍 No hay vencimientos próximos para hoy.")
            return

        for row in results:
            nombre, telefono, fecha_venc = row
            
            # Personalizamos el mensaje
            mensaje = (f"¡Hola {nombre}! 💪 Te saludamos de tu Gimnasio. "
                       f"Te recordamos que tu plan vence el {fecha_venc}. "
                       "¡No pierdas el ritmo, te esperamos para renovar!")

            # Enviamos al Gateway
            payload = {"number": telefono, "message": mensaje}
            response = requests.post(NODE_API_URL, json=payload)

            if response.status_code == 200:
                print(f"✅ Mensaje enviado exitosamente a {nombre}")
            else:
                print(f"❌ Error al enviar a {nombre}: {response.text}")

    except Exception as e:
        print(f"⚠️ Error durante la auditoría: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    print("🚀 Iniciando auditoría de membresías...")
    run_audit_and_notify()