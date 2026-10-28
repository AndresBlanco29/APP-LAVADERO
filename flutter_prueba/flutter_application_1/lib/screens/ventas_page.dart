import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_application_1/screens/DetallesVentas.dart';
import 'package:flutter_application_1/screens/empleados_page.dart';
import 'package:flutter_application_1/screens/finanzas_page.dart';
import 'package:flutter_application_1/api/api_client.dart';
import 'package:flutter_application_1/theme/zyntra_theme.dart';
import 'package:flutter_application_1/ventas_model.dart';
import 'package:intl/intl.dart';
import 'package:flutter_application_1/screens/dashboard_page.dart';
import 'package:flutter_application_1/screens/inventario_page.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:flutter_application_1/screens/Login.dart';
import 'package:flutter_application_1/screens/perfil.dart';
import 'package:flutter_application_1/shared/global_state.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:io';

AudioPlayer audioPlayer = AudioPlayer();

Future<void> reproducirSonido() async {
  await audioPlayer.play(AssetSource('sounds/caja.wav'));
}

class VentasApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return VentasScreen();
  }
}

class VentasScreen extends StatefulWidget {
  @override
  _VentasScreenState createState() => _VentasScreenState();
}

class _VentasScreenState extends State<VentasScreen> {
  List<Venta> ventas = [];
  List<Venta> ventasFiltradas = [];
  TextEditingController searchController = TextEditingController();
  int _selectedIndex = 4;
  String _profileImagePath = 'lib/imagenes/perfil.png';
  Timer? _refreshTimer;
  bool _cargando = true;
  bool _avisoAbierto = false;
  int? ultimoIdVenta;

  @override
  void initState() {
    super.initState();
    _loadProfileImage();
    obtenerVentas();
    _refreshTimer = Timer.periodic(const Duration(seconds: 10), (timer) {
      obtenerVentas();
    });
    searchController.addListener(_filtrarVentas);
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
    _refreshTimer?.cancel();
    searchController.dispose();
    super.dispose();
  }

  void _filtrarVentas() {
    String query = searchController.text.toLowerCase();
    setState(() {
      ventasFiltradas = ventas.where((venta) {
        final nombre = venta.nombreEmpleado.toLowerCase();
        final id = venta.id.toString();
        final placa = venta.placa.toLowerCase();
        final cliente = venta.cliente.toLowerCase();
        return nombre.contains(query) ||
            id.contains(query) ||
            placa.contains(query) ||
            cliente.contains(query);
      }).toList();
    });
  }

