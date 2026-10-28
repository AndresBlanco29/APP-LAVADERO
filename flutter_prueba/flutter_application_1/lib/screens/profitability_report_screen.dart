import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_application_1/services/comando_service.dart';
import 'package:flutter_application_1/theme/zyntra_theme.dart';

class ProfitabilityReportScreen extends StatefulWidget {
  const ProfitabilityReportScreen({super.key});

  @override
  State<ProfitabilityReportScreen> createState() =>
      _ProfitabilityReportScreenState();
}

class _ProfitabilityReportScreenState extends State<ProfitabilityReportScreen> {
  final _svc = ComandoService();
  Map<String, dynamic>? _data;
  int _dias = 30;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final data = await _svc.rentabilidad(dias: _dias);
    if (!mounted) return;
    setState(() => _data = data);
  }

  @override
  Widget build(BuildContext context) {
    final pres = ((_data?['por_presentacion'] as List?) ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    final cats = ((_data?['por_categoria'] as List?) ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    final top = ((_data?['top_productos'] as List?) ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    return Scaffold(
      backgroundColor: Zx.bg(context),
      appBar: AppBar(title: const Text('Utilidad por presentación')),
      body: _data == null
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  Wrap(
                    spacing: 8,
                    children: [
                      for (final d in [7, 30, 90])
                        ChoiceChip(
                          label: Text('$d días'),
                          selected: _dias == d,
                          selectedColor: Zyntra.accent,
                          onSelected: (_) {
                            setState(() => _dias = d);
                            _load();
                          },
                        ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Caja vs. blíster vs. unidad',
                    style: TextStyle(
                      color: Zx.text(context),
                      fontSize: 18,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 12),
                  SizedBox(
                    height: 220,
                    child: pres.isEmpty
                        ? Center(
                            child: Text(
                              'Sin datos de presentación en este periodo',
                              style: TextStyle(color: Zx.muted(context)),
                            ),
                          )
                        : BarChart(
                            BarChartData(
                              maxY: _max(pres, 'utilidad') * 1.2,
                              barGroups: [
                                for (var i = 0; i < pres.length; i++)
                                  BarChartGroupData(
                                    x: i,
                                    barRods: [
                                      BarChartRodData(
                                        toY: (pres[i]['utilidad'] as num)
                                            .toDouble(),
                                        width: 18,
                                        color: _color(i),
                                        borderRadius: BorderRadius.circular(6),
                                      ),
                                    ],
                                  ),
                              ],
                              titlesData: FlTitlesData(
                                leftTitles: const AxisTitles(
                                  sideTitles: SideTitles(showTitles: false),
                                ),
                                rightTitles: const AxisTitles(
                                  sideTitles: SideTitles(showTitles: false),
                                ),
                                topTitles: const AxisTitles(
                                  sideTitles: SideTitles(showTitles: false),
                                ),
                                bottomTitles: AxisTitles(
                                  sideTitles: SideTitles(
                                    showTitles: true,
                                    getTitlesWidget: (v, _) {
                                      final i = v.toInt();
                                      if (i < 0 || i >= pres.length) {
                                        return const SizedBox.shrink();
                                      }
                                      return Padding(
                                        padding: const EdgeInsets.only(top: 6),
                                        child: Text(
                                          '${pres[i]['presentacion']}',
                                          style: TextStyle(
                                            color: Zx.muted(context),
                                            fontSize: 11,
                                          ),
                                        ),
                                      );
                                    },
                                  ),
                                ),
                              ),
                              gridData: const FlGridData(show: false),
                              borderData: FlBorderData(show: false),
                            ),
                          ),
                  ),
                  const SizedBox(height: 8),
                  for (final p in pres)
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(
                        '${p['presentacion']}',
                        style: TextStyle(color: Zx.text(context)),
                      ),
                      subtitle: Text(
                        'Venta ${cop.format(p['venta'] ?? 0)}',
                        style: TextStyle(color: Zx.muted(context)),
                      ),
                      trailing: Text(
                        cop.format(p['utilidad'] ?? 0),
                        style: const TextStyle(
                          color: Zyntra.success,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  const SizedBox(height: 12),
                  Text(
                    'Utilidad por categoría',
                    style: TextStyle(
                      color: Zx.text(context),
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  for (final c in cats)
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(
                        '${c['categoria']}',
                        style: TextStyle(color: Zx.text(context)),
                      ),
                      trailing: Text(
                        cop.format(c['utilidad'] ?? 0),
                        style: TextStyle(color: Zx.text(context)),
                      ),
                    ),
                  const SizedBox(height: 12),
                  Text(
                    'Top productos por utilidad',
                    style: TextStyle(
                      color: Zx.text(context),
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  for (final t in top)
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(
                        '${t['producto']}',
                        style: TextStyle(color: Zx.text(context)),
                      ),
                      subtitle: Text(
                        '${t['presentacion']}',
                        style: TextStyle(color: Zx.muted(context)),
                      ),
                      trailing: Text(
                        cop.format(t['utilidad'] ?? 0),
                        style: const TextStyle(
                          color: Zyntra.cyan,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                ],
              ),
            ),
    );
  }

  double _max(List<Map<String, dynamic>> rows, String key) {
    var m = 1.0;
    for (final r in rows) {
      final v = (r[key] as num?)?.toDouble() ?? 0;
      if (v > m) m = v;
    }
    return m;
  }

  Color _color(int i) {
    const colors = [
      Zyntra.accent,
      Zyntra.cyan,
      Zyntra.purple,
      Zyntra.success,
      Zyntra.warning,
    ];
    return colors[i % colors.length];
  }
}
