from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. Definimos dónde se guardará el archivo de la base de datos
DATABASE_URL = "sqlite:///./tienda.db"

# 2. Creamos el motor de la base de datos
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# 3. Creamos la fábrica de sesiones (para hacer consultas, insertar, etc.)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. La clase base de la que heredarán nuestros modelos de tablas
Base = declarative_base()

# 5. Función auxiliar (Dependencia) para abrir y cerrar la base de datos en cada petición
def obtener_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()