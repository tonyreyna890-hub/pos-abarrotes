from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Aquí le decimos que cree un archivo llamado "tienda.db" en tu carpeta
URL_BASE_DATOS = "sqlite:///./tienda.db"

engine = create_engine(URL_BASE_DATOS, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Esta función nos dará acceso a la base de datos en cada consulta
def obtener_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()