from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime

DATABASE_URL = "sqlite:///./tienda.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ProductoTabla(Base):
    __tablename__ = "productos"
    codigo_barras = Column(String, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    precio_venta = Column(Float, nullable=False)
    existencia = Column(Integer, nullable=False)

class VentaTabla(Base):
    __tablename__ = "ventas"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    fecha = Column(DateTime, default=datetime.now)
    total = Column(Float, nullable=False)
    productos_vendidos = Column(String, nullable=False)

Base.metadata.create_all(bind=engine)

class ProductoCrear(BaseModel):
    codigo_barras: str
    nombre: str
    precio_venta: float
    existencia: int

    class Config:
        from_attributes = True

class DetalleVenta(BaseModel):
    total: float
    productos_vendidos: str

class DescuentoInventario(BaseModel):
    cantidad: int

app = FastAPI(title="Punto de Venta API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/productos/", response_model=list[ProductoCrear])
def obtener_todos_los_productos(db: Session = Depends(get_db)):
    return db.query(ProductoTabla).all()

@app.get("/productos/buscar", response_model=ProductoCrear)
def buscar_producto_por_nombre_o_codigo(q: str, db: Session = Depends(get_db)):
    producto = db.query(ProductoTabla).filter(
        or_(
            ProductoTabla.codigo_barras == q,
            ProductoTabla.nombre.ilike(f"%{q}%")
        )
    ).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto

@app.post("/productos/", status_code=201)
def registrar_producto(producto: ProductoCrear, db: Session = Depends(get_db)):
    existe = db.query(ProductoTabla).filter(ProductoTabla.codigo_barras == producto.codigo_barras).first()
    if existe:
        raise HTTPException(status_code=400, detail="El código de barras ya existe")
    nuevo_producto = ProductoTabla(**producto.dict())
    db.add(nuevo_producto)
    db.commit()
    db.refresh(nuevo_producto)
    return nuevo_producto

@app.put("/productos/{codigo_barras}")
def actualizar_producto_existente(codigo_barras: str, producto_editado: ProductoCrear, db: Session = Depends(get_db)):
    producto_db = db.query(ProductoTabla).filter(ProductoTabla.codigo_barras == codigo_barras).first()
    if not producto_db:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    producto_db.nombre = producto_editado.nombre
    producto_db.precio_venta = producto_editado.precio_venta
    producto_db.existencia = producto_editado.existencia
    db.commit()
    db.refresh(producto_db)
    return producto_db

@app.patch("/productos/{codigo_barras}/inventario")
def descontar_inventario(codigo_barras: str, item: DescuentoInventario, db: Session = Depends(get_db)):
    producto = db.query(ProductoTabla).filter(ProductoTabla.codigo_barras == codigo_barras).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if producto.existencia < item.cantidad:
        raise HTTPException(status_code=400, detail="Existencias insuficientes")
    producto.existencia -= item.cantidad
    db.commit()
    return {"mensaje": "Inventario rebajado", "nuevo_stock": producto.existencia}

@app.post("/ventas/", status_code=201)
def registrar_venta_historico(venta: DetalleVenta, db: Session = Depends(get_db)):
    nueva_venta = VentaTabla(total=venta.total, productos_vendidos=venta.productos_vendidos)
    db.add(nueva_venta)
    db.commit()
    db.refresh(nueva_venta)
    return {"mensaje": "Venta guardada", "id_venta": nueva_venta.id}

@app.get("/cierre-caja/")
def obtener_corte_del_dia(db: Session = Depends(get_db)):
    hoy = datetime.now().date()
    todas_las_ventas = db.query(VentaTabla).all()
    total_hoy = 0.0
    ventas_contador = 0
    for v in todas_las_ventas:
        if v.fecha.date() == hoy:
            total_hoy += v.total
            ventas_contador += 1
    return {"fecha": str(hoy), "total_generado": total_hoy, "numero_ventas": ventas_contador}