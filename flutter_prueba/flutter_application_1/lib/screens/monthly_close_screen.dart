import 'package:flutter/material.dart';
import 'package:flutter_application_1/services/comando_service.dart';
import 'package:flutter_application_1/theme/zyntra_theme.dart';

class MonthlyCloseScreen extends StatefulWidget {
  const MonthlyCloseScreen({super.key});

  @override
  State<MonthlyCloseScreen> createState() => _MonthlyCloseScreenState();
}

class _MonthlyCloseScreenState extends State<MonthlyCloseScreen> {
  final _svc = ComandoService();
  late int _mes;
  late int _anio;
  Map<String, dynamic>? _data;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    final now = DateTime.now();
    _mes = now.month;
    _anio = now.year;
    _load();
  }

  Future<void> _load() async {
    setState(() => _data = null);
    final data = await _svc.cierreMensual(mes: _mes, anio: _anio);
    if (!mounted) return;
    setState(() => _data = data);
  }

  Map<String, dynamic> get _pl =>
      Map<String, dynamic>.from((_data?['pl'] as Map?) ?? const {});
  Map<String, dynamic> get _bol =>
      Map<String, dynamic>.from((_data?['bolsillos'] as Map?) ?? const {});

  @override
  Widget build(BuildContext context) {
    final dias = ((_data?['dias'] as List?) ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    return Scaffold(
      backgroundColor: Zx.bg(context),
      appBar: AppBar(
        title: const Text('Cierre mensual'),
        actions: [
          IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: _data == null
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
                children: [
                  Row(
                    children: [
                      DropdownButton<int>(
                        value: _mes,
                        dropdownColor: Zx.card(context),
                        items: [
                          for (var m = 1; m <= 12; m++)
                            DropdownMenuItem(value: m, child: Text('$m')),
                        ],
                        onChanged: (v) {
                          if (v == null) return;
                          setState(() => _mes = v);
                          _load();
                        },
                      ),
                      const SizedBox(width: 12),
                      DropdownButton<int>(
                        value: _anio,
                        dropdownColor: Zx.card(context),
                        items: [
                          for (var y = DateTime.now().year - 2; y <= DateTime.now().year; y++)
                            DropdownMenuItem(value: y, child: Text('$y')),
                        ],
                        onChanged: (v) {
                          if (v == null) return;
                          setState(() => _anio = v);
                          _load();
                        },
                      ),
                      const Spacer(),
                      if (_data?['cerrado'] == true)
                        const Text('Mes cerrado', style: TextStyle(color: Zyntra.success)),
                    ],
                  ),
                  const SizedBox(height: 12),
                  _plCard(),
                  const SizedBox(height: 12),
                  _pocket('Proveedores', _bol['proveedores']),
                  _pocket('Provisiones', _bol['provisiones']),
                  _pocket('Utilidad', _bol['utilidad']),
                  const SizedBox(height: 8),
                  ElevatedButton(
                    onPressed: _busy ? null : _cerrar,
                    child: Text(_busy ? 'Guardando…' : 'Cerrar y consolidar el mes'),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Desglose día por día',
                    style: TextStyle(
                      color: Zx.text(context),
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 8),
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: DataTable(
                      headingRowColor: MaterialStatePropertyAll(Zx.card(context)),
                      columns: const [
                        DataColumn(label: Text('Día')),
                        DataColumn(label: Text('Venta')),
                        DataColumn(label: Text('Efectivo')),
                        DataColumn(label: Text('Virtual')),
                        DataColumn(label: Text('Proveed.')),
                        DataColumn(label: Text('Provis.')),
                        DataColumn(label: Text('Utilidad')),
                        DataColumn(label: Text('Egresos')),
                      ],
                      rows: [
                        for (final d in dias)
                          if (((d['venta'] as num?) ?? 0) > 0 ||
                              ((d['egresos'] as num?) ?? 0) > 0)
                            DataRow(
                              cells: [
                                DataCell(Text('${d['fecha']}'.substring(8))),
                                DataCell(Text(cop.format(d['venta'] ?? 0))),
                                DataCell(Text(cop.format(d['efectivo'] ?? 0))),
                                DataCell(Text(cop.format(d['virtual'] ?? 0))),
                                DataCell(Text(cop.format(d['entrada_proveedores'] ?? 0))),
                                DataCell(Text(cop.format(d['entrada_provisiones'] ?? 0))),
                                DataCell(Text(cop.format(d['entrada_utilidad'] ?? 0))),
                                DataCell(Text(cop.format(d['egresos'] ?? 0))),
                              ],
                            ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
    );
  }

  Widget _plCard() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Zx.card(context),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Estado de resultados',
            style: TextStyle(color: Zx.text(context), fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 10),
          _line('Venta total del mes', _pl['venta_total']),
          _line('(-) Costo de mercancía (COGS)', _pl['cogs']),
          _line('(=) Utilidad bruta', _pl['utilidad_bruta'], Zyntra.cyan),
          _line('(-) Gastos operativos', _pl['gastos_operativos']),
          _line('(=) Utilidad neta del negocio', _pl['utilidad_neta'], Zyntra.success),
        ],
      ),
    );
  }

  Widget _line(String k, dynamic v, [Color? color]) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        children: [
          Expanded(child: Text(k, style: TextStyle(color: Zx.muted(context)))),
          Text(
            cop.format(v ?? 0),
            style: TextStyle(
              color: color ?? Zx.text(context),
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }

  Widget _pocket(String title, dynamic raw) {
    final m = Map<String, dynamic>.from((raw as Map?) ?? const {});
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Zx.card(context),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(title, style: TextStyle(color: Zx.text(context), fontWeight: FontWeight.w700)),
          ),
          Text(
            'Saldo ${cop.format(m['saldo'] ?? 0)}',
            style: const TextStyle(color: Zyntra.cyan, fontWeight: FontWeight.w800),
          ),
        ],
      ),
    );
  }

  Future<void> _cerrar() async {
    setState(() => _busy = true);
    try {
      await _svc.cerrarMes(mes: _mes, anio: _anio);
      await _load();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Cierre mensual guardado')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('No se pudo cerrar: $e')),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }
}
