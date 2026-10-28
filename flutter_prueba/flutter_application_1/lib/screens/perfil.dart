import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'dart:io';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_application_1/services/comando_service.dart';
import 'package:flutter_application_1/theme/zyntra_theme.dart';

class PerfilPage extends StatefulWidget {
  @override
  _PerfilPageState createState() => _PerfilPageState();
}

class _PerfilPageState extends State<PerfilPage> {
  String _profileImagePath = 'lib/imagenes/perfil.png'; // Default profile image

  // Replace default admin data with placeholders
  String adminName = 'Nombre predeterminado';
  String adminPhone = '0000000000';
  String adminEmail = 'correo@ejemplo.com';
  bool _loadingUserData = true; // new loading state

  @override
  void initState() {
    super.initState();
    _loadProfileImage(); // Load saved image
    _loadUserData(); // Load logged-in user data saved at login
  }

  Future<void> _loadUserData() async {
    final prefs = await SharedPreferences.getInstance();
    final userId = prefs.getInt("admin_id");
    if (userId == null) {
      setState(() {
        _loadingUserData = false;
      });
      return;
    }
    final url = Uri.parse(
      'https://api-production-b438.up.railway.app/admin/$userId',
    );
    try {
      final response = await http.get(url);
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          adminName = data['Nombre']?.toString() ?? adminName;
          adminPhone = data['telefono']?.toString() ?? adminPhone;
          adminEmail = data['correo_electronico']?.toString() ?? adminEmail;
          _loadingUserData = false;
        });
      } else {
        print("Error: ${response.statusCode}");
        setState(() {
          _loadingUserData = false;
        });
      }
    } catch (e) {
      print("Error al cargar los datos del usuario: $e");
      setState(() {
        _loadingUserData = false;
      });
    }
  }

  Future<void> _loadProfileImage() async {
    final prefs = await SharedPreferences.getInstance();
    final storedPath = prefs.getString('profileImagePath');
    if (storedPath != null && storedPath.isNotEmpty) {
      setState(() {
        _profileImagePath = storedPath;
      });
    }
  }

  Future<void> _pickImage() async {
    final picker = ImagePicker();
    final pickedFile = await picker.pickImage(source: ImageSource.gallery);

    if (pickedFile != null) {
      setState(() {
        _profileImagePath = pickedFile.path; // Update profile image path
      });
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('profileImagePath', pickedFile.path);
    }
  }

  Future<void> _cambiarPin() async {
    final actual = TextEditingController();
    final nuevo = TextEditingController();
    final svc = ComandoService();
    final guardado = await svc.approvalPin();
    if (!mounted) return;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: Zx.card(context),
        title: const Text('PIN de aprobación'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (guardado.isNotEmpty)
              TextField(
                controller: actual,
                obscureText: true,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(hintText: 'PIN actual'),
              ),
            if (guardado.isNotEmpty) const SizedBox(height: 8),
            TextField(
              controller: nuevo,
              obscureText: true,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                hintText: 'Nuevo PIN (vacío para quitarlo)',
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancelar'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Guardar'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    if (guardado.isNotEmpty && actual.text.trim() != guardado) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('PIN actual incorrecto')),
      );
      return;
    }
    await svc.setApprovalPin(nuevo.text.trim());
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          nuevo.text.trim().isEmpty
              ? 'PIN eliminado'
              : 'PIN de aprobación actualizado',
        ),
      ),
    );
  }

  Future<void> _cambiarTema() async {
    final actual = ThemeController.mode.value;
    final elegido = await showModalBottomSheet<ThemeMode>(
      context: context,
      backgroundColor: Zx.card(context),
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              title: const Text('Sistema'),
              trailing: actual == ThemeMode.system
                  ? const Icon(Icons.check, color: Zyntra.cyan)
                  : null,
              onTap: () => Navigator.pop(ctx, ThemeMode.system),
            ),
            ListTile(
              title: const Text('Oscuro'),
              trailing: actual == ThemeMode.dark
                  ? const Icon(Icons.check, color: Zyntra.cyan)
                  : null,
              onTap: () => Navigator.pop(ctx, ThemeMode.dark),
            ),
            ListTile(
              title: const Text('Claro'),
              trailing: actual == ThemeMode.light
                  ? const Icon(Icons.check, color: Zyntra.cyan)
                  : null,
              onTap: () => Navigator.pop(ctx, ThemeMode.light),
            ),
          ],
        ),
      ),
    );
    if (elegido != null) await ThemeController.set(elegido);
  }

  @override
  Widget build(BuildContext context) {
    if (_loadingUserData) {
      return Scaffold(
        backgroundColor: Color(0xFF0B0E14),
        appBar: AppBar(
          title: Text('Perfil'),
          backgroundColor: Color(0xFF0B0E14),
        ),
        body: Center(child: CircularProgressIndicator()),
      );
    }
    return Scaffold(
      backgroundColor: Color(0xFF0B0E14),
      appBar: AppBar(title: Text('Perfil'), backgroundColor: Color(0xFF0B0E14)),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.start,
          children: [
            const SizedBox(height: 30),
            Stack(
              alignment: Alignment.bottomRight,
              children: [
                CircleAvatar(
                  radius: 70,
                  backgroundImage:
                      _profileImagePath.startsWith('lib/imagenes')
                          ? AssetImage(_profileImagePath) as ImageProvider
                          : FileImage(File(_profileImagePath)),
                ),
                IconButton(
                  icon: Icon(Icons.edit, color: Colors.white),
                  onPressed: _pickImage,
                  color: Color(0xFF3077FF),
                  iconSize: 30,
                ),
              ],
            ),
            const SizedBox(height: 16),
            // Display admin data fetched from the API
            Text(
              adminName,
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Divider(
              color: Colors.grey,
              thickness: 1,
              indent: 40,
              endIndent: 40,
            ),
            const SizedBox(height: 8),
            // Use loaded adminPhone and adminEmail
            _buildInfoRow('Teléfono', adminPhone),
            const SizedBox(height: 16),
            _buildInfoRow('Correo Electrónico', adminEmail),
            const SizedBox(height: 24),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 40),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'Centro de comando',
                    style: TextStyle(color: Zx.muted(context), fontSize: 14),
                  ),
                  const SizedBox(height: 8),
                  OutlinedButton(
                    onPressed: _cambiarPin,
                    child: const Text('PIN de aprobación'),
                  ),
                  const SizedBox(height: 8),
                  OutlinedButton(
                    onPressed: _cambiarTema,
                    child: const Text('Apariencia claro / oscuro'),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () {
                Navigator.pop(context); // Regresa a la pantalla anterior
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: Color(0xFF3077FF),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
              child: Text('Regresar'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 40.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: TextStyle(color: Colors.grey, fontSize: 16)),
          const SizedBox(height: 4),
          Text(
            value,
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const Divider(color: Colors.grey, thickness: 1),
        ],
      ),
    );
  }
}
