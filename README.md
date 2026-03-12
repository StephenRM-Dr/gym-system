# 🚀 Sistema de Gestión de Gimnasio (FastAPI + Node.js)

Este proyecto es una solución completa de gestión de membresías con un sistema de recordatorios automatizados vía WhatsApp.

## 🛠️ Tecnologías Utilizadas

- **Backend**: Python 3.12+ con **FastAPI** (API REST).
- **Base de Datos**: **PostgreSQL** (Postgres).
- **Frontend**: HTML/CSS con **Jinja2** (renderizado en servidor).
- **Notificaciones**: **Node.js** con **whatsapp-web.js** (Gateway de WhatsApp).

## 📋 Requisitos Previos

Asegúrate de tener instalado:
- Python 3.10+
- Node.js 16+
- PostgreSQL 12+

## ⚙️ Instalación y Configuración

### 1. Backend (Python)

1.  Navega al directorio `backend`:
    ```bash
    cd backend
    ```

2.  Instala las dependencias de Python:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configuración de Base de Datos**:
    - Crea un archivo `.env` en la carpeta `backend` (o edita `backend/.env` si existe).
    - Configura tus credenciales de PostgreSQL:
      ```env
      DB_HOST=localhost
      DB_NAME=gym_system
      DB_USER=postgres
      DB_PASS=admin
      DB_PORT=5432
      ```

4.  **Ejecutar el Servidor**:
    ```bash
    uvicorn main:app --reload
    ```
    El sistema estará disponible en `http://localhost:8000`.

### 2. Frontend (Node.js - WhatsApp Gateway)

1.  Navega al directorio `whatsapp-gateway`:
    ```bash
    cd whatsapp-gateway
    ```

2.  Instala las dependencias de Node.js:
    ```bash
    npm install
    ```

3.  **Ejecutar el Gateway**:
    ```bash
    node index.js
    ```
    - La primera vez que ejecutes esto, se abrirá una ventana de navegador para que escanees el código QR con tu WhatsApp.
    - Una vez conectado, el gateway estará listo para recibir peticiones en `http://localhost:3000`.

## 🔄 Proceso de Auditoría Automática

El sistema ejecuta un script de auditoría (`backend/main.py`) que:
1.  Busca socios cuyo plan vence **hoy** o en **3 días**.
2.  Envía un mensaje de recordatorio personalizado a través del Gateway de WhatsApp.
3.  Registra la notificación para evitar envíos duplicados.

**Para ejecutar la auditoría manualmente**:
```bash
cd backend
python main.py
```

## 📂 Estructura del Proyecto

- `backend/`: Lógica principal de la API y base de datos.
- `whatsapp-gateway/`: Servidor Node.js para enviar mensajes de WhatsApp.
- `templates/`: Vistas HTML renderizadas por Jinja2.

## 📝 Notas Importantes

- **Seguridad**: Asegúrate de no compartir tus archivos `.env` ni las credenciales de la base de datos.
- **WhatsApp**: El Gateway requiere que el dispositivo donde se ejecuta Node.js tenga sesión activa en WhatsApp Web.
- **Base de Datos**: Se asume que la base de datos `gym_system` ya existe y tiene las tablas necesarias (creadas por los scripts SQL iniciales).