from conexionLogin import *
from inventario import *
import mysql.connector

    
def mostrar_Productos():
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            cursor.execute("SELECT * FROM productos")
            Resultado = cursor.fetchall()
            cone.commit()
            cone.close()
            return Resultado
        
        except mysql.connector.Error as error:
            print("Error al mostrar los productos {}".format(error))
            

            
def Agregar_Producto(Nombre, precio_venta, precio_compra, cantidad, marca, descuento):
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            sql=("INSERT INTO productos values (null, %s, %s, %s, %s, %s, %s);")
            valores = (Nombre, precio_venta, precio_compra, cantidad, marca, descuento)
            cursor.execute(sql,valores)
            cone.commit()
            cone.close()
        except mysql.connector.Error as error:
            print("Error al agregar un producto {}".format(error))
            
def Agregar_Proveedor(NIT,Nombre, Telefono, Direccion):
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            sql = ("INSERT INTO proveedores VALUES (%s, %s, %s, %s);")
            valores = (NIT,Nombre, Telefono, Direccion)
            cursor.execute(sql, valores)
            cone.commit()
            cone.close()
        except mysql.connector.Error as error:
            print("Error al agregar un proveedor {}".format(error))

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
            sql=("SELECT * FROM productos WHERE Id_Producto LIKE %s OR Nombre LIKE %s OR Marca LIKE %s;")
            valores = ('%'+Codigo+'%','%'+Nombre+'%', '%' + Marca + '%')
            cursor.execute(sql,valores)
            Resultado = cursor.fetchall()
            cone.commit()
            cone.close()
            return Resultado
        except mysql.connector.Error as error:
            print("Error al buscar los productos {}".format(error))
            
def buscar_proveedor(NIT, Nombre):
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            sql = ("SELECT * FROM proveedores WHERE NIT LIKE %s OR Razon_Social LIKE %s")
            valores = ('%' + NIT + '%', '%' + Nombre + '%')
            cursor.execute(sql, valores)
            resultado = cursor.fetchall()
            cone.commit()
            cone.close()
            return resultado
        except mysql.connector.Error as error:
            print("Error al buscar los productos {}".format(error))
            
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
            
def modificar_producto(Nombre, precio_venta, precio_compra, Cantidad, Marca, Descuento, Codigo):
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            sql = ("UPDATE productos SET Nombre=%s, Precio_Venta=%s, Precio_Compra=%s, Cantidad=%s, Marca=%s, Descuento=%s WHERE Id_Producto=%s;")
            valores = (Nombre, precio_venta, precio_compra, Cantidad, Marca, Descuento, Codigo)
            cursor.execute(sql, valores)
            filas_afectadas = cursor.rowcount
            cone.commit()
            cone.close()
            return filas_afectadas > 0
        except mysql.connector.Error as error:
            print("Error al modificar los datos {}".format(error))
            
def modificar_proveedor(Nombre, Telefono, Direccion, NIT):
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            sql = "UPDATE proveedores SET Razon_Social = %s, Telefono = %s, Direccion = %s WHERE NIT = %s"
            valores = (Nombre, Telefono, Direccion, NIT)
            cursor.execute(sql, valores)
            filas_afectadas = cursor.rowcount
            cone.commit()
            cone.close()
            return filas_afectadas > 0
        except mysql.connector.Error as error:
            print("Error al modificar los datos {}".format(error))
            
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
            return cursor.rowcount
            
        except mysql.connector.Error as error:
            print("Error al conectarse a la base de datos {}".format(error))
            
def eliminar_proveedor(NIT):
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            sql = "DELETE FROM proveedores WHERE NIT = %s"
            valor = (NIT,)
            cursor.execute(sql, valor)
            cone.commit()
            cone.close()
            return cursor.rowcount
        except mysql.connector.Error as error:
            print("Error al conectarse a la base de datos {}".format(error))
            
def eliminar_personal(Codigo):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()

     
        print(f"Código a eliminar: {Codigo}")

  
        cursor.execute("SELECT Empleados_Id_Empleados FROM usuarios WHERE Id_Usuario = %s", (Codigo,))
        resultado = cursor.fetchone()
        
        if resultado:
            Id_Empleado = resultado[0]  

            # Primero eliminar el usuario
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
            sql = "SELECT Razon_Social FROM proveedores"
            cursor.execute(sql)
            proveedores = [row[0] for row in cursor.fetchall()]
            cursor.close()
            cone.close()
            return proveedores
        except mysql.connector.Error as error:
            print("Error al conectar la base de datos {}".format(error))
            
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
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            query = "UPDATE productos SET cantidad = %s WHERE nombre = %s"
            cursor.execute(query, (nueva_cantidad, nombre.strip()))
            cone.commit()
            cone.close()
        except mysql.connector.Error as error:
            print("Error al conectar la base de dato {}".format(error))
            
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
            cursor= cone.cursor()
            sql = "SELECT * FROM proveedores"
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
