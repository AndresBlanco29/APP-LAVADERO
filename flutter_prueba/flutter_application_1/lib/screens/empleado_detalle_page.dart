import 'package:flutter/material.dart';
import '../modelos/empleado_model.dart';

class DetalleEmpleado extends StatelessWidget {
  final Empleado empleado;

  const DetalleEmpleado({Key? key, required this.empleado}) : super(key: key);

  int _calcularEdad(String fechaNacimiento) {
    try {
      DateTime birthDate = DateTime.parse(fechaNacimiento);
      DateTime today = DateTime.now();
      int age = today.year - birthDate.year;
      if (today.month < birthDate.month || 
          (today.month == birthDate.month && today.day < birthDate.day)) {
        age--;
      }
      return age;
    } catch (e) {
      return 0;
    }
  }

  // Función para crear un ListTile de detalle
  Widget _buildDetailTile(IconData icon, String text) {
    return ListTile(
      leading: Icon(icon, color: Colors.white70),
      title: Text(text, style: const TextStyle(color: Colors.white)),
    );
  }
  
  // Separador horizontal con padding
  Widget _buildDivider() {
    return const Padding(
      padding: EdgeInsets.symmetric(horizontal: 16),
      child: Divider(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0B0E14),
      appBar: AppBar(
        title: const Text('Detalle del Empleado', style: TextStyle(color: Colors.white)),
        backgroundColor: const Color(0xFF10131A),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Encabezado modificado: el nombre siempre arriba y la foto debajo
          Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Text(
                empleado.nombres,
                style: const TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              const SizedBox(height: 16),
              Container(
                width: 240,
                height: 380,
                decoration: BoxDecoration(
                  color: Colors.grey[300],
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  Icons.person,
                  size: 220,
                  color: Colors.grey[600],
                ),
              ),
            ],
          ),
          const SizedBox(height: 40), // separación entre encabezado y detalles
          _buildDetailTile(Icons.work, empleado.cargo),
          _buildDivider(),
          _buildDetailTile(Icons.phone, empleado.telefono),
          _buildDivider(),
          _buildDetailTile(Icons.email, empleado.correo),
          _buildDivider(),
          _buildDetailTile(Icons.calendar_today, 'Fecha de Nacimiento: ${empleado.fechaNacimiento}'),
          _buildDivider(),
          _buildDetailTile(Icons.cake, 'Edad: ${_calcularEdad(empleado.fechaNacimiento)} años'),
          _buildDivider(),
          _buildDetailTile(Icons.calendar_view_day, 'Fecha de Ingreso: ${empleado.fechaIngreso}'),
          _buildDivider(),
          // Si se requiere mostrar "Fecha de Nacimiento" nuevamente, descomenta el siguiente bloque:
          // _buildDetailTile(Icons.calendar_today, 'Fecha de Nacimiento: ${empleado.fechaNacimiento}'),
        ],
      ),
    );
  }
}
