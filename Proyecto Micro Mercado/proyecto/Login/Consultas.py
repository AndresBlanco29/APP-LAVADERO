from conexionLogin import *
import mysql.connector
from datetime import datetime
import pytz
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
import json
import threading
import time

def apertura_caja( fecha, monto_inicial):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        sql = "INSERT INTO apertura_caja (fecha_apertura, Monto_Inicial) VALUES ( %s, %s)"
        valores = ( fecha, monto_inicial)
        cursor.execute(sql, valores)
        cone.commit()
        cone.close()
        return True
    except mysql.connector.Error as error:
        print("Error al registrar la apertura de caja {}".format(error))
        return False

def registrar_admin(usuario, contrasena, nombre_completo, telefono, correo):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        sql_admin = "INSERT INTO admin (usuario, contrasena, Nombre, telefono, correo_electronico) VALUES (%s, %s, %s, %s, %s)"
        valores_admin = (usuario, contrasena, nombre_completo, telefono, correo)
        cursor.execute(sql_admin, valores_admin)
        cone.commit()
        cone.close()
        return True
    except mysql.connector.Error as error:
        print("Error al registrar el admin {}".format(error))
        return False

def registrar_negocio(Nombre_Negocio, Direccion):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        sql = "INSERT INTO registro_negocio (Nombre_negocio, direccion) VALUES (%s, %s);"
        valores = (Nombre_Negocio, Direccion)
        cursor.execute(sql, valores)
        cone.commit()
        cone.close()
        return True 
    except mysql.connector.Error as error:
        print("Error al registrar el negocio: {}".format(error))
        return False  


    
def mostrar_Productos():
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            cursor.execute("SELECT * FROM productos")
            Resultado = cursor.fetchall()
            cone.close()
            return Resultado
        except mysql.connector.Error as error:
            print("Error al mostrar los productos {}".format(error))
            

            
def Agregar_Producto(Nombre, precio_venta, precio_compra, cantidad, marca, categoria="", ubicacion="", stock_minimo=10, proveedor="", iva=0, unidad_base="Unidad", permite_fraccion=1):
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            iva_pct = iva_a_porcentaje(iva)
            unidad = (unidad_base or "Unidad")[:40]
            fraccion = 1 if int(permite_fraccion or 0) else 0
            intentos = [
                (
                    "INSERT INTO productos (Nombre, Precio_Venta, Precio_Compra, Cantidad, Marca, Categoria, Ubicacion, Stock_Minimo, Proveedor, Iva, Unidad_Base, Permite_Fraccion) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);",
                    (Nombre, precio_venta, precio_compra, cantidad, marca, categoria or "", ubicacion or "", stock_minimo or 10, proveedor or "", iva_pct, unidad, fraccion),
                ),
                (
                    "INSERT INTO productos (Nombre, Precio_Venta, Precio_Compra, Cantidad, Marca, Categoria, Ubicacion, Stock_Minimo, Proveedor, Iva) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);",
                    (Nombre, precio_venta, precio_compra, cantidad, marca, categoria or "", ubicacion or "", stock_minimo or 10, proveedor or "", iva_pct),
                ),
                (
                    "INSERT INTO productos (Nombre, Precio_Venta, Precio_Compra, Cantidad, Marca, Categoria, Ubicacion, Stock_Minimo, Proveedor) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);",
                    (Nombre, precio_venta, precio_compra, cantidad, marca, categoria or "", ubicacion or "", stock_minimo or 10, proveedor or ""),
                ),
                (
                    "INSERT INTO productos (Nombre, Precio_Venta, Precio_Compra, Cantidad, Marca, Categoria, Ubicacion, Stock_Minimo) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s);",
                    (Nombre, precio_venta, precio_compra, cantidad, marca, categoria or "", ubicacion or "", stock_minimo or 10),
                ),
                (
                    "INSERT INTO productos (Nombre, Precio_Venta, Precio_Compra, Cantidad, Marca) VALUES (%s, %s, %s, %s, %s);",
                    (Nombre, precio_venta, precio_compra, cantidad, marca),
                ),
            ]
            producto_id = None
            for sql, valores in intentos:
                try:
                    cursor.execute(sql, valores)
                    producto_id = cursor.lastrowid
                    break
                except Exception:
                    continue
            cone.commit()
            cone.close()
            invalidar_catalogo()
            return producto_id
        except mysql.connector.Error as error:
            print("Error al agregar un producto {}".format(error))
            return None
            
IVA_CHOICES = ("0%", "5%", "19%")
GANANCIA_CHOICES = ("10%", "15%", "20%", "25%", "30%", "40%", "50%")
UTILIDAD_CHOICES = GANANCIA_CHOICES
UNIDADES_BASE = (
    "Unidad",
    "Tableta",
    "Cápsula",
    "Blíster",
    "Paquete",
    "Caja",
    "Bulto",
    "Gramo",
    "Kilogramo",
    "Mililitro",
    "Litro",
    "Metro",
)
TIPOS_NEGOCIO = ("Tienda", "Minimercado", "Supermercado", "Droguería", "Otro")
METODOS_PAGO = (
    "Efectivo",
    "Transferencia",
    "Nequi",
    "Daviplata",
    "Bancolombia",
    "Tarjeta",
    "Crédito",
    "Otro",
)
METODOS_PAGO_VENTA = ("Efectivo", "Transferencia", "Tarjeta", "Crédito")
METODOS_PAGO_VENTA_UI = (
    ("Efectivo", "Efectivo"),
    ("Transferencia", "Bre-b / Nequi / Transferencia"),
    ("Tarjeta", "Tarjeta Débito / Crédito"),
    ("Crédito", "Crédito / Fiado"),
)
METODOS_PAGO_COMPRA = METODOS_PAGO
_PRODUCTO_COLS = None
_PROVEEDORES_LAYOUT = None
_CLIENTES_LAYOUT = None
_cat_lock = threading.Lock()
_cat_rows = None
_cat_ts = 0.0


def invalidar_catalogo():
    global _cat_rows, _cat_ts
    with _cat_lock:
        _cat_rows = None
        _cat_ts = 0.0


def catalogo_listo():
    with _cat_lock:
        return _cat_rows is not None


def catalogo_productos(ttl=60):
    global _cat_rows, _cat_ts
    now = time.monotonic()
    with _cat_lock:
        if _cat_rows is not None and now - _cat_ts < ttl:
            return _cat_rows
    rows = mostrar_Productos() or []
    with _cat_lock:
        _cat_rows = rows
        _cat_ts = time.monotonic()
    return rows


def buscar_productos_rapido(texto, limite=15):
    t = (texto or "").strip().lower()
    if not t:
        return []
    out = []
    for row in catalogo_productos() or []:
        datos = parse_producto(row)
        if not datos:
            continue
        campos = (
            str(datos.get("id") or ""),
            str(datos.get("nombre") or ""),
            str(datos.get("marca") or ""),
            str(datos.get("categoria") or ""),
            str(datos.get("ubicacion") or ""),
        )
        if any(t in c.lower() for c in campos):
            out.append(row)
            if len(out) >= limite:
                break
    return out


def columnas_producto():
    global _PRODUCTO_COLS
    if _PRODUCTO_COLS is not None:
        return _PRODUCTO_COLS
    cone = FormularioLogin.conexion_base_de_datos()
    if not cone:
        return []
    cursor = cone.cursor()
    try:
        cursor.execute("SHOW COLUMNS FROM productos")
        _PRODUCTO_COLS = [row[0] for row in cursor.fetchall()]
    except Exception:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            cone.close()
        except Exception:
            pass
        return []
    try:
        cursor.close()
    except Exception:
        pass
    cone.close()
    return _PRODUCTO_COLS


def iva_a_porcentaje(texto):
    t = str(texto or "0").strip().upper().replace(",", ".").replace("%", "")
    t = t.replace("IVA", "").replace("SIN", "").strip()
    try:
        n = float("".join(c for c in t if c.isdigit() or c == ".") or 0)
    except (TypeError, ValueError):
        return 0.0
    if n < 0:
        return 0.0
    if n > 100:
        return 100.0
    return round(n, 2)


def iva_a_texto(valor):
    n = iva_a_porcentaje(valor)
    if abs(n - round(n)) < 0.001:
        return "{}%".format(int(round(n)))
    return "{:.2f}%".format(n)


def iva_para_editar(valor):
    n = iva_a_porcentaje(valor)
    if abs(n - round(n)) < 0.001:
        return str(int(round(n)))
    return "{:.2f}".format(n).rstrip("0").rstrip(".")


def escribir_iva(entry, valor=""):
    entry.delete(0, "end")
    texto = str(valor if valor is not None else "").strip()
    if texto == "":
        return
    entry.insert(0, iva_para_editar(texto))


def utilidad_a_porcentaje(texto):
    return ganancia_a_porcentaje(texto)


def utilidad_a_texto(valor):
    return ganancia_a_texto(valor)


def _dec(valor, places=6):
    try:
        n = Decimal(str(valor).replace(",", ".").strip() or "0")
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")
    q = Decimal("1").scaleb(-places) if places else Decimal("1")
    return n.quantize(q, rounding=ROUND_HALF_UP)


def a_unidades_base(cantidad, factor=1):
    return float(_dec(cantidad, 6) * _dec(factor, 6))


