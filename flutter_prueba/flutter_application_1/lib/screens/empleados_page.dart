import 'package:flutter/material.dart';
import '../services/empleados_service.dart';
import '../modelos/empleado_model.dart';
import 'dashboard_page.dart'; // agregado
import 'inventario_page.dart'; // agregado
import 'finanzas_page.dart'; // agregado
import 'ventas_page.dart'; // agregado
import 'empleado_detalle_page.dart'; // agregado
import '../widgets/bottom_nav_bar.dart'; // agregado
import 'package:flutter_application_1/screens/perfil.dart';
import 'package:flutter_application_1/screens/Login.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:io';

class EmpleadosPage extends StatefulWidget {
  @override
  _EmpleadosPageState createState() => _EmpleadosPageState();
}

class _EmpleadosPageState extends State<EmpleadosPage> {
  final EmpleadosService _empleadosService = EmpleadosService();
  List<Empleado> _empleados = [];
  List<Empleado> _filteredEmpleados = [];
  int _currentIndex = 2; // página Empleados
  String _profileImagePath = 'lib/imagenes/perfil.png'; // new

  // Se reutilizan las imágenes de navegación de dashboard_page
  final List<String> navigationImages = [
    'lib/imagenes/dash.png',
    'lib/imagenes/inventario.png',
    'lib/imagenes/cv.png',
    'lib/imagenes/presupuesto.png',
    'lib/imagenes/ventas.png',
  ];