  void _avisarVenta(Venta venta) {
    if (!mounted || _avisoAbierto) return;
    final placa = venta.placa.isEmpty ? 'Venta #${venta.id}' : venta.placa;
    final cliente = venta.cliente.isEmpty ? '' : '\n${venta.cliente}';
    final sede = [venta.sucursal, venta.zona].where((t) => t.isNotEmpty).join(' · ');
    final gente = venta.nombreEmpleado.isEmpty ? '' : '\n${venta.nombreEmpleado}';
    final ganancia = venta.ganancia <= 0
        ? ''
        : '\nGanancia \$${NumberFormat('#,###', 'es_ES').format(venta.ganancia)}';
    _avisoAbierto = true;
    showDialog<void>(
      context: context,
      builder: (dialogContext) {
        Future.delayed(const Duration(seconds: 4), () {
          if (dialogContext.mounted) Navigator.of(dialogContext).pop();
        });
        return AlertDialog(
          backgroundColor: const Color(0xFF1E9B45),
          title: const Text('Entró una venta', style: TextStyle(color: Colors.white)),
          content: Text(
            '$placa$cliente\n\$${NumberFormat('#,###', 'es_ES').format(venta.total)}'
            '${sede.isEmpty ? '' : '\n$sede'}'
            '$gente$ganancia',
            style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w800),
          ),
        );
      },
    ).whenComplete(() => _avisoAbierto = false);
  }

  Future<void> obtenerVentas() async {
    try {
      final data = await ApiClient.getJson('/ventas', ttl: Duration.zero);
      final list = data is List ? data : <dynamic>[];
      List<Venta> nuevasVentas = list
          .whereType<Map>()
          .map((ventaJson) => Venta.fromJson(Map<String, dynamic>.from(ventaJson)))
          .toList();

      nuevasVentas.sort((a, b) {
        try {
          return DateTime.parse(b.fecha).compareTo(DateTime.parse(a.fecha));
        } catch (_) {
          return 0;
        }
      });

      final activas = nuevasVentas.where((v) => !v.anulada).toList();
      if (ventas.isNotEmpty && activas.isNotEmpty) {
        if (ultimoIdVenta != null && activas.first.id != ultimoIdVenta) {
          reproducirSonido();
          agregarVentaComoEntrada(activas.first);
          _avisarVenta(activas.first);
        }
      }

      if (mounted) {
        setState(() {
          ventas = nuevasVentas;
          _filtrarVentasSinSet();
          _cargando = false;
          if (activas.isNotEmpty) {
            ultimoIdVenta = activas.first.id;
          } else if (nuevasVentas.isNotEmpty) {
            ultimoIdVenta = nuevasVentas.first.id;
          }
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _cargando = false;
        });
      }
    }
  }

  void _filtrarVentasSinSet() {
    String query = searchController.text.toLowerCase();
    ventasFiltradas = ventas.where((venta) {
      final nombre = venta.nombreEmpleado.toLowerCase();
      final id = venta.id.toString();
      return nombre.contains(query) || id.contains(query);
    }).toList();
  }

  void _mostrarDialogoCerrarSesion(BuildContext context) {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          backgroundColor: Zyntra.card,
          title: const Text('Confirmación', style: TextStyle(color: Colors.white)),
          content: const Text(
            '¿Está seguro que desea cerrar sesión?',
            style: TextStyle(color: Zyntra.muted),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cancelar'),
            ),
            TextButton(
              onPressed: () {
                Navigator.of(context).pushAndRemoveUntil(
                  MaterialPageRoute(builder: (context) => const LoginPage()),
                  (Route<dynamic> route) => false,
                );
              },
              child: const Text('Aceptar'),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final activas = ventasFiltradas.where((v) => !v.anulada).toList();
    final totalVisible = activas.fold<double>(0, (s, v) => s + v.total);

    return Scaffold(
      backgroundColor: Zyntra.bg,
      appBar: AppBar(
        backgroundColor: Zyntra.header,
        title: const Text(
          'Ventas',
          style: TextStyle(
            color: Colors.white,
            fontSize: 26,
            fontWeight: FontWeight.bold,
          ),
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12.0),
            child: PopupMenuButton<String>(
              color: Zyntra.elevated,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
              ),
              offset: const Offset(-10, 50),
              itemBuilder: (BuildContext context) => [
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
                          style: TextStyle(color: Colors.white, fontSize: 14),
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
                          style: TextStyle(color: Colors.white, fontSize: 14),
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
                  ).then((_) {
                    _loadProfileImage();
                  });
                } else if (value == 'cerrar_sesion') {
                  _mostrarDialogoCerrarSesion(context);
                }
              },
              icon: _profileImagePath.startsWith('lib/imagenes')
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
          preferredSize: const Size.fromHeight(96),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
            child: Column(
              children: [
                TextField(
                  controller: searchController,
                  style: const TextStyle(color: Colors.white),
                  decoration: InputDecoration(
                    hintText: 'Buscar por nombre o número',
                    hintStyle: const TextStyle(color: Zyntra.dim),
                    prefixIcon: const Icon(Icons.search, color: Colors.white),
                    filled: true,
                    fillColor: Zyntra.input,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide: BorderSide.none,
                    ),
                  ),
                ),
                const SizedBox(height: 6),
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    '${activas.length} tickets  ·  \$${NumberFormat('#,###', 'es_ES').format(totalVisible)}',
                    style: const TextStyle(color: Zyntra.muted, fontSize: 12),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
      body: _cargando && ventasFiltradas.isEmpty
          ? const Center(child: CircularProgressIndicator(color: Zyntra.cyan))
          : ventasFiltradas.isEmpty
              ? const Center(
                  child: Text(
                    'No hay ventas para mostrar',
                    style: TextStyle(color: Zyntra.muted, fontSize: 16),
                  ),
                )
              : RefreshIndicator(
                  color: Zyntra.accent,
                  onRefresh: () {
                    ApiClient.invalidate('/ventas');
                    return obtenerVentas();
                  },
                  child: ListView.builder(
                    itemCount: ventasFiltradas.length,
                    itemBuilder: (context, index) {
                      final venta = ventasFiltradas[index];
                      return Padding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 16.0,
                          vertical: 8.0,
                        ),
                        child: Container(
                          decoration: BoxDecoration(
                            color: venta.anulada ? Zyntra.anuladaBg : Zyntra.card,
                            borderRadius: BorderRadius.circular(12),
                            border: venta.anulada
                                ? Border.all(color: Zyntra.danger.withOpacity(0.45))
                                : Border.all(color: Zyntra.border),
                          ),
                          padding: const EdgeInsets.all(13),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        Text(
                                          'Venta #${venta.id}',
                                          style: TextStyle(
                                            color: Colors.white,
                                            fontWeight: FontWeight.bold,
                                            fontSize: 18,
                                            decoration: venta.anulada
                                                ? TextDecoration.lineThrough
                                                : TextDecoration.none,
                                          ),
                                        ),
                                        if (venta.anulada) ...[
                                          const SizedBox(width: 8),
                                          Container(
                                            padding: const EdgeInsets.symmetric(
                                              horizontal: 8,
                                              vertical: 2,
                                            ),
                                            decoration: BoxDecoration(
                                              color: Zyntra.danger,
                                              borderRadius: BorderRadius.circular(8),
                                            ),
                                            child: const Text(
                                              'ANULADA',
                                              style: TextStyle(
                                                color: Colors.white,
                                                fontSize: 11,
                                                fontWeight: FontWeight.bold,
                                              ),
                                            ),
                                          ),
                                        ],
                                      ],
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      DateFormat(
                                        "EEEE, d 'de' MMMM 'de' yyyy",
                                        'es_ES',
                                      ).format(DateTime.parse(venta.fecha)),
                                      style: const TextStyle(
                                        color: Zyntra.muted,
                                        fontSize: 14,
                                      ),
                                    ),
                                    Text(
                                      DateFormat(
                                        'h:mm a',
                                        'es_ES',
                                      ).format(DateTime.parse(venta.fecha)),
                                      style: const TextStyle(
                                        color: Zyntra.muted,
                                        fontSize: 14,
                                      ),
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      venta.lavadero && venta.placa.isNotEmpty
                                          ? '${venta.placa} · ${venta.cliente}'
                                          : venta.nombreEmpleado,
                                      style: const TextStyle(
                                        color: Zyntra.muted,
                                        fontWeight: FontWeight.bold,
                                        fontSize: 16,
                                      ),
                                    ),
                                    if (venta.lavadero && venta.sucursal.isNotEmpty)
                                      Text(
                                        venta.sucursal,
                                        style: const TextStyle(
                                          color: Zyntra.muted,
                                          fontSize: 14,
                                        ),
                                      ),
                                  ],
                                ),
                              ),
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.end,
                                children: [
                                  Text(
                                    '\$ ${NumberFormat('#,###', 'es_ES').format(venta.total)}',
                                    style: TextStyle(
                                      color: venta.anulada
                                          ? Zyntra.anuladaFg
                                          : Colors.white,
                                      fontSize: 18,
                                      fontWeight: FontWeight.bold,
                                      decoration: venta.anulada
                                          ? TextDecoration.lineThrough
                                          : TextDecoration.none,
                                    ),
                                  ),
                                  const SizedBox(height: 8),
                                  ElevatedButton(
                                    onPressed: () {
                                      Navigator.push(
                                        context,
                                        MaterialPageRoute(
                                          builder: (context) => DetallesVentas(
                                            numeroVenta: venta.id.toString(),
                                            fecha: DateFormat(
                                              'dd/MM/yyyy, h:mm a',
                                            ).format(DateTime.parse(venta.fecha)),
                                            Empleado: venta.nombreEmpleado,
                                            productos: venta.productosVendidos,
                                            total: venta.total,
                                            anulada: venta.anulada,
                                            ganancia: venta.ganancia,
                                            lavadero: venta.lavadero,
                                            placa: venta.placa,
                                            cliente: venta.cliente,
                                            telefono: venta.telefono,
                                            sucursal: venta.sucursal,
                                            zona: venta.zona,
                                            vehiculo: venta.vehiculo,
                                            cobradoPor: venta.cobradoPor,
                                            nota: venta.nota,
                                            comisiones: venta.comisiones,
                                            muchachos: venta.muchachos,
                                            pagos: venta.pagos,
                                          ),
                                        ),
                                      );
                                    },
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: venta.anulada
                                          ? Zyntra.danger
                                          : Zyntra.accent,
                                      shape: RoundedRectangleBorder(
                                        borderRadius: BorderRadius.circular(8),
                                      ),
                                      padding: const EdgeInsets.symmetric(
                                        horizontal: 16,
                                        vertical: 6,
                                      ),
                                    ),
                                    child: const Text(
                                      'Detalles',
                                      style: TextStyle(
                                        color: Colors.white,
                                        fontSize: 15,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),
      bottomNavigationBar: Container(
        height: 80,
        decoration: const BoxDecoration(
          color: Zyntra.nav,
          borderRadius: BorderRadius.only(
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
                      MaterialPageRoute(builder: (context) => const DashboardPage()),
                    );
                  } else if (index == 1) {
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (context) => const InventarioPage()),
                    );
                  } else if (index == 2) {
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (context) => EmpleadosPage()),
                    );
                  } else if (index == 3) {
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (context) => const FinanzasPage()),
                    );
                  }
                },
                child: Container(
                  margin: const EdgeInsets.symmetric(horizontal: 4, vertical: 8),
                  padding: const EdgeInsets.symmetric(vertical: 6),
                  decoration: isSelected
                      ? BoxDecoration(
                          color: Zyntra.accent,
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
      ),
    );
  }
}
