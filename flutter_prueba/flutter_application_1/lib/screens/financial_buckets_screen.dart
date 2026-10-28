import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_application_1/screens/finanzas_page.dart';
import 'package:flutter_application_1/screens/bolsillos_hub_screen.dart';
import 'package:flutter_application_1/screens/monthly_close_screen.dart';
import 'package:flutter_application_1/services/comando_service.dart';
import 'package:flutter_application_1/theme/zyntra_theme.dart';

class FinancialBucketsScreen extends StatefulWidget {
  const FinancialBucketsScreen({super.key});

  @override
  State<FinancialBucketsScreen> createState() => _FinancialBucketsScreenState();
}

class _FinancialBucketsScreenState extends State<FinancialBucketsScreen> {
  final _svc = ComandoService();
  Map<String, dynamic>? _data;
  String _vista = 'hoy';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final data = await _svc.bolsillos();
    if (!mounted) return;
    setState(() => _data = data);
  }

  List<Map<String, dynamic>> get _bolsillos {
    final raw = (_data?['bolsillos'] as List?) ?? const [];
    return raw.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  @override
  Widget build(BuildContext context) {
    final bolsas = _bolsillos;
    return Scaffold(
      backgroundColor: Zx.bg(context),
      appBar: AppBar(
        title: const Text('Bolsillos y provisiones'),
        actions: [
          IconButton(
            tooltip: 'Cierre mensual',
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const MonthlyCloseScreen()),
              );
            },
            icon: const Icon(Icons.calendar_month_outlined),
          ),
          IconButton(
            tooltip: 'Entradas y salidas',
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const FinanzasPage()),
              );
            },
            icon: const Icon(Icons.swap_vert),
          ),
          IconButton(
            onPressed: _crear,
            icon: const Icon(Icons.add_card_outlined),
          ),
        ],
      ),
      body: _data == null
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
                children: [
                  Text(
                    '¿Cuánto de la caja es de proveedores y cuánto es utilidad?',
                    style: TextStyle(color: Zx.muted(context), fontSize: 13),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      _chip('Hoy', 'hoy'),
                      const SizedBox(width: 8),
                      _chip('Mes', 'mes'),
                    ],
                  ),
                  const SizedBox(height: 16),
                  SizedBox(
                    height: 168,
                    child: bolsas.isEmpty
                        ? Center(
                            child: Text(
                              'Sin bolsillos. Créalos con +',
                              style: TextStyle(color: Zx.muted(context)),
                            ),
                          )
                        : PieChart(
                            PieChartData(
                              sectionsSpace: 3,
                              centerSpaceRadius: 42,
                              sections: [
                                for (final b in bolsas)
                                  PieChartSectionData(
                                    value: (b['porcentaje'] as num?)?.toDouble() ?? 0,
                                    color: _parseColor(b['color']),
                                    title: '${(b['porcentaje'] as num?)?.toStringAsFixed(0)}%',
                                    radius: 46,
                                    titleStyle: const TextStyle(
                                      color: Colors.white,
                                      fontSize: 11,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                              ],
                            ),
                          ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Venta ${_vista == 'hoy' ? 'de hoy' : 'del mes'}: ${cop.format(_data?[_vista == 'hoy' ? 'venta_hoy' : 'venta_mes'] ?? 0)}',
                    style: TextStyle(
                      color: Zx.text(context),
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  if ((_data?['recaudo_hoy'] as Map?) != null) ...[
                    const SizedBox(height: 6),
                    Text(
                      _recaudoTexto(),
                      style: TextStyle(color: Zx.muted(context), fontSize: 12),
                    ),
                  ],
                  const SizedBox(height: 14),
                  for (var i = 0; i < bolsas.length; i++)
                    _card(bolsas[i])
                        .animate()
                        .fadeIn(delay: (80 * i).ms)
                        .slideX(begin: 0.05),
                ],
              ),
            ),
    );
  }

  Widget _chip(String label, String value) {
    final on = _vista == value;
    return ChoiceChip(
      label: Text(label),
      selected: on,
      onSelected: (_) => setState(() => _vista = value),
      selectedColor: Zyntra.accent,
      labelStyle: TextStyle(color: on ? Colors.white : Zx.text(context)),
    );
  }

  Widget _card(Map<String, dynamic> b) {
    final color = _parseColor(b['color']);
    final asignado = _vista == 'hoy' ? b['asignado_hoy'] : b['asignado_mes'];
    final saldo = _vista == 'hoy' ? b['saldo_hoy'] : b['saldo_mes'];
    final meta = (b['meta_mensual'] as num?)?.toDouble() ?? 0;
    final mes = (b['asignado_mes'] as num?)?.toDouble() ?? 0;
    final progress = meta <= 0 ? 0.0 : (mes / meta).clamp(0.0, 1.0);
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [color.withOpacity(0.92), color.withOpacity(0.62)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.account_balance_wallet, color: Colors.white),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  '${b['nombre']}',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              Text(
                '${b['porcentaje']}%',
                style: const TextStyle(color: Colors.white70),
              ),
            ],
          ),
          const SizedBox(height: 18),
          Text(
            cop.format(saldo ?? 0),
            style: const TextStyle(
              color: Colors.white,
              fontSize: 28,
              fontWeight: FontWeight.w800,
            ),
          ),
          Text(
            'Asignado ${cop.format(asignado ?? 0)}',
            style: const TextStyle(color: Colors.white70),
          ),
          if (meta > 0) ...[
            const SizedBox(height: 10),
            LinearProgressIndicator(
              value: progress,
              backgroundColor: Colors.white24,
              color: Colors.white,
            ),
            const SizedBox(height: 4),
            Text(
              'Meta mensual ${cop.format(meta)}',
              style: const TextStyle(color: Colors.white70, fontSize: 12),
            ),
          ],
          const SizedBox(height: 10),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              for (final m in (((b['por_medio'] as List?) ?? const [])
                  .map((e) => Map<String, dynamic>.from(e as Map))))
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.black26,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    '${m['metodo']}: ${cop.format(_vista == 'hoy' ? m['saldo_hoy'] : m['saldo_mes'])}',
                    style: const TextStyle(color: Colors.white, fontSize: 11),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 12),
          Align(
            alignment: Alignment.centerRight,
            child: Wrap(
              spacing: 8,
              children: [
                if ('${b['codigo']}' == 'PROVEEDORES')
                  TextButton(
                    onPressed: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => const BolsillosHubScreen(),
                        ),
                      ).then((_) => _load());
                    },
                    style: TextButton.styleFrom(foregroundColor: Colors.white),
                    child: const Text('Abrir bolsillo proveedores'),
                  ),
                TextButton(
                  onPressed: () => _egreso(b),
                  style: TextButton.styleFrom(foregroundColor: Colors.white),
                  child: const Text('Registrar egreso'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _recaudoTexto() {
    final key = _vista == 'hoy' ? 'recaudo_hoy' : 'recaudo_mes';
    final r = Map<String, dynamic>.from((_data?[key] as Map?) ?? const {});
    return 'Efectivo ${cop.format(r['Efectivo'] ?? 0)} · Nequi ${cop.format(r['Nequi'] ?? 0)} · '
        'Tarjeta ${cop.format(r['Tarjeta'] ?? 0)} · Banco ${cop.format(r['Transferencia'] ?? 0)}';
  }

  List<Map<String, dynamic>> get _categorias {
    final raw = (_data?['categorias'] as List?) ?? const [];
    if (raw.isNotEmpty) {
      return raw.map((e) => Map<String, dynamic>.from(e as Map)).toList();
    }
    return const [
      {'id': 'NOMINA', 'nombre': 'Nómina de empleados'},
      {'id': 'REGENTE', 'nombre': 'Honorarios regente de farmacia'},
      {'id': 'ARRIENDO', 'nombre': 'Arriendo / alquiler'},
      {'id': 'SERVICIOS', 'nombre': 'Servicios públicos'},
      {'id': 'OTROS', 'nombre': 'Mantenimiento / otros'},
    ];
  }

  Future<void> _egreso(Map<String, dynamic> b) async {
    final monto = TextEditingController();
    final nota = TextEditingController();
    final comprobante = TextEditingController();
    var metodo = 'Efectivo';
    var categoria = '${b['codigo']}' == 'PROVISIONES' ? 'NOMINA' : '';
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Zx.card(context),
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setLocal) {
            return Padding(
              padding: EdgeInsets.only(
                left: 16,
                right: 16,
                top: 16,
                bottom: MediaQuery.of(ctx).viewInsets.bottom + 16,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    'Egreso de ${b['nombre']}',
                    style: TextStyle(
                      color: Zx.text(context),
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: monto,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(hintText: 'Monto'),
                  ),
                  const SizedBox(height: 8),
                  DropdownButtonFormField<String>(
                    value: metodo,
                    items: [
                      for (final m in ['Efectivo', 'Nequi', 'Tarjeta', 'Transferencia'])
                        DropdownMenuItem(value: m, child: Text(m)),
                    ],
                    onChanged: (v) => setLocal(() => metodo = v ?? metodo),
                    decoration: const InputDecoration(hintText: 'Medio de pago'),
                  ),
                  if ('${b['codigo']}' == 'PROVISIONES') ...[
                    const SizedBox(height: 8),
                    DropdownButtonFormField<String>(
                      value: categoria,
                      items: [
                        for (final c in _categorias.where((e) => e['id'] != 'PROVEEDOR'))
                          DropdownMenuItem(
                            value: '${c['id']}',
                            child: Text('${c['nombre']}'),
                          ),
                      ],
                      onChanged: (v) => setLocal(() => categoria = v ?? categoria),
                      decoration: const InputDecoration(hintText: 'Categoría'),
                    ),
                  ],
                  const SizedBox(height: 8),
                  TextField(
                    controller: nota,
                    decoration: const InputDecoration(hintText: 'Concepto'),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: comprobante,
                    decoration: const InputDecoration(hintText: 'Comprobante (opcional)'),
                  ),
                  const SizedBox(height: 12),
                  ElevatedButton(
                    onPressed: () => Navigator.pop(ctx, true),
                    child: const Text('Descontar del bolsillo'),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
    if (ok != true) return;
    final value = double.tryParse(monto.text.replaceAll(',', '.')) ?? 0;
    if (value <= 0) return;
    HapticFeedback.selectionClick();
    await _svc.egresoBolsillo(
      id: int.parse('${b['id']}'),
      monto: value,
      nota: nota.text.trim(),
      metodo: metodo,
      categoria: categoria,
      comprobante: comprobante.text.trim(),
    );
    await _load();
  }

  Future<void> _pagoProveedor(Map<String, dynamic> b) async {
    final nota = TextEditingController();
    final controllers = {
      for (final m in ['Efectivo', 'Nequi', 'Tarjeta', 'Transferencia'])
        m: TextEditingController(),
    };
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Zx.card(context),
      builder: (ctx) {
        return Padding(
          padding: EdgeInsets.only(
            left: 16,
            right: 16,
            top: 16,
            bottom: MediaQuery.of(ctx).viewInsets.bottom + 16,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Pago a proveedor (elige de dónde sale el dinero)',
                style: TextStyle(
                  color: Zx.text(context),
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 12),
              for (final m in controllers.keys) ...[
                TextField(
                  controller: controllers[m],
                  keyboardType: TextInputType.number,
                  decoration: InputDecoration(hintText: m),
                ),
                const SizedBox(height: 8),
              ],
              TextField(
                controller: nota,
                decoration: const InputDecoration(hintText: 'Factura o proveedor'),
              ),
              const SizedBox(height: 12),
              ElevatedButton(
                onPressed: () => Navigator.pop(ctx, true),
                child: const Text('Descontar de proveedores'),
              ),
            ],
          ),
        );
      },
    );
    if (ok != true) return;
    final origenes = <Map<String, dynamic>>[];
    controllers.forEach((metodo, ctrl) {
      final v = double.tryParse(ctrl.text.replaceAll(',', '.')) ?? 0;
      if (v > 0) origenes.add({'metodo': metodo, 'monto': v});
    });
    if (origenes.isEmpty) return;
    HapticFeedback.selectionClick();
    await _svc.pagoProveedor(origenes: origenes, nota: nota.text.trim());
    await _load();
  }

  Future<void> _crear() async {
    final nombre = TextEditingController();
    final pct = TextEditingController(text: '5');
    final meta = TextEditingController(text: '0');
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: Zx.card(context),
        title: const Text('Nuevo bolsillo'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nombre,
              decoration: const InputDecoration(hintText: 'Nombre'),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: pct,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(hintText: '% asignado'),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: meta,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(hintText: 'Meta mensual'),
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
            child: const Text('Crear'),
          ),
        ],
      ),
    );
    if (ok != true || nombre.text.trim().isEmpty) return;
    await _svc.crearBolsillo({
      'nombre': nombre.text.trim(),
      'porcentaje': double.tryParse(pct.text) ?? 0,
      'color': '#5EC8FF',
      'icono': 'wallet',
      'meta_mensual': double.tryParse(meta.text) ?? 0,
    });
    await _load();
  }

  Color _parseColor(dynamic raw) {
    final s = '${raw ?? '#3077FF'}'.replaceAll('#', '');
    try {
      return Color(int.parse('FF$s', radix: 16));
    } catch (_) {
      return Zyntra.accent;
    }
  }
}