  // Función para gestionar la navegación entre páginas
  void _onItemTapped(int index) {
    if (index == _currentIndex) return;
    switch (index) {
      case 0:
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => DashboardPage()),
        );
        break;
      case 1:
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => InventarioPage()),
        );
        break;
      case 2:
        // Ya estamos en EmpleadosPage
        break;
      case 3:
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => FinanzasPage()),
        );
        break;
      case 4:
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => VentasApp()),
        );
        break;
    }
  }

  @override
  void initState() {
    super.initState();
    _loadProfileImage(); // new
    _loadEmpleados();
  }

  Future<void> _loadProfileImage() async {
    final prefs = await SharedPreferences.getInstance();
    final stored = prefs.getString('profileImagePath');
    if (stored != null && stored.isNotEmpty) {
      setState(() {
        _profileImagePath = stored;
      });
    }
  }

  void _mostrarDialogoCerrarSesion(BuildContext context) {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: Text('Confirmación'),
          content: Text('¿Está seguro que desea cerrar sesión?'),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(context).pop(); // Cierra el diálogo
              },
              child: Text('Cancelar'),
            ),
            TextButton(
              onPressed: () {
                Navigator.of(context).pushAndRemoveUntil(
                  MaterialPageRoute(builder: (context) => LoginPage()),
                  (Route<dynamic> route) => false,
                );
              },
              child: Text('Aceptar'),
            ),
          ],
        );
      },
    );
  }

  void _loadEmpleados() async {
    try {
      final empleados = await _empleadosService.fetchEmpleados();
      setState(() {
        _empleados = empleados;
        _filteredEmpleados = empleados;
      });
    } catch (e) {
      print(e);
    }
  }

  void _filtrar(String query) {
    final filtrados =
        _empleados
            .where((e) => e.nombres.toLowerCase().contains(query.toLowerCase()))
            .toList();
    setState(() {
      _filteredEmpleados = filtrados;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0B0E14),
      appBar: PreferredSize(
        preferredSize: const Size.fromHeight(140), // increased height here
        child: AppBar(
          automaticallyImplyLeading: false,
          backgroundColor: const Color(0xFF0B0E14),
          title: const Text(
            'Empleados',
            style: TextStyle(
              color: Colors.white,
              fontSize: 24,
              fontWeight: FontWeight.bold,
            ),
          ),
          elevation: 0,
          actions: [
            PopupMenuButton<String>(
              color: const Color(0xFF3077FF),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(20),
              ),
              offset: const Offset(-10, 50),
              itemBuilder:
                  (BuildContext context) => [
                    PopupMenuItem<String>(
                      value: 'perfil',
                      height: 45,
                      child: Row(
                        children: [
                          Image.asset(
                            'lib/imagenes/avatar.png',
                            width: 24,
                            height: 24,
                          ),
                          const SizedBox(width: 10),
                          const Padding(
                            padding: EdgeInsets.only(left: 15.0),
                            child: Text(
                              'Ver Perfil',
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 14,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const PopupMenuDivider(height: 1),
                    PopupMenuItem<String>(
                      value: 'cerrar_sesion',
                      height: 45,
                      child: Row(
                        children: [
                          Image.asset(
                            'lib/imagenes/cerrar.png',
                            width: 24,
                            height: 24,
                          ),
                          const SizedBox(width: 10),
                          const Padding(
                            padding: EdgeInsets.only(left: 7.0),
                            child: Text(
                              'Cerrar Sesión',
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 14,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
              onSelected: (String value) {
                if (value == 'perfil') {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (context) => PerfilPage()),
                  );
                } else if (value == 'cerrar_sesion') {
                  _mostrarDialogoCerrarSesion(context);
                }
              },
              icon:
                  _profileImagePath.startsWith('lib/imagenes')
                      ? CircleAvatar(
                        radius: 20,
                        backgroundImage: AssetImage(_profileImagePath),
                      )
                      : CircleAvatar(
                        radius: 20,
                        backgroundImage: FileImage(File(_profileImagePath)),
                      ),
            ),
          ],
          bottom: PreferredSize(
            preferredSize: const Size.fromHeight(60),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(
                16,
                0,
                16,
                20,
              ), // increased bottom padding
              child: TextField(
                onChanged: _filtrar,
                style: const TextStyle(color: Colors.white),
                decoration: InputDecoration(
                  hintText: 'Buscar',
                  hintStyle: const TextStyle(color: Colors.white70),
                  filled: true,
                  fillColor: const Color(0xFF1A1F2C),
                  prefixIcon: const Icon(Icons.search, color: Colors.white70),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(10),
                    borderSide: BorderSide.none,
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
      body: SafeArea(
        child: Column(
          children: [
            const SizedBox(height: 12),
            Expanded(
              child: ListView.builder(
                itemCount: _filteredEmpleados.length,
                itemBuilder: (context, index) {
                  final emp = _filteredEmpleados[index];
                  return Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16.0,
                      vertical: 6,
                    ),
                    child: SizedBox(
                      height:
                          130, // fixed height for blue card; adjust as needed
                      child: Card(
                        color: const Color(0xFF161A24),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: ListTile(
                          // Si se usa un leading widget, se recomienda limitar su ancho:
                          minLeadingWidth:
                              40, // agregado para evitar que consuma todo el ancho
                          // Si se muestra una imagen de red, usar errorBuilder para gestionar errores:
                          leading: Image.network(
                            'https://via.placeholder.com/80x80.png?text=Arroz',
                            width: 80,
                            height: 80,
                            errorBuilder: (context, error, stackTrace) {
                              return const Icon(Icons.error, size: 80);
                            },
                          ),
                          title: Text(
                            emp.nombres,
                            style: const TextStyle(
                              fontWeight: FontWeight.bold,
                              color: Colors.white,
                            ),
                          ),
                          subtitle: Text(
                            emp.cargo,
                            style: const TextStyle(
                              color: Color.fromARGB(179, 216, 211, 211),
                            ),
                          ),
                          trailing: ElevatedButton(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: const Color(0xFF3077FF),
                              foregroundColor: Colors.white,
                            ),
                            onPressed: () {
                              Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder:
                                      (_) => DetalleEmpleado(empleado: emp),
                                ),
                              );
                            },
                            child: const Text('Detalles'),
                          ),
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: CustomBottomNavigationBar(
        currentIndex: _currentIndex,
      ),
    );
  }
}
