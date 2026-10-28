import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_application_1/services/comando_service.dart';
import 'package:flutter_application_1/theme/zyntra_theme.dart';
import 'package:intl/intl.dart';

final _cop = NumberFormat.currency(locale: 'es_CO', symbol: '\$', decimalDigits: 0);

class ProvisionObligacionesScreen extends StatefulWidget {
  const ProvisionObligacionesScreen({super.key, this.embedded = false});

  final bool embedded;

  @override
  State<ProvisionObligacionesScreen> createState() => _ProvisionObligacionesScreenState();
}

class _ProvisionObligacionesScreenState extends State<ProvisionObligacionesScreen>
    with SingleTickerProviderStateMixin {
  final _svc = ComandoService();
  Map<String, dynamic>? _data;
  String? _error;
  bool _busy = false;
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
      final data = await _svc.provisionObligacionesResumen();
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

  Map<String, dynamic> get _saldos =>
      Map<String, dynamic>.from((_data?['saldos'] as Map?) ?? const {});

  List<Map<String, dynamic>> _tipo(String t) {
    final por = Map<String, dynamic>.from((_data?['por_tipo'] as Map?) ?? const {});
    final raw = (por[t] as List?) ?? const [];
    return raw.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  @override
  Widget build(BuildContext context) {
    final content = _busy && _data == null
        ? const Center(child: CircularProgressIndicator())
        : Column(
            children: [
              if (_error != null)
                Padding(
                  padding: const EdgeInsets.all(12),
                  child: Text(_error!, style: const TextStyle(color: Colors.redAccent)),
                ),
              _saldosHeader(context),
              if (widget.embedded)
                TabBar(
                  controller: _tabs,
                  isScrollable: true,
                  tabs: const [
                    Tab(text: 'Empleados'),
                    Tab(text: 'Servicios'),
                    Tab(text: 'Sistema'),
                    Tab(text: 'Arriendo'),
                    Tab(text: 'Otras'),
                  ],
                ),
              Expanded(
                child: TabBarView(
                  controller: _tabs,
                  children: [
                    _empleadosTab(context),
                    _obligacionesTab(context, 'SERVICIOS'),
                    _obligacionesTab(context, 'SISTEMA'),
                    _obligacionesTab(context, 'ARRIENDO'),
                    _obligacionesTab(context, 'OTRAS'),
                  ],
                ),
              ),
            ],
          );

    if (widget.embedded) {
      return Scaffold(
        backgroundColor: Zx.bg(context),
        body: content,
      );
    }

    return Scaffold(
      backgroundColor: Zx.bg(context),
      appBar: AppBar(
        title: const Text('Obligaciones provisión'),
        actions: [
          IconButton(onPressed: _busy ? null : _load, icon: const Icon(Icons.refresh)),
        ],
        bottom: TabBar(
          controller: _tabs,
          isScrollable: true,
          tabs: const [
            Tab(text: 'Empleados'),
            Tab(text: 'Servicios'),
            Tab(text: 'Sistema'),
            Tab(text: 'Arriendo'),
            Tab(text: 'Otras'),
          ],
        ),
      ),
      body: content,
    );
  }

  Widget _saldosHeader(BuildContext context) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.fromLTRB(12, 8, 12, 4),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Zx.card(context),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Provisión administrativa — no crea dinero',
            style: TextStyle(color: Zx.muted(context), fontSize: 12),
          ),
          const SizedBox(height: 6),
          Text('Dinero real: ${_cop.format((_saldos['dinero_real'] as num?)?.toDouble() ?? 0)}',
              style: TextStyle(color: Zx.text(context), fontWeight: FontWeight.w600)),
          Text(
            'Comprometido: ${_cop.format((_saldos['dinero_comprometido'] as num?)?.toDouble() ?? 0)}',
            style: const TextStyle(color: Colors.orangeAccent),
          ),
          Text(
            'Disponible: ${_cop.format((_saldos['disponible'] as num?)?.toDouble() ?? 0)}',
            style: TextStyle(color: Zx.text(context), fontWeight: FontWeight.w800, fontSize: 16),
          ),
        ],
      ),
    );
  }

  Widget _empleadosTab(BuildContext context) {
    final emp = Map<String, dynamic>.from((_data?['empleados'] as Map?) ?? const {});
    final lista = ((emp['empleados'] as List?) ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    final movs = ((_data?['movimientos'] as List?) ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 24),
        children: [
          Text(
            'Reserva diaria (Σ/30): ${_cop.format((emp['reserva_diaria'] as num?)?.toDouble() ?? 0)}',
            style: TextStyle(color: Zx.muted(context)),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: [
              ElevatedButton.icon(
                onPressed: _addEmpleado,
                icon: const Icon(Icons.person_add_alt),
                label: const Text('Salario'),
              ),
              OutlinedButton.icon(
                onPressed: _pagarNomina,
                icon: const Icon(Icons.payments_outlined),
                label: const Text('Pagar nómina'),
              ),
            ],
          ),
          const SizedBox(height: 12),
          for (final e in lista)
            ListTile(
              title: Text('${e['nombre']}', style: TextStyle(color: Zx.text(context))),
              subtitle: Text(
                'Mensual ${_cop.format((e['salario_mensual'] as num?)?.toDouble() ?? 0)} · '
                'Día ${_cop.format((e['reserva_diaria'] as num?)?.toDouble() ?? 0)}',
                style: TextStyle(color: Zx.muted(context)),
              ),
            ),
          const SizedBox(height: 16),
          Text('Historial', style: TextStyle(color: Zx.text(context), fontWeight: FontWeight.w700)),
          for (final m in movs.take(20))
            ListTile(
              dense: true,
              title: Text('${m['tipo']} · ${m['categoria']}', style: TextStyle(color: Zx.text(context))),
              subtitle: Text('${m['fecha']}', style: TextStyle(color: Zx.muted(context), fontSize: 11)),
              trailing: Text(_cop.format((m['monto'] as num?)?.toDouble() ?? 0)),
            ),
        ],
      ),
    );
  }

  Widget _obligacionesTab(BuildContext context, String tipo) {
    final lista = _tipo(tipo);
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 24),
        children: [
          Align(
            alignment: Alignment.centerLeft,
            child: ElevatedButton.icon(
              onPressed: () => _addObligacion(tipo),
              icon: const Icon(Icons.add),
              label: Text('Nueva $tipo'),
            ),
          ),
          const SizedBox(height: 8),
          if (lista.isEmpty)
            Text('Sin obligaciones', style: TextStyle(color: Zx.muted(context))),
          for (final o in lista)
            Card(
              color: Zx.card(context),
              child: ListTile(
                title: Text('${o['nombre']}', style: TextStyle(color: Zx.text(context))),
                subtitle: Text(
                  '${o['estado']} · ${o['fecha_obligacion'] ?? ''}\n${o['descripcion'] ?? ''}',
                  style: TextStyle(color: Zx.muted(context), fontSize: 12),
                ),
                isThreeLine: true,
                trailing: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      _cop.format((o['valor'] as num?)?.toDouble() ?? 0),
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                    if ('${o['estado']}' == 'PENDIENTE')
                      TextButton(
                        onPressed: () => _pagar(int.parse('${o['id']}')),
                        child: const Text('Pagar'),
                      ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Future<void> _addEmpleado() async {
    final nombre = TextEditingController();
    final salario = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: Zx.card(context),
        title: const Text('Salario empleado'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(controller: nombre, decoration: const InputDecoration(hintText: 'Nombre')),
            TextField(
              controller: salario,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(hintText: 'Salario mensual'),
            ),
            const Text('Reserva diaria = salario / 30'),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          ElevatedButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Guardar')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await _svc.provisionObligacionesEmpleado(
        nombre: nombre.text.trim(),
        salarioMensual: double.tryParse(salario.text.replaceAll(',', '.')) ?? 0,
      );
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  Future<void> _addObligacion(String tipo) async {
    final nombre = TextEditingController();
    final valor = TextEditingController();
    final desc = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: Zx.card(context),
        title: Text('Obligación $tipo'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(controller: nombre, decoration: const InputDecoration(hintText: 'Nombre')),
            TextField(
              controller: valor,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(hintText: 'Valor'),
            ),
            TextField(controller: desc, decoration: const InputDecoration(hintText: 'Descripción')),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          ElevatedButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Comprometer')),
        ],
      ),
    );
    if (ok != true) return;
    HapticFeedback.selectionClick();
    try {
      await _svc.provisionObligacionesCrear(
        tipo: tipo,
        nombre: nombre.text.trim(),
        valor: double.tryParse(valor.text.replaceAll(',', '.')) ?? 0,
        descripcion: desc.text.trim(),
      );
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  Future<void> _pagar(int id) async {
    try {
      await _svc.provisionObligacionesPagar(id);
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  Future<void> _pagarNomina() async {
    try {
      await _svc.provisionObligacionesNomina();
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }
}
