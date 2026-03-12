import psycopg2
from database import get_connection
from datetime import datetime, timedelta

def register_member_payment(dni, plan_id):
    conn = get_connection()
    if not conn:
        return

    try:
        cur = conn.cursor()

        # 1. Obtener la duración del plan seleccionado
        cur.execute("SELECT name, duration_days FROM plans WHERE id = %s", (plan_id,))
        plan = cur.fetchone()
        
        if not plan:
            print("❌ Error: El Plan seleccionado no existe.")
            return
        
        plan_name, days = plan
        
        # 2. Calcular la nueva fecha de vencimiento
        new_expiration = datetime.now() + timedelta(days=days)

        # 3. Actualizar el miembro (o insertarlo si no existe)
        # Usamos ON CONFLICT para que si el DNI ya existe, solo actualice la fecha y el plan
        upsert_query = """
            INSERT INTO members (dni, full_name, phone_number, plan_id, status, registration_date, expiration_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (dni) 
            DO UPDATE SET 
                plan_id = EXCLUDED.plan_id,
                expiration_date = EXCLUDED.expiration_date,
                status = true;
        """
        
        # Para esta prueba, usaremos datos fijos, pero luego vendrán de un formulario
        # (dni, full_name, phone_number, plan_id, status, reg_date, exp_date)
        member_data = (dni, "Cliente VIP", "584247616215", plan_id, True, datetime.now(), new_expiration)
        
        cur.execute(upsert_query, member_data)
        conn.commit()
        
        print(f"✅ ¡Pago procesado! {plan_name} registrado.")
        print(f"📅 Nueva fecha de vencimiento: {new_expiration.strftime('%d/%m/%Y')}")

    except Exception as e:
        print(f"⚠️ Error al registrar pago: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    # Simulación de un registro en caja:
    print("--- Módulo de Caja ---")
    cedula = input("Ingrese DNI del cliente: ")
    id_plan = input("Ingrese ID del plan (ej. 1 para Mensual): ")
    register_member_payment(cedula, int(id_plan))