def costo_equivalente(costo_base, factor=1):
    return float((_dec(costo_base, 6) * _dec(factor, 6)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def parse_presentacion(row):
    if not row:
        return None
    return {
        "id": row[0],
        "producto_id": row[1],
        "nombre": row[2] or "Unidad",
        "factor": float(row[3] or 1),
        "unidad": row[4] or "",
        "codigo_barras": row[5] or "",
        "precio_venta": float(row[6] or 0),
        "utilidad_pct": float(row[7] or 0),
        "permite_venta": int(row[8] or 0) == 1,
        "activo": int(row[9] or 0) == 1,
        "es_default": int(row[10] or 0) == 1 if len(row) > 10 else False,
    }


def ganancia_a_porcentaje(texto):
    n = iva_a_porcentaje(texto)
    if n >= 100:
        return 99.99
    return n


def ganancia_a_texto(valor):
    return iva_a_texto(ganancia_a_porcentaje(valor))


def _a_float_precio(texto):
    from dinero import parse_dinero_o_none

    return parse_dinero_o_none(texto)


def costo_con_iva(precio_compra, iva_pct=0):
    compra = _a_float_precio(precio_compra)
    if compra is None or compra <= 0:
        return None
    iva = iva_a_porcentaje(iva_pct) / 100.0
    return compra * (1.0 + iva)


def desglose_compra(precio_ingresado, iva_pct=0, iva_incluido=False):
    """Separa base, IVA y total de un precio de compra.

    Precio_Compra del producto se guarda siempre como base (sin IVA) para
    que margen, inventario e inversión histórica sigan igual.
    """
    compra = _a_float_precio(precio_ingresado)
    if compra is None or compra < 0:
        return None
    r = iva_a_porcentaje(iva_pct) / 100.0
    if r <= 0:
        n = round(compra, 2)
        return {"base": n, "iva": 0.0, "total": n, "iva_incluido": bool(iva_incluido)}
    if iva_incluido:
        total = round(compra, 2)
        base = round(total / (1.0 + r), 2)
        iva_valor = round(total - base, 2)
    else:
        base = round(compra, 2)
        iva_valor = round(base * r, 2)
        total = round(base + iva_valor, 2)
    return {
        "base": base,
        "iva": iva_valor,
        "total": total,
        "iva_incluido": bool(iva_incluido),
    }


def validar_numero_factura(texto):
    t = str(texto or "").strip()
    if not t:
        return False, "El número de factura es obligatorio."
    if len(t) > 40:
        return False, "El número de factura no puede superar 40 caracteres."
    if any(ord(c) < 32 for c in t):
        return False, "El número de factura no es válido."
    return True, t


def precio_venta_con_margen(precio_compra, ganancia_pct, iva_pct=0):
    from dinero import redondear_centena

    costo = costo_con_iva(precio_compra, iva_pct)
    if costo is None:
        return None
    g = ganancia_a_porcentaje(ganancia_pct) / 100.0
    if g <= 0:
        return redondear_centena(costo)
    return redondear_centena(costo / (1.0 - g))


def margen_desde_precios(precio_compra, precio_venta, iva_pct=0):
    costo = costo_con_iva(precio_compra, iva_pct)
    from dinero import parse_dinero

    try:
        venta = parse_dinero(precio_venta)
    except (TypeError, ValueError):
        return 0.0
    if costo is None or venta <= 0:
        return 0.0
    n = (1.0 - (costo / venta)) * 100.0
    if n < 0:
        return 0.0
    return ganancia_a_porcentaje(n)


def conectar_margen_venta(
    compra_entry,
    ganancia_combo,
    venta_entry,
    iva_combo=None,
    costo_label=None,
    iva_incluido_var=None,
    on_margen=None,
):
    estado = {"lock": False}

    def iva_actual():
        return iva_combo.get() if iva_combo is not None else 0

    def iva_incluido():
        if iva_incluido_var is None:
            return False
        try:
            return bool(iva_incluido_var.get())
        except Exception:
            return False

    def desglose_actual():
        return desglose_compra(compra_entry.get().strip(), iva_actual(), iva_incluido())

    def refrescar_costo():
        if costo_label is None:
            return
        d = desglose_actual()
        iva_n = iva_a_porcentaje(iva_actual())
        if not d or d["base"] <= 0:
            if iva_incluido():
                costo_label.config(
                    text="El precio ingresado ya incluye IVA. El sistema calcula la base internamente y no lo vuelve a sumar."
                )
            else:
                costo_label.config(text="El precio de compra es sin IVA. La venta al público ya incluye IVA.")
            return
        from dinero import formato_dinero

        if iva_incluido() and iva_n:
            costo_label.config(
                text="IVA incluido en la factura: base {} + IVA {} = {}  ·  no se duplica el IVA".format(
                    formato_dinero(d["base"]), formato_dinero(d["iva"]), formato_dinero(d["total"])
                )
            )
        elif iva_n:
            costo_label.config(
                text="Sin IVA: base {} + IVA {} = {}  ·  venta = costo ÷ (1 − %)".format(
                    formato_dinero(d["base"]), formato_dinero(d["iva"]), formato_dinero(d["total"])
                )
            )
        else:
            costo_label.config(text="Sin IVA  ·  venta = compra ÷ (1 − %)  ·  puede redondear el precio de venta")

    def aplicar_venta(_event=None):
        if estado["lock"]:
            return
        d = desglose_actual()
        ganancia = ganancia_combo.get().strip()
        refrescar_costo()
        if not d or d["base"] <= 0 or not ganancia:
            return
        venta = precio_venta_con_margen(d["base"], ganancia, iva_actual())
        if venta is None:
            return
        estado["lock"] = True
        venta_entry.delete(0, "end")
        from dinero import formato_entrada

        venta_entry.insert(0, formato_entrada(str(int(venta))))
        estado["lock"] = False
        if on_margen:
            try:
                on_margen(ganancia_a_texto(ganancia), venta_entry.get(), False)
            except Exception:
                pass

    def aplicar_margen(_event=None):
        if estado["lock"]:
            return
        d = desglose_actual()
        venta = venta_entry.get().strip()
        refrescar_costo()
        if not d or d["base"] <= 0 or not venta:
            return
        margen = margen_desde_precios(d["base"], venta, iva_actual())
        texto = ganancia_a_texto(margen)
        estado["lock"] = True
        ganancia_combo.set(texto)
        estado["lock"] = False
        if on_margen:
            try:
                on_margen(texto, venta, True)
            except Exception:
                pass

    def redondear_venta_campo(_event=None):
        """Al salir del campo, deja el precio de venta en centena redonda."""
        if estado["lock"]:
            return
        from dinero import formato_entrada, parse_dinero, redondear_centena

        bruto = parse_dinero(venta_entry.get())
        if bruto <= 0:
            aplicar_margen()
            return
        red = redondear_centena(bruto)
        if abs(bruto - red) >= 0.5:
            estado["lock"] = True
            venta_entry.delete(0, "end")
            venta_entry.insert(0, formato_entrada(str(int(red))))
            estado["lock"] = False
        aplicar_margen()

    # Formato de dinero y luego recálculo de utilidad/precio
    try:
        from zyntra_ui import bind_money_entry

        bind_money_entry(venta_entry, on_change=aplicar_margen)
        bind_money_entry(compra_entry, on_change=aplicar_venta)
    except Exception:
        venta_entry.bind("<KeyRelease>", aplicar_margen, add="+")
        compra_entry.bind("<KeyRelease>", aplicar_venta, add="+")

    ganancia_combo.bind("<KeyRelease>", aplicar_venta, add="+")
    ganancia_combo.bind("<<ComboboxSelected>>", aplicar_venta, add="+")
    venta_entry.bind("<FocusOut>", redondear_venta_campo, add="+")
    if iva_combo is not None:
        iva_combo.bind("<KeyRelease>", aplicar_venta, add="+")
        iva_combo.bind("<FocusOut>", aplicar_venta, add="+")
        iva_combo.bind("<<ComboboxSelected>>", aplicar_venta, add="+")
    if iva_incluido_var is not None:
        try:
            iva_incluido_var.trace_add("write", lambda *_a: aplicar_venta())
        except Exception:
            iva_incluido_var.trace("w", lambda *_a: aplicar_venta())
    refrescar_costo()
    return aplicar_venta, aplicar_margen


def iva_de_fila(row):
    cols = columnas_producto()
    if "Iva" in cols and row and len(row) > cols.index("Iva"):
        try:
            return float(row[cols.index("Iva")] or 0)
        except (TypeError, ValueError, IndexError):
            return 0.0
    return 0.0


def _layout_proveedores(cursor):
    global _PROVEEDORES_LAYOUT
    if _PROVEEDORES_LAYOUT:
        return _PROVEEDORES_LAYOUT
    cursor.execute("SHOW COLUMNS FROM proveedores")
    cols = {row[0] for row in cursor.fetchall()}
    id_col = "NIT" if "NIT" in cols else ("Id_Proveedor" if "Id_Proveedor" in cols else None)
    name_col = "Razon_Social" if "Razon_Social" in cols else ("Nombre" if "Nombre" in cols else None)
    tel_col = "Telefono" if "Telefono" in cols else None
    dir_col = "Direccion" if "Direccion" in cols else None
    _PROVEEDORES_LAYOUT = (id_col, name_col, tel_col, dir_col)
    return _PROVEEDORES_LAYOUT


def Agregar_Proveedor(NIT, Nombre, Telefono, Direccion):
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            id_col, name_col, tel_col, dir_col = _layout_proveedores(cursor)
            if name_col == "Razon_Social" and id_col == "NIT":
                sql = "INSERT INTO proveedores (NIT, Razon_Social, Telefono, Direccion) VALUES (%s, %s, %s, %s)"
                valores = (NIT, Nombre, Telefono, Direccion)
            elif name_col:
                campos = [name_col]
                valores = [Nombre]
                if tel_col:
                    campos.append(tel_col)
                    valores.append(Telefono)
                if dir_col:
                    campos.append(dir_col)
                    valores.append(Direccion)
                if id_col == "NIT" and NIT:
                    campos.insert(0, id_col)
                    valores.insert(0, NIT)
                sql = "INSERT INTO proveedores ({}) VALUES ({})".format(
                    ", ".join(campos), ", ".join(["%s"] * len(valores))
                )
            else:
                sql = "INSERT INTO proveedores VALUES (%s, %s, %s, %s)"
                valores = (NIT, Nombre, Telefono, Direccion)
            cursor.execute(sql, tuple(valores))
            cone.commit()
            cone.close()
        except Exception as error:
            print("Error al agregar un proveedor {}".format(error))
            
def Agregar_entrada_dinero(Cantidad, Comentarios, Cajero, Fecha):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        sql = ("INSERT INTO entrada_dinero (Cantidad, Asunto, Cajero, Fecha) VALUES (%s, %s, %s, %s);")
        valores = (Cantidad, Comentarios, Cajero, Fecha)
        
        cursor.execute(sql, valores)
        cone.commit()
        print("Entrada de dinero registrada correctamente.")
    
    except pymysql.Error as error:
        print(f"Error al conectarse a la base de datos: {error}")
    
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'cone' in locals() and cone:
            cone.close()
            
def Agregar_salida_dinero(Cantidad, Comentarios, Cajero, Fecha):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        sql = ("INSERT INTO salida_dinero (Cantidad, Asunto, Cajero, Fecha) VALUES (%s, %s, %s, %s);")
        valores = (Cantidad, Comentarios, Cajero, Fecha)
        
        cursor.execute(sql, valores)
        cone.commit()
        print("Entrada de dinero registrada correctamente.")
    
    except pymysql.Error as error:
        print(f"Error al conectarse a la base de datos: {error}")
    
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'cone' in locals() and cone:
            cone.close()
            
def Agregar_Personal(Usuario, password, Nombre, Telefono, Correo):
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            sql_empleados = "INSERT INTO empleados (Nombres, Telefono, Correo) VALUES (%s, %s, %s)"
            valores_empleados = (Nombre, Telefono, Correo)
            cursor.execute(sql_empleados, valores_empleados)
            
            id_empleado = cursor.lastrowid
            
            sql_usuario = "INSERT INTO usuarios (Usuario, Contraseña, Empleados_Id_Empleados) VALUES (%s, %s, %s)"
            valores_usuario = (Usuario, password, id_empleado)
            cursor.execute(sql_usuario, valores_usuario)
            
            cone.commit()
            cone.close()
            
        except mysql.connector.Error as error:
            print("Error al agregar nuevo usuario {}".format(error))
            
def buscar_productos(Codigo, Nombre, Marca): 
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            try:
                sql = (
                    "SELECT * FROM productos WHERE Id_Producto LIKE %s OR Nombre LIKE %s OR Marca LIKE %s "
                    "OR Categoria LIKE %s OR Ubicacion LIKE %s;"
                )
                like = '%' + str(Codigo) + '%'
                valores = (like, '%' + str(Nombre) + '%', '%' + str(Marca) + '%', like, like)
                cursor.execute(sql, valores)
            except Exception:
                try:
                    cone.rollback()
                except Exception:
                    pass
                sql = "SELECT * FROM productos WHERE Id_Producto LIKE %s OR Nombre LIKE %s OR Marca LIKE %s;"
                valores = ('%' + Codigo + '%', '%' + Nombre + '%', '%' + Marca + '%')
                cursor.execute(sql, valores)
            Resultado = cursor.fetchall()
            cone.commit()
            cone.close()
            return Resultado
        except mysql.connector.Error as error:
            print("Error al buscar los productos {}".format(error))
            
def cantidad_producto(Codigo):
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            sql = "SELECT Cantidad FROM productos WHERE Id_Producto = %s;"
            valores = (Codigo,)
            cursor.execute(sql, valores)
            Resultado = cursor.fetchone()
            cursor.close()  
            cone.close()    
            return Resultado[0] if Resultado else None
        except mysql.connector.Error as error:
            print("Error al buscar la cantidad del producto: {}".format(error))

def obtener_producto(Codigo):
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            sql = "SELECT * FROM productos WHERE Id_Producto = %s;"
            valores = (Codigo,)
            cursor.execute(sql, valores)
            Resultado = cursor.fetchone()
            cursor.close()  
            cone.close()    
            return Resultado
        except mysql.connector.Error as error:
            print("Error al buscar el producto: {}".format(error))

def buscar_proveedor(NIT, Nombre):
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            id_col, name_col, tel_col, dir_col = _layout_proveedores(cursor)
            id_col = id_col or "Id_Proveedor"
            name_col = name_col or "Nombre"
            campos = [id_col, name_col, tel_col or "''", dir_col or "''"]
            sql = (
                "SELECT {0}, {1}, {2}, {3} FROM proveedores "
                "WHERE CAST({0} AS CHAR) LIKE %s OR {1} LIKE %s"
            ).format(*campos)
            valores = ("%" + str(NIT) + "%", "%" + str(Nombre) + "%")
            cursor.execute(sql, valores)
            resultado = cursor.fetchall()
            cone.close()
            return resultado
        except Exception as error:
            print("Error al buscar los proveedores {}".format(error))
            return []
            
def buscar_codigo(Codigo):
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            sql=("SELECT * FROM productos WHERE Id_Producto = %s;")
            valores = (Codigo,)
            cursor.execute(sql,valores)
            Resultado = cursor.fetchone()
            cone.commit()
            cone.close()
            return Resultado
        except mysql.connector.Error as error:
            print("Error al buscar los productos {}".format(error))
            
def modificar_producto(Nombre, precio_venta, precio_compra, Cantidad, Marca, Codigo, categoria="", ubicacion="", stock_minimo=10, proveedor="", iva=0, unidad_base="Unidad", permite_fraccion=1):
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            iva_pct = iva_a_porcentaje(iva)
            unidad = (unidad_base or "Unidad")[:40]
            fraccion = 1 if int(permite_fraccion or 0) else 0
            intentos = [
                (
                    "UPDATE productos SET Nombre=%s, Precio_Venta=%s, Precio_Compra=%s, Cantidad=%s, Marca=%s, "
                    "Categoria=%s, Ubicacion=%s, Stock_Minimo=%s, Proveedor=%s, Iva=%s, Unidad_Base=%s, Permite_Fraccion=%s WHERE Id_Producto=%s;",
                    (Nombre, precio_venta, precio_compra, Cantidad, Marca, categoria or "", ubicacion or "", stock_minimo or 10, proveedor or "", iva_pct, unidad, fraccion, Codigo),
                ),
                (
                    "UPDATE productos SET Nombre=%s, Precio_Venta=%s, Precio_Compra=%s, Cantidad=%s, Marca=%s, "
                    "Categoria=%s, Ubicacion=%s, Stock_Minimo=%s, Proveedor=%s, Iva=%s WHERE Id_Producto=%s;",
                    (Nombre, precio_venta, precio_compra, Cantidad, Marca, categoria or "", ubicacion or "", stock_minimo or 10, proveedor or "", iva_pct, Codigo),
                ),
                (
                    "UPDATE productos SET Nombre=%s, Precio_Venta=%s, Precio_Compra=%s, Cantidad=%s, Marca=%s, "
                    "Categoria=%s, Ubicacion=%s, Stock_Minimo=%s, Proveedor=%s WHERE Id_Producto=%s;",
                    (Nombre, precio_venta, precio_compra, Cantidad, Marca, categoria or "", ubicacion or "", stock_minimo or 10, proveedor or "", Codigo),
                ),
                (
                    "UPDATE productos SET Nombre=%s, Precio_Venta=%s, Precio_Compra=%s, Cantidad=%s, Marca=%s, "
                    "Categoria=%s, Ubicacion=%s, Stock_Minimo=%s WHERE Id_Producto=%s;",
                    (Nombre, precio_venta, precio_compra, Cantidad, Marca, categoria or "", ubicacion or "", stock_minimo or 10, Codigo),
                ),
                (
                    "UPDATE productos SET Nombre=%s, Precio_Venta=%s, Precio_Compra=%s, Cantidad=%s, Marca=%s WHERE Id_Producto=%s;",
                    (Nombre, precio_venta, precio_compra, Cantidad, Marca, Codigo),
                ),
            ]
            filas_afectadas = 0
            for sql, valores in intentos:
                try:
                    cursor.execute(sql, valores)
                    filas_afectadas = cursor.rowcount
                    break
                except Exception:
                    continue
            cone.commit()
            cone.close()
            invalidar_catalogo()
            return filas_afectadas > 0
        except mysql.connector.Error as error:
            print("Error al modificar los datos {}".format(error))
            
def modificar_proveedor(Nombre, Telefono, Direccion, NIT):
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            id_col, name_col, tel_col, dir_col = _layout_proveedores(cursor)
            sets = []
            valores = []
            if name_col:
                sets.append("{} = %s".format(name_col))
                valores.append(Nombre)
            if tel_col:
                sets.append("{} = %s".format(tel_col))
                valores.append(Telefono)
            if dir_col:
                sets.append("{} = %s".format(dir_col))
                valores.append(Direccion)
            if not sets or not id_col:
                cone.close()
                return False
            sql = "UPDATE proveedores SET {} WHERE {} = %s".format(", ".join(sets), id_col)
            valores.append(NIT)
            cursor.execute(sql, tuple(valores))
            filas_afectadas = cursor.rowcount
            cone.commit()
            cone.close()
            return filas_afectadas > 0
        except Exception as error:
            print("Error al modificar los datos {}".format(error))
            return False
            
def modificar_personal(Usuario, Contraseña, Nombre_Empleado, Numero, Codigo):
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            sql = "UPDATE usuarios u JOIN empleados e ON u.Empleados_Id_Empleados = e.Id_Empleados SET u.Usuario = %s ,u.Contraseña = %s, e.Nombres = %s, e.Telefono = %s WHERE u.Id_Usuario = %s"
            valores = (Usuario, Contraseña, Nombre_Empleado, Numero, Codigo)
            cursor.execute(sql, valores)
            filas_afectadas = cursor.rowcount
            cone.commit()
            cone.close()
            return filas_afectadas > 0
        except mysql.connector.Error as error:
            print("Error al modificar los datos {}".format(error))
            
def eliminar_producto(Codigo):
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            sql = "DELETE FROM productos WHERE Id_Producto = %s"
            valor = (Codigo,)
            cursor.execute(sql, valor)
            cone.commit()
            cone.close()
            invalidar_catalogo()
            return cursor.rowcount
            
        except mysql.connector.Error as error:
            print("Error al conectarse a la base de datos {}".format(error))
            
def eliminar_proveedor(NIT):
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            id_col, _nombre, _tel, _dir = _layout_proveedores(cursor)
            sql = "DELETE FROM proveedores WHERE {} = %s".format(id_col or "Id_Proveedor")
            cursor.execute(sql, (NIT,))
            cone.commit()
            cone.close()
            return cursor.rowcount
        except Exception as error:
            print("Error al conectarse a la base de datos {}".format(error))
            return 0
            
def eliminar_personal(Codigo):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()

        print(f"Código a eliminar: {Codigo}")

        cursor.execute("SELECT Empleados_Id_Empleados FROM usuarios WHERE Id_Usuario = %s", (Codigo,))
        resultado = cursor.fetchone()
        
        if resultado:
            Id_Empleado = resultado[0]

            sql_usuario = "DELETE FROM usuarios WHERE Id_Usuario = %s"
            valor_usuario = (Codigo,)
            cursor.execute(sql_usuario, valor_usuario)

            cursor.execute("SELECT COUNT(*) FROM usuarios WHERE Empleados_Id_Empleados = %s", (Id_Empleado,))
            count = cursor.fetchone()[0]
            if count == 0:
                sql_empleado = "DELETE FROM empleados WHERE Id_Empleados = %s"
                valor_empleado = (Id_Empleado,)
                cursor.execute(sql_empleado, valor_empleado)

            cone.commit()
            print("Usuario eliminado, y empleado eliminado si no tiene más referencias.")
        else:
            print("No se encontró el usuario con el Código proporcionado.")

        cone.close()
        
    except mysql.connector.Error as error:
        print("Error al conectarse a la base de datos: {}".format(error))


            
def llenar_combobox():
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            _id_col, name_col, _tel, _dir = _layout_proveedores(cursor)
            sql = "SELECT {} FROM proveedores ORDER BY {}".format(name_col or "Nombre", name_col or "Nombre")
            cursor.execute(sql)
            proveedores = [row[0] for row in cursor.fetchall() if row[0]]
            cursor.close()
            cone.close()
            return proveedores
        except Exception as error:
            print("Error al conectar la base de datos {}".format(error))
            return []
            
def obtener_producto_por_nombre(Nombre):
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            sql = "SELECT * FROM productos WHERE Nombre = %s"
            valores = (Nombre,)
            cursor.execute(sql, valores)
            producto = cursor.fetchone()  
            
            cone.close()
            
           
            if producto:
                return producto
            else:
                print("Producto no encontrado.")
                return None
        except mysql.connector.Error as error:
            print("Error al conectar la base de datos: {}".format(error))
            return None

def actualizar_cantidad_producto(nombre, nueva_cantidad):
    try:
        conexion = FormularioLogin.conexion_base_de_datos()
        cursor = conexion.cursor()
        consulta = "UPDATE productos SET cantidad = %s WHERE nombre = %s"
        valores = (nueva_cantidad, nombre)
        cursor.execute(consulta, valores)
        conexion.commit()

    
        if cursor.rowcount > 0:
            return True
        else:
            return False  
    except mysql.connector.Error as e:
        print(f"Error al actualizar: {e}")
        return False
    finally:
        cursor.close()
        conexion.close()

            
def mostrar_personal():
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            query = "SELECT usuarios.Id_Usuario, usuarios.Usuario, usuarios.Contraseña, empleados.Nombres, empleados.Telefono FROM usuarios JOIN empleados ON usuarios.Empleados_Id_Empleados = empleados.Id_Empleados"
            cursor.execute(query)
            resultado = cursor.fetchall()
            cone.close()
            return resultado
        except mysql.connector.Error as error:
            print("Error al conectar la base de dato {}".format(error))
            
def mostrar_proveedores():
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            id_col, name_col, tel_col, dir_col = _layout_proveedores(cursor)
            sql = "SELECT {}, {}, {}, {} FROM proveedores ORDER BY {}".format(
                id_col or "Id_Proveedor",
                name_col or "Nombre",
                tel_col or "''",
                dir_col or "''",
                name_col or "Nombre",
            )
            cursor.execute(sql)
            resultado = cursor.fetchall()
            cone.close()
            return resultado
        except Exception as error:
            print("Error al conectar la base de dato {}".format(error))
            return []
            
def mostrar_entrada_dinero():
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            sql = "SELECT * FROM entrada_dinero"
            cursor.execute(sql)
            resultado = cursor.fetchall()
            cone.close()
            return resultado
        except mysql.connector.Error as error:
            print("Error al conectar la base de dato {}".format(error))
            
def mostrar_salida_dinero():
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            sql = "SELECT * FROM salida_dinero"
            cursor.execute(sql)
            resultado = cursor.fetchall()
            cone.close()
            return resultado
        except mysql.connector.Error as error:
            print("Error al conectar la base de dato {}".format(error))
            
def buscar_personal(Codigo, Usuario, Nombres):
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            sql = "SELECT usuarios.Id_Usuario, usuarios.Usuario, usuarios.Contraseña, empleados.Nombres, empleados.Telefono FROM usuarios JOIN empleados ON usuarios.Empleados_Id_Empleados = empleados.Id_Empleados WHERE usuarios.Id_Usuario LIKE %s OR usuarios.Usuario LIKE %s OR empleados.Nombres LIKE %s"
            valores = ('%' +Codigo+ '%','%'+Usuario+'%', '%'+Nombres+ '%')
            cursor.execute(sql, valores)
            resultado = cursor.fetchall()
            cone.close()
            return resultado
        except mysql.connector.Error as error:
            print("Error al conectar la base de dato {}".format(error))
              
            
def realizar_venta(Total, Id_Empleado):
    cone = None
    cursor = None
    try:
        zona_colombia = pytz.timezone('America/Bogota')
        ahora = datetime.now(zona_colombia)
        fecha_mysql = ahora.strftime('%Y-%m-%d %H:%M:%S')
        cone = FormularioLogin.conexion_base_de_datos()
        if not cone:
            return None
        cursor = cone.cursor()
        sql = "INSERT INTO ventas (Fecha_Venta, Total, Empleados_Id_Empleados) VALUES (%s, %s, %s);"
        cursor.execute(sql, (fecha_mysql, Total, Id_Empleado))
        id_venta = cursor.lastrowid
        cone.commit()
        return id_venta
    except Exception as error:
        print("Error al conectar la base de datos: {}".format(error))
        return None
    finally:
        try:
            if cursor:
                cursor.close()
            if cone:
                cone.close()
        except Exception:
            pass
            
def insertar_producto_has_venta(id_venta, id_producto, cantidad, subtotal, extra=None):
        extra = extra or {}
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            valores_extra = (
                extra.get("presentacion_id"),
                str(extra.get("presentacion_nombre") or "")[:80],
                float(extra.get("factor") or 1),
                float(extra.get("cantidad_presentacion") or cantidad or 0),
                float(extra.get("costo_unitario") or 0),
                float(extra.get("utilidad") or 0),
            )
            intentos = [
                (
                    """INSERT INTO productos_has_ventas
                       (Ventas_Id_Factura, Productos_Id_Producto, Cantidad, Subtotal,
                        Presentacion_Id, Presentacion_Nombre, Factor, Cantidad_Presentacion, Costo_Unitario, Utilidad)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (id_venta, id_producto, cantidad, subtotal) + valores_extra,
                ),
                (
                    "INSERT INTO productos_has_ventas (Ventas_Id_Factura, Productos_Id_Producto, Cantidad, Subtotal) VALUES (%s, %s, %s, %s)",
                    (id_venta, id_producto, cantidad, subtotal),
                ),
            ]
            for sql, valores in intentos:
                try:
                    cursor.execute(sql, valores)
                    break
                except Exception:
                    continue
            cone.commit()
            
        except mysql.connector.Error as error:
            print("Error al conectar la base de dato {}".format(error))    
            return None
        
        finally:
            cursor.close()  
            cone.close()
                
def actualizar_stock(id_producto, cantidad_vendida):
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            sql = "UPDATE productos SET Cantidad = Cantidad - %s WHERE Id_Producto = %s"
            valores = (cantidad_vendida, id_producto)
            cursor.execute(sql, valores)
            cone.commit()
            
        except mysql.connector.Error as error:
            print("Error al conectar la base de dato {}".format(error))    
            return None
        
        finally:
            cursor.close()
            cone.close()


def cambiar_stock_base(id_producto, delta):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            "UPDATE productos SET Cantidad = Cantidad + %s WHERE Id_Producto = %s",
            (float(delta or 0), id_producto),
        )
        cone.commit()
        cone.close()
        return True
    except Exception as error:
        print("Error al cambiar stock: {}".format(error))
        return False
            
def mostrar_venta_por_fecha(fecha_inicio, fecha_fin):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        sql = """
            SELECT v.Id_Venta, v.Fecha_Venta, p.Nombre, vp.Cantidad, vp.Subtotal,
                   COALESCE(v.Anulada, 0)
            FROM ventas v
            JOIN productos_has_ventas vp ON v.Id_Venta = vp.Ventas_Id_Factura
            JOIN productos p ON vp.Productos_Id_Producto = p.Id_Producto
            WHERE v.Fecha_Venta BETWEEN %s AND %s;
        """
        valores = (fecha_inicio, fecha_fin)
        cursor.execute(sql, valores)
        ventas = cursor.fetchall()

        if ventas:
            return ventas
        else:
            print("No se encontraron ventas en el rango de fechas proporcionado.")
            return None

    except mysql.connector.Error as error:
        print(f"Error al conectar a la base de datos: {error}")
        return None

    finally:

        try:
            if cursor:
                cursor.close()
            if cone and hasattr(cone, 'is_connected') and cone.is_connected():
                cone.close()
        except Exception as e:
            print(f"Error al cerrar la conexión: {e}")
        

def mostrar_movimientos_por_fecha(fecha_inicio, fecha_fin):
        try:
            cone = FormularioLogin.conexion_base_de_datos()  
            cursor = cone.cursor()

       
            sql = """
                SELECT 'Entrada' AS tipo, e.Id_entrada, e.Asunto, e.Cantidad, e.Cajero, e.Fecha
                FROM entrada_dinero e
                WHERE e.Fecha BETWEEN %s AND %s
                UNION ALL
                SELECT 'Salida' AS tipo, s.Id_Salida, s.Asunto, s.Cantidad, s.Cajero, s.Fecha
                FROM salida_dinero s
                WHERE s.Fecha BETWEEN %s AND %s;
            """
            valores = (fecha_inicio, fecha_fin, fecha_inicio, fecha_fin)
            cursor.execute(sql, valores)
            movimientos = cursor.fetchall()

            return movimientos

        except mysql.connector.Error as error:
            print(f"Error al conectar a la base de datos: {error}")
            return None

        finally:
        
            try:
                if cursor:
                    cursor.close()
                if cone and hasattr(cone, 'is_connected') and cone.is_connected():
                    cone.close()
            except Exception as e:
                print(f"Error al cerrar la conexión: {e}")
           
def mostrar_venta_por_fecha_unica(fecha):
    cone = FormularioLogin.conexion_base_de_datos()
    cursor = cone.cursor()

    consulta = """
        SELECT v.Id_Venta, v.Fecha_Venta, p.Nombre, vp.Cantidad, vp.Subtotal
        FROM ventas v
        JOIN productos_has_ventas vp ON v.Id_Venta = vp.Ventas_Id_Factura
        JOIN productos p ON vp.Productos_Id_Producto = p.Id_Producto
        WHERE DATE(v.Fecha_Venta) = %s
    """
    cursor.execute(consulta, (fecha,))
    resultados = cursor.fetchall()
    
    cursor.close()
    return resultados
     
def buscar_codigo_venta(Codigo):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        sql = """
                SELECT v.Id_Venta, v.Fecha_Venta, p.Nombre,
                       COALESCE(NULLIF(vp.Presentacion_Nombre, ''), 'Unidad'),
                       COALESCE(NULLIF(vp.Cantidad_Presentacion, 0), vp.Cantidad),
                       vp.Subtotal,
                       CASE WHEN vp.Costo_Unitario IS NOT NULL AND vp.Costo_Unitario > 0
                            THEN vp.Costo_Unitario * COALESCE(NULLIF(vp.Cantidad_Presentacion, 0), vp.Cantidad)
                            ELSE (p.Precio_Compra * vp.Cantidad) END,
                       COALESCE(NULLIF(vp.Utilidad, 0), vp.Subtotal - (p.Precio_Compra * vp.Cantidad)),
                       COALESCE(v.Anulada, 0),
                       COALESCE(v.Estado, '')
                FROM ventas v
                JOIN productos_has_ventas vp ON v.Id_Venta = vp.Ventas_Id_Factura
                JOIN productos p ON vp.Productos_Id_Producto = p.Id_Producto
                WHERE v.Id_Venta LIKE %s;
        """
        valores = ('%'+Codigo+'%',)
        try:
            cursor.execute(sql, valores)
        except Exception:
            sql_old = sql.replace(",\n                       COALESCE(v.Estado, '')", "")
            cursor.execute(sql_old, valores)
        Resultado = cursor.fetchall()
        cone.close()
        return Resultado
    except mysql.connector.Error as error:
        print(f"Error al conectar a la base de datos: {error}")
    return None

def mostrar_R_Ventas():
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        sql = """
                SELECT v.Id_Venta, v.Fecha_Venta, p.Nombre, vp.Cantidad, vp.Subtotal,
                       COALESCE(v.Anulada, 0)
                FROM ventas v
                JOIN productos_has_ventas vp ON v.Id_Venta = vp.Ventas_Id_Factura
                JOIN productos p ON vp.Productos_Id_Producto = p.Id_Producto
                ORDER BY v.Fecha_Venta DESC
        """
        cursor.execute(sql)
        Resultado = cursor.fetchall()
        cone.close()
        return Resultado
    except mysql.connector.Error as error:
        print(f"Error al conectar a la base de datos: {error}")
    return None


def parse_producto(row):
    if not row:
        return None

    def _col(nombre, default="", idx_fallback=None):
        cols = columnas_producto()
        if cols and nombre in cols:
            i = cols.index(nombre)
            if len(row) > i:
                val = row[i]
                return default if val is None else val
        if idx_fallback is not None and len(row) > idx_fallback:
            val = row[idx_fallback]
            return default if val is None else val
        return default

    def _texto(valor, default=""):
        if valor is None:
            return default
        # Evita fechas/números tratados como texto de proveedor/categoría
        if hasattr(valor, "strftime"):
            return default
        return str(valor).strip()

    stock_raw = _col("Stock_Minimo", 10, 8)
    try:
        stock_min = int(stock_raw)
    except (TypeError, ValueError):
        stock_min = 10

    return {
        "id": _col("Id_Producto", row[0] if row else "", 0),
        "nombre": _texto(_col("Nombre", "", 1)),
        "precio_venta": _col("Precio_Venta", 0, 2),
        "precio_compra": _col("Precio_Compra", 0, 3),
        "cantidad": _col("Cantidad", 0, 4),
        "marca": _texto(_col("Marca", "", 5)),
        "categoria": _texto(_col("Categoria", "", 6)),
        "ubicacion": _texto(_col("Ubicacion", "", 7)),
        "stock_minimo": stock_min,
        "proveedor": _texto(_col("Proveedor", "", 9)),
        "iva": iva_de_fila(row),
        "unidad_base": _texto(_col("Unidad_Base", "Unidad")) or "Unidad",
        "permite_fraccion": int(_col("Permite_Fraccion", 1) or 1) == 1,
    }


def _valor_col_producto(row, nombre, default=""):
    cols = columnas_producto()
    if nombre in cols and row and len(row) > cols.index(nombre):
        val = row[cols.index(nombre)]
        return default if val is None else val
    return default


def listar_presentaciones(producto_id, solo_venta=False, solo_activas=True):
    if not producto_id:
        return []
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        sql = """SELECT Id, Producto_Id, Nombre, Factor, Unidad, Codigo_Barras,
                        Precio_Venta, Utilidad_Pct, Permite_Venta, Activo, Es_Default
                 FROM producto_presentaciones WHERE Producto_Id=%s"""
        if solo_activas:
            sql += " AND Activo=1"
        if solo_venta:
            sql += " AND Permite_Venta=1"
        sql += " ORDER BY Factor DESC, Id ASC"
        cursor.execute(sql, (producto_id,))
        filas = [parse_presentacion(r) for r in cursor.fetchall() or []]
        cone.close()
        return [f for f in filas if f]
    except Exception as error:
        print("Error al listar presentaciones: {}".format(error))
        return []


def mapa_presentaciones(solo_activas=True):
    resultado = {}
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        sql = """SELECT Id, Producto_Id, Nombre, Factor, Unidad, Codigo_Barras,
                        Precio_Venta, Utilidad_Pct, Permite_Venta, Activo, Es_Default
                 FROM producto_presentaciones"""
        if solo_activas:
            sql += " WHERE Activo=1"
        sql += " ORDER BY Factor DESC, Id ASC"
        cursor.execute(sql)
        for row in cursor.fetchall() or []:
            pres = parse_presentacion(row)
            if not pres:
                continue
            resultado.setdefault(int(pres["producto_id"]), []).append(pres)
        cone.close()
    except Exception as error:
        print("Error al mapear presentaciones: {}".format(error))
    return resultado


def presentacion_default(producto_id):
    filas = listar_presentaciones(producto_id, solo_venta=True)
    for fila in filas:
        if fila.get("es_default"):
            return fila
    for fila in filas:
        if abs(float(fila.get("factor") or 1) - 1) < 0.0000001:
            return fila
    return filas[0] if filas else None


def presentacion_por_id(pres_id):
    if not pres_id:
        return None
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            """SELECT Id, Producto_Id, Nombre, Factor, Unidad, Codigo_Barras,
                      Precio_Venta, Utilidad_Pct, Permite_Venta, Activo, Es_Default
               FROM producto_presentaciones WHERE Id=%s""",
            (pres_id,),
        )
        row = cursor.fetchone()
        cone.close()
        return parse_presentacion(row)
    except Exception as error:
        print("Error al leer presentación: {}".format(error))
        return None


def buscar_por_codigo_barras(codigo):
    codigo = str(codigo or "").strip()
    if not codigo:
        return None
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            """SELECT Id, Producto_Id, Nombre, Factor, Unidad, Codigo_Barras,
                      Precio_Venta, Utilidad_Pct, Permite_Venta, Activo, Es_Default
               FROM producto_presentaciones
               WHERE Codigo_Barras=%s AND Activo=1 AND Permite_Venta=1
               LIMIT 1""",
            (codigo,),
        )
        row = cursor.fetchone()
        cone.close()
        return parse_presentacion(row)
    except Exception as error:
        print("Error al buscar código de barras: {}".format(error))
        return None


def _valores_presentacion(item, costo_base=0, iva_pct=0, forzar_default=False):
    factor = float(item.get("factor") or 1)
    if factor <= 0:
        return None
    utilidad = utilidad_a_porcentaje(item.get("utilidad_pct"))
    try:
        precio = float(item.get("precio_venta") or 0)
    except (TypeError, ValueError):
        precio = 0
    if precio <= 0:
        precio = precio_venta_con_margen(costo_equivalente(costo_base, factor), utilidad, iva_pct) or 0
    es_def = bool(item.get("es_default")) or forzar_default
    return (
        str(item.get("nombre") or "Unidad")[:80],
        factor,
        str(item.get("unidad") or "")[:40],
        str(item.get("codigo_barras") or "")[:40],
        precio,
        utilidad,
        1 if item.get("permite_venta", True) else 0,
        1 if item.get("activo", True) else 0,
        1 if es_def else 0,
    )


def guardar_presentaciones(producto_id, presentaciones, costo_base=0, iva_pct=0):
    if not producto_id:
        return False
    filas = list(presentaciones or [])
    if not filas:
        filas = [
            {
                "nombre": "Unidad",
                "factor": 1,
                "utilidad_pct": 20,
                "precio_venta": precio_venta_con_margen(costo_base, 20, iva_pct) or 0,
                "permite_venta": True,
                "activo": True,
                "es_default": True,
                "codigo_barras": "",
                "unidad": "",
            }
        ]
    hay_default = any(x.get("es_default") for x in filas)
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute("SELECT Id FROM producto_presentaciones WHERE Producto_Id=%s", (producto_id,))
        existentes = {int(r[0]) for r in cursor.fetchall() or []}
        usados = set()
        for item in filas:
            forzar = (not hay_default) and abs(float(item.get("factor") or 1) - 1) < 0.0000001
            vals = _valores_presentacion(item, costo_base, iva_pct, forzar)
            if not vals:
                continue
            pres_id = item.get("id")
            try:
                pres_id = int(pres_id) if pres_id not in (None, "", 0, "0") else None
            except (TypeError, ValueError):
                pres_id = None
            if pres_id and pres_id in existentes:
                cursor.execute(
                    """UPDATE producto_presentaciones
                       SET Nombre=%s, Factor=%s, Unidad=%s, Codigo_Barras=%s, Precio_Venta=%s,
                           Utilidad_Pct=%s, Permite_Venta=%s, Activo=%s, Es_Default=%s
                       WHERE Id=%s AND Producto_Id=%s""",
                    vals + (pres_id, producto_id),
                )
                usados.add(pres_id)
            else:
                cursor.execute(
                    """INSERT INTO producto_presentaciones
                       (Producto_Id, Nombre, Factor, Unidad, Codigo_Barras, Precio_Venta, Utilidad_Pct,
                        Permite_Venta, Activo, Es_Default)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (producto_id,) + vals,
                )
                if cursor.lastrowid:
                    usados.add(int(cursor.lastrowid))
        sobran = existentes - usados
        if sobran:
            cursor.execute(
                "DELETE FROM producto_presentaciones WHERE Producto_Id=%s AND Id IN ({})".format(
                    ",".join(["%s"] * len(sobran))
                ),
                tuple(sobran),
            )
        cone.commit()
        cone.close()
        return True
    except Exception as error:
        print("Error al guardar presentaciones: {}".format(error))
        return False


def texto_equivalencias(stock_base, presentaciones, unidad_base="Unidad"):
    try:
        stock = float(stock_base or 0)
    except (TypeError, ValueError):
        stock = 0
    partes = ["{:.0f} {}".format(stock, unidad_base or "unid.")]
    vistos = set()
    for pres in presentaciones or []:
        factor = float(pres.get("factor") or 0)
        nombre = (pres.get("nombre") or "").strip()
        if factor <= 1 or not nombre or nombre.lower() in vistos:
            continue
        vistos.add(nombre.lower())
        eq = stock / factor
        if abs(eq - round(eq)) < 0.001:
            partes.append("{} {}".format(int(round(eq)), nombre.lower()))
        else:
            partes.append("{:.2f} {}".format(eq, nombre.lower()))
    return " · ".join(partes)


def registrar_movimiento_inventario(producto_id, tipo, cantidad_pres, factor, motivo="", usuario="", presentacion_id=None):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        base = a_unidades_base(cantidad_pres, factor)
        cursor.execute(
            """INSERT INTO inventario_movimientos
               (Producto_Id, Presentacion_Id, Tipo, Cantidad_Presentacion, Factor, Cantidad_Base, Motivo, Usuario, Fecha)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (producto_id, presentacion_id, tipo, float(cantidad_pres or 0), float(factor or 1), base, motivo[:220], usuario or "", _ahora()),
        )
        cone.commit()
        cone.close()
        return True
    except Exception as error:
        print("Error al registrar movimiento: {}".format(error))
        return False


def ensure_schema():
    global _PRODUCTO_COLS, _CLIENTES_LAYOUT
    cone = FormularioLogin.conexion_base_de_datos()
    if not cone:
        return False
    cursor = cone.cursor()
    try:
        cursor.execute("SELECT DATABASE()")
        db = cursor.fetchone()[0]
        def has_column(table, column):
            cursor.execute(
                """SELECT COUNT(*) FROM information_schema.COLUMNS
                   WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s""",
                (db, table, column),
            )
            return cursor.fetchone()[0] > 0

        def has_table(table):
            cursor.execute(
                """SELECT COUNT(*) FROM information_schema.TABLES
                   WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s""",
                (db, table),
            )
            return cursor.fetchone()[0] > 0

        for table, col, defn in (
            ("productos", "Categoria", "VARCHAR(80) DEFAULT ''"),
            ("productos", "Ubicacion", "VARCHAR(80) DEFAULT ''"),
            ("productos", "Stock_Minimo", "INT DEFAULT 10"),
            ("productos", "Proveedor", "VARCHAR(120) DEFAULT ''"),
            ("productos", "Iva", "DECIMAL(5,2) DEFAULT 0"),
            ("productos", "Unidad_Base", "VARCHAR(40) DEFAULT 'Unidad'"),
            ("productos", "Permite_Fraccion", "TINYINT DEFAULT 1"),
            ("config_pos", "Tipo_Negocio", "VARCHAR(40) DEFAULT 'Tienda'"),
            ("config_pos", "Dias_Alerta_Vence", "INT DEFAULT 30"),
            ("config_pos", "Usar_FEFO", "TINYINT DEFAULT 1"),
            ("config_pos", "Pct_Proveedores", "DECIMAL(7,2) DEFAULT 65"),
            ("config_pos", "Pct_Provisiones", "DECIMAL(7,2) DEFAULT 17"),
            ("config_pos", "Pct_Utilidad", "DECIMAL(7,2) DEFAULT 18"),
            ("config_pos", "Base_Gabinete", "DECIMAL(12,2) DEFAULT 0"),
            ("config_pos", "Pct_Recargo_Tarjeta", "DECIMAL(7,2) DEFAULT 6"),
            ("cierre_turno", "Tipo", "VARCHAR(20) DEFAULT 'definitivo'"),
            ("cierre_turno", "Efectivo_Retirar", "DECIMAL(12,2) DEFAULT 0"),
            ("cierre_turno", "Base_Dejada", "DECIMAL(12,2) DEFAULT 0"),
            ("cierre_turno", "Credito", "DECIMAL(12,2) DEFAULT 0"),
            ("cierre_turno", "Abonos", "DECIMAL(12,2) DEFAULT 0"),
            ("cierre_turno", "Estado", "VARCHAR(40) DEFAULT ''"),
            ("cierre_turno", "Observacion", "TEXT NULL"),
            ("cierre_turno", "Correcciones", "INT DEFAULT 0"),
            ("cierre_turno", "Fecha_Desde", "DATETIME NULL"),
            ("cierre_turno", "Usuario", "VARCHAR(80) DEFAULT ''"),
            ("cierre_turno", "Tickets", "INT DEFAULT 0"),
            ("cierre_turno", "Ticket_Impreso", "TINYINT DEFAULT 1"),
            ("cierre_turno", "Linea_Tiempo", "TEXT NULL"),
            ("compra_items", "Presentacion_Id", "INT NULL"),
            ("compra_items", "Presentacion_Nombre", "VARCHAR(80) DEFAULT ''"),
            ("compra_items", "Factor", "DECIMAL(14,6) DEFAULT 1"),
            ("compra_items", "Cantidad_Base", "DECIMAL(14,6) DEFAULT 0"),
            ("productos_has_ventas", "Presentacion_Id", "INT NULL"),
            ("productos_has_ventas", "Presentacion_Nombre", "VARCHAR(80) DEFAULT ''"),
            ("productos_has_ventas", "Factor", "DECIMAL(14,6) DEFAULT 1"),
            ("productos_has_ventas", "Cantidad_Presentacion", "DECIMAL(14,6) DEFAULT 0"),
            ("productos_has_ventas", "Costo_Unitario", "DECIMAL(12,4) DEFAULT 0"),
            ("productos_has_ventas", "Utilidad", "DECIMAL(12,2) DEFAULT 0"),
            ("productos_has_ventas", "Devuelto", "TINYINT DEFAULT 0"),
            ("lotes", "Costo", "DECIMAL(12,4) DEFAULT 0"),
            ("lotes", "Factura", "VARCHAR(40) DEFAULT ''"),
            ("lotes", "Presentacion_Id", "INT NULL"),
            ("lotes", "Presentacion_Nombre", "VARCHAR(80) DEFAULT ''"),
            ("clientes", "Limite_Credito", "DECIMAL(12,2) DEFAULT 0"),
            ("clientes", "Saldo_Pendiente", "DECIMAL(12,2) DEFAULT 0"),
            ("clientes", "Puntos", "INT DEFAULT 0"),
            ("ventas", "Cliente_Id", "INT NULL"),
            ("ventas", "Anulada", "TINYINT DEFAULT 0"),
            ("ventas", "Estado", "VARCHAR(20) DEFAULT 'ACTIVA'"),
        ):
            if has_table(table) and not has_column(table, col):
                try:
                    cursor.execute(f"ALTER TABLE `{table}` ADD COLUMN `{col}` {defn}")
                except Exception as error:
                    print("Aviso al agregar {}.{}: {}".format(table, col, error))
        _PRODUCTO_COLS = None
        _CLIENTES_LAYOUT = None
        for col in ("Cedula", "Telefono"):
            if not has_column("clientes", col):
                continue
            try:
                cursor.execute("SHOW COLUMNS FROM clientes LIKE %s", (col,))
                tipo = str((cursor.fetchone() or [None, ""])[1]).lower()
                if any(t in tipo for t in ("int", "double", "decimal", "float", "bigint")):
                    cursor.execute("ALTER TABLE clientes MODIFY `{}` VARCHAR(30)".format(col))
            except Exception:
                pass

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS venta_pagos (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Venta_Id INT NOT NULL,
                Metodo VARCHAR(40) NOT NULL,
                Monto DECIMAL(12,2) NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cierre_turno (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Cajero VARCHAR(80),
                Fecha DATETIME,
                Monto_Inicial DECIMAL(12,2),
                Conteo_Fisico DECIMAL(12,2),
                Esperado DECIMAL(12,2),
                Descuadre DECIMAL(12,2),
                Total_Ventas DECIMAL(12,2),
                Efectivo DECIMAL(12,2),
                Nequi DECIMAL(12,2),
                Tarjeta DECIMAL(12,2),
                Transferencia DECIMAL(12,2),
                Entradas DECIMAL(12,2),
                Salidas DECIMAL(12,2)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS bolsillos (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Nombre VARCHAR(80) NOT NULL,
                Porcentaje DECIMAL(7,2) NOT NULL DEFAULT 0,
                Color VARCHAR(16) DEFAULT '#3077FF',
                Icono VARCHAR(40) DEFAULT 'wallet',
                Meta_Mensual DECIMAL(12,2) DEFAULT 0,
                Activo TINYINT DEFAULT 1,
                Orden INT DEFAULT 0,
                Codigo VARCHAR(40) DEFAULT ''
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS bolsillo_movimientos (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Bolsillo_Id INT NOT NULL,
                Tipo VARCHAR(20) NOT NULL,
                Monto DECIMAL(12,2) NOT NULL,
                Nota VARCHAR(220) DEFAULT '',
                Fecha DATETIME,
                Venta_Id INT NULL,
                Metodo VARCHAR(40) DEFAULT '',
                Categoria VARCHAR(40) DEFAULT '',
                Usuario VARCHAR(80) DEFAULT '',
                Comprobante VARCHAR(100) DEFAULT '',
                Cierre_Id INT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cierre_diario_asignacion (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Cierre_Turno_Id INT NULL,
                Fecha DATETIME,
                Cajero VARCHAR(80) DEFAULT '',
                Pct_Proveedores DECIMAL(7,2) DEFAULT 0,
                Pct_Provisiones DECIMAL(7,2) DEFAULT 0,
                Pct_Utilidad DECIMAL(7,2) DEFAULT 0,
                Recaudo_Efectivo DECIMAL(12,2) DEFAULT 0,
                Recaudo_Nequi DECIMAL(12,2) DEFAULT 0,
                Recaudo_Tarjeta DECIMAL(12,2) DEFAULT 0,
                Recaudo_Transferencia DECIMAL(12,2) DEFAULT 0,
                Monto_Proveedores DECIMAL(12,2) DEFAULT 0,
                Monto_Provisiones DECIMAL(12,2) DEFAULT 0,
                Monto_Utilidad DECIMAL(12,2) DEFAULT 0
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cierre_mensual (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Mes INT NOT NULL,
                Anio INT NOT NULL,
                Total_Ventas DECIMAL(12,2) DEFAULT 0,
                Costo_Ventas DECIMAL(12,2) DEFAULT 0,
                Utilidad_Bruta DECIMAL(12,2) DEFAULT 0,
                Total_Gastos_Operativos DECIMAL(12,2) DEFAULT 0,
                Utilidad_Neta DECIMAL(12,2) DEFAULT 0,
                Recaudo_Proveedores DECIMAL(12,2) DEFAULT 0,
                Recaudo_Provisiones DECIMAL(12,2) DEFAULT 0,
                Recaudo_Utilidad DECIMAL(12,2) DEFAULT 0,
                Fecha_Cierre DATETIME,
                Usuario VARCHAR(80) DEFAULT '',
                UNIQUE KEY uq_cierre_mes (Mes, Anio)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS devolucion_solicitudes (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Venta_Id INT NOT NULL,
                Estado VARCHAR(32) NOT NULL DEFAULT 'PENDIENTE',
                Motivo VARCHAR(255) DEFAULT '',
                Nota_Respuesta VARCHAR(255) DEFAULT '',
                Cajero VARCHAR(80) DEFAULT '',
                Cliente VARCHAR(120) DEFAULT '',
                Total DECIMAL(12,2) DEFAULT 0,
                Admin_Id INT NULL,
                Fecha DATETIME,
                Fecha_Respuesta DATETIME NULL,
                Avisado_Caja TINYINT DEFAULT 0,
                INDEX idx_dev_estado (Estado),
                INDEX idx_dev_venta (Venta_Id)
            )
            """
        )
        for table, colname, defn in (
            ("bolsillos", "Codigo", "VARCHAR(40) DEFAULT ''"),
            ("bolsillo_movimientos", "Metodo", "VARCHAR(40) DEFAULT ''"),
            ("bolsillo_movimientos", "Categoria", "VARCHAR(40) DEFAULT ''"),
            ("bolsillo_movimientos", "Usuario", "VARCHAR(80) DEFAULT ''"),
            ("bolsillo_movimientos", "Comprobante", "VARCHAR(100) DEFAULT ''"),
            ("bolsillo_movimientos", "Cierre_Id", "INT NULL"),
            ("devolucion_solicitudes", "Avisado_Caja", "TINYINT DEFAULT 0"),
            ("devolucion_solicitudes", "Items", "TEXT NULL"),
        ):
            if has_table(table) and not has_column(table, colname):
                try:
                    cursor.execute(f"ALTER TABLE `{table}` ADD COLUMN `{colname}` {defn}")
                except Exception:
                    pass
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cierre_turno_medios (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Cierre_Id INT NOT NULL,
                Metodo VARCHAR(40) NOT NULL,
                Etiqueta VARCHAR(60) DEFAULT '',
                Sistema DECIMAL(12,2) DEFAULT 0,
                Declarado DECIMAL(12,2) DEFAULT 0,
                Diferencia DECIMAL(12,2) DEFAULT 0,
                INDEX idx_cierre_medios (Cierre_Id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS venta_pago_correcciones (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Venta_Id INT NOT NULL,
                Metodo_Anterior VARCHAR(40) NOT NULL,
                Metodo_Nuevo VARCHAR(40) NOT NULL,
                Monto DECIMAL(12,2) NOT NULL,
                Motivo VARCHAR(255) DEFAULT '',
                Usuario VARCHAR(80) DEFAULT '',
                Fecha DATETIME,
                Cierre_Id INT NULL,
                INDEX idx_vpc_venta (Venta_Id),
                INDEX idx_vpc_cierre (Cierre_Id),
                INDEX idx_vpc_fecha (Fecha)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cierre_general (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Estado VARCHAR(40) NOT NULL DEFAULT 'BORRADOR',
                Titulo VARCHAR(120) DEFAULT '',
                Fecha_Creacion DATETIME,
                Fecha_Actualizacion DATETIME NULL,
                Fecha_Consolidacion DATETIME NULL,
                Admin_Usuario VARCHAR(80) DEFAULT '',
                Admin_Id INT NULL,
                Observacion TEXT NULL,
                Total_Ventas DECIMAL(14,2) DEFAULT 0,
                Total_Efectivo DECIMAL(14,2) DEFAULT 0,
                Total_Nequi DECIMAL(14,2) DEFAULT 0,
                Total_Datafono DECIMAL(14,2) DEFAULT 0,
                Total_Diferencia DECIMAL(14,2) DEFAULT 0,
                INDEX idx_cg_estado (Estado)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cierre_general_dias (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Cierre_General_Id INT NOT NULL,
                Cierre_Turno_Id INT NOT NULL,
                Estado_Dia VARCHAR(40) DEFAULT 'PENDIENTE',
                Chk_Efectivo TINYINT DEFAULT 0,
                Chk_Nequi TINYINT DEFAULT 0,
                Chk_Datafono TINYINT DEFAULT 0,
                Chk_Ventas TINYINT DEFAULT 0,
                Chk_Correcciones TINYINT DEFAULT 0,
                Chk_Descuadres TINYINT DEFAULT 0,
                Chk_Observaciones TINYINT DEFAULT 0,
                Chk_Validado TINYINT DEFAULT 0,
                Nota_Admin TEXT NULL,
                INDEX idx_cgd_general (Cierre_General_Id),
                INDEX idx_cgd_turno (Cierre_Turno_Id),
                UNIQUE KEY uq_cgd_general_turno (Cierre_General_Id, Cierre_Turno_Id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS provision_admin_estado (
                Id INT PRIMARY KEY,
                Saldo_Pendiente DECIMAL(14,2) NOT NULL DEFAULT 0,
                Fecha_Actualizacion DATETIME NULL
            )
            """
        )
        cursor.execute(
            """
            INSERT IGNORE INTO provision_admin_estado (Id, Saldo_Pendiente, Fecha_Actualizacion)
            VALUES (1, 0, NULL)
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS provision_admin (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Cierre_General_Id INT NOT NULL,
                Estado VARCHAR(40) NOT NULL DEFAULT 'APLICADA',
                Fecha DATETIME,
                Admin_Usuario VARCHAR(80) DEFAULT '',
                Ventas_Generales DECIMAL(14,2) DEFAULT 0,
                Porcentaje DECIMAL(5,2) DEFAULT 30,
                Treinta_Porciento DECIMAL(14,2) DEFAULT 0,
                Provision_Objetivo DECIMAL(14,2) DEFAULT 0,
                Saldo_Pendiente_Anterior DECIMAL(14,2) DEFAULT 0,
                Objetivo_Total DECIMAL(14,2) DEFAULT 0,
                Efectivo_Disponible DECIMAL(14,2) DEFAULT 0,
                Efectivo_Provisionado DECIMAL(14,2) DEFAULT 0,
                Nuevo_Saldo_Pendiente DECIMAL(14,2) DEFAULT 0,
                Observacion TEXT NULL,
                UNIQUE KEY uq_prov_cierre_general (Cierre_General_Id),
                INDEX idx_prov_fecha (Fecha),
                INDEX idx_prov_estado (Estado)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS provision_bolsillo_saldo (
                Id INT PRIMARY KEY,
                Dinero_Real DECIMAL(14,2) NOT NULL DEFAULT 0,
                Fecha_Actualizacion DATETIME NULL
            )
            """
        )
        cursor.execute(
            "INSERT IGNORE INTO provision_bolsillo_saldo (Id, Dinero_Real, Fecha_Actualizacion) VALUES (1, 0, NULL)"
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS provision_empleados_salario (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Nombre VARCHAR(160) NOT NULL,
                Empleado_Id INT NULL,
                Salario_Mensual DECIMAL(14,2) NOT NULL DEFAULT 0,
                Activo TINYINT NOT NULL DEFAULT 1,
                Usuario VARCHAR(80) DEFAULT '',
                Observacion TEXT NULL,
                Fecha DATETIME,
                INDEX idx_pes_activo (Activo)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS provision_obligacion (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Tipo VARCHAR(40) NOT NULL,
                Nombre VARCHAR(160) NOT NULL,
                Descripcion TEXT NULL,
                Categoria VARCHAR(80) DEFAULT '',
                Valor DECIMAL(14,2) NOT NULL DEFAULT 0,
                Estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
                Fecha_Obligacion DATE NULL,
                Fecha_Vencimiento DATE NULL,
                Fecha_Pago DATETIME NULL,
                Empleado_Salario_Id INT NULL,
                Usuario VARCHAR(80) DEFAULT '',
                Usuario_Pago VARCHAR(80) DEFAULT '',
                Observacion TEXT NULL,
                Cierre_General_Id INT NULL,
                Fecha DATETIME,
                INDEX idx_po_tipo (Tipo),
                INDEX idx_po_estado (Estado),
                INDEX idx_po_fecha (Fecha)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS provision_bolsillo_mov (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Tipo VARCHAR(40) NOT NULL,
                Categoria VARCHAR(40) DEFAULT '',
                Monto DECIMAL(14,2) NOT NULL DEFAULT 0,
                Dinero_Real_Ant DECIMAL(14,2) DEFAULT 0,
                Dinero_Real_Nuevo DECIMAL(14,2) DEFAULT 0,
                Comprometido_Ant DECIMAL(14,2) DEFAULT 0,
                Comprometido_Nuevo DECIMAL(14,2) DEFAULT 0,
                Disponible_Ant DECIMAL(14,2) DEFAULT 0,
                Disponible_Nuevo DECIMAL(14,2) DEFAULT 0,
                Obligacion_Id INT NULL,
                Empleado_Salario_Id INT NULL,
                Referencia VARCHAR(120) DEFAULT '',
                Observacion TEXT NULL,
                Usuario VARCHAR(80) DEFAULT '',
                Cierre_General_Id INT NULL,
                Provision_Id INT NULL,
                Estado VARCHAR(20) DEFAULT 'ACTIVO',
                Fecha DATETIME,
                INDEX idx_pbm_fecha (Fecha),
                INDEX idx_pbm_tipo (Tipo),
                INDEX idx_pbm_cg (Cierre_General_Id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS bolsillo_proveedores_saldo (
                Id INT PRIMARY KEY,
                Efectivo DECIMAL(14,2) NOT NULL DEFAULT 0,
                Nequi DECIMAL(14,2) NOT NULL DEFAULT 0,
                Datafono DECIMAL(14,2) NOT NULL DEFAULT 0,
                Fecha_Actualizacion DATETIME NULL
            )
            """
        )
        cursor.execute(
            """
            INSERT IGNORE INTO bolsillo_proveedores_saldo (Id, Efectivo, Nequi, Datafono, Fecha_Actualizacion)
            VALUES (1, 0, 0, 0, NULL)
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS bolsillo_proveedores_mov (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Tipo VARCHAR(40) NOT NULL,
                Metodo VARCHAR(40) DEFAULT '',
                Monto DECIMAL(14,2) NOT NULL DEFAULT 0,
                Efectivo DECIMAL(14,2) NOT NULL DEFAULT 0,
                Nequi DECIMAL(14,2) NOT NULL DEFAULT 0,
                Datafono DECIMAL(14,2) NOT NULL DEFAULT 0,
                Saldo_Ef_Ant DECIMAL(14,2) DEFAULT 0,
                Saldo_Neq_Ant DECIMAL(14,2) DEFAULT 0,
                Saldo_Dat_Ant DECIMAL(14,2) DEFAULT 0,
                Saldo_Ef_Nuevo DECIMAL(14,2) DEFAULT 0,
                Saldo_Neq_Nuevo DECIMAL(14,2) DEFAULT 0,
                Saldo_Dat_Nuevo DECIMAL(14,2) DEFAULT 0,
                Proveedor_Id INT NULL,
                Proveedor_Nombre VARCHAR(160) DEFAULT '',
                Referencia VARCHAR(120) DEFAULT '',
                Observacion TEXT NULL,
                Usuario VARCHAR(80) DEFAULT '',
                Cierre_General_Id INT NULL,
                Provision_Id INT NULL,
                Estado VARCHAR(20) DEFAULT 'ACTIVO',
                Fecha DATETIME,
                INDEX idx_bpm_fecha (Fecha),
                INDEX idx_bpm_tipo (Tipo),
                INDEX idx_bpm_cg (Cierre_General_Id),
                INDEX idx_bpm_estado (Estado)
            )
            """
        )
        try:
            cursor.execute("SELECT COUNT(*) FROM bolsillos")
            if int((cursor.fetchone() or [0])[0] or 0) == 0:
                cursor.execute(
                    """INSERT INTO bolsillos
                       (Nombre, Porcentaje, Color, Icono, Meta_Mensual, Activo, Orden, Codigo)
                       VALUES
                       ('Caja Proveedores', 65, '#3077FF', 'truck', 0, 1, 1, 'PROVEEDORES'),
                       ('Utilidad neta', 18, '#22C55E', 'crown', 0, 1, 2, 'UTILIDAD'),
                       ('Provisiones / operación', 17, '#A084E8', 'building', 0, 1, 3, 'PROVISIONES')"""
                )
            else:
                cursor.execute("UPDATE bolsillos SET Codigo='PROVEEDORES' WHERE (Codigo IS NULL OR Codigo='') AND LOWER(Nombre) LIKE '%proveedor%'")
                cursor.execute("UPDATE bolsillos SET Codigo='UTILIDAD' WHERE (Codigo IS NULL OR Codigo='') AND LOWER(Nombre) LIKE '%utilidad%'")
                cursor.execute("UPDATE bolsillos SET Codigo='PROVISIONES' WHERE (Codigo IS NULL OR Codigo='') AND (LOWER(Nombre) LIKE '%operativ%' OR LOWER(Nombre) LIKE '%provisi%')")
        except Exception as error:
            print("Aviso al sembrar bolsillos: {}".format(error))
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS clientes (
                Id_Cliente INT AUTO_INCREMENT PRIMARY KEY,
                Nombre VARCHAR(120) NOT NULL,
                Documento VARCHAR(30) UNIQUE,
                Telefono VARCHAR(30),
                Limite_Credito DECIMAL(12,2) DEFAULT 0,
                Saldo_Pendiente DECIMAL(12,2) DEFAULT 0,
                Puntos INT DEFAULT 0
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cliente_movimientos (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Cliente_Id INT NOT NULL,
                Tipo VARCHAR(20) NOT NULL,
                Venta_Id INT NULL,
                Monto DECIMAL(12,2) DEFAULT 0,
                Puntos INT DEFAULT 0,
                Fecha DATETIME,
                Usuario VARCHAR(80),
                Comentario VARCHAR(220)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS config_pos (
                Id INT PRIMARY KEY,
                Pesos_Por_Punto INT DEFAULT 1000,
                Valor_Punto DECIMAL(12,2) DEFAULT 50,
                Dias_Cobertura INT DEFAULT 15
            )
            """
        )
        cursor.execute("INSERT IGNORE INTO config_pos (Id, Pesos_Por_Punto, Valor_Punto, Dias_Cobertura) VALUES (1, 1000, 50, 15)")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS logs_auditoria (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Usuario VARCHAR(80),
                Fecha DATETIME,
                Accion VARCHAR(80),
                Detalle VARCHAR(255)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS producto_recetas (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Producto_Id INT NOT NULL,
                Insumo_Id INT NOT NULL,
                Cantidad DECIMAL(12,3) NOT NULL DEFAULT 1
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS lotes (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Producto_Id INT NOT NULL,
                Cantidad DECIMAL(12,3) NOT NULL DEFAULT 0,
                Fecha_Vencimiento DATE NULL,
                Fecha_Ingreso DATETIME,
                Lote VARCHAR(40),
                Proveedor VARCHAR(120)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS compras (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Numero_Factura VARCHAR(40) DEFAULT '',
                Proveedor VARCHAR(120) DEFAULT '',
                Fecha DATETIME,
                Usuario VARCHAR(80) DEFAULT '',
                Metodo_Pago VARCHAR(40) DEFAULT 'Efectivo',
                Monto_Pagado DECIMAL(12,2) DEFAULT 0,
                Saldo_Pendiente DECIMAL(12,2) DEFAULT 0,
                Subtotal DECIMAL(12,2) DEFAULT 0,
                Iva DECIMAL(12,2) DEFAULT 0,
                Total DECIMAL(12,2) DEFAULT 0,
                Estado VARCHAR(20) DEFAULT 'PAGADA'
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS compra_items (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Compra_Id INT NOT NULL,
                Producto_Id INT NULL,
                Nombre VARCHAR(160) NOT NULL,
                Cantidad DECIMAL(12,3) NOT NULL DEFAULT 1,
                Iva_Pct DECIMAL(5,2) DEFAULT 0,
                Iva_Incluido TINYINT DEFAULT 0,
                Precio_Ingresado DECIMAL(12,2) DEFAULT 0,
                Precio_Base DECIMAL(12,2) DEFAULT 0,
                Iva_Valor DECIMAL(12,2) DEFAULT 0,
                Total_Linea DECIMAL(12,2) DEFAULT 0,
                Precio_Venta DECIMAL(12,2) DEFAULT 0,
                Fecha_Vence DATE NULL,
                Presentacion_Id INT NULL,
                Presentacion_Nombre VARCHAR(80) DEFAULT '',
                Factor DECIMAL(14,6) DEFAULT 1,
                Cantidad_Base DECIMAL(14,6) DEFAULT 0
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS producto_presentaciones (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Producto_Id INT NOT NULL,
                Nombre VARCHAR(80) NOT NULL,
                Factor DECIMAL(14,6) NOT NULL DEFAULT 1,
                Unidad VARCHAR(40) DEFAULT '',
                Codigo_Barras VARCHAR(40) DEFAULT '',
                Precio_Venta DECIMAL(12,2) DEFAULT 0,
                Utilidad_Pct DECIMAL(7,2) DEFAULT 0,
                Permite_Venta TINYINT DEFAULT 1,
                Activo TINYINT DEFAULT 1,
                Es_Default TINYINT DEFAULT 0,
                INDEX idx_pres_prod (Producto_Id),
                INDEX idx_pres_barras (Codigo_Barras)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS inventario_movimientos (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Producto_Id INT,
                Presentacion_Id INT NULL,
                Tipo VARCHAR(20) NOT NULL,
                Cantidad_Presentacion DECIMAL(14,6) DEFAULT 0,
                Factor DECIMAL(14,6) DEFAULT 1,
                Cantidad_Base DECIMAL(14,6) DEFAULT 0,
                Motivo VARCHAR(220) DEFAULT '',
                Usuario VARCHAR(80) DEFAULT '',
                Fecha DATETIME
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS inventario_sesiones (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Nombre VARCHAR(160) NOT NULL,
                Filtro_Tipo VARCHAR(40) DEFAULT 'todos',
                Filtro_Valor VARCHAR(120) DEFAULT '',
                Modo VARCHAR(20) DEFAULT 'asistido',
                Estado VARCHAR(20) DEFAULT 'abierta',
                Total_Items INT DEFAULT 0,
                Contados INT DEFAULT 0,
                Usuario VARCHAR(80) DEFAULT '',
                Fecha_Inicio DATETIME,
                Fecha_Cierre DATETIME NULL,
                Notas VARCHAR(255) DEFAULT ''
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS inventario_sesion_items (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Sesion_Id INT NOT NULL,
                Producto_Id INT NOT NULL,
                Nombre VARCHAR(200) DEFAULT '',
                Categoria VARCHAR(80) DEFAULT '',
                Ubicacion VARCHAR(80) DEFAULT '',
                Unidad_Base VARCHAR(40) DEFAULT 'Unidad',
                Stock_Asignado DECIMAL(14,6) DEFAULT 0,
                Stock_Al_Contar DECIMAL(14,6) NULL,
                Cantidad_Fisica DECIMAL(14,6) NULL,
                Diferencia DECIMAL(14,6) NULL,
                Estado VARCHAR(20) DEFAULT 'pendiente',
                Fecha_Conteo DATETIME NULL,
                Usuario_Conteo VARCHAR(80) DEFAULT '',
                Ajustado TINYINT DEFAULT 0,
                INDEX idx_sesion_estado (Sesion_Id, Estado),
                INDEX idx_sesion_prod (Sesion_Id, Producto_Id)
            )
            """
        )
        try:
            cursor.execute(
                """INSERT INTO producto_presentaciones
                   (Producto_Id, Nombre, Factor, Unidad, Precio_Venta, Utilidad_Pct, Permite_Venta, Activo, Es_Default)
                   SELECT p.Id_Producto, 'Unidad', 1,
                          COALESCE(NULLIF(p.Unidad_Base, ''), 'Unidad'),
                          COALESCE(p.Precio_Venta, 0), 0, 1, 1, 1
                   FROM productos p
                   WHERE NOT EXISTS (
                       SELECT 1 FROM producto_presentaciones x WHERE x.Producto_Id = p.Id_Producto
                   )"""
            )
        except Exception as error:
            print("Aviso al migrar presentaciones: {}".format(error))
        cone.commit()
        return True
    except Exception as error:
        print("Error al actualizar el esquema: {}".format(error))
        try:
            cone.rollback()
        except Exception:
            pass
        return False
    finally:
        cursor.close()
        cone.close()


def datos_negocio():
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute("SELECT Nombre_negocio, direccion FROM registro_negocio LIMIT 1")
        row = cursor.fetchone()
        cone.close()
        if row:
            return {"nombre": row[0] or "Zyntra POS", "direccion": row[1] or ""}
    except Exception as error:
        print("Error al leer datos del negocio: {}".format(error))
    return {"nombre": "Zyntra POS", "direccion": ""}


def guardar_pagos_venta(id_venta, pagos):
    if not id_venta or not pagos:
        return False
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        for metodo, monto in pagos.items():
            try:
                valor = float(monto)
            except (TypeError, ValueError):
                continue
            if valor <= 0:
                continue
            cursor.execute(
                "INSERT INTO venta_pagos (Venta_Id, Metodo, Monto) VALUES (%s, %s, %s)",
                (id_venta, metodo, valor),
            )
        cone.commit()
        cone.close()
        return True
    except Exception as error:
        print("Error al guardar pagos de venta: {}".format(error))
        return False


# Medios de conciliación diaria. Claves internas BD → etiqueta UI.
# Transferencia histórica se agrupa en NEQUI (Bre-b / Nequi / Transferencia).
MEDIOS_CONCILIACION = (
    ("Efectivo", "EFECTIVO", ("Efectivo",)),
    ("Nequi", "NEQUI", ("Nequi", "Transferencia")),
    ("Tarjeta", "DATAFONO", ("Tarjeta",)),
)
MEDIOS_RECLASIFICABLES = ("Efectivo", "Nequi", "Transferencia", "Tarjeta", "Crédito")
ESTADOS_CIERRE = ("CUADRADO", "CUADRADO_CON_CORRECCIONES", "CON_DESCUADRE")


def _round2(valor):
    try:
        return round(float(valor or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def etiqueta_medio_conciliacion(metodo):
    metodo = str(metodo or "").strip()
    for clave, etiqueta, fuentes in MEDIOS_CONCILIACION:
        if metodo == clave or metodo in fuentes:
            return etiqueta
    return metodo.upper() if metodo else ""


def normalizar_metodo_pago(metodo):
    """Normaliza alias de UI a clave de BD (no elimina medios existentes)."""
    texto = str(metodo or "").strip()
    low = texto.lower()
    if low in ("efectivo",):
        return "Efectivo"
    if low in ("nequi", "bre-b", "breb", "daviplata", "bancolombia"):
        return "Nequi"
    if low in ("transferencia", "transfer", "bre-b / nequi / transferencia"):
        return "Transferencia"
    if low in ("tarjeta", "datafono", "datáfono", "tarjeta débito / crédito", "debito", "crédito tarjeta"):
        return "Tarjeta"
    if low in ("crédito", "credito", "fiado", "crédito / fiado"):
        return "Crédito"
    if low in ("puntos",):
        return "Puntos"
    return texto


def sumar_medios_conciliacion(metodos_raw):
    """Agrupa totales de venta_pagos en EFECTIVO / NEQUI / DATAFONO (+ otros)."""
    raw = {str(k): _round2(v) for k, v in (metodos_raw or {}).items()}
    out = {}
    usados = set()
    for clave, etiqueta, fuentes in MEDIOS_CONCILIACION:
        total = 0.0
        for f in fuentes:
            total += _round2(raw.get(f))
            usados.add(f)
        out[clave] = {
            "metodo": clave,
            "etiqueta": etiqueta,
            "sistema": _round2(total),
        }
    for metodo, monto in raw.items():
        if metodo in usados or metodo in ("Puntos",) or monto <= 0:
            continue
        out[metodo] = {
            "metodo": metodo,
            "etiqueta": str(metodo).upper(),
            "sistema": _round2(monto),
        }
    return out


def calcular_estado_cierre(diferencias, correcciones_count=0, tolerancia=0.5):
    hay_diff = any(abs(_round2(d)) >= tolerancia for d in (diferencias or []))
    if hay_diff:
        return "CON_DESCUADRE"
    if int(correcciones_count or 0) > 0:
        return "CUADRADO_CON_CORRECCIONES"
    return "CUADRADO"


def obtener_pagos_venta(id_venta):
    pagos = {}
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            "SELECT Metodo, COALESCE(SUM(Monto), 0) FROM venta_pagos WHERE Venta_Id=%s GROUP BY Metodo",
            (id_venta,),
        )
        for metodo, monto in cursor.fetchall() or []:
            pagos[str(metodo)] = _round2(monto)
        cone.close()
    except Exception as error:
        print("Error al leer pagos de venta: {}".format(error))
    return pagos


def obtener_total_venta(id_venta):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            "SELECT COALESCE(Total, 0), COALESCE(Anulada, 0) FROM ventas WHERE Id_Venta=%s",
            (id_venta,),
        )
        row = cursor.fetchone()
        cone.close()
        if not row:
            return None, True
        return _round2(row[0]), bool(int(row[1] or 0))
    except Exception as error:
        print("Error al leer total de venta: {}".format(error))
        return None, True


def listar_ventas_turno_pagos(fecha_desde, id_empleado=None, limite=80):
    """Ventas del turno con desglose de pagos (para reclasificación)."""
    out = []
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        sql = """
            SELECT v.Id_Venta, v.Fecha_Venta, COALESCE(v.Total, 0)
            FROM ventas v
            WHERE v.Fecha_Venta >= %s AND COALESCE(v.Anulada, 0) = 0
        """
        vals = [fecha_desde]
        if id_empleado is not None:
            sql += " AND v.Empleados_Id_Empleados = %s"
            vals.append(id_empleado)
        sql += " ORDER BY v.Fecha_Venta DESC, v.Id_Venta DESC LIMIT %s"
        vals.append(int(limite))
        cursor.execute(sql, tuple(vals))
        ventas = cursor.fetchall() or []
        for id_venta, fecha, total in ventas:
            cursor.execute(
                "SELECT Metodo, COALESCE(SUM(Monto), 0) FROM venta_pagos WHERE Venta_Id=%s GROUP BY Metodo",
                (id_venta,),
            )
            pagos = {str(m): _round2(monto) for m, monto in (cursor.fetchall() or [])}
            out.append(
                {
                    "id_venta": int(id_venta),
                    "fecha": str(fecha),
                    "total": _round2(total),
                    "pagos": pagos,
                }
            )
        cone.close()
    except Exception as error:
        print("Error al listar ventas del turno: {}".format(error))
    return out


_ETIQUETA_PAGO_TICKET = {
    "Efectivo": "Efectivo",
    "Transferencia": "Transferencia",
    "Nequi": "Nequi",
    "Tarjeta": "Tarjeta",
    "Crédito": "Crédito",
    "Puntos": "Puntos",
}


def listar_ventas_cajero(id_empleado=None, usuario=None, fecha_desde=None, fecha_hasta=None, limite=200):
    """Historial de ventas del cajero actual (incluye anuladas marcadas)."""
    out = []
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        sql = """
            SELECT v.Id_Venta, v.Fecha_Venta, COALESCE(v.Total, 0),
                   COALESCE(v.Anulada, 0), COALESCE(v.Estado, '')
            FROM ventas v
            WHERE 1=1
        """
        vals = []
        if id_empleado is not None:
            sql += " AND v.Empleados_Id_Empleados = %s"
            vals.append(id_empleado)
        if fecha_desde:
            sql += " AND v.Fecha_Venta >= %s"
            vals.append(fecha_desde)
        if fecha_hasta:
            sql += " AND v.Fecha_Venta <= %s"
            vals.append(fecha_hasta)
        sql += " ORDER BY v.Fecha_Venta DESC, v.Id_Venta DESC LIMIT %s"
        vals.append(int(limite))
        cursor.execute(sql, tuple(vals))
        for row in cursor.fetchall() or []:
            id_venta = int(row[0])
            anulada = int(row[3] or 0) == 1
            estado = str(row[4] or "")
            if anulada or "ANUL" in estado.upper():
                estado_txt = "ANULADA"
            else:
                estado_txt = "ACTIVA"
            cursor.execute(
                "SELECT Metodo, COALESCE(SUM(Monto), 0) FROM venta_pagos WHERE Venta_Id=%s GROUP BY Metodo",
                (id_venta,),
            )
            pagos = {str(m): _round2(monto) for m, monto in (cursor.fetchall() or [])}
            try:
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(COALESCE(NULLIF(Cantidad_Presentacion, 0), Cantidad)), 0)
                    FROM productos_has_ventas WHERE Ventas_Id_Factura=%s
                    """,
                    (id_venta,),
                )
                articulos = float((cursor.fetchone() or [0])[0] or 0)
            except Exception:
                try:
                    cursor.execute(
                        "SELECT COALESCE(SUM(Cantidad), 0) FROM productos_has_ventas WHERE Ventas_Id_Factura=%s",
                        (id_venta,),
                    )
                    articulos = float((cursor.fetchone() or [0])[0] or 0)
                except Exception:
                    articulos = 0
            out.append(
                {
                    "id_venta": id_venta,
                    "fecha": str(row[1]),
                    "total": _round2(row[2]),
                    "anulada": anulada,
                    "estado": estado_txt,
                    "pagos": pagos,
                    "articulos": articulos,
                }
            )
        cone.close()
    except Exception as error:
        print("Error al listar ventas del cajero: {}".format(error))
    return out


def construir_info_ticket_venta(id_venta):
    """Arma el dict de ticket desde BD para reimpresión (sin datos administrativos internos)."""
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            """
            SELECT v.Id_Venta, v.Fecha_Venta, COALESCE(v.Total, 0),
                   COALESCE(v.Anulada, 0), COALESCE(v.Cliente_Id, NULL),
                   COALESCE(e.Nombres, '')
            FROM ventas v
            LEFT JOIN empleados e ON e.Id_Empleados = v.Empleados_Id_Empleados
            WHERE v.Id_Venta = %s
            """,
            (id_venta,),
        )
        row = cursor.fetchone()
        if not row:
            # fallback sin join empleados
            cursor.execute(
                "SELECT Id_Venta, Fecha_Venta, COALESCE(Total, 0), COALESCE(Anulada, 0), NULL, '' FROM ventas WHERE Id_Venta=%s",
                (id_venta,),
            )
            row = cursor.fetchone()
        cone.close()
        if not row:
            return None
    except Exception as error:
        print("Error al leer venta para ticket: {}".format(error))
        return None

    idv = int(row[0])
    total = _round2(row[2])
    lineas = detalle_lineas_venta(idv)
    productos = []
    for ln in lineas:
        if ln.get("devuelto"):
            continue
        cant = float(ln.get("cantidad") or 0)
        sub = float(ln.get("subtotal") or 0)
        precio = (sub / cant) if cant else 0
        productos.append(
            {
                "codigo": ln.get("producto_id"),
                "nombre": ln.get("producto") or "Producto",
                "presentacion": ln.get("presentacion") or "Unidad",
                "cantidad": cant,
                "cantidad_presentacion": cant,
                "subtotal": sub,
                "precio": round(precio, 2),
            }
        )
    pagos = obtener_pagos_venta(idv)
    pagos_ticket = {}
    for metodo, monto in (pagos or {}).items():
        if float(monto or 0) <= 0:
            continue
        etiqueta = _ETIQUETA_PAGO_TICKET.get(metodo, metodo)
        pagos_ticket[etiqueta] = float(monto)

    cliente = None
    cliente_id = row[4]
    if cliente_id:
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            cursor.execute(
                "SELECT Nombre FROM clientes WHERE Id_Cliente=%s OR Id_cliente=%s LIMIT 1",
                (cliente_id, cliente_id),
            )
            crow = cursor.fetchone()
            cone.close()
            if crow:
                cliente = {"id": cliente_id, "nombre": crow[0]}
        except Exception:
            try:
                cone = FormularioLogin.conexion_base_de_datos()
                cursor = cone.cursor()
                cursor.execute("SELECT Nombre FROM clientes WHERE Id_Cliente=%s LIMIT 1", (cliente_id,))
                crow = cursor.fetchone()
                cone.close()
                if crow:
                    cliente = {"id": cliente_id, "nombre": crow[0]}
            except Exception:
                pass

    return {
        "id_venta": idv,
        "fecha": str(row[1]),
        "total": total,
        "productos": productos,
        "pagos": pagos,
        "pagos_ticket": pagos_ticket,
        "cambio": 0,
        "cliente": cliente,
        "cajero": row[5] or "",
        "anulada": int(row[3] or 0) == 1,
        # Sin campos administrativos en reimpresión al cliente
        "aplica_recargo": False,
        "total_base": None,
        "pct_recargo": 0,
    }


def contar_correcciones_turno(fecha_desde, usuario=None):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        sql = "SELECT COUNT(*) FROM venta_pago_correcciones WHERE Fecha >= %s"
        vals = [fecha_desde]
        if usuario:
            sql += " AND Usuario = %s"
            vals.append(usuario)
        cursor.execute(sql, tuple(vals))
        n = int((cursor.fetchone() or [0])[0] or 0)
        cone.close()
        return n
    except Exception:
        return 0


def reclasificar_pago_venta(
    id_venta,
    metodo_origen,
    metodo_destino,
    monto,
    usuario,
    motivo,
    cierre_id=None,
):
    """
    Mueve monto entre medios de una venta sin alterar ventas.Total.
    La suma de venta_pagos debe seguir igual al total de la venta.
    """
    id_venta = int(id_venta)
    origen = normalizar_metodo_pago(metodo_origen)
    destino = normalizar_metodo_pago(metodo_destino)
    monto = _round2(monto)
    motivo = str(motivo or "").strip()
    if origen == destino:
        return False, "El medio origen y destino son iguales"
    if monto <= 0:
        return False, "El monto a reclasificar debe ser mayor a 0"
    if not motivo:
        return False, "El motivo de la corrección es obligatorio"
    if destino not in MEDIOS_RECLASIFICABLES and destino not in METODOS_PAGO:
        return False, "Medio de pago destino no permitido"
    total, anulada = obtener_total_venta(id_venta)
    if total is None:
        return False, "Venta no encontrada"
    if anulada:
        return False, "No se puede reclasificar una venta anulada"

    cone = FormularioLogin.conexion_base_de_datos()
    cursor = cone.cursor()
    try:
        cursor.execute(
            "SELECT Id, Metodo, Monto FROM venta_pagos WHERE Venta_Id=%s ORDER BY Id",
            (id_venta,),
        )
        filas = list(cursor.fetchall() or [])
        disponible = _round2(sum(_round2(m) for _i, met, m in filas if str(met) == origen))
        if disponible + 0.009 < monto:
            return False, "El medio {} solo tiene {}".format(origen, disponible)

        restante = monto
        for pid, met, mon in filas:
            if str(met) != origen or restante <= 0:
                continue
            mon = _round2(mon)
            if mon <= restante + 0.009:
                cursor.execute("DELETE FROM venta_pagos WHERE Id=%s", (pid,))
                restante = _round2(restante - mon)
            else:
                cursor.execute(
                    "UPDATE venta_pagos SET Monto=%s WHERE Id=%s",
                    (_round2(mon - restante), pid),
                )
                restante = 0.0

        # Sumar al destino (consolidar fila existente si hay)
        cursor.execute(
            "SELECT Id, Monto FROM venta_pagos WHERE Venta_Id=%s AND Metodo=%s ORDER BY Id LIMIT 1",
            (id_venta, destino),
        )
        dest = cursor.fetchone()
        if dest:
            cursor.execute(
                "UPDATE venta_pagos SET Monto=%s WHERE Id=%s",
                (_round2(_round2(dest[1]) + monto), dest[0]),
            )
        else:
            cursor.execute(
                "INSERT INTO venta_pagos (Venta_Id, Metodo, Monto) VALUES (%s, %s, %s)",
                (id_venta, destino, monto),
            )

        cursor.execute(
            "SELECT COALESCE(SUM(Monto), 0) FROM venta_pagos WHERE Venta_Id=%s",
            (id_venta,),
        )
        suma = _round2((cursor.fetchone() or [0])[0])
        if abs(suma - total) > 0.05:
            cone.rollback()
            return False, "La suma de pagos ({}) no coincide con el total de la venta ({})".format(
                suma, total
            )

        # Nunca tocar ventas.Total
        cursor.execute(
            """
            INSERT INTO venta_pago_correcciones
                (Venta_Id, Metodo_Anterior, Metodo_Nuevo, Monto, Motivo, Usuario, Fecha, Cierre_Id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                id_venta,
                origen,
                destino,
                monto,
                motivo[:250],
                (usuario or "")[:80],
                datetime.now(),
                cierre_id,
            ),
        )
        cone.commit()
        try:
            registrar_auditoria(
                usuario or "",
                "Reclasificación pago",
                "Venta #{} {} → {} por {}".format(id_venta, origen, destino, monto),
            )
        except Exception:
            pass
        try:
            from bolsillo_proveedores_svc import sincronizar_correccion_venta_si_consolidado

            sincronizar_correccion_venta_si_consolidado(
                id_venta, origen, destino, monto, usuario, motivo
            )
        except Exception as sync_err:
            print("Aviso sync bolsillo proveedores: {}".format(sync_err))
        return True, "Pago reclasificado correctamente"
    except Exception as error:
        try:
            cone.rollback()
        except Exception:
            pass
        print("Error al reclasificar pago: {}".format(error))
        return False, "Error al reclasificar: {}".format(error)
    finally:
        try:
            cursor.close()
            cone.close()
        except Exception:
            pass


def vincular_correcciones_a_cierre(cierre_id, fecha_desde, usuario=None):
    if not cierre_id:
        return 0
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        sql = """
            UPDATE venta_pago_correcciones
            SET Cierre_Id=%s
            WHERE Cierre_Id IS NULL AND Fecha >= %s
        """
        vals = [cierre_id, fecha_desde]
        if usuario:
            sql += " AND Usuario=%s"
            vals.append(usuario)
        cursor.execute(sql, tuple(vals))
        n = cursor.rowcount or 0
        cone.commit()
        cone.close()
        return int(n)
    except Exception as error:
        print("Error al vincular correcciones: {}".format(error))
        return 0


def listar_correcciones_cierre(cierre_id=None, fecha_desde=None, limite=100):
    out = []
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        sql = """
            SELECT Id, Venta_Id, Metodo_Anterior, Metodo_Nuevo, Monto, Motivo, Usuario, Fecha, Cierre_Id
            FROM venta_pago_correcciones WHERE 1=1
        """
        vals = []
        if cierre_id:
            sql += " AND Cierre_Id=%s"
            vals.append(cierre_id)
        if fecha_desde:
            sql += " AND Fecha >= %s"
            vals.append(fecha_desde)
        sql += " ORDER BY Fecha DESC, Id DESC LIMIT %s"
        vals.append(int(limite))
        cursor.execute(sql, tuple(vals))
        for row in cursor.fetchall() or []:
            out.append(
                {
                    "id": row[0],
                    "venta_id": row[1],
                    "metodo_anterior": row[2],
                    "metodo_nuevo": row[3],
                    "monto": _round2(row[4]),
                    "motivo": row[5] or "",
                    "usuario": row[6] or "",
                    "fecha": str(row[7]),
                    "cierre_id": row[8],
                }
            )
        cone.close()
    except Exception as error:
        print("Error al listar correcciones: {}".format(error))
    return out


def resumen_conciliacion_turno(fecha_desde, id_empleado=None, usuario=None, nombre_empleado=None):
    """Totales de sistema por medio + extras de caja (efectivo esperado)."""
    metodos, total_ventas, tickets, articulos = totales_pagos_desde(fecha_desde, id_empleado)
    agrupados = sumar_medios_conciliacion(metodos)
    entradas, salidas = totales_movimientos_desde(fecha_desde, usuario, nombre_empleado)
    abonos_efectivo, abonos_otros = totales_abonos_desde(fecha_desde, usuario, nombre_empleado)
    overlap = totales_entradas_abono_cxc(fecha_desde, usuario, nombre_empleado)
    entradas_otras = max(entradas - overlap, 0)
    # Efectivo sistema del arqueo = ventas efectivo + abonos + entradas - salidas
    ef = agrupados.get("Efectivo", {"metodo": "Efectivo", "etiqueta": "EFECTIVO", "sistema": 0.0})
    ef_ventas = _round2(ef.get("sistema"))
    ef_caja = _round2(ef_ventas + abonos_efectivo + entradas_otras - salidas)
    ef["sistema_ventas"] = ef_ventas
    ef["sistema"] = ef_caja
    ef["abonos"] = _round2(abonos_efectivo)
    ef["entradas"] = _round2(entradas_otras)
    ef["salidas"] = _round2(salidas)
    agrupados["Efectivo"] = ef
    # Abonos digitales se suman a Nequi si no hay desglose fino
    if abonos_otros > 0 and "Nequi" in agrupados:
        agrupados["Nequi"]["sistema"] = _round2(agrupados["Nequi"]["sistema"] + abonos_otros)
        agrupados["Nequi"]["abonos_otros"] = _round2(abonos_otros)
    nequi_raw = _round2(metodos.get("Nequi"))
    transfer_raw = _round2(metodos.get("Transferencia"))
    return {
        "medios": agrupados,
        "metodos_raw": {k: _round2(v) for k, v in metodos.items()},
        "total_ventas": _round2(total_ventas),
        "tickets": int(tickets),
        "articulos": int(articulos),
        "nequi_detalle": {"Nequi": nequi_raw, "Transferencia": transfer_raw},
        "credito": _round2(metodos.get("Crédito")),
        "abonos_efectivo": _round2(abonos_efectivo),
        "abonos_otros": _round2(abonos_otros),
        "entradas": _round2(entradas_otras),
        "salidas": _round2(salidas),
        "correcciones": contar_correcciones_turno(fecha_desde, usuario),
    }


def guardar_cierre_turno(datos):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        tipo = str(datos.get("tipo") or "definitivo")[:20]
        efectivo_retirar = float(datos.get("efectivo_retirar") or datos.get("Efectivo") or 0)
        base_dejada = float(datos.get("base_dejada") or datos.get("monto_inicial") or 0)
        estado = str(datos.get("estado") or "")[:40]
        observacion = str(datos.get("observacion") or "")[:2000]
        correcciones = int(datos.get("correcciones") or 0)
        fecha_desde = datos.get("inicio") or datos.get("fecha_desde")
        usuario = datos.get("usuario") or ""
        try:
            sql = (
                "INSERT INTO cierre_turno (Cajero, Fecha, Monto_Inicial, Conteo_Fisico, Esperado, Descuadre, "
                "Total_Ventas, Efectivo, Nequi, Tarjeta, Transferencia, Entradas, Salidas, "
                "Tipo, Efectivo_Retirar, Base_Dejada, Estado, Observacion, Correcciones, Fecha_Desde, Usuario, "
                "Tickets, Ticket_Impreso, Linea_Tiempo) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            )
            valores = (
                datos.get("cajero"),
                datos.get("fecha"),
                datos.get("monto_inicial", 0),
                datos.get("conteo_fisico", 0),
                datos.get("esperado", 0),
                datos.get("descuadre", 0),
                datos.get("total_ventas", 0),
                datos.get("Efectivo", 0),
                datos.get("Nequi", 0),
                datos.get("Tarjeta", 0),
                datos.get("Transferencia", 0),
                datos.get("entradas", 0) + datos.get("abonos", 0),
                datos.get("salidas", 0),
                tipo,
                efectivo_retirar,
                base_dejada,
                estado,
                observacion,
                correcciones,
                fecha_desde,
                usuario,
                int(datos.get("tickets") or 0),
                1 if datos.get("ticket_impreso") else 0,
                str(datos.get("linea_tiempo_json") or "")[:4000] or None,
            )
            cursor.execute(sql, valores)
        except Exception:
            try:
                sql = (
                    "INSERT INTO cierre_turno (Cajero, Fecha, Monto_Inicial, Conteo_Fisico, Esperado, Descuadre, "
                    "Total_Ventas, Efectivo, Nequi, Tarjeta, Transferencia, Entradas, Salidas, "
                    "Tipo, Efectivo_Retirar, Base_Dejada, Estado, Observacion, Correcciones, Fecha_Desde, Usuario, "
                    "Tickets, Ticket_Impreso) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                )
                valores = (
                    datos.get("cajero"),
                    datos.get("fecha"),
                    datos.get("monto_inicial", 0),
                    datos.get("conteo_fisico", 0),
                    datos.get("esperado", 0),
                    datos.get("descuadre", 0),
                    datos.get("total_ventas", 0),
                    datos.get("Efectivo", 0),
                    datos.get("Nequi", 0),
                    datos.get("Tarjeta", 0),
                    datos.get("Transferencia", 0),
                    datos.get("entradas", 0) + datos.get("abonos", 0),
                    datos.get("salidas", 0),
                    tipo,
                    efectivo_retirar,
                    base_dejada,
                    estado,
                    observacion,
                    correcciones,
                    fecha_desde,
                    usuario,
                    int(datos.get("tickets") or 0),
                    1 if datos.get("ticket_impreso") else 0,
                )
                cursor.execute(sql, valores)
            except Exception:
                try:
                    sql = (
                        "INSERT INTO cierre_turno (Cajero, Fecha, Monto_Inicial, Conteo_Fisico, Esperado, Descuadre, "
                        "Total_Ventas, Efectivo, Nequi, Tarjeta, Transferencia, Entradas, Salidas, "
                        "Tipo, Efectivo_Retirar, Base_Dejada, Estado, Observacion, Correcciones, Fecha_Desde, Usuario) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    )
                    valores = (
                        datos.get("cajero"),
                        datos.get("fecha"),
                        datos.get("monto_inicial", 0),
                        datos.get("conteo_fisico", 0),
                        datos.get("esperado", 0),
                        datos.get("descuadre", 0),
                        datos.get("total_ventas", 0),
                        datos.get("Efectivo", 0),
                        datos.get("Nequi", 0),
                        datos.get("Tarjeta", 0),
                        datos.get("Transferencia", 0),
                        datos.get("entradas", 0) + datos.get("abonos", 0),
                        datos.get("salidas", 0),
                        tipo,
                        efectivo_retirar,
                        base_dejada,
                        estado,
                        observacion,
                        correcciones,
                        fecha_desde,
                        usuario,
                    )
                    cursor.execute(sql, valores)
                except Exception:
                    try:
                        sql = (
                            "INSERT INTO cierre_turno (Cajero, Fecha, Monto_Inicial, Conteo_Fisico, Esperado, Descuadre, "
                            "Total_Ventas, Efectivo, Nequi, Tarjeta, Transferencia, Entradas, Salidas, "
                            "Tipo, Efectivo_Retirar, Base_Dejada) "
                            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                        )
                        valores = (
                            datos.get("cajero"),
                            datos.get("fecha"),
                            datos.get("monto_inicial", 0),
                            datos.get("conteo_fisico", 0),
                            datos.get("esperado", 0),
                            datos.get("descuadre", 0),
                            datos.get("total_ventas", 0),
                            datos.get("Efectivo", 0),
                            datos.get("Nequi", 0),
                            datos.get("Tarjeta", 0),
                            datos.get("Transferencia", 0),
                            datos.get("entradas", 0) + datos.get("abonos", 0),
                            datos.get("salidas", 0),
                            tipo,
                            efectivo_retirar,
                            base_dejada,
                        )
                        cursor.execute(sql, valores)
                    except Exception:
                        sql = (
                            "INSERT INTO cierre_turno (Cajero, Fecha, Monto_Inicial, Conteo_Fisico, Esperado, Descuadre, "
                            "Total_Ventas, Efectivo, Nequi, Tarjeta, Transferencia, Entradas, Salidas) "
                            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                        )
                        valores = (
                            datos.get("cajero"),
                            datos.get("fecha"),
                            datos.get("monto_inicial", 0),
                            datos.get("conteo_fisico", 0),
                            datos.get("esperado", 0),
                            datos.get("descuadre", 0),
                            datos.get("total_ventas", 0),
                            datos.get("Efectivo", 0),
                            datos.get("Nequi", 0),
                            datos.get("Tarjeta", 0),
                            datos.get("Transferencia", 0),
                            datos.get("entradas", 0) + datos.get("abonos", 0),
                            datos.get("salidas", 0),
                        )
                        cursor.execute(sql, valores)
        cierre_id = cursor.lastrowid

        for linea in datos.get("medios_conciliacion") or []:
            try:
                cursor.execute(
                    """
                    INSERT INTO cierre_turno_medios
                        (Cierre_Id, Metodo, Etiqueta, Sistema, Declarado, Diferencia)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        cierre_id,
                        str(linea.get("metodo") or "")[:40],
                        str(linea.get("etiqueta") or "")[:60],
                        _round2(linea.get("sistema")),
                        _round2(linea.get("declarado")),
                        _round2(linea.get("diferencia")),
                    ),
                )
            except Exception as error:
                print("Aviso medio cierre: {}".format(error))

        cone.commit()
        cone.close()

        if fecha_desde:
            vincular_correcciones_a_cierre(cierre_id, fecha_desde, usuario)

        if tipo != "temporal":
            try:
                # Conserva distribución existente (entrega bolsillos = futura)
                if "pct_proveedores" not in datos:
                    try:
                        cfg = obtener_config_pos()
                        datos["pct_proveedores"] = cfg.get("pct_proveedores", 65)
                        datos["pct_provisiones"] = cfg.get("pct_provisiones", 17)
                        datos["pct_utilidad"] = cfg.get("pct_utilidad", 18)
                    except Exception:
                        pass
                aplicar_distribucion_cierre(cierre_id, datos)
            except Exception as error:
                print("Error al distribuir bolsillos del cierre: {}".format(error))
        try:
            registrar_auditoria(
                usuario or datos.get("cajero") or "",
                "Cierre diario",
                "Cierre #{} estado={} descuadre={}".format(
                    cierre_id, estado or "-", datos.get("descuadre", 0)
                ),
            )
        except Exception:
            pass
        return cierre_id or True
    except Exception as error:
        print("Error al guardar cierre de turno: {}".format(error))
        return False


def marcar_ticket_cierre_impreso(cierre_id, impreso=True):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        try:
            cursor.execute(
                "UPDATE cierre_turno SET Ticket_Impreso=%s WHERE Id=%s",
                (1 if impreso else 0, int(cierre_id)),
            )
        except Exception:
            cone.close()
            return False
        cone.commit()
        cone.close()
        return True
    except Exception as error:
        print("Error marcar ticket cierre: {}".format(error))
        return False


def listar_cierres_ticket_pendiente(usuario=None, es_admin=False, limite=40):
    """Cierres definitivos sin ticket impreso. Admin ve todos; vendedor solo los suyos."""
    out = []
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        try:
            sql = """
                SELECT Id, Cajero, Fecha, Total_Ventas, Estado, Usuario, Correcciones,
                       COALESCE(Tickets, 0), COALESCE(Ticket_Impreso, 0), COALESCE(Tipo, 'definitivo')
                FROM cierre_turno
                WHERE COALESCE(Ticket_Impreso, 0)=0
                  AND COALESCE(Tipo, 'definitivo') <> 'temporal'
            """
            vals = []
            if not es_admin:
                sql += " AND (LOWER(Usuario)=LOWER(%s) OR LOWER(Cajero)=LOWER(%s))"
                vals.extend([str(usuario or "").strip(), str(usuario or "").strip()])
            sql += " ORDER BY Id DESC LIMIT %s"
            vals.append(int(limite))
            cursor.execute(sql, tuple(vals))
            for row in cursor.fetchall() or []:
                out.append(
                    {
                        "id": int(row[0]),
                        "cajero": row[1] or "",
                        "fecha": str(row[2] or ""),
                        "total_ventas": _round2(row[3]),
                        "estado": row[4] or "",
                        "usuario": row[5] or "",
                        "correcciones": int(row[6] or 0),
                        "tickets": int(row[7] or 0),
                        "ticket_impreso": int(row[8] or 0),
                        "tipo": row[9] or "definitivo",
                    }
                )
        except Exception as error:
            print("Aviso listar tickets pendientes: {}".format(error))
        cone.close()
    except Exception as error:
        print("Error listar tickets pendientes: {}".format(error))
    return out


def construir_datos_ticket_cierre(cierre_id):
    """Arma el dict para reimprimir el ticket de un cierre guardado."""
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute("SELECT * FROM cierre_turno WHERE Id=%s", (int(cierre_id),))
        raw = cursor.fetchone()
        if not raw:
            cone.close()
            return None
        cols = [d[0] for d in cursor.description]
        ct = dict(zip(cols, raw))
        medios = []
        try:
            cursor.execute(
                """
                SELECT Metodo, Etiqueta, Sistema, Declarado, Diferencia
                FROM cierre_turno_medios WHERE Cierre_Id=%s
                """,
                (int(cierre_id),),
            )
            for m, e, s, d, diff in cursor.fetchall() or []:
                medios.append(
                    {
                        "metodo": m,
                        "etiqueta": e or m,
                        "sistema": _round2(s),
                        "declarado": _round2(d),
                        "diferencia": _round2(diff),
                    }
                )
        except Exception:
            pass
        cone.close()
        correcciones = []
        try:
            correcciones = listar_correcciones_cierre(cierre_id=int(cierre_id), limite=50)
        except Exception:
            pass
        if not medios:
            medios = [
                {
                    "metodo": "Efectivo",
                    "etiqueta": "EFECTIVO",
                    "sistema": _round2(ct.get("Esperado")),
                    "declarado": _round2(ct.get("Efectivo") or ct.get("Conteo_Fisico")),
                    "diferencia": _round2(ct.get("Descuadre")),
                },
                {
                    "metodo": "Nequi",
                    "etiqueta": "NEQUI",
                    "sistema": _round2(ct.get("Nequi")) + _round2(ct.get("Transferencia")),
                    "declarado": _round2(ct.get("Nequi")) + _round2(ct.get("Transferencia")),
                    "diferencia": 0,
                },
                {
                    "metodo": "Tarjeta",
                    "etiqueta": "DATAFONO",
                    "sistema": _round2(ct.get("Tarjeta")),
                    "declarado": _round2(ct.get("Tarjeta")),
                    "diferencia": 0,
                },
            ]
        out = {
            "cierre_id": int(cierre_id),
            "id": int(cierre_id),
            "cajero": ct.get("Cajero") or "",
            "usuario": ct.get("Usuario") or ct.get("Cajero") or "",
            "fecha": str(ct.get("Fecha") or ""),
            "total_ventas": _round2(ct.get("Total_Ventas")),
            "tickets": int(ct.get("Tickets") or 0),
            "estado": ct.get("Estado") or "",
            "observacion": ct.get("Observacion") or "",
            "correcciones": int(ct.get("Correcciones") or len(correcciones) or 0),
            "lista_correcciones": correcciones,
            "medios_conciliacion": medios,
            "Efectivo": _round2(ct.get("Efectivo")),
            "Nequi": _round2(ct.get("Nequi")),
            "Tarjeta": _round2(ct.get("Tarjeta")),
            "tipo": ct.get("Tipo") or "definitivo",
            "inicio": str(ct.get("Fecha_Desde") or ""),
            "linea_tiempo": [],
        }
        # Horarios: JSON guardado o reconstrucción del día
        try:
            from turno_linea_tiempo import (
                linea_tiempo_desde_json,
                reconstruir_linea_tiempo_dia,
            )

            eventos = linea_tiempo_desde_json(ct.get("Linea_Tiempo") or "")
            if not eventos:
                eventos = reconstruir_linea_tiempo_dia(
                    ct.get("Usuario") or ct.get("Cajero") or "",
                    hasta_id=int(cierre_id),
                )
            out["linea_tiempo"] = eventos
        except Exception:
            out["linea_tiempo"] = []
        return out
    except Exception as error:
        print("Error construir ticket cierre: {}".format(error))
        return None


def _id_bolsillo_codigo(cursor, codigo):
    try:
        cursor.execute(
            "SELECT Id FROM bolsillos WHERE UPPER(Codigo)=%s AND Activo=1 ORDER BY Id LIMIT 1",
            (codigo.upper(),),
        )
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception:
        return None


def aplicar_distribucion_cierre(cierre_id, datos):
    pct_p = float(datos.get("pct_proveedores") or 65)
    pct_r = float(datos.get("pct_provisiones") or 17)
    pct_u = float(datos.get("pct_utilidad") or 18)
    total_pct = pct_p + pct_r + pct_u
    if total_pct <= 0:
        return False
    pct_p = pct_p * 100.0 / total_pct
    pct_r = pct_r * 100.0 / total_pct
    pct_u = pct_u * 100.0 / total_pct
    medios = {
        "Efectivo": float(datos.get("Efectivo") or 0),
        "Nequi": float(datos.get("Nequi") or 0),
        "Tarjeta": float(datos.get("Tarjeta") or 0),
        "Transferencia": float(datos.get("Transferencia") or 0),
    }
    cone = FormularioLogin.conexion_base_de_datos()
    cursor = cone.cursor()
    ids = {
        "PROVEEDORES": _id_bolsillo_codigo(cursor, "PROVEEDORES"),
        "PROVISIONES": _id_bolsillo_codigo(cursor, "PROVISIONES"),
        "UTILIDAD": _id_bolsillo_codigo(cursor, "UTILIDAD"),
    }
    # Entrega 4: PROVEEDORES ya no se alimenta con el % del cierre diario.
    # El bolsillo de proveedores se acredita al consolidar el cierre general
    # (Nequi + Datafono + efectivo sobrante tras provisión admin).
    partes = {"PROVEEDORES": 0.0, "PROVISIONES": 0.0, "UTILIDAD": 0.0}
    lineas = []
    for metodo, monto in medios.items():
        m_r = round(monto * pct_r / 100.0, 2)
        m_u = round(monto * pct_u / 100.0, 2)
        partes["PROVISIONES"] += m_r
        partes["UTILIDAD"] += m_u
        lineas.append(("PROVISIONES", metodo, m_r))
        lineas.append(("UTILIDAD", metodo, m_u))
    cursor.execute(
        """
        INSERT INTO cierre_diario_asignacion
            (Cierre_Turno_Id, Fecha, Cajero, Pct_Proveedores, Pct_Provisiones, Pct_Utilidad,
             Recaudo_Efectivo, Recaudo_Nequi, Recaudo_Tarjeta, Recaudo_Transferencia,
             Monto_Proveedores, Monto_Provisiones, Monto_Utilidad)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            cierre_id,
            datos.get("fecha"),
            datos.get("cajero") or "",
            0.0,
            round(pct_r, 2),
            round(pct_u, 2),
            medios["Efectivo"],
            medios["Nequi"],
            medios["Tarjeta"],
            medios["Transferencia"],
            0.0,
            round(partes["PROVISIONES"], 2),
            round(partes["UTILIDAD"], 2),
        ),
    )
    ahora = datetime.now()
    for codigo, metodo, monto in lineas:
        bid = ids.get(codigo)
        if not bid or monto <= 0:
            continue
        cursor.execute(
            """
            INSERT INTO bolsillo_movimientos
                (Bolsillo_Id, Tipo, Monto, Nota, Fecha, Metodo, Categoria, Usuario, Cierre_Id)
            VALUES (%s, 'INGRESO', %s, %s, %s, %s, 'CIERRE', %s, %s)
            """,
            (
                bid,
                monto,
                "Cierre diario {}".format(codigo.title()),
                ahora,
                metodo,
                datos.get("cajero") or datos.get("usuario") or "",
                cierre_id,
            ),
        )
    try:
        cursor.execute(
            """UPDATE config_pos SET Pct_Proveedores=%s, Pct_Provisiones=%s, Pct_Utilidad=%s WHERE Id=1""",
            (round(pct_p, 2), round(pct_r, 2), round(pct_u, 2)),
        )
    except Exception:
        pass
    cone.commit()
    cone.close()
    return True


def totales_movimientos_desde(fecha_desde, cajero=None, nombre_empleado=None):
    entradas = 0.0
    salidas = 0.0
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        if cajero or nombre_empleado:
            cursor.execute(
                """SELECT COALESCE(SUM(Cantidad), 0) FROM entrada_dinero
                   WHERE Fecha >= %s AND (Cajero = %s OR Cajero = %s)""",
                (fecha_desde, cajero or "", nombre_empleado or ""),
            )
            entradas = float(cursor.fetchone()[0] or 0)
            cursor.execute(
                """SELECT COALESCE(SUM(Cantidad), 0) FROM salida_dinero
                   WHERE Fecha >= %s AND (Cajero = %s OR Cajero = %s)""",
                (fecha_desde, cajero or "", nombre_empleado or ""),
            )
            salidas = float(cursor.fetchone()[0] or 0)
        else:
            cursor.execute("SELECT COALESCE(SUM(Cantidad), 0) FROM entrada_dinero WHERE Fecha >= %s", (fecha_desde,))
            entradas = float(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT COALESCE(SUM(Cantidad), 0) FROM salida_dinero WHERE Fecha >= %s", (fecha_desde,))
            salidas = float(cursor.fetchone()[0] or 0)
        cone.close()
    except Exception as error:
        print("Error al totalizar movimientos de caja: {}".format(error))
    return entradas, salidas


def totales_abonos_desde(fecha_desde, cajero=None, nombre_empleado=None):
    efectivo = 0.0
    otros = 0.0
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        sql = """
            SELECT COALESCE(Comentario, ''), COALESCE(SUM(Monto), 0)
            FROM cliente_movimientos
            WHERE Tipo='ABONO' AND Fecha >= %s
        """
        args = [fecha_desde]
        if cajero or nombre_empleado:
            sql += " AND (Usuario = %s OR Usuario = %s)"
            args.extend([cajero or "", nombre_empleado or ""])
        sql += " GROUP BY Comentario"
        cursor.execute(sql, tuple(args))
        for comentario, monto in cursor.fetchall() or []:
            texto = str(comentario or "").lower()
            if "nequi" in texto or "tarjeta" in texto or "transferencia" in texto:
                otros += float(monto or 0)
            else:
                efectivo += float(monto or 0)
        cone.close()
    except Exception as error:
        print("Error al totalizar abonos: {}".format(error))
    return efectivo, otros


def totales_entradas_abono_cxc(fecha_desde, cajero=None, nombre_empleado=None):
    total = 0.0
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        sql = """
            SELECT COALESCE(SUM(Cantidad), 0) FROM entrada_dinero
            WHERE Fecha >= %s AND Asunto LIKE %s
        """
        args = [fecha_desde, "Abono CxC%"]
        if cajero or nombre_empleado:
            sql += " AND (Cajero = %s OR Cajero = %s)"
            args.extend([cajero or "", nombre_empleado or ""])
        cursor.execute(sql, tuple(args))
        total = float((cursor.fetchone() or [0])[0] or 0)
        cone.close()
    except Exception as error:
        print("Error al totalizar entradas de abono: {}".format(error))
    return total


def utilidad_ventas(fecha_inicio=None, fecha_fin=None):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        sql = """
            SELECT
                COALESCE(SUM(vp.Subtotal), 0) AS ventas,
                COALESCE(SUM(vp.Subtotal - (p.Precio_Compra * vp.Cantidad)), 0) AS utilidad,
                COUNT(DISTINCT v.Id_Venta) AS tickets
            FROM productos_has_ventas vp
            JOIN productos p ON vp.Productos_Id_Producto = p.Id_Producto
            JOIN ventas v ON v.Id_Venta = vp.Ventas_Id_Factura
            WHERE COALESCE(v.Anulada, 0) = 0
              AND COALESCE(vp.Devuelto, 0) = 0
        """
        valores = ()
        if fecha_inicio and fecha_fin:
            sql += " AND v.Fecha_Venta BETWEEN %s AND %s"
            valores = (fecha_inicio, fecha_fin)
        try:
            cursor.execute(sql, valores)
        except Exception:
            cursor.execute(sql.replace("AND COALESCE(vp.Devuelto, 0) = 0", ""), valores)
        row = cursor.fetchone() or (0, 0, 0)
        cone.close()
        return {
            "ventas": float(row[0] or 0),
            "utilidad": float(row[1] or 0),
            "tickets": int(row[2] or 0),
        }
    except Exception as error:
        print("Error al calcular utilidad: {}".format(error))
        return {"ventas": 0.0, "utilidad": 0.0, "tickets": 0}


def top_productos_vendidos(limit=10, fecha_inicio=None, fecha_fin=None):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        sql = """
            SELECT p.Nombre, SUM(vp.Cantidad) AS qty, SUM(vp.Subtotal) AS total
            FROM productos_has_ventas vp
            JOIN productos p ON vp.Productos_Id_Producto = p.Id_Producto
            JOIN ventas v ON v.Id_Venta = vp.Ventas_Id_Factura
            WHERE COALESCE(v.Anulada, 0) = 0
              AND COALESCE(vp.Devuelto, 0) = 0
        """
        valores = []
        if fecha_inicio and fecha_fin:
            sql += " AND v.Fecha_Venta BETWEEN %s AND %s"
            valores.extend([fecha_inicio, fecha_fin])
        sql += " GROUP BY p.Id_Producto, p.Nombre ORDER BY qty DESC LIMIT %s"
        valores.append(int(limit))
        try:
            cursor.execute(sql, tuple(valores))
        except Exception:
            cursor.execute(sql.replace("AND COALESCE(vp.Devuelto, 0) = 0", ""), tuple(valores))
        rows = cursor.fetchall()
        cone.close()
        return rows or []
    except Exception as error:
        print("Error al consultar top productos: {}".format(error))
        return []


def productos_sin_movimiento(dias=30):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        sql = """
            SELECT p.Id_Producto, p.Nombre, p.Cantidad, p.Marca
            FROM productos p
            WHERE p.Id_Producto NOT IN (
                SELECT DISTINCT vp.Productos_Id_Producto
                FROM productos_has_ventas vp
                JOIN ventas v ON v.Id_Venta = vp.Ventas_Id_Factura
                WHERE v.Fecha_Venta >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                  AND COALESCE(v.Anulada, 0) = 0
            )
            ORDER BY p.Cantidad DESC, p.Nombre
        """
        cursor.execute(sql, (int(dias),))
        rows = cursor.fetchall()
        cone.close()
        return rows or []
    except Exception as error:
        print("Error al consultar productos sin movimiento: {}".format(error))
        return []


def detalle_utilidad_ventas(fecha_inicio=None, fecha_fin=None):
    sql_full = """
        SELECT v.Id_Venta, v.Fecha_Venta, p.Nombre,
               COALESCE(NULLIF(vp.Presentacion_Nombre, ''), 'Unidad') AS presentacion,
               COALESCE(NULLIF(vp.Cantidad_Presentacion, 0), vp.Cantidad) AS cant_pres,
               vp.Subtotal,
               CASE
                   WHEN vp.Costo_Unitario IS NOT NULL AND vp.Costo_Unitario > 0
                   THEN vp.Costo_Unitario * COALESCE(NULLIF(vp.Cantidad_Presentacion, 0), vp.Cantidad)
                   ELSE (p.Precio_Compra * vp.Cantidad)
               END AS costo,
               COALESCE(NULLIF(vp.Utilidad, 0), vp.Subtotal - (p.Precio_Compra * vp.Cantidad)) AS utilidad,
               COALESCE(v.Anulada, 0) AS anulada,
               COALESCE(v.Estado, '') AS estado
        FROM ventas v
        JOIN productos_has_ventas vp ON v.Id_Venta = vp.Ventas_Id_Factura
        JOIN productos p ON vp.Productos_Id_Producto = p.Id_Producto
    """
    sql_mid = """
        SELECT v.Id_Venta, v.Fecha_Venta, p.Nombre,
               COALESCE(NULLIF(vp.Presentacion_Nombre, ''), 'Unidad') AS presentacion,
               COALESCE(NULLIF(vp.Cantidad_Presentacion, 0), vp.Cantidad) AS cant_pres,
               vp.Subtotal,
               CASE
                   WHEN vp.Costo_Unitario IS NOT NULL AND vp.Costo_Unitario > 0
                   THEN vp.Costo_Unitario * COALESCE(NULLIF(vp.Cantidad_Presentacion, 0), vp.Cantidad)
                   ELSE (p.Precio_Compra * vp.Cantidad)
               END AS costo,
               COALESCE(NULLIF(vp.Utilidad, 0), vp.Subtotal - (p.Precio_Compra * vp.Cantidad)) AS utilidad,
               COALESCE(v.Anulada, 0) AS anulada
        FROM ventas v
        JOIN productos_has_ventas vp ON v.Id_Venta = vp.Ventas_Id_Factura
        JOIN productos p ON vp.Productos_Id_Producto = p.Id_Producto
    """
    sql_old = """
        SELECT v.Id_Venta, v.Fecha_Venta, p.Nombre, 'Unidad', vp.Cantidad, vp.Subtotal,
               (p.Precio_Compra * vp.Cantidad) AS costo,
               (vp.Subtotal - (p.Precio_Compra * vp.Cantidad)) AS utilidad,
               COALESCE(v.Anulada, 0) AS anulada
        FROM ventas v
        JOIN productos_has_ventas vp ON v.Id_Venta = vp.Ventas_Id_Factura
        JOIN productos p ON vp.Productos_Id_Producto = p.Id_Producto
    """
    valores = ()
    extra = ""
    if fecha_inicio and fecha_fin:
        extra = " WHERE v.Fecha_Venta BETWEEN %s AND %s"
        valores = (fecha_inicio, fecha_fin)
    extra += " ORDER BY v.Fecha_Venta DESC"
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        try:
            cursor.execute(sql_full + extra, valores)
        except Exception:
            try:
                cursor.execute(sql_mid + extra, valores)
            except Exception:
                cursor.execute(sql_old + extra, valores)
        rows = cursor.fetchall()
        cone.close()
        return rows or []
    except Exception as error:
        print("Error al consultar detalle de utilidad: {}".format(error))
        return []


def resumen_ventas(fecha_inicio=None, fecha_fin=None, codigo=None):
    """Una fila por ticket, sin desglose de productos."""
    sql = """
        SELECT v.Id_Venta, v.Fecha_Venta,
               COUNT(vp.Productos_Id_Producto) AS items,
               COALESCE(SUM(vp.Subtotal), 0) AS subtotal,
               COALESCE(SUM(
                   CASE
                       WHEN vp.Costo_Unitario IS NOT NULL AND vp.Costo_Unitario > 0
                       THEN vp.Costo_Unitario * COALESCE(NULLIF(vp.Cantidad_Presentacion, 0), vp.Cantidad)
                       ELSE p.Precio_Compra * vp.Cantidad
                   END
               ), 0) AS costo,
               COALESCE(SUM(
                   COALESCE(NULLIF(vp.Utilidad, 0), vp.Subtotal - (p.Precio_Compra * vp.Cantidad))
               ), 0) AS utilidad,
               COALESCE(v.Anulada, 0) AS anulada,
               COALESCE(v.Estado, '') AS estado
        FROM ventas v
        LEFT JOIN productos_has_ventas vp ON v.Id_Venta = vp.Ventas_Id_Factura
        LEFT JOIN productos p ON vp.Productos_Id_Producto = p.Id_Producto
    """
    sql_old = """
        SELECT v.Id_Venta, v.Fecha_Venta, COUNT(vp.Productos_Id_Producto),
               COALESCE(SUM(vp.Subtotal), 0),
               COALESCE(SUM(p.Precio_Compra * vp.Cantidad), 0),
               COALESCE(SUM(vp.Subtotal - (p.Precio_Compra * vp.Cantidad)), 0),
               COALESCE(v.Anulada, 0), ''
        FROM ventas v
        LEFT JOIN productos_has_ventas vp ON v.Id_Venta = vp.Ventas_Id_Factura
        LEFT JOIN productos p ON vp.Productos_Id_Producto = p.Id_Producto
    """
    where = []
    valores = []
    if fecha_inicio and fecha_fin:
        where.append("v.Fecha_Venta BETWEEN %s AND %s")
        valores.extend([fecha_inicio, fecha_fin])
    if codigo:
        where.append("CAST(v.Id_Venta AS CHAR) LIKE %s")
        valores.append("%{}%".format(codigo))
    extra = (" WHERE " + " AND ".join(where)) if where else ""
    extra += " GROUP BY v.Id_Venta, v.Fecha_Venta, v.Anulada, v.Estado ORDER BY v.Fecha_Venta DESC"
    extra_old = extra.replace(", v.Estado", "")
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        try:
            cursor.execute(sql + extra, tuple(valores))
        except Exception:
            cursor.execute(sql_old + extra_old, tuple(valores))
        rows = cursor.fetchall() or []
        cone.close()
        return rows
    except Exception as error:
        print("Error al consultar resumen de ventas: {}".format(error))
        return []


def detalle_lineas_venta(id_venta):
    sql = """
        SELECT vp.Productos_Id_Producto, p.Nombre,
               COALESCE(NULLIF(vp.Presentacion_Nombre, ''), 'Unidad') AS presentacion,
               COALESCE(NULLIF(vp.Cantidad_Presentacion, 0), vp.Cantidad) AS cant_pres,
               vp.Cantidad, vp.Subtotal,
               CASE
                   WHEN vp.Costo_Unitario IS NOT NULL AND vp.Costo_Unitario > 0
                   THEN vp.Costo_Unitario * COALESCE(NULLIF(vp.Cantidad_Presentacion, 0), vp.Cantidad)
                   ELSE p.Precio_Compra * vp.Cantidad
               END AS costo,
               COALESCE(NULLIF(vp.Utilidad, 0), vp.Subtotal - (p.Precio_Compra * vp.Cantidad)) AS utilidad,
               COALESCE(vp.Presentacion_Id, 0), COALESCE(vp.Factor, 1),
               COALESCE(vp.Devuelto, 0)
        FROM productos_has_ventas vp
        JOIN productos p ON p.Id_Producto = vp.Productos_Id_Producto
        WHERE vp.Ventas_Id_Factura = %s
        ORDER BY p.Nombre
    """
    sql_old = """
        SELECT vp.Productos_Id_Producto, p.Nombre, 'Unidad', vp.Cantidad, vp.Cantidad, vp.Subtotal,
               p.Precio_Compra * vp.Cantidad, vp.Subtotal - (p.Precio_Compra * vp.Cantidad),
               0, 1, 0
        FROM productos_has_ventas vp
        JOIN productos p ON p.Id_Producto = vp.Productos_Id_Producto
        WHERE vp.Ventas_Id_Factura = %s
    """
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        try:
            cursor.execute(sql, (id_venta,))
        except Exception:
            cursor.execute(sql_old, (id_venta,))
        filas = []
        for row in cursor.fetchall() or []:
            filas.append(
                {
                    "producto_id": row[0],
                    "producto": row[1],
                    "presentacion": row[2] or "Unidad",
                    "cantidad": float(row[3] or 0),
                    "cantidad_base": float(row[4] or 0),
                    "subtotal": float(row[5] or 0),
                    "costo": float(row[6] or 0),
                    "utilidad": float(row[7] or 0),
                    "presentacion_id": int(row[8] or 0),
                    "factor": float(row[9] or 1),
                    "devuelto": int(row[10] or 0) == 1,
                }
            )
        cone.close()
        return filas
    except Exception as error:
        print("Error al leer líneas de venta: {}".format(error))
        return []


def utilidad_por_presentacion(fecha_inicio=None, fecha_fin=None):
    sql = """
        SELECT p.Nombre,
               COALESCE(NULLIF(vp.Presentacion_Nombre, ''), 'Unidad') AS presentacion,
               SUM(COALESCE(NULLIF(vp.Cantidad_Presentacion, 0), vp.Cantidad)) AS cant,
               SUM(vp.Cantidad) AS base,
               SUM(vp.Subtotal) AS ventas,
               SUM(COALESCE(NULLIF(vp.Utilidad, 0), vp.Subtotal - (p.Precio_Compra * vp.Cantidad))) AS utilidad
        FROM productos_has_ventas vp
        JOIN productos p ON vp.Productos_Id_Producto = p.Id_Producto
        JOIN ventas v ON v.Id_Venta = vp.Ventas_Id_Factura
        WHERE COALESCE(v.Anulada, 0) = 0
    """
    valores = []
    if fecha_inicio and fecha_fin:
        sql += " AND v.Fecha_Venta BETWEEN %s AND %s"
        valores.extend([fecha_inicio, fecha_fin])
    sql += " GROUP BY p.Id_Producto, p.Nombre, COALESCE(NULLIF(vp.Presentacion_Nombre, ''), 'Unidad') ORDER BY utilidad DESC"
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(sql, tuple(valores))
        rows = cursor.fetchall() or []
        cone.close()
        return rows
    except Exception as error:
        print("Error al consultar utilidad por presentación: {}".format(error))
        return []


def detalle_compras(fecha_inicio=None, fecha_fin=None):
    sql = """
        SELECT c.Fecha, c.Numero_Factura, c.Proveedor, i.Nombre,
               COALESCE(NULLIF(i.Presentacion_Nombre, ''), 'Unidad'),
               i.Cantidad, COALESCE(NULLIF(i.Cantidad_Base, 0), i.Cantidad),
               i.Precio_Base, i.Iva_Valor, i.Total_Linea
        FROM compra_items i
        JOIN compras c ON c.Id = i.Compra_Id
    """
    valores = ()
    if fecha_inicio and fecha_fin:
        sql += " WHERE c.Fecha BETWEEN %s AND %s"
        valores = (fecha_inicio, fecha_fin)
    sql += " ORDER BY c.Fecha DESC"
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(sql, valores)
        rows = cursor.fetchall() or []
        cone.close()
        return rows
    except Exception as error:
        print("Error al consultar compras: {}".format(error))
        return []


def totales_pagos_desde(fecha_desde, id_empleado=None):
    metodos = {"Efectivo": 0.0, "Nequi": 0.0, "Tarjeta": 0.0, "Transferencia": 0.0, "Crédito": 0.0}
    total_ventas = 0.0
    tickets = 0
    articulos = 0
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        sql_pagos = """
            SELECT vp.Metodo, COALESCE(SUM(vp.Monto), 0)
            FROM venta_pagos vp
            JOIN ventas v ON v.Id_Venta = vp.Venta_Id
            WHERE v.Fecha_Venta >= %s
              AND COALESCE(v.Anulada, 0) = 0
        """
        valores = [fecha_desde]
        if id_empleado is not None:
            sql_pagos += " AND v.Empleados_Id_Empleados = %s"
            valores.append(id_empleado)
        sql_pagos += " GROUP BY vp.Metodo"
        cursor.execute(sql_pagos, tuple(valores))
        for metodo, monto in cursor.fetchall() or []:
            if metodo in metodos:
                metodos[metodo] = float(monto or 0)
        sql_ventas = "SELECT COALESCE(SUM(Total), 0), COUNT(*) FROM ventas WHERE Fecha_Venta >= %s AND COALESCE(Anulada, 0) = 0"
        valores_v = [fecha_desde]
        if id_empleado is not None:
            sql_ventas += " AND Empleados_Id_Empleados = %s"
            valores_v.append(id_empleado)
        cursor.execute(sql_ventas, tuple(valores_v))
        row = cursor.fetchone() or (0, 0)
        total_ventas = float(row[0] or 0)
        tickets = int(row[1] or 0)
        sql_art = """
            SELECT COALESCE(SUM(vp.Cantidad), 0)
            FROM productos_has_ventas vp
            JOIN ventas v ON v.Id_Venta = vp.Ventas_Id_Factura
            WHERE v.Fecha_Venta >= %s
              AND COALESCE(v.Anulada, 0) = 0
        """
        valores_a = [fecha_desde]
        if id_empleado is not None:
            sql_art += " AND v.Empleados_Id_Empleados = %s"
            valores_a.append(id_empleado)
        cursor.execute(sql_art, tuple(valores_a))
        articulos = int((cursor.fetchone() or (0,))[0] or 0)
        cone.close()
    except Exception as error:
        print("Error al totalizar pagos del turno: {}".format(error))
    return metodos, total_ventas, tickets, articulos


def _ahora():
    zona = pytz.timezone("America/Bogota")
    return datetime.now(zona).strftime("%Y-%m-%d %H:%M:%S")


def registrar_auditoria(usuario, accion, detalle=""):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            "INSERT INTO logs_auditoria (Usuario, Fecha, Accion, Detalle) VALUES (%s, %s, %s, %s)",
            (usuario or "-", _ahora(), accion or "", str(detalle or "")[:255]),
        )
        cone.commit()
        cone.close()
        return True
    except Exception as error:
        print("Error al registrar auditoría: {}".format(error))
        return False


def obtener_config_pos():
    defaults = {
        "pesos_por_punto": 1000,
        "valor_punto": 50.0,
        "dias_cobertura": 15,
        "tipo_negocio": "Tienda",
        "dias_alerta_vence": 30,
        "usar_fefo": True,
        "pct_proveedores": 65.0,
        "pct_provisiones": 17.0,
        "pct_utilidad": 18.0,
        "base_gabinete": 0.0,
        "pct_recargo_tarjeta": 6.0,
    }
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        try:
            cursor.execute(
                """SELECT Pesos_Por_Punto, Valor_Punto, Dias_Cobertura, Tipo_Negocio, Dias_Alerta_Vence, Usar_FEFO,
                          Pct_Proveedores, Pct_Provisiones, Pct_Utilidad, Base_Gabinete, Pct_Recargo_Tarjeta
                   FROM config_pos WHERE Id=1"""
            )
            row = cursor.fetchone()
            cone.close()
            if row:
                return {
                    "pesos_por_punto": int(row[0] or 1000),
                    "valor_punto": float(row[1] or 50),
                    "dias_cobertura": int(row[2] or 15),
                    "tipo_negocio": (row[3] or "Tienda"),
                    "dias_alerta_vence": int(row[4] or 30),
                    "usar_fefo": int(row[5] if row[5] is not None else 1) == 1,
                    "pct_proveedores": float(row[6] if len(row) > 6 and row[6] is not None else 65),
                    "pct_provisiones": float(row[7] if len(row) > 7 and row[7] is not None else 17),
                    "pct_utilidad": float(row[8] if len(row) > 8 and row[8] is not None else 18),
                    "base_gabinete": float(row[9] if len(row) > 9 and row[9] is not None else 0),
                    "pct_recargo_tarjeta": float(row[10] if len(row) > 10 and row[10] is not None else 6),
                }
        except Exception:
            try:
                cone.rollback()
            except Exception:
                pass
            cursor.execute("SELECT Pesos_Por_Punto, Valor_Punto, Dias_Cobertura FROM config_pos WHERE Id=1")
            row = cursor.fetchone()
            cone.close()
            if row:
                defaults["pesos_por_punto"] = int(row[0] or 1000)
                defaults["valor_punto"] = float(row[1] or 50)
                defaults["dias_cobertura"] = int(row[2] or 15)
    except Exception as error:
        print("Error al leer config POS: {}".format(error))
    return defaults


def guardar_config_pos(
    pesos_por_punto=None,
    valor_punto=None,
    dias_cobertura=None,
    tipo_negocio=None,
    dias_alerta_vence=None,
    usar_fefo=None,
    base_gabinete=None,
    pct_recargo_tarjeta=None,
):
    actual = obtener_config_pos()
    pesos = actual["pesos_por_punto"] if pesos_por_punto is None else int(pesos_por_punto)
    valor = actual["valor_punto"] if valor_punto is None else float(valor_punto)
    dias = actual["dias_cobertura"] if dias_cobertura is None else int(dias_cobertura)
    tipo = actual["tipo_negocio"] if tipo_negocio is None else str(tipo_negocio or "Tienda")[:40]
    alerta = actual["dias_alerta_vence"] if dias_alerta_vence is None else int(dias_alerta_vence)
    fefo = actual["usar_fefo"] if usar_fefo is None else bool(usar_fefo)
    base = actual["base_gabinete"] if base_gabinete is None else float(base_gabinete)
    pct_recargo = actual["pct_recargo_tarjeta"] if pct_recargo_tarjeta is None else float(pct_recargo_tarjeta)
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        try:
            cursor.execute(
                """INSERT INTO config_pos
                   (Id, Pesos_Por_Punto, Valor_Punto, Dias_Cobertura, Tipo_Negocio, Dias_Alerta_Vence, Usar_FEFO,
                    Base_Gabinete, Pct_Recargo_Tarjeta)
                   VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE
                     Pesos_Por_Punto=%s, Valor_Punto=%s, Dias_Cobertura=%s,
                     Tipo_Negocio=%s, Dias_Alerta_Vence=%s, Usar_FEFO=%s,
                     Base_Gabinete=%s, Pct_Recargo_Tarjeta=%s""",
                (
                    pesos, valor, dias, tipo, alerta, 1 if fefo else 0, base, pct_recargo,
                    pesos, valor, dias, tipo, alerta, 1 if fefo else 0, base, pct_recargo,
                ),
            )
        except Exception:
            cursor.execute(
                """INSERT INTO config_pos (Id, Pesos_Por_Punto, Valor_Punto, Dias_Cobertura)
                   VALUES (1, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE Pesos_Por_Punto=%s, Valor_Punto=%s, Dias_Cobertura=%s""",
                (pesos, valor, dias, pesos, valor, dias),
            )
        cone.commit()
        cone.close()
        return True
    except Exception as error:
        print("Error al guardar config POS: {}".format(error))
        return False


def pct_recargo_tarjeta():
    try:
        return float(obtener_config_pos().get("pct_recargo_tarjeta") or 6)
    except (TypeError, ValueError):
        return 6.0


def base_gabinete_config():
    try:
        return float(obtener_config_pos().get("base_gabinete") or 0)
    except (TypeError, ValueError):
        return 0.0


def precio_con_recargo(precio_real, pct=None):
    from dinero import redondear_centena

    try:
        base = float(precio_real or 0)
    except (TypeError, ValueError):
        base = 0.0
    if pct is None:
        pct = pct_recargo_tarjeta()
    try:
        pct = float(pct or 0)
    except (TypeError, ValueError):
        pct = 0.0
    if pct <= 0:
        return redondear_centena(base)
    return redondear_centena(base * (1.0 + pct / 100.0))


def venta_aplica_recargo(pagos):
    """Recargo solo si interviene tarjeta débito/crédito (sola o en pago mixto)."""
    for metodo, monto in (pagos or {}).items():
        if str(metodo) in ("Puntos",):
            continue
        try:
            if float(monto or 0) <= 0:
                continue
        except (TypeError, ValueError):
            continue
        nombre = str(metodo or "").strip().lower()
        if nombre == "tarjeta" or nombre.startswith("tarjeta"):
            return True
    return False

def parse_cliente(row):
    if not row:
        return None
    layout = _layout_clientes()
    names = layout["cols"]

    def val(key):
        col = layout.get(key)
        if not col or col not in names:
            return None
        idx = names.index(col)
        if len(row) <= idx:
            return None
        return row[idx]

    def texto(valor):
        if valor is None:
            return ""
        if isinstance(valor, float) and valor == int(valor):
            return str(int(valor))
        return str(valor).strip()

    nombre = texto(val("nombre"))
    apellido = texto(val("apellido"))
    if apellido and apellido not in nombre:
        nombre = (nombre + " " + apellido).strip()
    return {
        "id": val("id"),
        "nombre": nombre,
        "documento": texto(val("documento")),
        "telefono": texto(val("telefono")),
        "limite": float(val("limite") or 0),
        "saldo": float(val("saldo") or 0),
        "puntos": int(val("puntos") or 0),
    }


def _layout_clientes(cursor=None):
    global _CLIENTES_LAYOUT
    if _CLIENTES_LAYOUT:
        return _CLIENTES_LAYOUT
    close = False
    cone = None
    if cursor is None:
        cone = FormularioLogin.conexion_base_de_datos()
        if not cone:
            return {
                "cols": [],
                "id": "Id_Cliente",
                "nombre": "Nombre",
                "apellido": None,
                "documento": "Documento",
                "telefono": "Telefono",
                "limite": "Limite_Credito",
                "saldo": "Saldo_Pendiente",
                "puntos": "Puntos",
            }
        cursor = cone.cursor()
        close = True
    cursor.execute("SHOW COLUMNS FROM clientes")
    names = [r[0] for r in cursor.fetchall() or []]
    cols = set(names)
    _CLIENTES_LAYOUT = {
        "cols": names,
        "id": "Id_Cliente" if "Id_Cliente" in cols else (names[0] if names else "Id_Cliente"),
        "nombre": "Nombre" if "Nombre" in cols else ("Nombres" if "Nombres" in cols else None),
        "apellido": "Apellidos" if "Apellidos" in cols else None,
        "documento": "Documento" if "Documento" in cols else ("Cedula" if "Cedula" in cols else None),
        "telefono": "Telefono" if "Telefono" in cols else None,
        "limite": "Limite_Credito" if "Limite_Credito" in cols else None,
        "saldo": "Saldo_Pendiente" if "Saldo_Pendiente" in cols else None,
        "puntos": "Puntos" if "Puntos" in cols else None,
    }
    if close:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            cone.close()
        except Exception:
            pass
    return _CLIENTES_LAYOUT


def obtener_cliente(id_cliente):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        layout = _layout_clientes(cursor)
        cursor.execute("SELECT * FROM clientes WHERE {}=%s".format(layout["id"]), (id_cliente,))
        row = cursor.fetchone()
        cone.close()
        return parse_cliente(row)
    except Exception as error:
        print("Error al obtener cliente: {}".format(error))
        return None


def buscar_clientes(texto):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        layout = _layout_clientes(cursor)
        like = "%" + str(texto or "") + "%"
        filtros = []
        args = []
        for key in ("nombre", "apellido", "documento", "telefono"):
            col = layout.get(key)
            if col:
                filtros.append("{} LIKE %s".format(col))
                args.append(like)
        sql = "SELECT * FROM clientes"
        if filtros:
            sql += " WHERE " + " OR ".join(filtros)
        if layout.get("nombre"):
            sql += " ORDER BY {}".format(layout["nombre"])
        cursor.execute(sql, tuple(args))
        rows = [parse_cliente(r) for r in cursor.fetchall() or []]
        cone.close()
        return rows
    except Exception as error:
        print("Error al buscar clientes: {}".format(error))
        return []


def listar_clientes():
    return buscar_clientes("")


def guardar_cliente(nombre, documento, telefono, limite, id_cliente=None):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        layout = _layout_clientes(cursor)
        nombre = (nombre or "").strip()
        documento = (documento or "").strip()
        telefono = (telefono or "").strip()
        campos = {}
        if layout.get("nombre"):
            campos[layout["nombre"]] = nombre
        if layout.get("apellido"):
            partes = nombre.split(None, 1)
            campos[layout["nombre"]] = partes[0]
            campos[layout["apellido"]] = partes[1] if len(partes) > 1 else ""
        if layout.get("documento"):
            campos[layout["documento"]] = documento
        if layout.get("telefono"):
            campos[layout["telefono"]] = telefono
        if layout.get("limite"):
            campos[layout["limite"]] = limite or 0
        if not campos:
            cone.close()
            return False, "La tabla de clientes no tiene columnas reconocidas."
        if id_cliente:
            sets = ", ".join("{}=%s".format(col) for col in campos)
            sql = "UPDATE clientes SET {} WHERE {}=%s".format(sets, layout["id"])
            cursor.execute(sql, tuple(campos.values()) + (id_cliente,))
        else:
            if layout.get("saldo"):
                campos[layout["saldo"]] = 0
            if layout.get("puntos"):
                campos[layout["puntos"]] = 0
            cols = ", ".join(campos.keys())
            placeholders = ", ".join(["%s"] * len(campos))
            sql = "INSERT INTO clientes ({}) VALUES ({})".format(cols, placeholders)
            cursor.execute(sql, tuple(campos.values()))
        cone.commit()
        cone.close()
        return True, ""
    except Exception as error:
        print("Error al guardar cliente: {}".format(error))
        msg = str(error)
        if "Duplicate" in msg or "1062" in msg:
            return False, "Esa cédula / documento ya está registrada."
        return False, "No se pudo guardar el cliente. {}".format(error)


def movimientos_cliente(id_cliente):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            """SELECT Fecha, Tipo, Monto, Puntos, Venta_Id, Usuario, Comentario
               FROM cliente_movimientos WHERE Cliente_Id=%s ORDER BY Fecha DESC, Id DESC""",
            (id_cliente,),
        )
        rows = cursor.fetchall() or []
        cone.close()
        return rows
    except Exception as error:
        print("Error al listar movimientos del cliente: {}".format(error))
        return []


def _movimiento_cliente(id_cliente, tipo, monto=0, puntos=0, venta_id=None, usuario="", comentario=""):
    cone = FormularioLogin.conexion_base_de_datos()
    cursor = cone.cursor()
    cursor.execute(
        """INSERT INTO cliente_movimientos (Cliente_Id, Tipo, Venta_Id, Monto, Puntos, Fecha, Usuario, Comentario)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
        (id_cliente, tipo, venta_id, monto, puntos, _ahora(), usuario, comentario),
    )
    cone.commit()
    cone.close()


def aplicar_credito_cliente(id_cliente, monto, venta_id, usuario):
    cliente = obtener_cliente(id_cliente)
    if not cliente:
        return False, "Cliente no encontrado"
    disponible = cliente["limite"] - cliente["saldo"]
    if monto > disponible + 0.01:
        from dinero import formato_dinero

        return False, f"Supera el cupo disponible ({formato_dinero(disponible)})"
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            "UPDATE clientes SET Saldo_Pendiente = Saldo_Pendiente + %s WHERE Id_Cliente=%s",
            (monto, id_cliente),
        )
        cone.commit()
        cone.close()
        _movimiento_cliente(id_cliente, "CREDITO", monto, 0, venta_id, usuario, "Venta a crédito / fiado")
        return True, ""
    except Exception as error:
        print("Error al aplicar crédito: {}".format(error))
        return False, "No se pudo registrar el crédito"


def registrar_abono_cliente(id_cliente, monto, usuario, comentario="Abono en efectivo", metodo="Efectivo"):
    cliente = obtener_cliente(id_cliente)
    if not cliente:
        return False, "Cliente no encontrado"
    if monto <= 0:
        return False, "El abono debe ser mayor a cero"
    if monto > cliente["saldo"] + 0.01:
        from dinero import formato_dinero

        return False, f"El abono supera el saldo ({formato_dinero(cliente['saldo'])})"
    metodo = (metodo or "Efectivo").strip() or "Efectivo"
    detalle = comentario or "Abono en {}".format(metodo.lower())
    if metodo.lower() not in str(detalle).lower():
        detalle = "{} ({})".format(detalle, metodo)
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            "UPDATE clientes SET Saldo_Pendiente = Saldo_Pendiente - %s WHERE Id_Cliente=%s",
            (monto, id_cliente),
        )
        cone.commit()
        cone.close()
        _movimiento_cliente(id_cliente, "ABONO", monto, 0, None, usuario, detalle)
        if metodo.lower() == "efectivo":
            nombre = cliente.get("nombre") or "cliente"
            Agregar_entrada_dinero(
                monto,
                "Abono CxC: {} — {}".format(nombre, detalle),
                usuario,
                _ahora(),
            )
        return True, ""
    except Exception as error:
        print("Error al registrar abono: {}".format(error))
        return False, "No se pudo registrar el abono"


def ajustar_puntos_cliente(id_cliente, puntos, venta_id, usuario, tipo="PUNTOS", comentario=""):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute("UPDATE clientes SET Puntos = GREATEST(Puntos + %s, 0) WHERE Id_Cliente=%s", (int(puntos), id_cliente))
        cone.commit()
        cone.close()
        _movimiento_cliente(id_cliente, tipo, 0, int(puntos), venta_id, usuario, comentario)
        return True
    except Exception as error:
        print("Error al ajustar puntos: {}".format(error))
        return False


def asociar_cliente_venta(id_venta, id_cliente):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute("UPDATE ventas SET Cliente_Id=%s WHERE Id_Venta=%s", (id_cliente, id_venta))
        cone.commit()
        cone.close()
        return True
    except Exception as error:
        print("Error al asociar cliente a la venta: {}".format(error))
        return False


def asignar_proveedor_producto(nombre, proveedor):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute("UPDATE productos SET Proveedor=%s WHERE Nombre=%s", (proveedor or "", nombre))
        cone.commit()
        cone.close()
        return True
    except Exception as error:
        print("Error al asignar proveedor: {}".format(error))
        return False


def registrar_compra_mercancia(header, items, cajero=""):
    """Guarda el documento de compra (factura, pago, desglose IVA) sin tocar el inventario.

    El inventario, lotes y precios se actualizan aparte para no duplicar lógica.
    Productos y compras anteriores no se modifican.
    """
    if not items:
        return False, "No hay artículos para registrar.", None
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        factura = (header or {}).get("numero_factura") or ""
        proveedor = (header or {}).get("proveedor") or ""
        usuario = (header or {}).get("usuario") or ""
        metodo = (header or {}).get("metodo_pago") or "Efectivo"
        if metodo not in METODOS_PAGO_COMPRA:
            metodo = "Otro"
        pagado = round(float((header or {}).get("monto_pagado") or 0), 2)
        saldo = round(float((header or {}).get("saldo_pendiente") or 0), 2)
        subtotal = round(float((header or {}).get("subtotal") or 0), 2)
        iva_total = round(float((header or {}).get("iva") or 0), 2)
        total = round(float((header or {}).get("total") or 0), 2)
        estado = (header or {}).get("estado") or ("PENDIENTE" if saldo > 0.009 else "PAGADA")
        cursor.execute(
            """INSERT INTO compras
               (Numero_Factura, Proveedor, Fecha, Usuario, Metodo_Pago,
                Monto_Pagado, Saldo_Pendiente, Subtotal, Iva, Total, Estado)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                factura[:40],
                proveedor[:120],
                _ahora(),
                str(usuario)[:80],
                metodo[:40],
                pagado,
                saldo,
                subtotal,
                iva_total,
                total,
                estado[:20],
            ),
        )
        compra_id = cursor.lastrowid
        for item in items:
            vence = item.get("fecha_vence") or None
            if vence == "":
                vence = None
            factor = float(item.get("factor") or 1) or 1
            cant_pres = float(item.get("cantidad") or 0)
            cant_base = float(item.get("cantidad_base") or a_unidades_base(cant_pres, factor))
            args_full = (
                    compra_id,
                    item.get("producto_id"),
                    str(item.get("nombre") or "")[:160],
                    cant_pres,
                    iva_a_porcentaje(item.get("iva_pct")),
                    1 if item.get("iva_incluido") else 0,
                    round(float(item.get("precio_ingresado") or 0), 2),
                    round(float(item.get("precio_base") or 0), 2),
                    round(float(item.get("iva_valor") or 0), 2),
                    round(float(item.get("total_linea") or 0), 2),
                    round(float(item.get("precio_venta") or 0), 2),
                    vence,
                    item.get("presentacion_id"),
                    str(item.get("presentacion_nombre") or "")[:80],
                    factor,
                    cant_base,
            )
            try:
                cursor.execute(
                    """INSERT INTO compra_items
                       (Compra_Id, Producto_Id, Nombre, Cantidad, Iva_Pct, Iva_Incluido,
                        Precio_Ingresado, Precio_Base, Iva_Valor, Total_Linea, Precio_Venta, Fecha_Vence,
                        Presentacion_Id, Presentacion_Nombre, Factor, Cantidad_Base)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    args_full,
                )
            except Exception:
                cursor.execute(
                    """INSERT INTO compra_items
                       (Compra_Id, Producto_Id, Nombre, Cantidad, Iva_Pct, Iva_Incluido,
                        Precio_Ingresado, Precio_Base, Iva_Valor, Total_Linea, Precio_Venta, Fecha_Vence)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    args_full[:12],
                )
        cone.commit()
        if str(metodo).strip().lower() == "efectivo" and pagado > 0:
            asunto = "Compra mercancía"
            if factura:
                asunto += " factura {}".format(factura)
            if proveedor:
                asunto += " · {}".format(proveedor)
            Agregar_salida_dinero(pagado, asunto[:220], cajero or usuario or "-", _ahora())
        try:
            from dinero import formato_dinero

            registrar_auditoria(
                usuario or cajero,
                "Compra de mercancía",
                "Factura {} total {} pagado {} saldo {}".format(
                    factura or "-", formato_dinero(total), formato_dinero(pagado), formato_dinero(saldo)
                ),
            )
        except Exception:
            pass
        cursor.close()
        cone.close()
        return True, "ok", compra_id
    except Exception as error:
        print("Error al registrar compra: {}".format(error))
        try:
            cone.rollback()
        except Exception:
            pass
        try:
            cursor.close()
            cone.close()
        except Exception:
            pass
        return False, "No se pudo guardar el documento de compra: {}".format(error), None


def actualizar_precios_recepcion(nombre, precio_compra, precio_venta, iva=0):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        iva_pct = iva_a_porcentaje(iva)
        intentos = [
            (
                "UPDATE productos SET Precio_Compra=%s, Precio_Venta=%s, Iva=%s WHERE Nombre=%s",
                (precio_compra, precio_venta, iva_pct, nombre),
            ),
            (
                "UPDATE productos SET Precio_Compra=%s, Precio_Venta=%s WHERE Nombre=%s",
                (precio_compra, precio_venta, nombre),
            ),
        ]
        ok = False
        for sql, valores in intentos:
            try:
                cursor.execute(sql, valores)
                ok = True
                break
            except Exception:
                continue
        cone.commit()
        cone.close()
        return ok
    except Exception as error:
        print("Error al actualizar precios de recepción: {}".format(error))
        return False


def sugerido_compra(dias=15):
    from math import ceil
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        sql = """
            SELECT p.Id_Producto, p.Nombre, p.Cantidad, p.Stock_Minimo, p.Precio_Compra,
                   COALESCE(p.Proveedor, ''), COALESCE(SUM(vp.Cantidad), 0)
            FROM productos p
            LEFT JOIN productos_has_ventas vp ON vp.Productos_Id_Producto = p.Id_Producto
            LEFT JOIN ventas v ON v.Id_Venta = vp.Ventas_Id_Factura
                 AND v.Fecha_Venta >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                 AND COALESCE(v.Anulada, 0) = 0
            GROUP BY p.Id_Producto, p.Nombre, p.Cantidad, p.Stock_Minimo, p.Precio_Compra, p.Proveedor
            ORDER BY COALESCE(p.Proveedor, ''), p.Nombre
        """
        try:
            cursor.execute(sql, (int(dias),))
        except Exception:
            cursor.execute(
                """
                SELECT p.Id_Producto, p.Nombre, p.Cantidad, 10, p.Precio_Compra,
                       '', COALESCE(SUM(vp.Cantidad), 0)
                FROM productos p
                LEFT JOIN productos_has_ventas vp ON vp.Productos_Id_Producto = p.Id_Producto
                LEFT JOIN ventas v ON v.Id_Venta = vp.Ventas_Id_Factura
                     AND v.Fecha_Venta >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                GROUP BY p.Id_Producto, p.Nombre, p.Cantidad, p.Precio_Compra
                ORDER BY p.Nombre
                """,
                (int(dias),),
            )
        filas = []
        for row in cursor.fetchall() or []:
            codigo, nombre, stock, minimo, costo, proveedor, vendido = row
            stock = float(stock or 0)
            minimo = float(minimo if minimo is not None else 10)
            costo = float(costo or 0)
            vendido = float(vendido or 0)
            promedio = vendido / float(dias or 15)
            objetivo = max(minimo, promedio * float(dias or 15))
            sugerido = int(ceil(max(0, objetivo - stock)))
            if sugerido <= 0:
                continue
            filas.append(
                {
                    "codigo": codigo,
                    "nombre": nombre,
                    "proveedor": proveedor or "Sin proveedor",
                    "stock": int(stock),
                    "minimo": int(minimo),
                    "vendido": int(vendido),
                    "promedio": round(promedio, 2),
                    "sugerido": sugerido,
                    "costo": costo,
                    "total": sugerido * costo,
                }
            )
        cone.close()
        return filas
    except Exception as error:
        print("Error al calcular sugerido de compra: {}".format(error))
        return []


def items_de_venta(id_venta):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            "SELECT Productos_Id_Producto, Cantidad, Subtotal FROM productos_has_ventas WHERE Ventas_Id_Factura=%s",
            (id_venta,),
        )
        rows = cursor.fetchall() or []
        cone.close()
        return rows
    except Exception as error:
        print("Error al leer ítems de venta: {}".format(error))
        return []


def _parse_items_json(texto):
    if not texto:
        return []
    if isinstance(texto, (list, tuple)):
        return list(texto)
    try:
        data = json.loads(texto)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _linea_pedida(producto_id, presentacion_id, items):
    if not items:
        return True
    pid = int(producto_id or 0)
    pres = int(presentacion_id or 0)
    for item in items:
        try:
            ip = int(item.get("producto_id") or item.get("Productos_Id_Producto") or 0)
        except (TypeError, ValueError):
            continue
        if ip != pid:
            continue
        try:
            ipres = int(item.get("presentacion_id") or 0)
        except (TypeError, ValueError):
            ipres = 0
        if ipres == 0 or ipres == pres:
            return True
    return False


def devolver_venta(id_venta, usuario, items=None):
    items = _parse_items_json(items) if not isinstance(items, list) else items
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute("SELECT Anulada, Cliente_Id, Total FROM ventas WHERE Id_Venta=%s", (id_venta,))
        venta = cursor.fetchone()
        if not venta:
            cone.close()
            return False, "No existe esa venta"
        if int(venta[0] or 0) == 1:
            cone.close()
            return False, "La venta ya fue anulada"
        try:
            cursor.execute(
                """SELECT Productos_Id_Producto, Cantidad, Presentacion_Id, Presentacion_Nombre, Factor,
                          Cantidad_Presentacion, Subtotal, COALESCE(Devuelto, 0)
                   FROM productos_has_ventas WHERE Ventas_Id_Factura=%s""",
                (id_venta,),
            )
            crudas = cursor.fetchall() or []
        except Exception:
            cursor.execute(
                "SELECT Productos_Id_Producto, Cantidad, NULL, 'Unidad', 1, Cantidad, Subtotal, 0 FROM productos_has_ventas WHERE Ventas_Id_Factura=%s",
                (id_venta,),
            )
            crudas = cursor.fetchall() or []
        lineas = []
        for row in crudas:
            if int(row[7] or 0) == 1:
                continue
            if not _linea_pedida(row[0], row[2], items):
                continue
            lineas.append(row)
        if not lineas:
            cone.close()
            return False, "No hay ítems pendientes por devolver en esa venta"
        cone.close()
        returned_sub = 0.0
        for row in lineas:
            id_producto = row[0]
            cantidad_base = float(row[1] or 0)
            pres_id = row[2] if len(row) > 2 else None
            factor = float(row[4] or 1) if len(row) > 4 else 1
            cant_pres = float(row[5] or cantidad_base) if len(row) > 5 else cantidad_base
            returned_sub += float(row[6] or 0)
            cambiar_stock_base(id_producto, cantidad_base)
            reponer_lotes(id_producto, cantidad_base)
            registrar_movimiento_inventario(
                id_producto,
                "DEVOLUCION",
                cant_pres,
                factor or 1,
                "Devolución venta {}".format(id_venta),
                usuario or "",
                pres_id,
            )
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute("SHOW COLUMNS FROM productos_has_ventas LIKE 'Devuelto'")
        tiene_devuelto = bool(cursor.fetchone())
        if tiene_devuelto:
            if items:
                for row in lineas:
                    cursor.execute(
                        """UPDATE productos_has_ventas SET Devuelto=1
                           WHERE Ventas_Id_Factura=%s AND Productos_Id_Producto=%s
                             AND COALESCE(Presentacion_Id, 0)=COALESCE(%s, 0)""",
                        (id_venta, row[0], row[2]),
                    )
            else:
                cursor.execute(
                    "UPDATE productos_has_ventas SET Devuelto=1 WHERE Ventas_Id_Factura=%s",
                    (id_venta,),
                )
            cursor.execute(
                """SELECT COUNT(*) FROM productos_has_ventas
                   WHERE Ventas_Id_Factura=%s AND COALESCE(Devuelto, 0)=0""",
                (id_venta,),
            )
            restantes = int((cursor.fetchone() or [0])[0] or 0)
        else:
            restantes = 0 if not items else 1
        cursor.execute("SHOW COLUMNS FROM ventas LIKE 'Estado'")
        tiene_estado = bool(cursor.fetchone())
        if restantes <= 0:
            if tiene_estado:
                cursor.execute(
                    "UPDATE ventas SET Anulada=1, Estado='ANULADA' WHERE Id_Venta=%s",
                    (id_venta,),
                )
            else:
                cursor.execute("UPDATE ventas SET Anulada=1 WHERE Id_Venta=%s", (id_venta,))
            tipo = "completa"
        else:
            if tiene_estado:
                cursor.execute(
                    "UPDATE ventas SET Anulada=0, Estado='PARCIAL' WHERE Id_Venta=%s",
                    (id_venta,),
                )
            tipo = "parcial"
        cone.commit()
        cone.close()
    except Exception as error:
        print("Error al devolver venta: {}".format(error))
        return False, "No se pudo anular la venta"

    id_cliente = venta[1]
    if id_cliente:
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            if tipo == "completa":
                cursor.execute(
                    "SELECT Tipo, Monto, Puntos FROM cliente_movimientos WHERE Venta_Id=%s",
                    (id_venta,),
                )
                for tipo_mov, monto, puntos in cursor.fetchall() or []:
                    if tipo_mov == "CREDITO":
                        cursor.execute(
                            "UPDATE clientes SET Saldo_Pendiente = GREATEST(Saldo_Pendiente - %s, 0) WHERE Id_Cliente=%s",
                            (monto, id_cliente),
                        )
                    elif tipo_mov in ("PUNTOS", "CANJE"):
                        cursor.execute(
                            "UPDATE clientes SET Puntos = GREATEST(Puntos - %s, 0) WHERE Id_Cliente=%s",
                            (puntos, id_cliente),
                        )
            elif returned_sub > 0:
                cursor.execute(
                    "UPDATE clientes SET Saldo_Pendiente = GREATEST(Saldo_Pendiente - %s, 0) WHERE Id_Cliente=%s",
                    (returned_sub, id_cliente),
                )
            cone.commit()
            cone.close()
        except Exception as error:
            print("Error al revertir cliente en devolución: {}".format(error))
    if tipo == "completa":
        registrar_auditoria(usuario, "Devolución", "Anuló la venta #{}".format(id_venta))
        return True, "Venta devuelta, stock y lotes restaurados"
    registrar_auditoria(
        usuario,
        "Devolución",
        "Devolvió {} ítem(s) de la venta #{}".format(len(lineas), id_venta),
    )
    return True, "Ítems devueltos, stock y lotes restaurados"


ZYNTRA_API_URL = "https://api-production-b438.up.railway.app"


def _venta_es_de_hoy(fecha):
    try:
        bogota = pytz.timezone("America/Bogota")
        hoy = datetime.now(bogota).date()
    except Exception:
        hoy = datetime.now().date()
    if fecha is None:
        return False
    if isinstance(fecha, datetime):
        return fecha.date() == hoy
    try:
        return int(fecha.year) == hoy.year and int(fecha.month) == hoy.month and int(fecha.day) == hoy.day
    except Exception:
        pass
    texto = str(fecha)[:10]
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date() == hoy
    except Exception:
        return False


def _ensure_devolucion_solicitudes(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS devolucion_solicitudes (
            Id INT AUTO_INCREMENT PRIMARY KEY,
            Venta_Id INT NOT NULL,
            Estado VARCHAR(32) NOT NULL DEFAULT 'PENDIENTE',
            Motivo VARCHAR(255) DEFAULT '',
            Nota_Respuesta VARCHAR(255) DEFAULT '',
            Cajero VARCHAR(80) DEFAULT '',
            Cliente VARCHAR(120) DEFAULT '',
            Total DECIMAL(12,2) DEFAULT 0,
            Admin_Id INT NULL,
            Fecha DATETIME,
            Fecha_Respuesta DATETIME NULL,
            Avisado_Caja TINYINT DEFAULT 0,
            Items TEXT NULL,
            INDEX idx_dev_estado (Estado),
            INDEX idx_dev_venta (Venta_Id)
        )
        """
    )
    try:
        cursor.execute("SHOW COLUMNS FROM devolucion_solicitudes LIKE 'Avisado_Caja'")
        if not cursor.fetchone():
            cursor.execute(
                "ALTER TABLE devolucion_solicitudes ADD COLUMN Avisado_Caja TINYINT DEFAULT 0"
            )
    except Exception:
        pass
    try:
        cursor.execute("SHOW COLUMNS FROM devolucion_solicitudes LIKE 'Items'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE devolucion_solicitudes ADD COLUMN Items TEXT NULL")
    except Exception:
        pass


def devoluciones_resueltas_pendientes_aviso():
    """Solicitudes ya resueltas por el admin que la caja todavía no ha avisado."""
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        _ensure_devolucion_solicitudes(cursor)
        cone.commit()
        try:
            cursor.execute(
                """
                SELECT Id, Venta_Id, Estado, COALESCE(Nota_Respuesta, ''), COALESCE(Total, 0), Items
                FROM devolucion_solicitudes
                WHERE Estado IN ('APROBADO', 'RECHAZADO')
                  AND COALESCE(Avisado_Caja, 0) = 0
                ORDER BY Fecha_Respuesta ASC, Id ASC
                """
            )
        except Exception:
            cursor.execute(
                """
                SELECT Id, Venta_Id, Estado, COALESCE(Nota_Respuesta, ''), COALESCE(Total, 0)
                FROM devolucion_solicitudes
                WHERE Estado IN ('APROBADO', 'RECHAZADO')
                  AND COALESCE(Avisado_Caja, 0) = 0
                ORDER BY Fecha_Respuesta ASC, Id ASC
                """
            )
        rows = cursor.fetchall() or []
        cone.close()
        avisos = []
        for row in rows:
            avisos.append(
                {
                    "id": row[0],
                    "venta_id": row[1],
                    "estado": str(row[2] or "").upper(),
                    "nota": row[3] or "",
                    "total": float(row[4] or 0),
                    "items": _parse_items_json(row[5] if len(row) > 5 else None),
                }
            )
        return avisos
    except Exception as error:
        print("Error al leer devoluciones resueltas: {}".format(error))
        return []


def marcar_devoluciones_avisadas(ids):
    ids = [int(i) for i in (ids or []) if i]
    if not ids:
        return
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        _ensure_devolucion_solicitudes(cursor)
        placeholders = ",".join(["%s"] * len(ids))
        cursor.execute(
            "UPDATE devolucion_solicitudes SET Avisado_Caja=1 WHERE Id IN ({})".format(
                placeholders
            ),
            tuple(ids),
        )
        cone.commit()
        cone.close()
    except Exception as error:
        print("Error al marcar devoluciones avisadas: {}".format(error))


def aplicar_resolucion_devolucion(id_venta, estado, usuario, items=None):
    """Si el admin aprobó y aún hay ítems, restaura stock de esos ítems."""
    estado = str(estado or "").upper()
    if "APROB" not in estado:
        return True, "rechazada"
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            "SELECT COALESCE(Anulada, 0) FROM ventas WHERE Id_Venta=%s",
            (id_venta,),
        )
        row = cursor.fetchone()
        cone.close()
        if not row:
            return False, "no existe"
        if int(row[0] or 0) == 1:
            return True, "ya_anulada"
        return devolver_venta(id_venta, usuario or "caja", items=items)
    except Exception as error:
        print("Error al completar anulación remota: {}".format(error))
        return False, str(error)


def _post_devolucion_api(id_venta, usuario, motivo, cliente, items=None):
    import urllib.error
    import urllib.request

    payload = json.dumps(
        {
            "venta_id": int(id_venta),
            "motivo": motivo or "Devolución mismo día",
            "cajero": usuario or "",
            "cliente": cliente or "",
            "items": items or [],
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "{}/api/v1/devoluciones/solicitar/".format(ZYNTRA_API_URL),
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            return 200 <= getattr(resp, "status", 200) < 300, body
    except urllib.error.HTTPError as error:
        try:
            detalle = error.read().decode("utf-8", errors="ignore")
        except Exception:
            detalle = str(error)
        return False, detalle
    except Exception as error:
        return False, str(error)


def solicitar_o_devolver_venta(id_venta, usuario, motivo="", items=None):
    """Mismo día: pide aprobación al dueño. Días anteriores: anula de inmediato."""
    items = _parse_items_json(items) if not isinstance(items, list) else list(items or [])
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            "SELECT Anulada, Fecha_Venta, Total, Cliente_Id FROM ventas WHERE Id_Venta=%s",
            (id_venta,),
        )
        venta = cursor.fetchone()
        if not venta:
            cone.close()
            return False, "No existe esa venta"
        if int(venta[0] or 0) == 1:
            cone.close()
            return False, "La venta ya fue anulada"
        cursor.execute("SHOW COLUMNS FROM ventas LIKE 'Estado'")
        if cursor.fetchone():
            cursor.execute("SELECT Estado FROM ventas WHERE Id_Venta=%s", (id_venta,))
            estado_row = cursor.fetchone()
            estado = str((estado_row or [""])[0] or "").upper()
            if "PENDIENTE" in estado:
                cone.close()
                return True, "Esta devolución ya espera aprobación del administrador en la app."
        fecha = venta[1]
        total = float(venta[2] or 0)
        if items:
            total = round(sum(float(it.get("subtotal") or 0) for it in items), 2) or total
        cliente_id = venta[3]
        cliente = ""
        if cliente_id:
            try:
                cursor.execute(
                    "SELECT Nombre FROM clientes WHERE Id_Cliente=%s",
                    (cliente_id,),
                )
                fila = cursor.fetchone()
                cliente = (fila[0] if fila else "") or ""
            except Exception:
                cliente = ""
        if not _venta_es_de_hoy(fecha):
            cone.close()
            return devolver_venta(id_venta, usuario, items=items or None)

        motivo_txt = motivo or (
            "Devolución parcial mismo día" if items else "Devolución mismo día"
        )
        ok_api, _detalle = _post_devolucion_api(id_venta, usuario, motivo_txt, cliente, items)
        if ok_api:
            cone.close()
            registrar_auditoria(
                usuario,
                "Devolución",
                "Solicitó aprobación remota de la venta #{}".format(id_venta),
            )
            return True, "Solicitud enviada al administrador. La caja espera la aprobación en el celular."

        _ensure_devolucion_solicitudes(cursor)
        cursor.execute(
            """
            SELECT Id FROM devolucion_solicitudes
            WHERE Venta_Id=%s AND Estado='PENDIENTE'
            ORDER BY Id DESC LIMIT 1
            """,
            (id_venta,),
        )
        if cursor.fetchone():
            cone.close()
            return True, "Esta devolución ya espera aprobación del administrador en la app."
        items_txt = json.dumps(items, ensure_ascii=False) if items else None
        try:
            cursor.execute(
                """
                INSERT INTO devolucion_solicitudes
                    (Venta_Id, Estado, Motivo, Cajero, Cliente, Total, Fecha, Items)
                VALUES (%s, 'PENDIENTE', %s, %s, %s, %s, %s, %s)
                """,
                (
                    id_venta,
                    motivo_txt[:250],
                    (usuario or "")[:80],
                    (cliente or "")[:120],
                    total,
                    datetime.now(),
                    items_txt,
                ),
            )
        except Exception:
            cursor.execute(
                """
                INSERT INTO devolucion_solicitudes
                    (Venta_Id, Estado, Motivo, Cajero, Cliente, Total, Fecha)
                VALUES (%s, 'PENDIENTE', %s, %s, %s, %s, %s)
                """,
                (
                    id_venta,
                    motivo_txt[:250],
                    (usuario or "")[:80],
                    (cliente or "")[:120],
                    total,
                    datetime.now(),
                ),
            )
        cursor.execute("SHOW COLUMNS FROM ventas LIKE 'Estado'")
        if cursor.fetchone():
            cursor.execute(
                "UPDATE ventas SET Estado='PENDIENTE_APROBACION' WHERE Id_Venta=%s",
                (id_venta,),
            )
        cone.commit()
        cone.close()
        registrar_auditoria(
            usuario,
            "Devolución",
            "Registró solicitud de devolución de la venta #{}".format(id_venta),
        )
        return True, "Solicitud registrada. El administrador debe aprobarla en la app."
    except Exception as error:
        print("Error al solicitar devolución: {}".format(error))
        return False, "No se pudo enviar la solicitud de devolución"


def hay_conexion():
    try:
        cone = FormularioLogin.conexion_base_de_datos(silencioso=True)
        if not cone:
            return False
        cone.ping(reconnect=False)
        cone.close()
        return True
    except Exception:
        return False


def obtener_receta(id_producto):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            """SELECT r.Insumo_Id, p.Nombre, r.Cantidad
               FROM producto_recetas r
               JOIN productos p ON p.Id_Producto = r.Insumo_Id
               WHERE r.Producto_Id=%s""",
            (id_producto,),
        )
        rows = cursor.fetchall() or []
        cone.close()
        return [{"insumo_id": r[0], "nombre": r[1], "cantidad": float(r[2] or 0)} for r in rows]
    except Exception as error:
        print("Error al leer receta: {}".format(error))
        return []


def guardar_receta(id_producto, insumos):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute("DELETE FROM producto_recetas WHERE Producto_Id=%s", (id_producto,))
        for item in insumos or []:
            cursor.execute(
                "INSERT INTO producto_recetas (Producto_Id, Insumo_Id, Cantidad) VALUES (%s,%s,%s)",
                (id_producto, item["insumo_id"], item["cantidad"]),
            )
        cone.commit()
        cone.close()
        return True
    except Exception as error:
        print("Error al guardar receta: {}".format(error))
        return False


def validar_insumos(id_producto, cantidad_venta):
    faltantes = []
    for item in obtener_receta(id_producto):
        necesario = float(item["cantidad"]) * float(cantidad_venta)
        disponible = cantidad_producto(item["insumo_id"])
        try:
            disponible = float(disponible or 0)
        except (TypeError, ValueError):
            disponible = 0
        if necesario > disponible + 0.0001:
            faltantes.append(f"{item['nombre']} (req. {necesario:g}, hay {disponible:g})")
    return faltantes


def descontar_insumos(id_producto, cantidad_venta):
    receta = obtener_receta(id_producto)
    for item in receta:
        qty = float(item["cantidad"]) * float(cantidad_venta)
        actualizar_stock(item["insumo_id"], qty)
        descontar_lotes(item["insumo_id"], qty)
    return bool(receta)


def registrar_lote(id_producto, cantidad, fecha_vencimiento, proveedor="", lote="", costo=0, factura="", presentacion_id=None, presentacion_nombre=""):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        args = (
            id_producto,
            cantidad,
            fecha_vencimiento or None,
            _ahora(),
            lote or "",
            proveedor or "",
            round(float(costo or 0), 4),
            str(factura or "")[:40],
            presentacion_id,
            str(presentacion_nombre or "")[:80],
        )
        try:
            cursor.execute(
                """INSERT INTO lotes (Producto_Id, Cantidad, Fecha_Vencimiento, Fecha_Ingreso, Lote, Proveedor,
                   Costo, Factura, Presentacion_Id, Presentacion_Nombre)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                args,
            )
        except Exception:
            cursor.execute(
                """INSERT INTO lotes (Producto_Id, Cantidad, Fecha_Vencimiento, Fecha_Ingreso, Lote, Proveedor)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                args[:6],
            )
        cone.commit()
        cone.close()
        return True
    except Exception as error:
        print("Error al registrar lote: {}".format(error))
        return False


def descontar_lotes(id_producto, cantidad):
    restante = float(cantidad or 0)
    if restante <= 0:
        return
    usar_fefo = True
    try:
        usar_fefo = bool(obtener_config_pos().get("usar_fefo", True))
    except Exception:
        usar_fefo = True
    orden = "Fecha_Vencimiento IS NULL, Fecha_Vencimiento ASC, Id ASC" if usar_fefo else "Id ASC"
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            "SELECT Id, Cantidad FROM lotes WHERE Producto_Id=%s AND Cantidad>0 ORDER BY {}".format(orden),
            (id_producto,),
        )
        for lote_id, cant in cursor.fetchall() or []:
            if restante <= 0:
                break
            cant = float(cant or 0)
            toma = min(cant, restante)
            cursor.execute("UPDATE lotes SET Cantidad = Cantidad - %s WHERE Id=%s", (toma, lote_id))
            restante -= toma
        cone.commit()
        cone.close()
    except Exception as error:
        print("Error al descontar lotes: {}".format(error))


def reponer_lotes(id_producto, cantidad):
    qty = float(cantidad or 0)
    if qty <= 0:
        return False
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            """SELECT Id FROM lotes WHERE Producto_Id=%s
               ORDER BY Fecha_Vencimiento IS NULL, Fecha_Vencimiento ASC, Id DESC LIMIT 1""",
            (id_producto,),
        )
        row = cursor.fetchone()
        if row:
            cursor.execute("UPDATE lotes SET Cantidad = Cantidad + %s WHERE Id=%s", (qty, row[0]))
        else:
            cursor.execute(
                """INSERT INTO lotes (Producto_Id, Cantidad, Fecha_Ingreso, Lote, Proveedor)
                   VALUES (%s, %s, %s, %s, %s)""",
                (id_producto, qty, _ahora(), "DEVOLUCION", ""),
            )
        cone.commit()
        cone.close()
        return True
    except Exception as error:
        print("Error al reponer lotes: {}".format(error))
        return False


def alertas_margen_presentaciones(producto_id, costo_base, iva=0):
    avisos = []
    try:
        costo_base = float(costo_base or 0)
    except (TypeError, ValueError):
        return avisos
    for pres in listar_presentaciones(producto_id, solo_activas=False) or []:
        costo = costo_equivalente(costo_base, pres.get("factor") or 1)
        venta = float(pres.get("precio_venta") or 0)
        nombre = pres.get("nombre") or "Unidad"
        if venta <= 0:
            continue
        if venta <= costo:
            from dinero import formato_dinero

            avisos.append("{}: costo {} ≥ precio {}".format(nombre, formato_dinero(costo), formato_dinero(venta)))
            continue
        margen = ((venta - costo) / venta) * 100
        if margen < 5:
            avisos.append("{}: utilidad {:.1f}% (muy baja)".format(nombre, margen))
    return avisos


def ajustar_inventario(producto_id, cantidad_pres, factor, tipo, motivo, usuario="", presentacion_id=None):
    tipo = str(tipo or "ENTRADA").upper()
    if tipo not in ("ENTRADA", "SALIDA"):
        return False, "El ajuste debe ser entrada o salida"
    motivo = str(motivo or "").strip()
    if not motivo:
        return False, "Indique el motivo del ajuste"
    n = _a_float_precio(cantidad_pres)
    if n is None:
        return False, "Cantidad inválida"
    cant = n
    try:
        fac = float(factor or 1) or 1
    except (TypeError, ValueError):
        return False, "Cantidad inválida"
    if cant <= 0:
        return False, "La cantidad debe ser mayor a 0"
    base = a_unidades_base(cant, fac)
    producto = parse_producto(obtener_producto(producto_id) or [])
    if not producto:
        return False, "No existe el producto"
    stock = float(producto.get("cantidad") or 0)
    if tipo == "SALIDA":
        if stock + 0.0001 < base:
            return False, "No hay suficiente existencia ({} en base)".format(stock)
        actualizar_stock(producto_id, base)
        descontar_lotes(producto_id, base)
    else:
        cambiar_stock_base(producto_id, base)
    registrar_movimiento_inventario(producto_id, tipo, cant, fac, motivo, usuario or "", presentacion_id)
    registrar_auditoria(
        usuario,
        "Ajuste inventario",
        "{} {} × {} ({} base) de {}".format(tipo, cant, producto.get("nombre"), base, producto_id),
    )
    return True, "{} de {} unidades base registrada.".format(tipo.title(), base)


def listar_movimientos_inventario(producto_id, limite=80):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            """SELECT Fecha, Tipo, Cantidad_Presentacion, Factor, Cantidad_Base, Motivo, Usuario
               FROM inventario_movimientos WHERE Producto_Id=%s
               ORDER BY Fecha DESC, Id DESC LIMIT %s""",
            (producto_id, int(limite)),
        )
        rows = cursor.fetchall() or []
        cone.close()
        return rows
    except Exception as error:
        print("Error al listar movimientos: {}".format(error))
        return []


def listar_categorias_productos():
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            """SELECT DISTINCT TRIM(Categoria) FROM productos
               WHERE Categoria IS NOT NULL AND TRIM(Categoria) <> ''
               ORDER BY 1"""
        )
        rows = [r[0] for r in (cursor.fetchall() or []) if r and r[0]]
        cone.close()
        return rows
    except Exception as error:
        print("Error al listar categorías: {}".format(error))
        return []


def listar_ubicaciones_productos():
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            """SELECT DISTINCT TRIM(Ubicacion) FROM productos
               WHERE Ubicacion IS NOT NULL AND TRIM(Ubicacion) <> ''
               ORDER BY 1"""
        )
        rows = [r[0] for r in (cursor.fetchall() or []) if r and r[0]]
        cone.close()
        return rows
    except Exception as error:
        print("Error al listar ubicaciones: {}".format(error))
        return []


def _productos_para_conteo(filtro_tipo, filtro_valor):
    filtro_tipo = (filtro_tipo or "todos").strip().lower()
    filtro_valor = (filtro_valor or "").strip()
    cone = FormularioLogin.conexion_base_de_datos()
    if not cone:
        return []
    cursor = cone.cursor()
    try:
        sql = """SELECT Id_Producto, Nombre, COALESCE(Categoria,''), COALESCE(Ubicacion,''),
                        COALESCE(Cantidad,0), COALESCE(Unidad_Base,'Unidad')
                 FROM productos"""
        params = []
        if filtro_tipo == "categoria" and filtro_valor:
            sql += " WHERE TRIM(Categoria)=%s"
            params.append(filtro_valor)
        elif filtro_tipo == "ubicacion" and filtro_valor:
            sql += " WHERE TRIM(Ubicacion)=%s"
            params.append(filtro_valor)
        sql += " ORDER BY COALESCE(Ubicacion,''), Nombre, Id_Producto"
        cursor.execute(sql, params)
        return cursor.fetchall() or []
    finally:
        try:
            cursor.close()
            cone.close()
        except Exception:
            pass


_INV_FISICO_SCHEMA_OK = False


def ensure_inventario_fisico_schema():
    """Crea solo tablas de conteo (rápido). Evita ensure_schema() completo al abrir el módulo."""
    global _INV_FISICO_SCHEMA_OK
    if _INV_FISICO_SCHEMA_OK:
        return True
    cone = FormularioLogin.conexion_base_de_datos()
    if not cone:
        return False
    cursor = cone.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS inventario_sesiones (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Nombre VARCHAR(160) NOT NULL,
                Filtro_Tipo VARCHAR(40) DEFAULT 'todos',
                Filtro_Valor VARCHAR(120) DEFAULT '',
                Modo VARCHAR(20) DEFAULT 'asistido',
                Estado VARCHAR(20) DEFAULT 'abierta',
                Total_Items INT DEFAULT 0,
                Contados INT DEFAULT 0,
                Usuario VARCHAR(80) DEFAULT '',
                Fecha_Inicio DATETIME,
                Fecha_Cierre DATETIME NULL,
                Notas VARCHAR(255) DEFAULT ''
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS inventario_sesion_items (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Sesion_Id INT NOT NULL,
                Producto_Id INT NOT NULL,
                Nombre VARCHAR(200) DEFAULT '',
                Categoria VARCHAR(80) DEFAULT '',
                Ubicacion VARCHAR(80) DEFAULT '',
                Unidad_Base VARCHAR(40) DEFAULT 'Unidad',
                Stock_Asignado DECIMAL(14,6) DEFAULT 0,
                Stock_Al_Contar DECIMAL(14,6) NULL,
                Cantidad_Fisica DECIMAL(14,6) NULL,
                Diferencia DECIMAL(14,6) NULL,
                Estado VARCHAR(20) DEFAULT 'pendiente',
                Fecha_Conteo DATETIME NULL,
                Usuario_Conteo VARCHAR(80) DEFAULT '',
                Ajustado TINYINT DEFAULT 0,
                INDEX idx_sesion_estado (Sesion_Id, Estado),
                INDEX idx_sesion_prod (Sesion_Id, Producto_Id)
            )
            """
        )
        cone.commit()
        _INV_FISICO_SCHEMA_OK = True
        return True
    except Exception as error:
        print("Error esquema inventario físico: {}".format(error))
        try:
            cone.rollback()
        except Exception:
            pass
        return False
    finally:
        cursor.close()
        cone.close()


def crear_sesion_inventario(nombre, filtro_tipo="todos", filtro_valor="", usuario="", notas=""):
    ensure_inventario_fisico_schema()
    nombre = str(nombre or "").strip()
    if not nombre:
        return None, "Indique un nombre para la sesión"
    filtro_tipo = (filtro_tipo or "todos").strip().lower()
    if filtro_tipo not in ("todos", "categoria", "ubicacion"):
        filtro_tipo = "todos"
    filtro_valor = str(filtro_valor or "").strip()
    if filtro_tipo in ("categoria", "ubicacion") and not filtro_valor:
        return None, "Seleccione el valor del filtro"
    productos = _productos_para_conteo(filtro_tipo, filtro_valor)
    if not productos:
        return None, "No hay productos para ese filtro"
    cone = FormularioLogin.conexion_base_de_datos()
    if not cone:
        return None, "Sin conexión a la base de datos"
    cursor = cone.cursor()
    try:
        cursor.execute(
            """INSERT INTO inventario_sesiones
               (Nombre, Filtro_Tipo, Filtro_Valor, Modo, Estado, Total_Items, Contados, Usuario, Fecha_Inicio, Notas)
               VALUES (%s,%s,%s,'asistido','abierta',%s,0,%s,%s,%s)""",
            (nombre[:160], filtro_tipo, filtro_valor[:120], len(productos), usuario or "", _ahora(), (notas or "")[:255]),
        )
        sesion_id = cursor.lastrowid
        for row in productos:
            pid, nom, cat, ubi, cant, unidad = row
            cursor.execute(
                """INSERT INTO inventario_sesion_items
                   (Sesion_Id, Producto_Id, Nombre, Categoria, Ubicacion, Unidad_Base,
                    Stock_Asignado, Estado)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,'pendiente')""",
                (
                    sesion_id,
                    int(pid),
                    str(nom or "")[:200],
                    str(cat or "")[:80],
                    str(ubi or "")[:80],
                    str(unidad or "Unidad")[:40],
                    float(cant or 0),
                ),
            )
        cone.commit()
        registrar_auditoria(
            usuario,
            "Inventario físico",
            "Sesión #{} creada ({}) con {} productos".format(sesion_id, nombre, len(productos)),
        )
        return sesion_id, "Sesión creada con {} productos.".format(len(productos))
    except Exception as error:
        try:
            cone.rollback()
        except Exception:
            pass
        print("Error al crear sesión inventario: {}".format(error))
        return None, "No se pudo crear la sesión: {}".format(error)
    finally:
        cursor.close()
        cone.close()


def listar_sesiones_inventario(solo_abiertas=False, limite=40):
    ensure_inventario_fisico_schema()
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        sql = """SELECT Id, Nombre, Filtro_Tipo, Filtro_Valor, Estado, Total_Items, Contados,
                        Usuario, Fecha_Inicio, Fecha_Cierre, Modo
                 FROM inventario_sesiones"""
        if solo_abiertas:
            sql += " WHERE Estado IN ('abierta','pausada')"
        sql += " ORDER BY Fecha_Inicio DESC LIMIT %s"
        cursor.execute(sql, (int(limite),))
        rows = cursor.fetchall() or []
        cone.close()
        out = []
        for r in rows:
            total = int(r[5] or 0)
            contados = int(r[6] or 0)
            pct = int(round(100.0 * contados / total)) if total else 0
            out.append(
                {
                    "id": r[0],
                    "nombre": r[1],
                    "filtro_tipo": r[2],
                    "filtro_valor": r[3],
                    "estado": r[4],
                    "total": total,
                    "contados": contados,
                    "usuario": r[7],
                    "fecha_inicio": r[8],
                    "fecha_cierre": r[9],
                    "modo": r[10],
                    "pct": pct,
                }
            )
        return out
    except Exception as error:
        print("Error al listar sesiones: {}".format(error))
        return []


def obtener_sesion_inventario(sesion_id):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            """SELECT Id, Nombre, Filtro_Tipo, Filtro_Valor, Estado, Total_Items, Contados,
                      Usuario, Fecha_Inicio, Fecha_Cierre, Modo, Notas
               FROM inventario_sesiones WHERE Id=%s""",
            (int(sesion_id),),
        )
        r = cursor.fetchone()
        cone.close()
        if not r:
            return None
        total = int(r[5] or 0)
        contados = int(r[6] or 0)
        return {
            "id": r[0],
            "nombre": r[1],
            "filtro_tipo": r[2],
            "filtro_valor": r[3],
            "estado": r[4],
            "total": total,
            "contados": contados,
            "usuario": r[7],
            "fecha_inicio": r[8],
            "fecha_cierre": r[9],
            "modo": r[10],
            "notas": r[11],
            "pct": int(round(100.0 * contados / total)) if total else 0,
        }
    except Exception as error:
        print("Error al obtener sesión: {}".format(error))
        return None


def _refrescar_progreso_sesion(cursor, sesion_id):
    cursor.execute(
        """SELECT
              SUM(CASE WHEN Estado IN ('contado','ajustado','omitido') THEN 1 ELSE 0 END),
              COUNT(*)
           FROM inventario_sesion_items WHERE Sesion_Id=%s""",
        (int(sesion_id),),
    )
    row = cursor.fetchone() or (0, 0)
    contados = int(row[0] or 0)
    total = int(row[1] or 0)
    cursor.execute(
        "UPDATE inventario_sesiones SET Contados=%s, Total_Items=%s WHERE Id=%s",
        (contados, total, int(sesion_id)),
    )
    return contados, total


def listar_items_sesion(sesion_id, estado=None):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        sql = """SELECT Id, Producto_Id, Nombre, Categoria, Ubicacion, Unidad_Base,
                        Stock_Asignado, Stock_Al_Contar, Cantidad_Fisica, Diferencia,
                        Estado, Fecha_Conteo, Usuario_Conteo, Ajustado
                 FROM inventario_sesion_items WHERE Sesion_Id=%s"""
        params = [int(sesion_id)]
        if estado:
            sql += " AND Estado=%s"
            params.append(estado)
        sql += " ORDER BY Ubicacion, Nombre, Id"
        cursor.execute(sql, params)
        rows = cursor.fetchall() or []
        cone.close()
        out = []
        for r in rows:
            out.append(
                {
                    "id": r[0],
                    "producto_id": r[1],
                    "nombre": r[2],
                    "categoria": r[3],
                    "ubicacion": r[4],
                    "unidad_base": r[5],
                    "stock_asignado": float(r[6] or 0),
                    "stock_al_contar": None if r[7] is None else float(r[7]),
                    "cantidad_fisica": None if r[8] is None else float(r[8]),
                    "diferencia": None if r[9] is None else float(r[9]),
                    "estado": r[10],
                    "fecha_conteo": r[11],
                    "usuario_conteo": r[12],
                    "ajustado": int(r[13] or 0),
                }
            )
        return out
    except Exception as error:
        print("Error al listar ítems sesión: {}".format(error))
        return []


def siguiente_item_pendiente(sesion_id, despues_id=None):
    items = listar_items_sesion(sesion_id, estado="pendiente")
    if not items:
        return None
    if despues_id:
        for i, it in enumerate(items):
            if it["id"] == despues_id and i + 1 < len(items):
                return items[i + 1]
    return items[0]


def buscar_item_sesion_por_codigo(sesion_id, texto):
    texto = str(texto or "").strip()
    if not texto:
        return None
    items = listar_items_sesion(sesion_id)
    if texto.isdigit():
        for it in items:
            if str(it["producto_id"]) == texto:
                return it
    q = texto.lower()
    for it in items:
        if q in (it.get("nombre") or "").lower():
            return it
    return None


def registrar_conteo_item(item_id, cantidad_fisica, usuario="", aplicar_ajuste=True):
    """Guarda conteo asistido; si hay diferencia aplica stock y movimiento CONTEO."""
    ensure_inventario_fisico_schema()
    n = _a_float_precio(cantidad_fisica)
    if n is None:
        return False, "Cantidad física inválida", None
    if n < 0:
        return False, "La cantidad no puede ser negativa", None
    cone = FormularioLogin.conexion_base_de_datos()
    if not cone:
        return False, "Sin conexión", None
    cursor = cone.cursor()
    try:
        cursor.execute(
            """SELECT Id, Sesion_Id, Producto_Id, Nombre, Estado, Ajustado
               FROM inventario_sesion_items WHERE Id=%s""",
            (int(item_id),),
        )
        row = cursor.fetchone()
        if not row:
            return False, "Ítem no encontrado", None
        _id, sesion_id, producto_id, nombre, estado, ya_ajustado = row
        if estado == "omitido":
            return False, "Este producto fue omitido", None

        cursor.execute("SELECT Cantidad FROM productos WHERE Id_Producto=%s", (int(producto_id),))
        prow = cursor.fetchone()
        if not prow:
            return False, "Producto eliminado del catálogo", None
        stock_actual = float(prow[0] or 0)
        fisica = float(n)
        diferencia = fisica - stock_actual

        cursor.execute(
            """UPDATE inventario_sesion_items
               SET Stock_Al_Contar=%s, Cantidad_Fisica=%s, Diferencia=%s,
                   Estado=%s, Fecha_Conteo=%s, Usuario_Conteo=%s
               WHERE Id=%s""",
            (
                stock_actual,
                fisica,
                diferencia,
                "contado",
                _ahora(),
                usuario or "",
                int(item_id),
            ),
        )

        msg_extra = ""
        aplicar_lotes = 0.0
        if aplicar_ajuste and abs(diferencia) > 0.0001:
            if diferencia > 0:
                cursor.execute(
                    "UPDATE productos SET Cantidad = Cantidad + %s WHERE Id_Producto=%s",
                    (diferencia, int(producto_id)),
                )
            else:
                if stock_actual + 0.0001 < abs(diferencia):
                    cone.rollback()
                    return False, "Stock insuficiente para aplicar el faltante", None
                cursor.execute(
                    "UPDATE productos SET Cantidad = Cantidad - %s WHERE Id_Producto=%s",
                    (abs(diferencia), int(producto_id)),
                )
                aplicar_lotes = abs(diferencia)
            motivo = "Conteo sesión #{} · físico {} vs sistema {}".format(
                sesion_id, fisica, stock_actual
            )
            cursor.execute(
                """INSERT INTO inventario_movimientos
                   (Producto_Id, Presentacion_Id, Tipo, Cantidad_Presentacion, Factor, Cantidad_Base, Motivo, Usuario, Fecha)
                   VALUES (%s,NULL,'CONTEO',%s,1,%s,%s,%s,%s)""",
                (
                    int(producto_id),
                    abs(diferencia),
                    abs(diferencia),
                    motivo[:220],
                    usuario or "",
                    _ahora(),
                ),
            )
            cursor.execute(
                "UPDATE inventario_sesion_items SET Estado='ajustado', Ajustado=1 WHERE Id=%s",
                (int(item_id),),
            )
            msg_extra = " Stock ajustado ({}{}).".format(
                "+" if diferencia > 0 else "",
                int(diferencia) if float(diferencia) == int(diferencia) else round(diferencia, 2),
            )
        elif abs(diferencia) <= 0.0001:
            cursor.execute(
                "UPDATE inventario_sesion_items SET Estado='ajustado', Ajustado=1 WHERE Id=%s",
                (int(item_id),),
            )
            msg_extra = " Cuadre exacto."

        contados, total = _refrescar_progreso_sesion(cursor, sesion_id)
        cone.commit()
        if aplicar_lotes > 0:
            try:
                descontar_lotes(producto_id, aplicar_lotes)
            except Exception:
                pass
        registrar_auditoria(
            usuario,
            "Inventario físico",
            "Conteo {} ({}) físico={} sistema={} diff={}".format(
                producto_id, nombre, fisica, stock_actual, diferencia
            ),
        )
        return (
            True,
            "Conteo guardado.{} Avance {}/{}.".format(msg_extra, contados, total),
            {"sesion_id": sesion_id, "contados": contados, "total": total, "diferencia": diferencia},
        )
    except Exception as error:
        try:
            cone.rollback()
        except Exception:
            pass
        print("Error al registrar conteo: {}".format(error))
        return False, "No se pudo guardar el conteo: {}".format(error), None
    finally:
        cursor.close()
        cone.close()


def omitir_item_conteo(item_id, usuario=""):
    cone = FormularioLogin.conexion_base_de_datos()
    if not cone:
        return False, "Sin conexión"
    cursor = cone.cursor()
    try:
        cursor.execute(
            "SELECT Sesion_Id, Estado FROM inventario_sesion_items WHERE Id=%s",
            (int(item_id),),
        )
        row = cursor.fetchone()
        if not row:
            return False, "Ítem no encontrado"
        sesion_id, estado = row
        if estado in ("contado", "ajustado"):
            return False, "Ya fue contado; no se puede omitir"
        cursor.execute(
            """UPDATE inventario_sesion_items
               SET Estado='omitido', Fecha_Conteo=%s, Usuario_Conteo=%s
               WHERE Id=%s""",
            (_ahora(), usuario or "", int(item_id)),
        )
        _refrescar_progreso_sesion(cursor, sesion_id)
        cone.commit()
        return True, "Producto omitido"
    except Exception as error:
        try:
            cone.rollback()
        except Exception:
            pass
        return False, str(error)
    finally:
        cursor.close()
        cone.close()


def pausar_sesion_inventario(sesion_id):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            "UPDATE inventario_sesiones SET Estado='pausada' WHERE Id=%s AND Estado='abierta'",
            (int(sesion_id),),
        )
        cone.commit()
        cone.close()
        return True
    except Exception as error:
        print("Error al pausar sesión: {}".format(error))
        return False


def reanudar_sesion_inventario(sesion_id):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            "UPDATE inventario_sesiones SET Estado='abierta' WHERE Id=%s AND Estado IN ('abierta','pausada')",
            (int(sesion_id),),
        )
        cone.commit()
        cone.close()
        return True
    except Exception as error:
        print("Error al reanudar sesión: {}".format(error))
        return False


def cerrar_sesion_inventario(sesion_id, usuario="", forzar=False):
    sesion = obtener_sesion_inventario(sesion_id)
    if not sesion:
        return False, "Sesión no encontrada"
    pendientes = listar_items_sesion(sesion_id, estado="pendiente")
    if pendientes and not forzar:
        return False, "Quedan {} productos pendientes. Complete o omita, o fuerce el cierre.".format(
            len(pendientes)
        )
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            "UPDATE inventario_sesiones SET Estado='cerrada', Fecha_Cierre=%s WHERE Id=%s",
            (_ahora(), int(sesion_id)),
        )
        cone.commit()
        cone.close()
        registrar_auditoria(
            usuario,
            "Inventario físico",
            "Sesión #{} cerrada ({}%)".format(sesion_id, sesion.get("pct")),
        )
        return True, "Sesión cerrada"
    except Exception as error:
        return False, str(error)


def resumen_diferencias_sesion(sesion_id):
    items = [
        it
        for it in listar_items_sesion(sesion_id)
        if it.get("estado") in ("contado", "ajustado") and it.get("diferencia") is not None
    ]
    faltantes = [it for it in items if (it.get("diferencia") or 0) < -0.0001]
    sobrantes = [it for it in items if (it.get("diferencia") or 0) > 0.0001]
    return {
        "faltantes": faltantes,
        "sobrantes": sobrantes,
        "cuadre": [it for it in items if abs(it.get("diferencia") or 0) <= 0.0001],
        "total_faltante_unidades": sum(abs(it["diferencia"]) for it in faltantes),
        "total_sobrante_unidades": sum(it["diferencia"] for it in sobrantes),
    }


def historial_compras_producto(producto_id, limite=80):
    """Facturas de compra asociadas al producto (kardex de entradas desde proveedores)."""
    if not producto_id:
        return []
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            """SELECT c.Fecha, c.Numero_Factura, c.Proveedor,
                      COALESCE(NULLIF(i.Presentacion_Nombre, ''), 'Unidad'),
                      i.Cantidad, COALESCE(NULLIF(i.Cantidad_Base, 0), i.Cantidad),
                      i.Precio_Base, i.Total_Linea, c.Usuario
               FROM compra_items i
               JOIN compras c ON c.Id = i.Compra_Id
               WHERE i.Producto_Id=%s
               ORDER BY c.Fecha DESC, c.Id DESC
               LIMIT %s""",
            (int(producto_id), int(limite)),
        )
        rows = cursor.fetchall() or []
        cone.close()
        return rows
    except Exception as error:
        print("Error al listar compras del producto: {}".format(error))
        return []


def historial_ventas_producto(producto_id, limite=80):
    """Salidas por venta del producto."""
    if not producto_id:
        return []
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            """SELECT v.Fecha_Venta,
                      COALESCE(NULLIF(vp.Presentacion_Nombre, ''), 'Unidad'),
                      COALESCE(NULLIF(vp.Cantidad_Presentacion, 0), vp.Cantidad),
                      CASE
                        WHEN COALESCE(NULLIF(vp.Cantidad_Presentacion, 0), vp.Cantidad) > 0
                        THEN vp.Subtotal / COALESCE(NULLIF(vp.Cantidad_Presentacion, 0), vp.Cantidad)
                        ELSE 0
                      END,
                      vp.Subtotal,
                      COALESCE(e.Usuario, e.Nombre, '')
               FROM productos_has_ventas vp
               JOIN ventas v ON v.Id_Venta = vp.Ventas_Id_Factura
               LEFT JOIN empleados e ON e.Id_Empleados = v.Empleados_Id_Empleados
               WHERE vp.Productos_Id_Producto=%s
                 AND COALESCE(v.Anulada, 0) = 0
               ORDER BY v.Fecha_Venta DESC, v.Id_Venta DESC
               LIMIT %s""",
            (int(producto_id), int(limite)),
        )
        rows = cursor.fetchall() or []
        cone.close()
        return rows
    except Exception as error:
        print("Error al listar ventas del producto: {}".format(error))
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            cursor.execute(
                """SELECT v.Fecha_Venta, 'Unidad', vp.Cantidad,
                          CASE WHEN vp.Cantidad > 0 THEN vp.Subtotal / vp.Cantidad ELSE 0 END,
                          vp.Subtotal, ''
                   FROM productos_has_ventas vp
                   JOIN ventas v ON v.Id_Venta = vp.Ventas_Id_Factura
                   WHERE vp.Productos_Id_Producto=%s
                   ORDER BY v.Fecha_Venta DESC
                   LIMIT %s""",
                (int(producto_id), int(limite)),
            )
            rows = cursor.fetchall() or []
            cone.close()
            return rows
        except Exception as error2:
            print("Error alterno ventas producto: {}".format(error2))
            return []

def mapa_vencimientos():
    resultado = {}
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            """SELECT Producto_Id, MIN(Fecha_Vencimiento)
               FROM lotes
               WHERE Cantidad > 0 AND Fecha_Vencimiento IS NOT NULL
               GROUP BY Producto_Id"""
        )
        for producto_id, fecha in cursor.fetchall() or []:
            resultado[int(producto_id)] = fecha
        cone.close()
    except Exception as error:
        print("Error al leer vencimientos: {}".format(error))
    return resultado


def lotes_por_vencer(dias=None):
    if dias is None:
        try:
            dias = int(obtener_config_pos().get("dias_alerta_vence") or 30)
        except (TypeError, ValueError):
            dias = 30
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            """SELECT l.Id, p.Id_Producto, p.Nombre, l.Cantidad, l.Fecha_Vencimiento, l.Lote, l.Proveedor
               FROM lotes l
               JOIN productos p ON p.Id_Producto = l.Producto_Id
               WHERE l.Cantidad > 0 AND l.Fecha_Vencimiento IS NOT NULL
                 AND l.Fecha_Vencimiento <= DATE_ADD(CURDATE(), INTERVAL %s DAY)
               ORDER BY l.Fecha_Vencimiento ASC""",
            (int(dias),),
        )
        rows = cursor.fetchall() or []
        cone.close()
        return rows
    except Exception as error:
        print("Error al consultar lotes por vencer: {}".format(error))
        return []



