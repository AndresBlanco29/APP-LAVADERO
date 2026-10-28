from conexionLogin import *
import mysql.connector


class usuarios():
    
    def ValidacionUsuarios(usuario, contraseña):
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            # Consulta en la tabla admin
            query_admin = "SELECT * FROM admin WHERE usuario = %s AND contrasena = %s"
            cursor.execute(query_admin, (usuario, contraseña))
            resultados_admin = cursor.fetchall()
            
            # Consulta en la tabla usuarios
            query_usuarios = "SELECT * FROM usuarios WHERE Usuario = %s AND Contraseña = %s"
            cursor.execute(query_usuarios, (usuario, contraseña))
            resultados_usuarios = cursor.fetchall()
            
            cone.close()
            if resultados_admin or resultados_usuarios:
                print("Credenciales validadas correctamente para:", usuario)  # debug
                return True
            else:
                print("No se encontraron registros para:", usuario)  # debug
                return False
        except mysql.connector.Error as error:
            print("Error al conectar la base de datos {}".format(error))
            return False

    def Obtener_Nombre_Empleado(Usuario):
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            
           
            query = """
                SELECT e.Nombres AS Nombre 
                FROM usuarios u
                JOIN empleados e ON u.Empleados_Id_Empleados = e.Id_empleados
                WHERE u.Usuario = %s
                UNION
                SELECT a.Nombre AS Nombre 
                FROM admin a
                WHERE a.usuario = %s
            """
            cursor.execute(query, (Usuario, Usuario))
            resultado = cursor.fetchone()
            
            cursor.close()
            cone.close()  
            
            if resultado:
                return resultado[0]  
            
            return None  

        except mysql.connector.Error as error:
            print(f"Error al conectar a la base de datos: {error}")
            return None  

    def Obtener_Id_Empleado(Usuario):
        try:
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            query = """
                SELECT u.Empleados_Id_Empleados AS id
                FROM usuarios u
                WHERE u.Usuario = %s
                UNION
                SELECT a.Id_admin AS id
                FROM admin a
                WHERE a.usuario = %s
            """
            cursor.execute(query, (Usuario, Usuario))
            resultado = cursor.fetchone()
            print(f"[DEBUG] Resultado de Obtener_Id_Empleado para {Usuario}: {resultado}")
            cursor.close()
            cone.close()
            return resultado[0] if resultado else None
        except mysql.connector.Error as error:
            print(f"Error al conectar a la base de datos: {error}")
            return None



