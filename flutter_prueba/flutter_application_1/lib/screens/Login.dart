import 'package:flutter/material.dart';
import 'package:flutter_application_1/screens/Recuprerar_contraseña.dart';
import 'package:flutter_application_1/screens/dashboard_page.dart';
import 'package:flutter_application_1/theme/zyntra_theme.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final TextEditingController usuarioController = TextEditingController();
  final TextEditingController contrasenaController = TextEditingController();

    Future<Map<String, dynamic>?> loginAdmin(
    String usuario,
    String contrasena,
  ) async {
    final uri = Uri.parse(
      'https://api-production-b438.up.railway.app/admin',
    ).replace(
      queryParameters: {'usuario': usuario, 'contrasena': contrasena},
    );

    final response = await http.get(uri).timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) {
      throw Exception(
        'La API no responde (${response.statusCode}). Revisa Railway.',
      );
    }
    final decoded = json.decode(response.body);
    if (decoded is! List || decoded.isEmpty) {
      return null;
    }
    return Map<String, dynamic>.from(decoded.first as Map);
  }

  void iniciarSesion() async {
    String usuario = usuarioController.text.trim();
    String contrasena = contrasenaController.text.trim();

    if (usuario.isEmpty || contrasena.isEmpty) {
      mostrarMensaje('Por favor completa todos los campos', Colors.red);
      return;
    }

    try {
      final admin = await loginAdmin(usuario, contrasena);
      if (!mounted) return;
      if (admin == null) {
        mostrarMensaje('Usuario o contraseña incorrectos', Colors.red);
        return;
      }

      final idAdmin = int.tryParse(
            '${admin['id_admin'] ?? admin['Id_admin'] ?? admin['Id_Admin'] ?? 0}',
          ) ??
          0;
      final prefs = await SharedPreferences.getInstance();
      await prefs.setInt('admin_id', idAdmin);
      await prefs.setString('admin_usuario', usuario);
      await prefs.setBool('es_admin', admin['es_admin'] == true || idAdmin > 0);
      if (!mounted) return;
      mostrarMensaje('Ingreso exitoso', Colors.green);
      if (!mounted) return;
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (context) => const DashboardPage()),
      );
    } catch (e) {
      if (!mounted) return;
      mostrarMensaje('No se pudo conectar: $e', Colors.red);
    }
  }

  void mostrarMensaje(String texto, Color color) {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(texto), backgroundColor: color));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Zyntra.bg,
      body: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24.0),
        child: Center(
          child: SingleChildScrollView(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  width: 72,
                  height: 72,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: Zyntra.accent,
                    borderRadius: BorderRadius.circular(18),
                  ),
                  child: const Text(
                    'Z',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 36,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                const Text(
                  'Zyntra POS',
                  style: TextStyle(
                    fontSize: 32,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Centro de comando',
                  style: TextStyle(fontSize: 18, color: Zyntra.muted),
                ),
                const SizedBox(height: 24),
                Image.asset('lib/imagenes/lider.png', height: 100, width: 100),
                const SizedBox(height: 24),
                CustomInputField(
                  icon: Icons.person,
                  hintText: 'Usuario',
                  controller: usuarioController,
                ),
                const SizedBox(height: 16),
                CustomInputField(
                  icon: Icons.lock,
                  hintText: 'Contraseña',
                  controller: contrasenaController,
                  obscureText: true,
                ),
                const SizedBox(height: 32),
                SizedBox(
                  width: double.infinity,
                  height: 50,
                  child: ElevatedButton(
                    onPressed: iniciarSesion,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Zyntra.accent,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                    child: const Text(
                      'Entrar',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                TextButton(
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => RecuperarContrasenaPage(),
                      ),
                    );
                  },
                  child: const Text(
                    '¿Olvidaste tu contraseña?',
                    style: TextStyle(color: Zyntra.muted),
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
    required this.controller,
    this.obscureText = false,
  });

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      obscureText: obscureText,
      style: const TextStyle(color: Colors.white),
      decoration: InputDecoration(
        filled: true,
        fillColor: Zyntra.input,
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
