// lib/modelos/db_helper.dart
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import 'dart:async';

class DBHelper {
  static Future<Database> initDB() async {
    final path = join(await getDatabasesPath(), 'app_db.db');
    return openDatabase(
      path,
      version: 1,
      onCreate: (db, version) async {
        await db.execute('''
          CREATE TABLE usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            correo TEXT UNIQUE,
            telefono TEXT,
            contrasena TEXT
          )
        ''');
      },
    );
  }

  // Método mejorado: registro con campos directos
  static Future<int> registrarUsuario(
    String nombre,
    String correo,
    String telefono,
    String contrasena,
  ) async {
    final db = await initDB();
    try {
      return await db.insert('usuarios', {
        'nombre': nombre,
        'correo': correo,
        'telefono': telefono,
        'contrasena': contrasena,
      }, conflictAlgorithm: ConflictAlgorithm.fail);
    } catch (e) {
      throw Exception('Error al registrar usuario: $e');
    }
  }

  static Future<bool> login(String nombre, String contrasena) async {
    final db = await initDB();
    final resultado = await db.query(
      'usuarios',
      where: 'nombre = ? AND contrasena = ?',
      whereArgs: [nombre, contrasena],
    );

    // Verifica si se encontró un usuario con las credenciales proporcionadas
    return resultado.isNotEmpty;
  }

  static Future<bool> existeUsuario(String correo) async {
    final db = await initDB();
    final res = await db.query(
      'usuarios',
      where: 'correo = ?',
      whereArgs: [correo],
    );
    return res.isNotEmpty;
  }
}
