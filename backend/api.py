from fastapi import FastAPI, HTTPException, Request, Form
from pydantic import BaseModel
import requests
from database import get_connection
from datetime import datetime, timedelta
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse

templates = Jinja2Templates(directory="templates")
app = FastAPI(title="Gym System API")
NODE_API_URL = "http://localhost:3000/send-message"

# --- Modelos de Datos ---
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
        # 1. Métricas Principales
        cur.execute("SELECT COUNT(*) FROM members WHERE status = true")
        total_activos = cur.fetchone()[0]
        
        cur.execute("SELECT full_name, phone_number FROM members WHERE expiration_date = CURRENT_DATE AND status = true")
        vencen_hoy = cur.fetchall()
        
        cur.execute("SELECT COUNT(*) FROM members WHERE expiration_date BETWEEN CURRENT_DATE + 1 AND CURRENT_DATE + 7 AND status = true")
        proximos_count = cur.fetchone()[0]

        # 2. Datos para Gráfico de Ingresos (Últimos 12 meses)
        cur.execute("""
            WITH monthly_summary AS (
                SELECT 
                    TO_CHAR(payment_date, 'YYYY-MM') as month, 
                    SUM(amount) as total
                FROM payment_logs
                WHERE payment_date >= NOW() - INTERVAL '12 months'
                GROUP BY month
            ),
            months AS (
                SELECT TO_CHAR(GENERATE_SERIES(
                    NOW() - INTERVAL '11 months',
                    NOW(),
                    INTERVAL '1 month'
                ), 'YYYY-MM') as month
            )
            SELECT
                TO_CHAR(TO_DATE(m.month, 'YYYY-MM'), 'Mon') as month_name,
                COALESCE(s.total, 0) as total_amount
            FROM months m
            LEFT JOIN monthly_summary s ON m.month = s.month
            ORDER BY m.month ASC;
        """)
        ingresos_raw = cur.fetchall()
        ingresos_labels = [row[0] for row in ingresos_raw]
        ingresos_values = [float(row[1]) for row in ingresos_raw]

        # 3. Datos para Gráfico de Inscripciones (Últimos 7 días)
        cur.execute("""
            SELECT TO_CHAR(created_at, 'DD/MM'), COUNT(*)
            FROM members
            WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY TO_CHAR(created_at, 'DD/MM'), created_at
            ORDER BY created_at ASC
        """)
        inscripciones_raw = cur.fetchall()
        inscripciones_labels = [row[0] for row in inscripciones_raw]
        inscripciones_values = [row[1] for row in inscripciones_raw]

        # 4. Planes para el modal
        cur.execute("SELECT id, name FROM plans ORDER BY duration_days ASC")
        lista_planes = [{"id": row[0], "nombre": row[1]} for row in cur.fetchall()]

        # ÚNICO RETURN con toda la data consolidada
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "resumen": {
                "total_socios_activos": total_activos,
                "vencimientos_hoy_count": len(vencen_hoy),
                "proximos_7_dias_count": proximos_count
            },
            "detalles_hoy": [{"nombre": row[0], "telefono": row[1]} for row in vencen_hoy],
            "planes": lista_planes,
            "graficos": {
                "ingresos_labels": ingresos_labels,
                "ingresos_values": ingresos_values,
                "inscripciones_labels": inscripciones_labels,
                "inscripciones_values": inscripciones_values
            }
        })

    except Exception as e:
        print(f"Error en Dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.post("/register-payment-web")
async def register_payment_web(dni: str = Form(...), plan_id: int = Form(...)):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT expiration_date, id FROM members WHERE dni = %s", (dni,))
        member = cur.fetchone()
        
        if member is None:
            return {"error": f"El DNI {dni} no está registrado."}
            
        current_expiration = member[0]
        member_id = member[1]

        cur.execute("SELECT duration_days, price FROM plans WHERE id = %s", (plan_id,))
        plan_data = cur.fetchone()
        days_to_add = plan_data[0]
        price = plan_data[1]
        
        hoy = datetime.now().date()
        base_date = max(hoy, current_expiration) if current_expiration else hoy
        new_expiration = base_date + timedelta(days=days_to_add)

        # Actualización de Socio
        cur.execute("UPDATE members SET expiration_date = %s, plan_id = %s, status = true WHERE id = %s", 
                   (new_expiration, plan_id, member_id))

        # Log de Auditoría
        cur.execute("""
            INSERT INTO payment_logs (member_id, plan_id, amount, previous_expiration, new_expiration)
            VALUES (%s, %s, %s, %s, %s)
        """, (member_id, plan_id, price, current_expiration, new_expiration))

        conn.commit()
        return RedirectResponse(url="/dashboard", status_code=303)
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()
        conn.close()

@app.post("/add-member")
async def add_member(
    full_name: str = Form(...),
    dni: str = Form(...),
    phone_number: str = Form(...),
    plan_id: int = Form(...),
):
    print("add_member function called")
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Verificar si el DNI ya existe
        cur.execute("SELECT id FROM members WHERE dni = %s", (dni,))
        if cur.fetchone():
            # Idealmente, aquí devolverías un mensaje de error a la UI
            raise HTTPException(status_code=409, detail="El DNI ya está registrado.")

        # Obtener datos del plan
        cur.execute("SELECT duration_days, price FROM plans WHERE id = %s", (plan_id,))
        plan_data = cur.fetchone()
        if not plan_data:
            raise HTTPException(status_code=404, detail="Plan no encontrado.")
        
        days_to_add, price = plan_data
        expiration_date = datetime.now().date() + timedelta(days=days_to_add)

        # Insertar nuevo socio
        cur.execute(
            """
            INSERT INTO members (full_name, dni, phone_number, plan_id, expiration_date, status, created_at)
            VALUES (%s, %s, %s, %s, %s, true, NOW())
            RETURNING id;
            """,
            (full_name, dni, phone_number, plan_id, expiration_date)
        )
        new_member_id = cur.fetchone()[0]

        # Registrar el primer pago
        cur.execute(
            """
            INSERT INTO payment_logs (member_id, plan_id, amount, new_expiration)
            VALUES (%s, %s, %s, %s);
            """,
            (new_member_id, plan_id, price, expiration_date)
        )

        conn.commit()
        return RedirectResponse(url="/dashboard", status_code=303)
    except Exception as e:
        conn.rollback()
        # Aquí podrías loggear el error o mostrar una página de error más amigable
        raise HTTPException(status_code=500, detail=f"Error interno: {e}")
    finally:
        cur.close()
        conn.close()


@app.get("/members/list", response_class=HTMLResponse)
def get_members_list(request: Request, filter: str = "all", page: int = 1):
    conn = get_connection()
    cur = conn.cursor()
    try:
        limit = 10
        offset = (page - 1) * limit
        
        if filter == "activos":
            where_clause = "WHERE status = true"
            title = "Socios Activos"
        elif filter == "vencen_hoy":
            where_clause = "WHERE expiration_date = CURRENT_DATE AND status = true"
            title = "Vencimientos de Hoy"
        elif filter == "proximos":
            where_clause = "WHERE expiration_date BETWEEN CURRENT_DATE + 1 AND CURRENT_DATE + 7 AND status = true"
            title = "Próximos Vencimientos"
        else:
            where_clause = ""
            title = "Lista General"

        cur.execute(f"SELECT full_name, dni, phone_number, expiration_date FROM members {where_clause} LIMIT %s OFFSET %s", (limit, offset))
        members = cur.fetchall()
        
        cur.execute(f"SELECT COUNT(*) FROM members {where_clause}")
        total_count = cur.fetchone()[0]
        total_pages = (total_count + limit - 1) // limit
        
        cur.execute("SELECT id, name FROM plans ORDER BY duration_days ASC")
        lista_planes = [{"id": row[0], "nombre": row[1]} for row in cur.fetchall()]

        return templates.TemplateResponse("members_list.html", {
            "request": request,
            "members": members,
            "title": title,
            "filter": filter,
            "current_page": page,
            "total_pages": total_pages,
            "planes": lista_planes
        })
    finally:
        cur.close()
        conn.close()

@app.post("/resend-whatsapp")
async def resend_whatsapp(request: Request):
    data = await request.json()
    phone_number = data.get("phone_number")
    full_name = data.get("full_name")
    
    message = (f"⚠️ ¡Hola {full_name}! Tu plan vence HOY. "
               "No pierdas el ritmo de entrenamiento, te esperamos para renovar.")
    
    payload = {"number": phone_number, "message": message}
    try:
        response = requests.post(NODE_API_URL, json=payload, timeout=10)
        return {"status": "sent" if response.status_code == 200 else "failed"}
    except Exception as e:
        return {"error": str(e)}
