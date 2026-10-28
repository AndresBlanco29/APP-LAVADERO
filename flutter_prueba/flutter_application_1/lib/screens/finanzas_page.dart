import 'dart:convert';
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:flutter_application_1/screens/perfil.dart';
import 'package:flutter_application_1/screens/Login.dart';
import 'package:flutter_application_1/screens/dashboard_page.dart';
import 'package:flutter_application_1/screens/inventario_page.dart';
import 'package:flutter_application_1/screens/empleados_page.dart';
import 'package:flutter_application_1/screens/ventas_page.dart';
import 'package:flutter_application_1/api/api_client.dart';
import 'package:flutter_application_1/ventas_model.dart';
import 'package:intl/intl.dart';
import 'package:flutter_application_1/screens/financial_buckets_screen.dart';
import 'package:flutter_application_1/screens/DetallesFinanzas.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:io';

class FinanzasPage extends StatefulWidget {
  const FinanzasPage({Key? key}) : super(key: key);

  @override
  State<FinanzasPage> createState() => _FinanzasPageState();
}

class _FinanzasPageState extends State<FinanzasPage> {
  int _selectedIndex = 3;
  bool isLoading = true;
  List<dynamic> _finanzas = [];
  Timer? _timer;
  TextEditingController searchController = TextEditingController();
  String _profileImagePath = 'lib/imagenes/perfil.png';

  // Filter flag: if true, show today's entries; if false, show previous days.
  bool _filtroHoy = true;

