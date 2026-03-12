import os
import psycopg2
from dotenv import load_dotenv

# Carga las variables del archivo .env
load_dotenv()

def get_connection():
    try:
        connection = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASS'),
            port=os.getenv('DB_PORT')
        )
        return connection
    except Exception as e:
        print(f"Error conectando a la base de datos: {e}")
        return None