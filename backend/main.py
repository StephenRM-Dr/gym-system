import requests
from database import get_connection
from datetime import datetime

# URL del Gateway de Node.js
NODE_API_URL = "http://localhost:3000/send-message"

def run_audit_and_notify():
    conn = get_connection()
    if not conn:
        return

    try:
        cur = conn.cursor()
        
        # MEJORA: Seleccionamos solo hoy o exactamente en 3 días
        # Calculamos la diferencia de días para personalizar el mensaje
        query = """
            SELECT id, full_name, phone_number, expiration_date,
                   (expiration_date - CURRENT_DATE) as dias_restantes
            FROM members 
            WHERE status = true
            AND (expiration_date = CURRENT_DATE OR expiration_date = CURRENT_DATE + INTERVAL '3 days')
            AND (last_notification_date IS NULL OR last_notification_date < CURRENT_DATE);
        """
        cur.execute(query)
        results = cur.fetchall()

        if not results:
            print("🔍 No hay vencimientos específicos para notificar hoy.")
            return

        for row in results:
            member_id, nombre, telefono, fecha_venc, dias_restantes = row
            
            # Personalizamos el mensaje según la urgencia
            if dias_restantes == 3:
                mensaje = (f"¡Hola {nombre}! 💪 Te recordamos que tu plan en el Gimnasio "
                           f"vence en 3 días ({fecha_venc}). ¡Te esperamos para renovar!")
            else:
                mensaje = (f"⚠️ ¡Hola {nombre}! Tu plan vence HOY. "
                           "No pierdas el ritmo de entrenamiento, te esperamos en caja para renovar.")

            # Enviamos al Gateway
            payload = {"number": telefono, "message": mensaje}
            
            try:
                response = requests.post(NODE_API_URL, json=payload, timeout=10)
                
                if response.status_code == 200:
                    print(f"✅ Mensaje enviado ({dias_restantes} días) a {nombre}")
                    # Actualizar la fecha de última notificación para evitar SPAM
                    cur.execute("""
                        UPDATE members 
                        SET last_notification_date = CURRENT_DATE 
                        WHERE id = %s
                    """, (member_id,))
                    conn.commit()
                else:
                    print(f"❌ Error Gateway para {nombre}: {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"📡 Error de conexión con el Gateway: {e}")

    except Exception as e:
        print(f"⚠️ Error durante la auditoría: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    print(f"🚀 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iniciando auditoría...")
    run_audit_and_notify()