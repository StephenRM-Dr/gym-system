from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from database import get_connection
from datetime import datetime, timedelta
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request
from fastapi import Form
from fastapi.responses import RedirectResponse


templates = Jinja2Templates(directory="templates")

app = FastAPI(title="Gym System API")
NODE_API_URL = "http://localhost:3000/send-message"


# --- Modelos de Datos (Pydantic) ---
class PaymentRequest(BaseModel):
    dni: str
    full_name: str
    phone_number: str
    plan_id: int

# --- Endpoints ---

@app.get("/")
def read_root():
    return {"status": "Gym API is running"}
@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard_view(request: Request):
    conn = get_connection()
    cur = conn.cursor()
    try:
        # 1. Métricas
        cur.execute("SELECT COUNT(*) FROM members WHERE status = true")
        total_activos = cur.fetchone()[0]
        
        cur.execute("SELECT full_name, phone_number FROM members WHERE expiration_date = CURRENT_DATE AND status = true")
        vencen_hoy = cur.fetchall()
        
        cur.execute("SELECT full_name, expiration_date FROM members WHERE expiration_date BETWEEN CURRENT_DATE + 1 AND CURRENT_DATE + 7 AND status = true")
        proximos = cur.fetchall()

        # 2. Planes para el modal
        cur.execute("SELECT id, name FROM plans")
        lista_planes = [{"id": row[0], "nombre": row[1]} for row in cur.fetchall()]

        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "resumen": {
                "total_socios_activos": total_activos,
                "vencimientos_hoy_count": len(vencen_hoy)
            },
            "detalles_hoy": [{"nombre": row[0], "telefono": row[1]} for row in vencen_hoy],
            "proximos_7_dias": proximos,
            "planes": lista_planes
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@app.post("/register-payment-web")
async def register_payment_web(dni: str = Form(...), plan_id: int = Form(...)):
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # 1. Validamos si el miembro existe
        cur.execute("SELECT expiration_date, full_name FROM members WHERE dni = %s", (dni,))
        member = cur.fetchone()
        
        if member is None:
            # En lugar de explotar, devolvemos un error amigable
            return {"error": f"El DNI {dni} no está registrado en el sistema."}
            
        current_expiration = member[0]
        nombre_usuario = member[1]

        # 2. Obtener días del plan
        cur.execute("SELECT duration_days FROM plans WHERE id = %s", (plan_id,))
        plan_data = cur.fetchone()
        if not plan_data:
            return {"error": "El plan seleccionado no existe."}
        
        days_to_add = plan_data[0]
        hoy = datetime.now().date()

        # 3. Lógica de Acumulación mejorada
        # Si la fecha es None (nula en DB) o ya pasó, usamos HOY
        if current_expiration is None or current_expiration < hoy:
            base_date = hoy
        else:
            base_date = current_expiration

        new_expiration = base_date + timedelta(days=days_to_add)

        # 4. Actualización
        # 1. Actualizamos al socio y obtenemos su ID interno
        cur.execute("""
            UPDATE members 
            SET expiration_date = %s, plan_id = %s, status = true 
            WHERE dni = %s RETURNING id
        """, (new_expiration, plan_id, dni))

        res = cur.fetchone()
        if res:
            member_id = res[0]
            # 2. Insertamos el LOG del pago para auditoría
            cur.execute("""
                INSERT INTO payment_logs (member_id, plan_id, amount, previous_expiration, new_expiration)
                VALUES (%s, %s, (SELECT price FROM plans WHERE id = %s), %s, %s)
            """, (member_id, plan_id, plan_id, current_expiration, new_expiration))

        conn.commit()
        return RedirectResponse(url="/dashboard", status_code=303)

    except Exception as e:
        conn.rollback()
        return {"error": f"Error interno: {str(e)}"}
    finally:
        cur.close()
        conn.close()

@app.post("/resend-whatsapp")
async def resend_whatsapp(request: Request):
    data = await request.json()
    phone_number = data.get("phone_number")
    full_name = data.get("full_name")
    
    if not phone_number or not full_name:
        raise HTTPException(status_code=400, detail="Phone number and name are required.")

    message = (f"⚠️ ¡Hola {full_name}! Tu plan vence HOY. "
               "No pierdas el ritmo de entrenamiento, te esperamos en caja para renovar.")
    
    payload = {"number": phone_number, "message": message}
    
    try:
        response = requests.post(NODE_API_URL, json=payload, timeout=10)
        
        if response.status_code == 200:
            return {"status": "Message sent successfully"}
        else:
            raise HTTPException(status_code=response.status_code, detail=f"Error from gateway: {response.text}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to gateway: {str(e)}")