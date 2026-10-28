import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_application_1/services/comando_service.dart';
import 'package:flutter_application_1/theme/zyntra_theme.dart';
import 'package:intl/intl.dart';

final _cop = NumberFormat.currency(locale: 'es_CO', symbol: '\$', decimalDigits: 0);

class BolsilloProveedoresScreen extends StatefulWidget {
  const BolsilloProveedoresScreen({super.key, this.embedded = false});

  /// Cuando está dentro del módulo unificado de bolsillos (sin AppBar propio).
  final bool embedded;

  @override
  State<BolsilloProveedoresScreen> createState() => _BolsilloProveedoresScreenState();
}

class _BolsilloProveedoresScreenState extends State<BolsilloProveedoresScreen> {
  final _svc = ComandoService();
  Map<String, dynamic>? _data;
  String? _error;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final data = await _svc.bolsilloProveedoresResumen();
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

  @override
  Widget build(BuildContext context) {
    final movs = ((_data?['movimientos'] as List?) ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    final integridad = _data?['integridad_ok'] == true;

    final body = _busy && _data == null
        ? const Center(child: CircularProgressIndicator())
        : RefreshIndicator(
            onRefresh: _load,
            child: ListView(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 88),
              children: [
                if (_error != null)
                  Text(_error!, style: const TextStyle(color: Colors.redAccent)),
                  Text(
                    'Disponible = efectivo sobrante (post-provisión) + billetera digital. '
                    'Datafono → billetera el siguiente día hábil a las 14:00.',
                    style: TextStyle(color: Zx.muted(context)),
                  ),
                  const SizedBox(height: 12),
                  _saldoCard(context, integridad),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      OutlinedButton.icon(
                        onPressed: _obligacion,
                        icon: const Icon(Icons.receipt_long_outlined),
                        label: const Text('Obligación'),
                      ),
                      OutlinedButton.icon(
                        onPressed: _reclasificar,
                        icon: const Icon(Icons.swap_horiz),
                        label: const Text('Corregir medio'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Movimientos',
                    style: TextStyle(
                      color: Zx.text(context),
                      fontWeight: FontWeight.w700,
                      fontSize: 16,
                    ),
                  ),
                  const SizedBox(height: 8),
                  if (movs.isEmpty)
                    Text('Sin movimientos', style: TextStyle(color: Zx.muted(context))),
                  for (final m in movs) _movTile(context, m),
                ],
              ),
            );

    final fab = FloatingActionButton.extended(
      onPressed: _pago,
      icon: const Icon(Icons.payments_outlined),
      label: const Text('Pagar'),
    );

    if (widget.embedded) {
      return Scaffold(
        backgroundColor: Zx.bg(context),
        floatingActionButton: fab,
        body: body,
      );
    }

    return Scaffold(
      backgroundColor: Zx.bg(context),
      appBar: AppBar(
        title: const Text('Bolsillo proveedores'),
        actions: [
          IconButton(onPressed: _busy ? null : _load, icon: const Icon(Icons.refresh)),
        ],
      ),
      floatingActionButton: fab,
      body: body,
    );
  }

  Widget _saldoCard(BuildContext context, bool integridad) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Zx.card(context),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _row('Efectivo', _saldos['efectivo']),
          _row('Billetera digital', _saldos['nequi'] ?? _saldos['billetera_digital']),
          _row('Datafono pendiente', _saldos['datafono_pendiente']),
          const Divider(height: 20),
          _row(
            'Disponible',
            _saldos['disponible'] ??
                (((_saldos['efectivo'] as num?)?.toDouble() ?? 0) +
                    ((_saldos['nequi'] as num?)?.toDouble() ?? 0)),
            bold: true,
          ),
          _row('Total (disp. + pendiente)', _saldos['total']),
          const SizedBox(height: 6),
          Text(
            integridad
                ? 'Integridad OK · pagos permiten negativo + crédito por faltante'
                : 'ALERTA de integridad de saldos',
            style: TextStyle(
              color: integridad ? Colors.greenAccent.shade200 : Colors.redAccent,
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
  }

  Widget _row(String label, dynamic value, {bool bold = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: TextStyle(
                color: Zx.muted(context),
                fontWeight: bold ? FontWeight.w700 : FontWeight.w400,
              ),
            ),
          ),
          Text(
            _cop.format((value as num?)?.toDouble() ?? 0),
            style: TextStyle(
              color: Zx.text(context),
              fontWeight: bold ? FontWeight.w800 : FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _movTile(BuildContext context, Map<String, dynamic> m) {
    final tipo = '${m['tipo'] ?? ''}';
    final isOblig = tipo == 'OBLIGACION';
    return ListTile(
      contentPadding: EdgeInsets.zero,
      title: Text(
        '$tipo · ${m['metodo'] ?? ''}',
        style: TextStyle(color: Zx.text(context), fontWeight: FontWeight.w600),
      ),
      subtitle: Text(
        '${m['proveedor_nombre'] ?? ''} ${m['referencia'] ?? ''}\n'
        '${m['fecha'] ?? ''} · ${m['usuario'] ?? ''}'
        '${isOblig ? ' · DEUDA (no es dinero)' : ''}',
        style: TextStyle(color: Zx.muted(context), fontSize: 12),
      ),
      isThreeLine: true,
      trailing: Text(
        _cop.format((m['monto'] as num?)?.toDouble() ?? 0),
        style: TextStyle(
          color: isOblig ? Colors.orangeAccent : Zx.text(context),
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }

  Future<void> _pago() async {
    final prov = TextEditingController();
    final total = TextEditingController();
    final ref = TextEditingController();
    final obs = TextEditingController();
    final ef = TextEditingController(text: '0');
    final nq = TextEditingController(text: '0');
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
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Pago / compra a proveedor',
                  style: TextStyle(color: Zx.text(context), fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                Text(
                  'Disp. Ef ${_cop.format((_saldos['efectivo'] as num?)?.toDouble() ?? 0)} · '
                  'Billetera ${_cop.format((_saldos['nequi'] as num?)?.toDouble() ?? 0)} · '
                  'Pend. datafono ${_cop.format((_saldos['datafono_pendiente'] as num?)?.toDouble() ?? 0)}',
                  style: TextStyle(color: Zx.muted(context), fontSize: 12),
                ),
                Text(
                  'Efectivo y billetera separados. Faltante = crédito automático (no bloquea).',
                  style: TextStyle(color: Colors.orangeAccent.shade100, fontSize: 11),
                ),
                const SizedBox(height: 12),
                TextField(controller: prov, decoration: const InputDecoration(hintText: 'Proveedor')),
                TextField(
                  controller: total,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(hintText: 'Valor total compra'),
                ),
                TextField(
                  controller: ef,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(hintText: 'Efectivo pagado'),
                ),
                TextField(
                  controller: nq,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(hintText: 'Billetera digital pagada'),
                ),
                TextField(controller: ref, decoration: const InputDecoration(hintText: 'Referencia')),
                TextField(controller: obs, decoration: const InputDecoration(hintText: 'Observación')),
                const SizedBox(height: 12),
                ElevatedButton(
                  onPressed: () => Navigator.pop(ctx, true),
                  child: const Text('Registrar'),
                ),
              ],
            ),
          ),
        );
      },
    );
    if (ok != true) return;
    double p(String t) => double.tryParse(t.replaceAll(',', '.')) ?? 0;
    final origenes = <Map<String, dynamic>>[];
    if (p(ef.text) > 0) origenes.add({'metodo': 'Efectivo', 'monto': p(ef.text)});
    if (p(nq.text) > 0) origenes.add({'metodo': 'Nequi', 'monto': p(nq.text)});
    HapticFeedback.selectionClick();
    try {
      await _svc.bolsilloProveedoresPago(
        proveedor: prov.text.trim(),
        total: p(total.text),
        origenes: origenes,
        referencia: ref.text.trim(),
        observacion: obs.text.trim(),
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Compra/pago registrado')));
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  Future<void> _obligacion() async {
    final prov = TextEditingController();
    final total = TextEditingController();
    final obs = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: Zx.card(context),
        title: const Text('Obligación a crédito'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('No aumenta saldos de dinero. Solo registra deuda.'),
            TextField(controller: prov, decoration: const InputDecoration(hintText: 'Proveedor')),
            TextField(
              controller: total,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(hintText: 'Valor'),
            ),
            TextField(controller: obs, decoration: const InputDecoration(hintText: 'Observación')),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          ElevatedButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Registrar')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await _svc.bolsilloProveedoresObligacion(
        proveedor: prov.text.trim(),
        total: double.tryParse(total.text.replaceAll(',', '.')) ?? 0,
        observacion: obs.text.trim(),
      );
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  Future<void> _reclasificar() async {
    var origen = 'Efectivo';
    var destino = 'Billetera digital';
    final monto = TextEditingController();
    final obs = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setLocal) {
            return AlertDialog(
              backgroundColor: Zx.card(context),
              title: const Text('Corregir medio'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  DropdownButtonFormField<String>(
                    value: origen,
                    items: [
                      for (final m in ['Efectivo', 'Billetera digital'])
                        DropdownMenuItem(value: m, child: Text(m)),
                    ],
                    onChanged: (v) => setLocal(() => origen = v ?? origen),
                    decoration: const InputDecoration(hintText: 'Desde'),
                  ),
                  DropdownButtonFormField<String>(
                    value: destino,
                    items: [
                      for (final m in ['Efectivo', 'Billetera digital'])
                        DropdownMenuItem(value: m, child: Text(m)),
                    ],
                    onChanged: (v) => setLocal(() => destino = v ?? destino),
                    decoration: const InputDecoration(hintText: 'Hacia'),
                  ),
                  TextField(
                    controller: monto,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(hintText: 'Monto'),
                  ),
                  TextField(controller: obs, decoration: const InputDecoration(hintText: 'Motivo')),
                ],
              ),
              actions: [
                TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
                ElevatedButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Aplicar')),
              ],
            );
          },
        );
      },
    );
    if (ok != true) return;
    try {
      await _svc.bolsilloProveedoresReclasificar(
        metodoOrigen: origen,
        metodoDestino: destino,
        monto: double.tryParse(monto.text.replaceAll(',', '.')) ?? 0,
        observacion: obs.text.trim(),
      );
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }
}
