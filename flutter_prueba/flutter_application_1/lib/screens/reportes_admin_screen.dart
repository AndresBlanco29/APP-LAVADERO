import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_application_1/services/comando_service.dart';
import 'package:flutter_application_1/theme/zyntra_theme.dart';
import 'package:intl/intl.dart';

final _cop = NumberFormat.currency(locale: 'es_CO', symbol: '\$', decimalDigits: 0);

class ReportesAdminScreen extends StatefulWidget {
  const ReportesAdminScreen({super.key});

  @override
  State<ReportesAdminScreen> createState() => _ReportesAdminScreenState();
}

class _ReportesAdminScreenState extends State<ReportesAdminScreen>
    with SingleTickerProviderStateMixin {
  final _svc = ComandoService();
  Map<String, dynamic>? _data;
  String? _error;
  bool _busy = false;
  String _preset = 'mes';
  String? _medio;
  late TabController _tabs;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 5, vsync: this);
    _load();
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final data = await _svc.reportesAdminDashboard(
        preset: _preset,
        medioPago: _medio,
      );
      if (!mounted) return;
      setState(() {
        _data = data;
        _busy = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _error = '$e';
      });
    }
  }

  Map<String, dynamic> get _ventas =>
      Map<String, dynamic>.from((_data?['ventas'] as Map?) ?? const {});
  Map<String, dynamic> get _bolsillos =>
      Map<String, dynamic>.from((_data?['bolsillos'] as Map?) ?? const {});
  Map<String, dynamic> get _rent =>
      Map<String, dynamic>.from((_data?['rentabilidad'] as Map?) ?? const {});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Zx.bg(context),
      appBar: AppBar(
        title: const Text('Dashboard admin'),
        actions: [
          IconButton(onPressed: _busy ? null : _load, icon: const Icon(Icons.refresh)),
        ],
        bottom: TabBar(
          controller: _tabs,
          isScrollable: true,
          tabs: const [
            Tab(text: 'Resumen'),
            Tab(text: 'Ventas'),
            Tab(text: 'Bolsillos'),
            Tab(text: 'Proveedores'),
            Tab(text: 'Cierres'),
          ],
        ),
      ),
      body: _busy && _data == null
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                _filters(context),
                if (_error != null)
                  Padding(
                    padding: const EdgeInsets.all(8),
                    child: Text(_error!, style: const TextStyle(color: Colors.redAccent)),
                  ),
                Expanded(
                  child: TabBarView(
                    controller: _tabs,
                    children: [
                      _tabResumen(context),
                      _tabVentas(context),
                      _tabBolsillos(context),
                      _tabProveedores(context),
                      _tabCierres(context),
                    ],
                  ),
                ),
              ],
            ),
    );
  }

  Widget _filters(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
      child: Row(
        children: [
          for (final p in ['hoy', 'ayer', 'semana', 'mes', 'año'])
            Padding(
              padding: const EdgeInsets.only(right: 6),
              child: ChoiceChip(
                label: Text(p),
                selected: _preset == p,
                onSelected: (_) {
                  setState(() => _preset = p);
                  _load();
                },
              ),
            ),
          const SizedBox(width: 8),
          for (final m in [null, 'Efectivo', 'Nequi', 'Datafono'])
            Padding(
              padding: const EdgeInsets.only(right: 6),
              child: FilterChip(
                label: Text(m ?? 'Todos medios'),
                selected: _medio == m,
                onSelected: (_) {
                  setState(() => _medio = m);
                  _load();
                },
              ),
            ),
        ],
      ),
    );
  }

  Widget _kpi(String label, String value, {Color? accent}) {
    return Expanded(
      child: Container(
        margin: const EdgeInsets.all(4),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Zx.card(context),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: TextStyle(color: Zx.muted(context), fontSize: 11)),
            const SizedBox(height: 4),
            Text(
              value,
              style: TextStyle(
                color: accent ?? Zx.text(context),
                fontWeight: FontWeight.w800,
                fontSize: 15,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _tabResumen(BuildContext context) {
    final alertas = ((_data?['alertas'] as List?) ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    final medio = Map<String, dynamic>.from((_ventas['por_medio'] as Map?) ?? const {});
    final prov = Map<String, dynamic>.from((_bolsillos['proveedores'] as Map?) ?? const {});
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(12, 4, 12, 24),
        children: [
          Text(
            _data?['nota_datafono']?.toString() ?? '',
            style: TextStyle(color: Zx.muted(context), fontSize: 12),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              _kpi('Ventas', _cop.format((_ventas['total'] as num?)?.toDouble() ?? 0)),
              _kpi('Tickets', '${_ventas['tickets'] ?? 0}'),
            ],
          ),
          Row(
            children: [
              _kpi('Ticket prom.', _cop.format((_ventas['ticket_promedio'] as num?)?.toDouble() ?? 0)),
              _kpi(
                'Margen',
                '${(_rent['margen_pct'] as num?)?.toStringAsFixed(1) ?? 0}%',
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text('Medios de pago (periodo)', style: _h(context)),
          const SizedBox(height: 8),
          SizedBox(
            height: 180,
            child: PieChart(
              PieChartData(
                sectionsSpace: 2,
                centerSpaceRadius: 36,
                sections: [
                  for (final e in [
                    ('Efectivo', medio['efectivo'], const Color(0xFF22C55E)),
                    ('Nequi', medio['nequi'], const Color(0xFF3077FF)),
                    ('Datafono', medio['datafono'], const Color(0xFFF59E0B)),
                    ('Otros', medio['otros'], const Color(0xFF94A3B8)),
                  ])
                    if (((e.$2 as num?)?.toDouble() ?? 0) > 0)
                      PieChartSectionData(
                        value: (e.$2 as num).toDouble(),
                        title: e.$1,
                        color: e.$3,
                        radius: 48,
                        titleStyle: const TextStyle(fontSize: 10, color: Colors.white),
                      ),
                ],
              ),
            ),
          ),
          Text(
            'Datafono aquí = medio de pago, no bolsillo',
            style: TextStyle(color: Zx.muted(context), fontSize: 11),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 16),
          Text('Proveedores (saldo actual)', style: _h(context)),
          const SizedBox(height: 8),
          SizedBox(
            height: 160,
            child: BarChart(
              BarChartData(
                maxY: _maxProv(prov) * 1.2 + 1,
                barGroups: [
                  for (var i = 0; i < 3; i++)
                    BarChartGroupData(
                      x: i,
                      barRods: [
                        BarChartRodData(
                          toY: [
                            (prov['efectivo'] as num?)?.toDouble() ?? 0,
                            (prov['nequi'] as num?)?.toDouble() ?? 0,
                            (prov['datafono'] as num?)?.toDouble() ?? 0,
                          ][i],
                          width: 22,
                          color: [
                            const Color(0xFF22C55E),
                            const Color(0xFF3077FF),
                            const Color(0xFFF59E0B),
                          ][i],
                          borderRadius: BorderRadius.circular(4),
                        ),
                      ],
                    ),
                ],
                titlesData: FlTitlesData(
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      getTitlesWidget: (v, _) => Text(
                        ['Ef', 'Nq', 'Dt'][v.toInt().clamp(0, 2)],
                        style: TextStyle(color: Zx.muted(context), fontSize: 11),
                      ),
                    ),
                  ),
                  leftTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                ),
                gridData: const FlGridData(show: false),
                borderData: FlBorderData(show: false),
              ),
            ),
          ),
          Text(
            'Total proveedores ${_cop.format((prov['total'] as num?)?.toDouble() ?? 0)}',
            style: TextStyle(color: Zx.text(context), fontWeight: FontWeight.w700),
            textAlign: TextAlign.center,
          ),
          if (alertas.isNotEmpty) ...[
            const SizedBox(height: 12),
            for (final a in alertas)
              Text('⚠ ${a['mensaje']}', style: const TextStyle(color: Colors.orangeAccent)),
          ],
        ],
      ),
    );
  }

  double _maxProv(Map<String, dynamic> p) {
    final vals = [
      (p['efectivo'] as num?)?.toDouble() ?? 0,
      (p['nequi'] as num?)?.toDouble() ?? 0,
      (p['datafono'] as num?)?.toDouble() ?? 0,
    ];
    return vals.reduce((a, b) => a > b ? a : b);
  }

  TextStyle _h(BuildContext context) => TextStyle(
        color: Zx.text(context),
        fontWeight: FontWeight.w800,
        fontSize: 16,
      );

  Widget _tabVentas(BuildContext context) {
    final serie = ((_ventas['serie_diaria'] as List?) ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    final vend = ((_ventas['por_vendedor'] as List?) ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    final prod = ((_ventas['por_producto'] as List?) ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          Text('Ventas por día', style: _h(context)),
          const SizedBox(height: 8),
          SizedBox(
            height: 200,
            child: serie.isEmpty
                ? Center(child: Text('Sin datos', style: TextStyle(color: Zx.muted(context))))
                : BarChart(
                    BarChartData(
                      maxY: serie
                              .map((e) => (e['ventas'] as num?)?.toDouble() ?? 0)
                              .fold<double>(0, (a, b) => a > b ? a : b) *
                          1.2 +
                          1,
                      barGroups: [
                        for (var i = 0; i < serie.length && i < 14; i++)
                          BarChartGroupData(
                            x: i,
                            barRods: [
                              BarChartRodData(
                                toY: (serie[i]['ventas'] as num?)?.toDouble() ?? 0,
                                width: 10,
                                color: Zyntra.accent,
                                borderRadius: BorderRadius.circular(3),
                              ),
                            ],
                          ),
                      ],
                      titlesData: const FlTitlesData(show: false),
                      gridData: const FlGridData(show: false),
                      borderData: FlBorderData(show: false),
                    ),
                  ),
          ),
          const SizedBox(height: 12),
          Text(
            'Datafono vendido: ${_cop.format((_ventas['datafono_vendido'] as num?)?.toDouble() ?? 0)} (medio → proveedores)',
            style: TextStyle(color: Zx.muted(context)),
          ),
          const SizedBox(height: 16),
          Text('Por vendedor', style: _h(context)),
          for (final v in vend.take(10))
            ListTile(
              dense: true,
              title: Text('${v['vendedor']}', style: TextStyle(color: Zx.text(context))),
              trailing: Text(_cop.format((v['ventas'] as num?)?.toDouble() ?? 0)),
              subtitle: Text('${v['tickets']} tickets', style: TextStyle(color: Zx.muted(context))),
            ),
          Text('Top productos', style: _h(context)),
          for (final p in prod.take(10))
            ListTile(
              dense: true,
              title: Text('${p['nombre']}', style: TextStyle(color: Zx.text(context))),
              trailing: Text(_cop.format((p['ventas'] as num?)?.toDouble() ?? 0)),
            ),
          const SizedBox(height: 8),
          Text('Rentabilidad', style: _h(context)),
          Text(
            'Costo ${_cop.format((_rent['costo'] as num?)?.toDouble() ?? 0)} · '
            'Utilidad ${_cop.format((_rent['utilidad_bruta'] as num?)?.toDouble() ?? 0)}',
            style: TextStyle(color: Zx.muted(context)),
          ),
        ],
      ),
    );
  }

  Widget _tabBolsillos(BuildContext context) {
    final admin = Map<String, dynamic>.from((_bolsillos['administrativo'] as Map?) ?? const {});
    final prov = Map<String, dynamic>.from((_bolsillos['proveedores'] as Map?) ?? const {});
    final excluidos = ((_bolsillos['excluidos'] as List?) ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        _card(
          context,
          'Administrativo',
          [
            'Objetivo ${_cop.format((admin['objetivo'] as num?)?.toDouble() ?? 0)}',
            'Provisionado ${_cop.format((admin['provisionado'] as num?)?.toDouble() ?? 0)}',
            'Pendiente ${_cop.format((admin['pendiente'] as num?)?.toDouble() ?? 0)}',
            'Obligaciones ${_cop.format((admin['obligaciones'] as num?)?.toDouble() ?? 0)}',
            'Disponible ${_cop.format((admin['disponible'] as num?)?.toDouble() ?? 0)}',
            'Datafono: NO incluido (solo efectivo)',
          ],
        ),
        const SizedBox(height: 10),
        _card(
          context,
          'Proveedores',
          [
            'Efectivo ${_cop.format((prov['efectivo'] as num?)?.toDouble() ?? 0)}',
            'Nequi ${_cop.format((prov['nequi'] as num?)?.toDouble() ?? 0)}',
            'Datafono ${_cop.format((prov['datafono'] as num?)?.toDouble() ?? 0)} (desglose)',
            'TOTAL ${_cop.format((prov['total'] as num?)?.toDouble() ?? 0)}',
            'TOTAL = Ef + Nq + Dt',
          ],
        ),
        const SizedBox(height: 10),
        for (final e in excluidos)
          Text(
            'Excluido como bolsillo: ${e['nombre']} — ${e['razon']}',
            style: const TextStyle(color: Colors.orangeAccent, fontSize: 12),
          ),
      ],
    );
  }

  Widget _card(BuildContext context, String title, List<String> lines) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Zx.card(context),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: _h(context)),
          const SizedBox(height: 8),
          for (final l in lines)
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Text(l, style: TextStyle(color: Zx.text(context))),
            ),
        ],
      ),
    );
  }

  Widget _tabProveedores(BuildContext context) {
    final pagos = (((_data?['proveedores'] as Map?)?['pagos'] as List?) ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    final movs = ((_data?['movimientos_proveedores'] as List?) ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        Text('Pagos (medios: Ef / Nq / Datafono / mixto)', style: _h(context)),
        if (pagos.isEmpty)
          Text('Sin pagos en vista', style: TextStyle(color: Zx.muted(context))),
        for (final p in pagos.take(30))
          ListTile(
            title: Text('${p['proveedor']}', style: TextStyle(color: Zx.text(context))),
            subtitle: Text(
              '${p['fecha']} · ${p['medio']} · bolsillo PROVEEDORES',
              style: TextStyle(color: Zx.muted(context), fontSize: 11),
            ),
            trailing: Text(_cop.format((p['valor'] as num?)?.toDouble() ?? 0)),
          ),
        const SizedBox(height: 12),
        Text('Movimientos', style: _h(context)),
        for (final m in movs.take(40))
          ListTile(
            dense: true,
            title: Text('${m['tipo']} · ${m['medio_pago']}', style: TextStyle(color: Zx.text(context))),
            subtitle: Text(
              '${m['fecha']} · ${m['proveedor']} · ${m['usuario']}\n'
              'Dt ${_cop.format((m['datafono'] as num?)?.toDouble() ?? 0)} (solo proveedores)',
              style: TextStyle(color: Zx.muted(context), fontSize: 11),
            ),
            isThreeLine: true,
            trailing: Text(_cop.format((m['valor'] as num?)?.toDouble() ?? 0)),
          ),
      ],
    );
  }

  Widget _tabCierres(BuildContext context) {
    final cierres = Map<String, dynamic>.from((_data?['cierres'] as Map?) ?? const {});
    final diarios = ((cierres['diarios'] as List?) ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    final generales = ((cierres['generales'] as List?) ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        Text('Cierres diarios · correcciones: ${cierres['correcciones'] ?? 0}', style: _h(context)),
        for (final c in diarios)
          ListTile(
            title: Text('#${c['id']} ${c['vendedor']}', style: TextStyle(color: Zx.text(context))),
            subtitle: Text(
              '${c['fecha']} · Ef ${_cop.format((c['efectivo'] as num?)?.toDouble() ?? 0)} · '
              'Nq ${_cop.format((c['nequi'] as num?)?.toDouble() ?? 0)} · '
              'Dt ${_cop.format((c['datafono'] as num?)?.toDouble() ?? 0)}\n'
              '${c['estado']} · Diff ${_cop.format((c['diferencia'] as num?)?.toDouble() ?? 0)}',
              style: TextStyle(color: Zx.muted(context), fontSize: 11),
            ),
            isThreeLine: true,
          ),
        const SizedBox(height: 12),
        Text('Cierres generales', style: _h(context)),
        for (final g in generales)
          ListTile(
            title: Text('#${g['id']} ${g['estado']}', style: TextStyle(color: Zx.text(context))),
            subtitle: Text(
              'Dt ${_cop.format((g['datafono'] as num?)?.toDouble() ?? 0)} · '
              'Ef ${_cop.format((g['efectivo'] as num?)?.toDouble() ?? 0)} · '
              'Nq ${_cop.format((g['nequi'] as num?)?.toDouble() ?? 0)}',
              style: TextStyle(color: Zx.muted(context)),
            ),
          ),
      ],
    );
  }
}
