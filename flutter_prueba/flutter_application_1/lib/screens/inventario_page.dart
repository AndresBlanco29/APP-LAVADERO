import 'package:flutter/material.dart';
import 'package:flutter_application_1/modelos/producto_model.dart';
import 'package:flutter_application_1/services/producto_service.dart';
import 'package:flutter_application_1/screens/dashboard_page.dart';
import 'package:flutter_application_1/screens/empleados_page.dart';
import 'package:flutter_application_1/screens/finanzas_page.dart';
import 'package:flutter_application_1/screens/ventas_page.dart';
import 'package:flutter_application_1/widgets/bottom_nav_bar.dart'; // Nueva importación
import 'package:flutter_application_1/screens/perfil.dart';
import 'package:flutter_application_1/screens/Login.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:io';

class InventarioPage extends StatefulWidget {
  const InventarioPage({Key? key}) : super(key: key);

  @override
  _InventarioPageState createState() => _InventarioPageState();
}

class _InventarioPageState extends State<InventarioPage> {
  late Future<List<Producto>> _productos;
  String _searchQuery =
      ''; // Nueva variable para almacenar el texto de búsqueda
  String _profileImagePath = 'lib/imagenes/perfil.png'; // new

  @override
  void initState() {
    super.initState();
    _loadProfileImage(); // new
    _productos = ProductoService().obtener_productos();
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

  Color getStockColor(int stock) {
    if (stock <= 10) return Colors.red;
    if (stock <= 20) return Colors.orange;
    return Colors.greenAccent; // Verde más brillante
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0B0E14),
      appBar: PreferredSize(
        preferredSize: const Size.fromHeight(140), // increased height here
        child: AppBar(
          automaticallyImplyLeading: false,
          title: const Text(
            'Inventario',
            style: TextStyle(
              color: Colors.white,
              fontSize: 24,
              fontWeight: FontWeight.bold,
            ),
          ),
          backgroundColor: const Color(0xFF0B0E14),
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
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 20),
              child: TextField(
                onChanged: (value) => setState(() => _searchQuery = value),
                style: const TextStyle(color: Colors.white),
                decoration: InputDecoration(
                  hintText: 'Buscar producto',
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
      body: FutureBuilder<List<Producto>>(
        future: _productos,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text('Error al cargar productos'));
          }
          final productos = snapshot.data!;
          final filteredProductos =
              productos
                  .where(
                    (producto) => producto.nombre.toLowerCase().contains(
                      _searchQuery.toLowerCase(),
                    ),
                  )
                  .toList();
          return ListView.builder(
            itemCount: filteredProductos.length,
            itemBuilder: (context, index) {
              final producto = filteredProductos[index];
              return Card(
                margin: EdgeInsets.symmetric(vertical: 8, horizontal: 12),
                color: Color(0xFF161A24),
                child: SizedBox(
                  height: 130,
                  child: ListTile(
leading: 
  producto.imagenUrl != null && producto.imagenUrl!.isNotEmpty
      ? Image.network(
          producto.imagenUrl!.startsWith("http")
              ? producto.imagenUrl!
              : 'https://api-production-b438.up.railway.app${producto.imagenUrl!}',
          width: 60, // increased width
          height: 60, // increased height
          errorBuilder: (context, error, stackTrace) {
            return Icon(
              Icons.image_not_supported,
              size: 60, // increased icon size
              color: Colors.grey,
            );
          },
        )
      : Icon(Icons.image_not_supported, size: 80, color: Colors.grey),
                    title: Padding(
                      padding: const EdgeInsets.only(top: 25, left: 20),
                      child: Text(
                        producto.nombre,
                        style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                          fontSize: 20,
                        ),
                      ),
                    ),
                    subtitle: Padding(
                      padding: const EdgeInsets.only(top: 2, left: 20),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            producto.codigoBarras,
                            style: TextStyle(
                              color: const Color.fromARGB(255, 216, 215, 215),
                              fontSize: 14,
                            ),
                          ),
                          Text(
                            'Stock: ${producto.cantidad}',
                            style: TextStyle(
                              color: getStockColor(producto.cantidad),
                              fontWeight: FontWeight.bold,
                              fontSize: 16,
                            ),
                          ),
                        ],
                      ),
                    ),
                    trailing: Text(
                      '\$ ${producto.precioVenta}',
                      style: TextStyle(color: Colors.white, fontSize: 22),
                    ),
                  ),
                ),
              );
            },
          );
        },
      ),
      bottomNavigationBar: CustomBottomNavigationBar(
        currentIndex: 1, // Índice para Inventario
      ),
    );
  }
}
