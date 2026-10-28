import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_application_1/screens/Login.dart';
import 'package:flutter_application_1/screens/approval_detail_screen.dart';
import 'package:flutter_application_1/screens/fefo_alerts_screen.dart';
import 'package:flutter_application_1/screens/financial_buckets_screen.dart';
import 'package:flutter_application_1/screens/monthly_close_screen.dart';
import 'package:flutter_application_1/screens/cierre_general_screen.dart';
import 'package:flutter_application_1/screens/provision_admin_screen.dart';
import 'package:flutter_application_1/screens/bolsillos_hub_screen.dart';
import 'package:flutter_application_1/screens/reportes_admin_screen.dart';
import 'package:flutter_application_1/screens/pendientes_list_screen.dart';
import 'package:flutter_application_1/screens/perfil.dart';
import 'package:flutter_application_1/screens/profitability_report_screen.dart';
import 'package:flutter_application_1/api/api_client.dart';
import 'package:flutter_application_1/services/comando_service.dart';
import 'package:flutter_application_1/ventas_model.dart';
import 'package:flutter_application_1/theme/zyntra_theme.dart';
import 'package:flutter_application_1/widgets/bottom_nav_bar.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import 'comparativa_page.dart';
import 'rotacion_page.dart';

class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key});

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  final _svc = ComandoService();
  Map<String, dynamic>? _resumen;
  List<Map<String, dynamic>> _pendientes = [];
  int _currentIndex = 0;
  Timer? _refreshTimer;
  Timer? _wsRetry;
  WebSocketChannel? _ws;
  int _wsAttempt = 0;
  bool _wsClosing = false;
  String _profileImagePath = 'lib/imagenes/perfil.png';
  final Set<int> _vistos = {};
  bool _avisosListos = false;
  bool _modalAbierto = false;
  final AudioPlayer _caja = AudioPlayer();
  final _plata = NumberFormat.currency(locale: 'es_CO', symbol: '\$', decimalDigits: 0);

  @override
  void initState() {
    super.initState();
    _loadProfileImage();
    _refreshData();
    _connectWs();
    _refreshTimer = Timer.periodic(const Duration(seconds: 8), (_) {
      _refreshData();
    });
  }

  Future<void> _connectWs() async {
    _wsRetry?.cancel();
    try {
      final id = await _svc.adminId();
      _wsClosing = true;
      await _ws?.sink.close();
      _wsClosing = false;
      _ws = WebSocketChannel.connect(Uri.parse(_svc.wsUrl(id)));
      _wsAttempt = 0;
      _ws!.stream.listen((mensaje) {
        _refreshData();
        _avisoCaja(mensaje);
      }, onError: (_) {
        if (!_wsClosing) _scheduleWsReconnect();
      }, onDone: () {
        if (!_wsClosing) _scheduleWsReconnect();
      });
    } catch (_) {
      _wsClosing = false;
      _scheduleWsReconnect();
    }
  }

  Future<void> _avisoCaja(dynamic mensaje) async {
    if (!mounted) return;
    Map<String, dynamic>? data;
    try {
      final crudo = mensaje is String ? mensaje : mensaje.toString();
      final decodificado = jsonDecode(crudo);
      if (decodificado is Map) {
        data = Map<String, dynamic>.from(decodificado);
      }
    } catch (_) {
      return;
    }
    if (data == null || data['tipo'] != 'orden_cobrada') return;
    final ventaId = (data['venta_id'] as num?)?.toInt() ?? 0;
    if (ventaId > 0 && !_vistos.add(ventaId)) return;
    try {
      await _caja.play(AssetSource('sounds/caja.wav'));
    } catch (_) {}
    if (!mounted || _modalAbierto) return;
    final total = (data['total'] as num?) ?? 0;
    final sucursal = '${data['sucursal'] ?? ''}';
    final zona = '${data['zona'] ?? ''}';
    final placa = '${data['placa'] ?? ''}';
    final cliente = '${data['cliente'] ?? ''}';
    final ganancia = (data['ganancia'] as num?) ?? 0;
    final gente = ((data['colaboradores'] as List?) ?? const [])
        .map((e) => '$e')
        .where((e) => e.isNotEmpty)
        .join(', ');
    final sede = [sucursal, zona].where((t) => t.isNotEmpty).join(' · ');
    final lineas = [
      if (placa.isNotEmpty) placa,
      if (cliente.isNotEmpty) cliente,
      _plata.format(total),
      if (sede.isNotEmpty) sede,
      if (gente.isNotEmpty) gente,
      if (ganancia > 0) 'Ganancia ${_plata.format(ganancia)}',
    ];
    _modalAbierto = true;
    showDialog<void>(
      context: context,
      builder: (dialogContext) {
        Future.delayed(const Duration(seconds: 4), () {
          if (dialogContext.mounted) Navigator.of(dialogContext).pop();
        });
        return AlertDialog(
          backgroundColor: const Color(0xFF1E9B45),
          title: const Text('Entró plata', style: TextStyle(color: Colors.white)),
          content: Text(
            lineas.join('\n'),
            style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w800),
          ),
        );
      },
    ).whenComplete(() => _modalAbierto = false);
  }

  void _scheduleWsReconnect() {
    if (!mounted) return;
    _wsAttempt = (_wsAttempt + 1).clamp(1, 6);
    _wsRetry?.cancel();
    _wsRetry = Timer(Duration(seconds: 2 * _wsAttempt), () {
      if (mounted) _connectWs();
    });
  }

  Future<void> _loadProfileImage() async {
    final prefs = await SharedPreferences.getInstance();
    final storedPath = prefs.getString('profileImagePath');
    if (storedPath != null && storedPath.isNotEmpty && mounted) {
      setState(() => _profileImagePath = storedPath);
    }
  }

  @override
  void dispose() {
    _wsClosing = true;
    _refreshTimer?.cancel();
    _wsRetry?.cancel();
    _ws?.sink.close();
    _caja.dispose();
    super.dispose();
  }

  Map<String, dynamic> get _hoy =>
      Map<String, dynamic>.from((_resumen?['hoy'] as Map?) ?? const {});
  Map<String, dynamic> get _mes =>
      Map<String, dynamic>.from((_resumen?['mes'] as Map?) ?? const {});
  Map<String, dynamic> get _fefo =>
      Map<String, dynamic>.from((_resumen?['fefo'] as Map?) ?? const {});

  Future<void> _vigilarVentas() async {
    try {
      final data = await ApiClient.getJson('/ventas', ttl: Duration.zero);
      final list = data is List ? data : <dynamic>[];
      final ventas = list
          .whereType<Map>()
          .map((item) => Venta.fromJson(Map<String, dynamic>.from(item)))
          .where((venta) => !venta.anulada)
          .toList();
      ventas.sort((a, b) {
        try {
          return DateTime.parse(b.fecha).compareTo(DateTime.parse(a.fecha));
        } catch (_) {
          return 0;
        }
      });
      if (!_avisosListos) {
        for (final venta in ventas) {
          _vistos.add(venta.id);
        }
        _avisosListos = true;
        return;
      }
      final nuevas = <Venta>[];
      for (final venta in ventas) {
        if (_vistos.contains(venta.id)) continue;
        nuevas.add(venta);
      }
      if (nuevas.isEmpty || !mounted) return;
      for (final venta in nuevas.skip(1)) {
        _vistos.add(venta.id);
      }
      final venta = nuevas.first;
      _avisoCaja(jsonEncode({
        'tipo': 'orden_cobrada',
        'venta_id': venta.id,
        'total': venta.total,
        'sucursal': venta.sucursal,
        'zona': venta.zona,
        'placa': venta.placa,
        'cliente': venta.cliente,
        'ganancia': venta.ganancia,
        'colaboradores': venta.lavadero
            ? venta.muchachos.map((p) => '${p['nombre'] ?? ''}').where((n) => n.isNotEmpty).toList()
            : [venta.nombreEmpleado],
      }));
    } catch (_) {}
  }

  Future<void> _refreshData() async {
    try {
      final data = await _svc.resumen();
      final pend = await _svc.pendientes();
      if (!mounted) return;
      setState(() {
        _resumen = data;
        _pendientes = pend;
      });
      _maybeAlert(pend);
      await _vigilarVentas();
    } catch (_) {
      if (!mounted || _resumen != null) return;
      setState(() {
        _resumen = {
          'hoy': {
            'venta': 0,
            'costo': 0,
            'utilidad': 0,
            'margen_pct': 0,
            'tickets': 0,
          },
          'mes': {
            'venta': 0,
            'costo': 0,
            'utilidad': 0,
            'margen_pct': 0,
            'tickets': 0,
          },
          'fefo': {'vencidos': 0, 'd30': 0, 'd60': 0, 'd90': 0},
          'live_sales': <dynamic>[],
        };
      });
    }
  }

  Future<void> _maybeAlert(List<Map<String, dynamic>> pend) async {
    if (_modalAbierto || !mounted || pend.isEmpty) return;
    final nuevo = pend.cast<Map<String, dynamic>>().where((s) {
      final id = int.tryParse('${s['id']}') ?? 0;
      return id > 0 && !_vistos.contains(id);
    });
    if (nuevo.isEmpty) return;
    final sol = nuevo.first;
    _vistos.add(int.parse('${sol['id']}'));
    _modalAbierto = true;
    await ApprovalDetailScreen.show(context, sol);
    _modalAbierto = false;
    await _refreshData();
  }

  void _mostrarDialogoCerrarSesion(BuildContext context) {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          backgroundColor: Zx.card(context),
          title: Text('Confirmación', style: TextStyle(color: Zx.text(context))),
          content: Text(
            '¿Está seguro que desea cerrar sesión?',
            style: TextStyle(color: Zx.muted(context)),
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
    final live = ((_resumen?['live_sales'] as List?) ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    return Scaffold(
      backgroundColor: Zx.bg(context),
      extendBody: true,
      body: SafeArea(
        child: RefreshIndicator(
          color: Zyntra.accent,
          onRefresh: _refreshData,
          child: _resumen == null
              ? const Center(child: CircularProgressIndicator(color: Zyntra.cyan))
              : ListView(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 100),
                  children: [
                    _header(),
                    const SizedBox(height: 16),
                    _kpis(),
                    const SizedBox(height: 12),
                    _pocketsTeaser(),
                    const SizedBox(height: 12),
                    _quickActions(),
                    if (_pendientes.isNotEmpty) ...[
                      const SizedBox(height: 12),
                      _pendingBanner(),
                    ],
                    const SizedBox(height: 12),
                    _fefoRow(),
                    const SizedBox(height: 12),
                    _alertasOperativas(),
                    const SizedBox(height: 16),
                    Text(
                      'Stream de ventas',
                      style: TextStyle(
                        color: Zx.text(context),
                        fontWeight: FontWeight.w800,
                        fontSize: 16,
                      ),
                    ),
                    const SizedBox(height: 8),
                    if (live.isEmpty)
                      Text(
                        'Aún no hay facturas en vivo',
                        style: TextStyle(color: Zx.muted(context)),
                      ),
                    for (final v in live.take(8)) _saleTile(v),
                  ],
                ),
        ),
      ),
      bottomNavigationBar: CustomBottomNavigationBar(
        currentIndex: _currentIndex,
      ),
    );
  }

  Widget _header() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Zyntra',
              style: TextStyle(
                color: Zyntra.cyan,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
            Text(
              'Centro de comando',
              style: TextStyle(
                color: Zx.text(context),
                fontSize: 24,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
        PopupMenuButton<String>(
          color: Zx.elevated(context),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          offset: const Offset(-10, 50),
          itemBuilder: (BuildContext context) => [
            PopupMenuItem<String>(
              value: 'perfil',
              child: Text('Ver Perfil', style: TextStyle(color: Zx.text(context))),
            ),
            const PopupMenuDivider(height: 1),
            PopupMenuItem<String>(
              value: 'cerrar_sesion',
              child: Text(
                'Cerrar Sesión',
                style: TextStyle(color: Zx.text(context)),
              ),
            ),
          ],
          onSelected: (String value) {
            if (value == 'perfil') {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => PerfilPage()),
              ).then((_) => _loadProfileImage());
            } else if (value == 'cerrar_sesion') {
              _mostrarDialogoCerrarSesion(context);
            }
          },
          icon: CircleAvatar(
            radius: 20,
            backgroundImage: _profileImagePath.startsWith('lib/imagenes')
                ? AssetImage(_profileImagePath) as ImageProvider
                : FileImage(File(_profileImagePath)),
          ),
        ),
      ],
    );
  }

  Widget _kpis() {
    final venta = (_hoy['venta'] as num?)?.toDouble() ?? 0;
    final costo = (_hoy['costo'] as num?)?.toDouble() ?? 0;
    final utilidad = (_hoy['utilidad'] as num?)?.toDouble() ?? 0;
    final margen = (_hoy['margen_pct'] as num?)?.toDouble() ?? 0;
    return Column(
      children: [
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF1B3A8A), Color(0xFF3077FF)],
            ),
            borderRadius: BorderRadius.circular(20),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Utilidad real de hoy', style: TextStyle(color: Colors.white70)),
              const SizedBox(height: 6),
              Text(
                cop.format(utilidad),
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 32,
                  fontWeight: FontWeight.w800,
                ),
              ),
              Text(
                'Margen ${margen.toStringAsFixed(1)}% · ${ _hoy['tickets'] ?? 0} tickets',
                style: const TextStyle(color: Colors.white70),
              ),
            ],
          ),
        ).animate().fadeIn().slideY(begin: 0.08),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(child: _mini('Venta hoy', cop.format(venta), Zyntra.accent)),
            const SizedBox(width: 8),
            Expanded(child: _mini('Costo hoy', cop.format(costo), Zyntra.warning)),
          ],
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: _mini(
                'Utilidad mes',
                cop.format(_mes['utilidad'] ?? 0),
                Zyntra.success,
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _mini(
                'Venta mes',
                cop.format(_mes['venta'] ?? 0),
                Zyntra.purple,
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _mini(String title, String value, Color accent) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Zx.card(context),
        borderRadius: BorderRadius.circular(14),
        border: Border(left: BorderSide(color: accent, width: 3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: TextStyle(color: Zx.muted(context), fontSize: 12)),
          const SizedBox(height: 4),
          Text(
            value,
            style: TextStyle(
              color: Zx.text(context),
              fontWeight: FontWeight.w800,
              fontSize: 16,
            ),
          ),
        ],
      ),
    );
  }

  Widget _pendingBanner() {
    return GestureDetector(
      onTap: () {
        final Widget destino = _pendientes.length == 1
            ? ApprovalDetailScreen(solicitud: _pendientes.first)
            : const PendientesListScreen();
        Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => destino),
        ).then((_) => _refreshData());
      },
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Zyntra.warning.withOpacity(0.15),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Zyntra.warning),
        ),
        child: Row(
          children: [
            Container(
              width: 10,
              height: 10,
              decoration: const BoxDecoration(
                color: Zyntra.warning,
                shape: BoxShape.circle,
              ),
            ).animate(onPlay: (c) => c.repeat(reverse: true)).fade(duration: 600.ms),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                '${_pendientes.length} devolución(es) esperando aprobación',
                style: TextStyle(
                  color: Zx.text(context),
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            const Icon(Icons.chevron_right, color: Zyntra.warning),
          ],
        ),
      ),
    );
  }

  Widget _fefoRow() {
    return GestureDetector(
      onTap: () {
        Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => const FefoAlertsScreen()),
        );
      },
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Zx.card(context),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Control FEFO',
              style: TextStyle(
                color: Zx.text(context),
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                _dot('Vencidos', _fefo['vencidos'] ?? 0, Zyntra.danger),
                _dot('<30d', _fefo['d30'] ?? 0, Zyntra.warning),
                _dot('<60d', _fefo['d60'] ?? 0, Zyntra.accent),
                _dot('<90d', _fefo['d90'] ?? 0, Zyntra.cyan),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _dot(String label, dynamic n, Color color) {
    return Expanded(
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(vertical: 8),
            decoration: BoxDecoration(
              color: color.withOpacity(0.15),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Center(
              child: Text(
                '$n',
                style: TextStyle(
                  color: color,
                  fontWeight: FontWeight.w800,
                  fontSize: 18,
                ),
              ),
            ),
          ),
          const SizedBox(height: 4),
          Text(label, style: TextStyle(color: Zx.muted(context), fontSize: 11)),
        ],
      ),
    );
  }

  Widget _alertasOperativas() {
    final stock = _resumen?['stock_bajo'] ?? 0;
    final cierres = _resumen?['cierres_hoy'] ?? 0;
    return Row(
      children: [
        Expanded(
          child: _mini('Stock mínimo', '$stock productos', Zyntra.danger),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: _mini('Cierres de caja hoy', '$cierres', Zyntra.cyan),
        ),
      ],
    );
  }

  Widget _pocketsTeaser() {
    final bolsas = (((_resumen?['bolsillos'] as Map?)?['bolsillos'] as List?) ??
            const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    return GestureDetector(
      onTap: () {
        Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => const FinancialBucketsScreen()),
        );
      },
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Zx.card(context),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  'Bolsillos financieros',
                  style: TextStyle(
                    color: Zx.text(context),
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const Spacer(),
                const Icon(Icons.chevron_right, color: Zyntra.cyan),
              ],
            ),
            const SizedBox(height: 8),
            if (bolsas.isEmpty)
              Text(
                'Separa proveedores, utilidad, operación e impuestos',
                style: TextStyle(color: Zx.muted(context)),
              )
            else
              SizedBox(
                height: 86,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: bolsas.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 8),
                  itemBuilder: (_, i) {
                    final b = bolsas[i];
                    return Container(
                      width: 150,
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Zyntra.accent.withOpacity(0.18),
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '${b['nombre']}',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              color: Zx.text(context),
                              fontWeight: FontWeight.w600,
                              fontSize: 12,
                            ),
                          ),
                          const Spacer(),
                          Text(
                            cop.format(b['saldo_hoy'] ?? 0),
                            style: const TextStyle(
                              color: Zyntra.cyan,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _quickActions() {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        _action('Utilidad', Icons.insights, () {
          Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const ProfitabilityReportScreen()),
          );
        }),
        _action('Bolsillos', Icons.account_balance_wallet_outlined, () {
          Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const FinancialBucketsScreen()),
          );
        }),
        _action('Cierre mensual', Icons.calendar_month, () {
          Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const MonthlyCloseScreen()),
          );
        }),
        _action('Cierre general', Icons.fact_check_outlined, () {
          Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const CierreGeneralScreen()),
          );
        }),
        _action('Provisión admin', Icons.savings_outlined, () {
          Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const ProvisionAdminScreen()),
          );
        }),
        _action('Bolsillos', Icons.account_balance_wallet_outlined, () {
          Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const BolsillosHubScreen()),
          );
        }),
        _action('D. Admin', Icons.dashboard_customize_outlined, () {
          Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const ReportesAdminScreen()),
          );
        }),
        _action('Rotación', Icons.sync, () {
          Navigator.push(context, MaterialPageRoute(builder: (_) => RotacionPage()));
        }),
        _action('Comparativos', Icons.stacked_bar_chart, () {
          Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => ComparativaPage()),
          );
        }),
      ],
    );
  }

  Widget _action(String label, IconData icon, VoidCallback onTap) {
    return ElevatedButton.icon(
      onPressed: onTap,
      icon: Icon(icon, size: 18),
      label: Text(label),
      style: ElevatedButton.styleFrom(backgroundColor: Zx.elevated(context)),
    );
  }

  Widget _saleTile(Map<String, dynamic> v) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Zx.card(context),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '#${v['id']} · ${v['cajero'] ?? 'Caja'}',
                  style: TextStyle(
                    color: Zx.text(context),
                    fontWeight: FontWeight.w700,
                  ),
                ),
                Text(
                  '${v['pago'] ?? 'Efectivo'} · ${v['fecha'] ?? ''}',
                  style: TextStyle(color: Zx.muted(context), fontSize: 12),
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                cop.format(v['total'] ?? 0),
                style: TextStyle(color: Zx.text(context), fontWeight: FontWeight.bold),
              ),
              Text(
                'Utilidad ${cop.format(v['utilidad'] ?? 0)}',
                style: const TextStyle(color: Zyntra.success, fontSize: 12),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
