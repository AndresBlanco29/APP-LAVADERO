import 'package:flutter/material.dart';
import 'package:flutter_application_1/db_helper.dart';
import 'login.dart'; // nuevo: importar la página de login

//void main() {
//runApp(const MyApp());
//}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Registro',
      debugShowCheckedModeBanner: false,
      home: const RegistroPage(),
    );
  }
}

class RegistroPage extends StatefulWidget {
  const RegistroPage({super.key});

  @override
  State<RegistroPage> createState() => _RegistroPageState();
}

class _RegistroPageState extends State<RegistroPage> {
  final TextEditingController _nombreController = TextEditingController();
  final TextEditingController _correoController = TextEditingController();
  final TextEditingController _telefonoController = TextEditingController();
  final TextEditingController _contrasenaController = TextEditingController();

  void _registrarUsuario() async {
    final nombre = _nombreController.text.trim();
    final correo = _correoController.text.trim();
    final telefono = _telefonoController.text.trim();
    final contrasena = _contrasenaController.text.trim();

    if (nombre.isEmpty ||
        correo.isEmpty ||
        telefono.isEmpty ||
        contrasena.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Por favor completa todos los campos'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    try {
      // Llama al método para registrar el usuario en la base de datos
      await DBHelper.registrarUsuario(nombre, correo, telefono, contrasena);

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Usuario registrado exitosamente'),
          backgroundColor: Colors.green,
        ),
      );

      // Limpiar campos después de registrar
      _nombreController.clear();
      _correoController.clear();
      _telefonoController.clear();
      _contrasenaController.clear();

      // Navegar a la página de inicio de sesión
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (context) => const LoginPage()),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error al registrar usuario: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0B0E14),
      body: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24.0),
        child: Center(
          child: SingleChildScrollView(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Text(
                  'Hola!',
                  style: TextStyle(
                    fontSize: 32,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Crea tu cuenta',
                  style: TextStyle(fontSize: 18, color: Colors.white70),
                ),
                const SizedBox(height: 24),
                Image.asset(
                  'lib/imagenes/lider.png', // <-- nombre de la imagen que subirás
                  height: 120,
                  width: 120,
                ),
                const SizedBox(height: 24),
                CustomInputField(
                  icon: Icons.person,
                  hintText: 'Nombre',
                  controller: _nombreController,
                ),
                const SizedBox(height: 16),
                CustomInputField(
                  icon: Icons.email,
                  hintText: 'Correo Electrónico',
                  controller: _correoController,
                ),
                const SizedBox(height: 16),
                CustomInputField(
                  icon: Icons.phone,
                  hintText: 'Teléfono',
                  controller: _telefonoController,
                ),
                const SizedBox(height: 16),
                CustomInputField(
                  icon: Icons.lock,
                  hintText: 'Contraseña',
                  obscureText: true,
                  controller: _contrasenaController,
                ),
                const SizedBox(height: 32),
                SizedBox(
                  width: double.infinity,
                  height: 50,
                  child: ElevatedButton(
                    onPressed: _registrarUsuario,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF3077FF),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                    ),
                    child: const Text(
                      'Registrarse',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class CustomInputField extends StatelessWidget {
  final IconData icon;
  final String hintText;
  final bool obscureText;
  final TextEditingController controller;

  const CustomInputField({
    super.key,
    required this.icon,
    required this.hintText,
    this.obscureText = false,
    required this.controller,
  });

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      obscureText: obscureText,
      style: const TextStyle(color: Colors.white),
      decoration: InputDecoration(
        filled: true,
        fillColor: const Color(0xFF1A1F2C),
        prefixIcon: Icon(icon, color: Colors.white70),
        hintText: hintText,
        hintStyle: const TextStyle(color: Colors.white54),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide.none,
        ),
      ),
    );
  }
}