  @override
  void initState() {
    super.initState();
    _loadProfileImage();
    obtenerFinanzas();
    _timer = Timer.periodic(Duration(seconds: 10), (timer) {
      obtenerFinanzas();
    });
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

  @override
  void dispose() {
    _timer?.cancel();
    searchController.dispose();
    super.dispose();
  }

  Future<List<dynamic>> _obtenerVentas() async {
    try {
      // Fetch employees data to build a mapping: employee id -> employee name
      final responseEmp = await http.get(
        Uri.parse("https://api-production-b438.up.railway.app/empleados"),
      );
      Map employeeMap = {};
      if (responseEmp.statusCode == 200) {
        List<dynamic> empleadosData = json.decode(responseEmp.body);
        for (var emp in empleadosData) {
          employeeMap[emp['Id_Empleados']] = emp['Nombres'];
        }
        print("Employee Map: $employeeMap"); // Debug print to verify mapping
      } else {
        print("Error al cargar empleados");
      }
      final ventasRaw = await ApiClient.getJson('/ventas');
      final ventasData = ventasRaw is List ? ventasRaw : <dynamic>[];
      return ventasData.whereType<Map>().where((venta) {
        return !ventaEstaAnulada(Map<String, dynamic>.from(venta));
      }).map((venta) {
        String empleado = venta['empleados']?['Nombres'] ?? "No asignado";
        return {
          'tipo': 'Entrada',
          'descripcion': "Venta realizada",
          'monto': venta['Total'] ?? 0,
          'fecha': venta['Fecha_Venta'] ?? DateTime.now().toIso8601String(),
          'cajero': empleado,
          'id': venta['Id_Venta'],
        };
      }).toList();
    } catch (e) {
      debugPrint("Error al obtener ventas: $e");
      return []; // Return an empty list in case of error
    }
  }

  Future<void> obtenerFinanzas() async {
    try {
      final responseFinanzas = await http.get(
        Uri.parse("https://api-production-b438.up.railway.app/finanzas"),
      );

      if (responseFinanzas.statusCode == 200) {
        Map<String, dynamic> dataFinanzas = json.decode(responseFinanzas.body);
        List<dynamic> entradas = dataFinanzas['entradas'] ?? [];
        List<dynamic> salidas = dataFinanzas['salidas'] ?? [];

        // Obtener las ventas de la función _obtenerVentas
        List<dynamic> ventas = await _obtenerVentas();

        // Combine all data into finanzasList
        List<dynamic> finanzasList = [
          ...entradas.map(
            (entrada) => {
              'tipo': 'Entrada',
              'descripcion': entrada['Asunto'] ?? "Entrada sin descripción",
              'monto': entrada['Cantidad'] ?? 0,
              'fecha': entrada['Fecha'] ?? DateTime.now().toIso8601String(),
              'cajero': entrada['Cajero'] ?? "No especificado",
            },
          ),
          ...ventas, // Add the ventas list here
          ...salidas.map(
            (salida) => {
              'tipo': 'Salida',
              'descripcion': salida['Asunto'] ?? "Salida sin descripción",
              'monto': salida['Cantidad'] ?? 0,
              'fecha': salida['Fecha'] ?? DateTime.now().toIso8601String(),
              'cajero': salida['Cajero'] ?? "No especificado",
            },
          ),
        ];

        // Sort by date in descending order
        finanzasList.sort(
          (a, b) =>
              DateTime.parse(b['fecha']).compareTo(DateTime.parse(a['fecha'])),
        );

        setState(() {
          _finanzas = finanzasList;
          isLoading = false;
        });
      } else {
        throw Exception("Error al cargar Finanzas");
      }
    } catch (e) {
      debugPrint("Error: $e");
      setState(() {
        isLoading = false;
      });
    }
  }

  // Helper method to group a list of items by date (formatted "dd/MM/yyyy")
  Map<String, List<dynamic>> _groupByDate(List<dynamic> items) {
    Map<String, List<dynamic>> groups = {};
    for (var item in items) {
      DateTime fecha = DateTime.parse(item['fecha']);
      String dayStr = DateFormat("dd/MM/yyyy").format(fecha);
      if (!groups.containsKey(dayStr)) {
        groups[dayStr] = [];
      }
      groups[dayStr]!.add(item);
    }
    return groups;
  }

  // Modified _filtroButton to accept callback (unchanged from your version)
  Widget _filtroButton(
    String text, {
    bool isSelected = false,
    VoidCallback? onPressed,
  }) {
    return Padding(
      padding: const EdgeInsets.only(top: 10),
      child: ElevatedButton(
        onPressed: onPressed ?? () {},
        style: ElevatedButton.styleFrom(
          backgroundColor: isSelected ? Color(0xFF3077FF) : Colors.white,
          foregroundColor: isSelected ? Colors.white : Colors.black,
          side: BorderSide(color: isSelected ? Colors.white : Colors.black),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
          elevation: 0,
          minimumSize: Size(180, 42),
        ),
        child: Text(text),
      ),
    );
  }

  void mostrarDialogoCerrarSesion(BuildContext context) {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('Confirmación'),
          content: const Text('¿Está seguro que desea cerrar sesión?'),
          actions: [
            TextButton(
              child: const Text('Cancelar'),
              onPressed: () {
                Navigator.of(context).pop();
              },
            ),
            TextButton(
              child: const Text('Aceptar'),
              onPressed: () {
                Navigator.of(context).popUntil((route) => route.isFirst);
              },
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final DateTime now = DateTime.now();
    String hoyStr = DateFormat("yyyyMMdd").format(now);
    String query = searchController.text.toLowerCase();
    List<dynamic> finanzasFiltradas;
    if (_filtroHoy) {
      finanzasFiltradas =
          _finanzas.where((item) {
            DateTime fecha = DateTime.parse(item['fecha']);
            String itemDate = DateFormat("yyyyMMdd").format(fecha);
            return itemDate == hoyStr &&
                ((item['tipo'] ?? "").toLowerCase().contains(query) ||
                    (item['descripcion'] ?? "").toLowerCase().contains(query));
          }).toList();
    } else {
      finanzasFiltradas =
          _finanzas.where((item) {
            DateTime fecha = DateTime.parse(item['fecha']);
            String itemDate = DateFormat("yyyyMMdd").format(fecha);
            return itemDate != hoyStr &&
                ((item['tipo'] ?? "").toLowerCase().contains(query) ||
                    (item['descripcion'] ?? "").toLowerCase().contains(query));
          }).toList();
    }

    return Scaffold(
      backgroundColor: Color(0xFF0B0E14),
      appBar: AppBar(
        automaticallyImplyLeading: false, // added to remove the back arrow
        backgroundColor: Color(0xFF0B0E14),
        title: Text(
          'Finanzas',
          style: TextStyle(
            color: Colors.white,
            fontFamily: 'Verdana',
            fontSize: 28,
            fontWeight: FontWeight.bold,
          ),
        ),
        actions: [
          IconButton(
            tooltip: 'Bolsillos',
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => const FinancialBucketsScreen(),
                ),
              );
            },
            icon: const Icon(Icons.account_balance_wallet_outlined, color: Colors.white),
          ),
          Padding(
            padding: const EdgeInsets.only(right: 12.0),
            child: PopupMenuButton<String>(
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
                  mostrarDialogoCerrarSesion(context);
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
          ),
        ],
        bottom: PreferredSize(
          preferredSize: Size.fromHeight(90),
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 16.0,
                  vertical: 15,
                ),
                child: TextField(
                  controller: searchController,
                  style: TextStyle(color: Colors.white70),
                  decoration: InputDecoration(
                    hintText: 'Buscar por tipo o descripción',
                    hintStyle: TextStyle(color: Colors.white70),
                    prefixIcon: Icon(Icons.search, color: Colors.white),
                    filled: true,
                    fillColor: Color(0x21EDEBEB),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(5),
                      borderSide: BorderSide.none,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 8),
            ],
          ),
        ),
      ),
      body: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              _filtroButton(
                "Hoy",
                isSelected: _filtroHoy,
                onPressed: () {
                  setState(() {
                    _filtroHoy = true;
                  });
                },
              ),
              const SizedBox(width: 10),
              _filtroButton(
                "Otras Finanzas",
                isSelected: !_filtroHoy,
                onPressed: () {
                  setState(() {
                    _filtroHoy = false;
                  });
                },
              ),
            ],
          ),
          // Display results:
          Expanded(
            child:
                isLoading
                    ? const Center(child: CircularProgressIndicator())
                    : _filtroHoy
                    ? ListView.builder(
                      padding: const EdgeInsets.all(16),
                      itemCount: finanzasFiltradas.length,
                      itemBuilder: (context, index) {
                        final item = finanzasFiltradas[index];
                        return Padding(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 1.0,
                            vertical: 8.0,
                          ),
                          child: SizedBox(
                            height: 110, // altura fija del cuadro
                            child: Container(
                              decoration: BoxDecoration(
                                color: const Color(0xFF0B0E14),
                                borderRadius: BorderRadius.circular(16),
                              ),
                              padding: const EdgeInsets.all(20),
                              child: Row(
                                mainAxisAlignment:
                                    MainAxisAlignment.spaceBetween,
                                children: [
                                  if (item['tipo'] == 'Entrada')
                                    Image.asset(
                                      'lib/imagenes/flecha_verde.png',
                                      width: 45,
                                      height: 45,
                                    )
                                  else if (item['tipo'] == 'Salida')
                                    Image.asset(
                                      'lib/imagenes/flecha_roja.png',
                                      width: 45,
                                      height: 45,
                                    ),
                                  const SizedBox(width: 10),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      mainAxisAlignment:
                                          MainAxisAlignment.center,
                                      children: [
                                        Text(
                                          item['tipo'] ?? "",
                                          style: const TextStyle(
                                            color: Colors.white,
                                            fontSize: 22,
                                            fontWeight: FontWeight.bold,
                                          ),
                                        ),
                                        const SizedBox(height: 6),
                                        Text(
                                          item['descripcion'] ?? "",
                                          style: const TextStyle(
                                            color: Colors.white70,
                                            fontSize: 16,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                  Column(
                                    crossAxisAlignment: CrossAxisAlignment.end,
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: [
                                      Text(
                                        "\$${NumberFormat("#,###.##", "es_ES").format(item['monto'])}",
                                        style: TextStyle(
                                          color:
                                              item['tipo'] == 'Entrada'
                                                  ? Colors.green
                                                  : Colors.red,
                                          fontSize: 20,
                                          fontWeight: FontWeight.bold,
                                        ),
                                      ),
                                      const SizedBox(height: 8),
                                      ElevatedButton(
                                        onPressed: () {
                                          Navigator.push(
                                            context,
                                            MaterialPageRoute(
                                              builder:
                                                  (context) => DetallesFinanzas(
                                                    item: item,
                                                  ),
                                            ),
                                          );
                                        },
                                        style: ElevatedButton.styleFrom(
                                          backgroundColor: const Color(
                                            0xFF3077FF,
                                          ),
                                          shape: RoundedRectangleBorder(
                                            borderRadius: BorderRadius.circular(
                                              6,
                                            ),
                                          ),
                                          padding: const EdgeInsets.symmetric(
                                            horizontal: 13, // antes 16
                                            vertical: 5, // antes 6
                                          ),
                                          minimumSize: const Size(
                                            0,
                                            32,
                                          ), // opcional: fija altura mínima
                                          tapTargetSize:
                                              MaterialTapTargetSize
                                                  .shrinkWrap, // reduce el área táctil
                                        ),
                                        child: const Text(
                                          "Detalles",
                                          style: TextStyle(
                                            fontSize: 14, // antes 16
                                            color: Colors.white,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                          ),
                        );
                      },
                    )
                    : _buildGroupedList(
                      finanzasFiltradas,
                    ), // show grouped results for past days
          ),
        ],
      ),
      bottomNavigationBar: _bottomNavigationBar(),
    );
  }

  // Helper: build grouped ListView for "Otras Finanzas"
  Widget _buildGroupedList(List<dynamic> items) {
    // Group items by day string "dd/MM/yyyy"
    final groups = <String, List<dynamic>>{};
    for (var item in items) {
      DateTime fecha = DateTime.parse(item['fecha']);
      String dayStr = DateFormat("dd/MM/yyyy").format(fecha);
      groups.putIfAbsent(dayStr, () => []).add(item);
    }
    // Sort group keys in descending order (most recent first)
    final sortedKeys =
        groups.keys.toList()..sort((a, b) {
          DateTime fa = DateFormat("dd/MM/yyyy").parse(a);
          DateTime fb = DateFormat("dd/MM/yyyy").parse(b);
          return fb.compareTo(fa);
        });
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: sortedKeys.length,
      itemBuilder: (context, index) {
        final key = sortedKeys[index];
        final groupItems = groups[key]!;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              key,
              style: const TextStyle(
                fontSize: 16,
                color: Colors.black,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            ...groupItems.map((item) {
              return Padding(
                padding: const EdgeInsets.symmetric(horizontal: 0, vertical: 6),
                child: SizedBox(
                  height: 110, // altura fija del cuadro azul
                  child: Container(
                    decoration: BoxDecoration(
                      color: const Color(0xFF0B0E14),
                      borderRadius: BorderRadius.circular(16),
                    ),
                    padding: const EdgeInsets.all(20),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        if (item['tipo'] == 'Entrada')
                          Image.asset(
                            'lib/imagenes/flecha_verde.png',
                            width: 45,
                            height: 45,
                          )
                        else if (item['tipo'] == 'Salida')
                          Image.asset(
                            'lib/imagenes/flecha_roja.png',
                            width: 45,
                            height: 45,
                          ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text(
                                item['tipo'] ?? "",
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 20,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              const SizedBox(height: 6),
                              Text(
                                item['descripcion'] ?? "",
                                style: const TextStyle(
                                  color: Colors.white70,
                                  fontSize: 16,
                                ),
                              ),
                            ],
                          ),
                        ),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              "\$${NumberFormat("#,###.##", "es_ES").format(item['monto'])}",
                              style: TextStyle(
                                color:
                                    item['tipo'] == 'Entrada'
                                        ? Colors.green
                                        : Colors.red,
                                fontSize: 20,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 8),
                            ElevatedButton(
                              onPressed: () {
                                Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                    builder:
                                        (context) =>
                                            DetallesFinanzas(item: item),
                                  ),
                                );
                              },
                              style: ElevatedButton.styleFrom(
                                backgroundColor: const Color(0xFF3077FF),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 12, // antes 16
                                  vertical: 4, // antes 6
                                ),
                                minimumSize: const Size(
                                  0,
                                  32,
                                ), // opcional: fija altura mínima
                                tapTargetSize:
                                    MaterialTapTargetSize
                                        .shrinkWrap, // reduce el área táctil
                              ),
                              child: const Text(
                                "Detalles",
                                style: TextStyle(
                                  fontSize: 14, // antes 16
                                  color: Colors.white,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              );
            }).toList(),
            const SizedBox(height: 16),
          ],
        );
      },
    );
  }

  Widget _bottomNavigationBar() {
    return Container(
      height: 80,
      decoration: BoxDecoration(
        color: const Color(0xFF0B0E14),
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(20),
          topRight: Radius.circular(20),
        ),
      ),
      child: Row(
        children: List.generate(5, (index) {
          final iconPaths = [
            'lib/imagenes/dash.png',
            'lib/imagenes/inventario.png',
            'lib/imagenes/cv.png',
            'lib/imagenes/presupuesto.png',
            'lib/imagenes/ventas.png',
          ];
          final labels = [
            'Dashboard',
            'Inventario',
            'Empleados',
            'Finanzas',
            'Ventas',
          ];

          final isSelected = _selectedIndex == index;

          return Expanded(
            child: GestureDetector(
              onTap: () {
                setState(() {
                  _selectedIndex = index;
                });
                if (index == 0) {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (context) => DashboardPage()),
                  );
                } else if (index == 1) {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (context) => InventarioPage()),
                  );
                } else if (index == 2) {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (context) => EmpleadosPage()),
                  );
                } else if (index == 3) {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (context) => FinanzasPage()),
                  );
                } else if (index == 4) {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (context) => VentasScreen()),
                  );
                }
              },
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 4, vertical: 8),
                padding: const EdgeInsets.symmetric(vertical: 6),
                decoration:
                    isSelected
                        ? BoxDecoration(
                          color: const Color(0xFF3077FF),
                          borderRadius: BorderRadius.circular(20),
                        )
                        : null,
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Image.asset(iconPaths[index], width: 29, height: 29),
                    const SizedBox(height: 4),
                    Text(
                      labels[index],
                      style: const TextStyle(fontSize: 13, color: Colors.white),
                    ),
                  ],
                ),
              ),
            ),
          );
        }),
      ),
    );
  }
}
