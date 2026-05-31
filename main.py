from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse  # <-- ¡AGREGA ESTA LÍNEA AQUÍ ARRIBA!
from pydantic import BaseModel
from sqlalchemy import Column, String, Float, Integer, DateTime
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from database import Base, engine, obtener_db
app = FastAPI()

# ==========================================
# MODELOS DE LAS TABLAS (SQL)
# ==========================================
class ProductoTabla(Base):
    __tablename__ = "productos"
    
    codigo_barras = Column(String, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    precio = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False)

class VentaTabla(Base):
    __tablename__ = "ventas"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    codigo_barras = Column(String, nullable=False)
    nombre_producto = Column(String, nullable=False)
    cantidad = Column(Integer, nullable=False)
    total = Column(Float, nullable=False)
    fecha_hora = Column(DateTime, default=func.now())

Base.metadata.create_all(bind=engine)

class FormatoProducto(BaseModel):
    codigo_barras: str
    nombre: str
    precio: float
    stock: int

    class Config:
        from_attributes = True


@app.get("/")
def inicio():
    return FileResponse("index.html")


# 1. BUSCAR PRODUCTO
@app.get("/buscar/{codigo_barras}")
def buscar_producto(codigo_barras: str, db: Session = Depends(obtener_db)):
    producto = db.query(ProductoTabla).filter(ProductoTabla.codigo_barras == codigo_barras).first()
    if producto:
        return producto
    raise HTTPException(status_code=404, detail="Producto no encontrado")


# 2. AGREGAR PRODUCTO
@app.post("/agregar/")
def agregar_o_actualizar_producto(producto_datos: FormatoProducto, db: Session = Depends(obtener_db)):
    # Buscamos si el código ya existe usando tus modelos de la base de datos
    producto_existente = db.query(ProductoTabla).filter(ProductoTabla.codigo_barras == producto_datos.codigo_barras).first()
    
    if producto_existente:
        # Si ya existe, sobreescribimos los valores con los nuevos datos
        producto_existente.nombre = producto_datos.nombre
        producto_existente.precio = producto_datos.precio
        producto_existente.stock = producto_datos.stock  # Reemplaza el stock viejo por el nuevo
        db.commit()
        return {"mensaje": f"¡{producto_datos.nombre} actualizado con éxito!"}
    
    # Si es totalmente nuevo, lo registramos por primera vez
    nuevo_producto = ProductoTabla(
        codigo_barras=producto_datos.codigo_barras,
        nombre=producto_datos.nombre,
        precio=producto_datos.precio,
        stock=producto_datos.stock
    )
    db.add(nuevo_producto)
    db.commit()
    return {"mensaje": f"¡{producto_datos.nombre} registrado por primera vez!"}


# 3. VENDER PRODUCTO (¡Ahora puedes poner cuántos se llevan!)
@app.put("/vender/{codigo_barras}")
def vender_producto(codigo_barras: str, cantidad: int = 1, db: Session = Depends(obtener_db)):
    if cantidad <= 0:
        raise HTTPException(status_code=400, detail="La cantidad a vender debe ser mayor a 0")

    producto = db.query(ProductoTabla).filter(ProductoTabla.codigo_barras == codigo_barras).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no registrado")
    
    # Validamos si hay suficiente stock para cubrir la cantidad pedida
    if producto.stock >= cantidad:
        # Calculamos el dinero total de esta venta en particular
        total_venta = producto.precio * cantidad
        
        # A) Restamos la cantidad al inventario
        producto.stock -= cantidad
        
        # B) Registramos la venta con su cantidad y total correcto
        nueva_venta = VentaTabla(
            codigo_barras=producto.codigo_barras,
            nombre_producto=producto.nombre,
            cantidad=cantidad,
            total=total_venta
        )
        db.add(nueva_venta)
        db.commit()
        db.refresh(producto)
        
        return {
            "mensaje": f"¡Venta de {cantidad} pieza(s) procesada!",
            "ticket": {
                "producto": producto.nombre,
                "cantidad_vendida": cantidad,
                "total_cobrado": total_venta,
                "inventario_restante": producto.stock
            }
        }
        
    raise HTTPException(status_code=400, detail=f"Stock insuficiente. Solo quedan {producto.stock} piezas")


# 4. VER HISTORIAL DE VENTAS DETALLADO
@app.get("/historial-ventas/")
def ver_historial_ventas(db: Session = Depends(obtener_db)):
    ventas = db.query(VentaTabla).all()
    return {"ventas_totales": ventas}


# 5. CORTE DE CAJA: GANANCIAS TOTALES (¡NUEVO!)
@app.get("/corte-caja/")
def obtener_corte_caja(db: Session = Depends(obtener_db)):
    # Le pedimos a SQL que sume toda la columna 'total' de la tabla ventas
    suma_total = db.query(func.sum(VentaTabla.total)).scalar()
    
    # Si la base de datos está vacía, la suma dará None. Lo convertimos a 0.0 para que se vea limpio
    if suma_total is None:
        suma_total = 0.0
        
    return {
        "mensaje": "Corte de caja generado exitosamente",
        "dinero_total_en_caja": suma_total
    }