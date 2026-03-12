import psycopg2
import requests
from datetime import datetime, timedelta

# 1. Configuración de conexiones
DB_PARAMS = {
    "host": "localhost",
    "database": "gym_system",
    "user": "postgres",
    "password": "1234"
}
NODE_API_URL = "http://localhost:3000/send-message"

def check_and_send_alerts():
    conn = get_connection()
    if conn:
        cur = conn.cursor()

        # 2. Query de Auditoría: Buscar miembros que vencen en 3 días
        # Filtramos por status activo y que la fecha de vencimiento sea pronto
        query = """
            SELECT full_name, phone_number, expiration_date 
            FROM members 
            WHERE expiration_date = CURRENT_DATE + INTERVAL '3 days'
            AND status = uuid_true_si_es_boolean; -- Ajusta según tu tipo de dato
        """
        cur.execute(query)
        vencimientos = cur.fetchall()

        for socio in vencimientos:
            nombre, telefono, fecha = socio
            mensaje = f"Hola {nombre}, te saludamos del Gym. Te recordamos que tu plan vence el {fecha}. ¡No te quedes sin entrenar!"
            
            # 3. Disparar al Gateway de Node.js
            payload = {"number": telefono, "message": mensaje}
            response = requests.post(NODE_API_URL, json=payload)
            
            if response.status_code == 200:
                print(f"✅ Alerta enviada a {nombre}")
            else:
                print(f"❌ Error enviando a {nombre}: {response.text}")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error en el sistema: {e}")

if __name__ == "__main__":
    check_and_send_alerts()