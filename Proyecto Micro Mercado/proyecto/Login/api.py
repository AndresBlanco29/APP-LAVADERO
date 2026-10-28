from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
import mysql.connector

class Producto(BaseModel):
    Id_Producto:       int
    Nombre:            str
    Precio_Venta:      float
    Precio_Compra:     float
    Cantidad:          int
    Marca:             str
    Descripcion:       Optional[str]
    Categoria:         Optional[str]
    Fecha_Entrada:     Optional[date]
    Fecha_Vencimiento: Optional[date]
    Unidad_Medida:     Optional[str]
    Proveedor_ID:      Optional[int]
    Ubicacion_Estante: Optional[str]
    ubicacion_pasillo: Optional[str]
    Codigo_Barras:     Optional[str]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="api_user",
        password="solomessi10",
        database="proyecto_micro_mercado"
    )

@app.get("/api/productos", response_model=List[Producto])
def listar_productos(
    codigo_barras: Optional[str] = Query(None, alias="codigo_barras")
):
    """
    Si llamas /api/productos devuelve TODOS los productos.
    Si llamas /api/productos?codigo_barras=123 devuelve solo
    aquellos con Codigo_Barras = '123'.
    """
    db     = get_db()
    cursor = db.cursor(dictionary=True)
    
    if codigo_barras:
        sql = """
          SELECT 
            Id_Producto, Nombre, Precio_Venta, Precio_Compra,
            Cantidad, Marca, Descripcion, Categoria,
            Fecha_Entrada, Fecha_Vencimiento,
            Unidad_Medida, Proveedor_ID,
            Ubicacion_Estante, ubicacion_pasillo, Codigo_Barras
          FROM productos
          WHERE Codigo_Barras = %s
        """
        cursor.execute(sql, (codigo_barras,))
    else:
        sql = """
          SELECT 
            Id_Producto, Nombre, Precio_Venta, Precio_Compra,
            Cantidad, Marca, Descripcion, Categoria,
            Fecha_Entrada, Fecha_Vencimiento,
            Unidad_Medida, Proveedor_ID,
            Ubicacion_Estante, ubicacion_pasillo, Codigo_Barras
          FROM productos
        """
        cursor.execute(sql)

    filas = cursor.fetchall()
    cursor.close()
    db.close()
    return filas


def _dict_rows(sql, valores=()):
    from conexionLogin import FormularioLogin
    cone = FormularioLogin.conexion_base_de_datos()
    if not cone:
        return []
    cursor = cone.cursor()
    cursor.execute(sql, valores)
    cols = [d[0] for d in cursor.description]
    filas = [dict(zip(cols, row)) for row in cursor.fetchall()]
    cursor.close()
    cone.close()
    return filas


def _marcar_estado(venta):
    anulada = int(venta.get("Anulada") or 0) == 1
    venta["Anulada"] = 1 if anulada else 0
    venta["anulada"] = anulada
    venta["Estado"] = "ANULADA" if anulada else "ACTIVA"
    venta["estado"] = venta["Estado"]
    return venta


@app.get("/api/ventas")
def listar_ventas():
    filas = _dict_rows(
        """
        SELECT v.Id_Venta, v.Fecha_Venta, v.Total,
               COALESCE(v.Anulada, 0) AS Anulada
        FROM ventas v
        ORDER BY v.Fecha_Venta DESC
        LIMIT 500
        """
    )
    return [_marcar_estado(row) for row in filas]


@app.get("/api/ventas/{id_venta}")
def detalle_venta(id_venta: int):
    cab = _dict_rows(
        """
        SELECT v.Id_Venta, v.Fecha_Venta, v.Total,
               COALESCE(v.Anulada, 0) AS Anulada
        FROM ventas v
        WHERE v.Id_Venta = %s
        """,
        (id_venta,),
    )
    if not cab:
        return {"error": "Venta no encontrada"}
    venta = _marcar_estado(cab[0])
    venta["productos"] = _dict_rows(
        """
        SELECT p.Id_Producto, p.Nombre, vp.Cantidad, vp.Subtotal
        FROM productos_has_ventas vp
        JOIN productos p ON p.Id_Producto = vp.Productos_Id_Producto
        WHERE vp.Ventas_Id_Factura = %s
        """,
        (id_venta,),
    )
    return venta

