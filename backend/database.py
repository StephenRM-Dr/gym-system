from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# IMPORTANTE: Reemplaza 'tu_password' por la que pusiste en la instalación de Postgres
USER = "postgres"
PASS = "1234" 
HOST = "localhost"
PORT = "5432"
DB_NAME = "gym_system"

SQLALCHEMY_DATABASE_URL = f"postgresql://{USER}:{PASS}@{HOST}:{PORT}/{DB_NAME}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependencia para obtener la DB en las rutas de FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()