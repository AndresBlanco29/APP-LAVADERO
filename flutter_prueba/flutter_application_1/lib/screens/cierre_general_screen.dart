import 'package:flutter/material.dart';
import 'package:flutter_application_1/services/comando_service.dart';
import 'package:flutter_application_1/theme/zyntra_theme.dart';

const _checklistDefs = [
  ('chk_efectivo', 'Efectivo verificado'),
  ('chk_nequi', 'Nequi verificado'),
  ('chk_datafono', 'Datafono verificado'),
  ('chk_ventas', 'Ventas conciliadas'),
  ('chk_correcciones', 'Correcciones revisadas'),
  ('chk_descuadres', 'Descuadres revisados'),
  ('chk_observaciones', 'Observaciones revisadas'),
  ('chk_validado', 'Cierre validado'),
];

class CierreGeneralScreen extends StatefulWidget {
  const CierreGeneralScreen({super.key});

  @override
  State<CierreGeneralScreen> createState() => _CierreGeneralScreenState();
}

class _CierreGeneralScreenState extends State<CierreGeneralScreen> {
  final _svc = ComandoService();
  List<Map<String, dynamic>> _lista = [];
  Map<String, dynamic>? _detalle;
  bool _busy = false;
  String? _error;

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
      final list = await _svc.cierreGeneralList();
      Map<String, dynamic>? det = _detalle;
      if (det != null && det['id'] != null) {
        det = await _svc.cierreGeneralGet(int.parse('${det['id']}'));
      }
      if (!mounted) return;
      setState(() {
        _lista = list;
        _detalle = (det != null && det.isNotEmpty) ? det : null;
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

  Future<void> _abrir(int id) async {
    setState(() => _busy = true);
    try {
      final det = await _svc.cierreGeneralGet(id);
      if (!mounted) return;
      setState(() {
        _detalle = det.isEmpty ? null : det;
        _busy = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _busy = false);
      _toast('Error: $e', error: true);
    }
  }

  Future<void> _nuevo() async {
    setState(() => _busy = true);
    List<Map<String, dynamic>> diarios = [];
    try {
      diarios = await _svc.cierreGeneralDiarios();
    } catch (e) {
      if (!mounted) return;
      setState(() => _busy = false);
      _toast('No se pudieron cargar diarios: $e', error: true);
      return;
    }
    if (!mounted) return;
    setState(() => _busy = false);
    if (diarios.isEmpty) {
      _toast('No hay cierres diarios disponibles');
      return;
    }
    final selected = <int>{};
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setLocal) {
            return AlertDialog(
              backgroundColor: Zx.card(ctx),
              title: Text('Nuevo cierre general', style: TextStyle(color: Zx.text(ctx))),
              content: SizedBox(
                width: 420,
                height: 360,
                child: ListView.builder(
                  itemCount: diarios.length,
                  itemBuilder: (_, i) {
                    final d = diarios[i];
                    final id = int.tryParse('${d['id']}') ?? 0;
                    return CheckboxListTile(
                      value: selected.contains(id),
                      onChanged: (v) {
                        setLocal(() {
                          if (v == true) {
                            selected.add(id);
                          } else {
                            selected.remove(id);
                          }
                        });
                      },
                      title: Text(
                        '#$id  ${d['fecha']}  ·  ${d['vendedor']}',
                        style: TextStyle(color: Zx.text(ctx), fontSize: 13),
                      ),
                      subtitle: Text(
                        'Ventas ${cop.format(d['ventas'] ?? 0)}  Diff ${cop.format(d['diferencia'] ?? 0)}  ${d['estado']}',
                        style: TextStyle(color: Zx.muted(ctx), fontSize: 12),
                      ),
                    );
                  },
                ),
              ),
              actions: [
                TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
                TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Crear')),
              ],
            );
          },
        );
      },
    );
    if (ok != true || selected.isEmpty) return;
    setState(() => _busy = true);
    try {
      final res = await _svc.cierreGeneralCrear(idsCierres: selected.toList());
      final id = int.tryParse('${res['id']}') ?? 0;
      await _load();
      if (id > 0) await _abrir(id);
      _toast(res['mensaje']?.toString() ?? 'Creado');
    } catch (e) {
      _toast('$e', error: true);
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _checklistDia(Map<String, dynamic> dia) async {
    final gid = int.tryParse('${_detalle?['id']}') ?? 0;
    final tid = int.tryParse('${dia['cierre_turno_id']}') ?? 0;
    if (gid <= 0 || tid <= 0) return;
    final estado = '${_detalle?['estado'] ?? ''}';
    final locked = estado == 'CONSOLIDADO' || estado == 'ANULADO';
    final chk = Map<String, bool>.from(
      (_checklistDefs).fold<Map<String, bool>>({}, (acc, e) {
        acc[e.$1] = (dia['checklist'] as Map?)?[e.$1] == true;
        return acc;
      }),
    );
    final notaCtrl = TextEditingController(text: '${dia['nota_admin'] ?? ''}');
    final det = Map<String, dynamic>.from((dia['detalle'] as Map?) ?? const {});
    final correcciones = ((det['correcciones'] as List?) ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();

    final saved = await showModalBottomSheet<bool>(
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
                bottom: MediaQuery.of(ctx).viewInsets.bottom + 24,
              ),
              child: SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Día #$tid · ${dia['fecha']} · ${dia['vendedor']}',
                      style: TextStyle(color: Zx.text(ctx), fontWeight: FontWeight.w800),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Diff ${cop.format(dia['diferencia'] ?? 0)} · Estado día ${dia['estado_dia']}',
                      style: TextStyle(color: Zx.muted(ctx)),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Obs vendedor: ${dia['observaciones'] ?? det['observaciones'] ?? '-'}',
                      style: TextStyle(color: Zx.muted(ctx), fontSize: 13),
                    ),
                    if (correcciones.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Text('Correcciones', style: TextStyle(color: Zyntra.warning, fontWeight: FontWeight.w700)),
                      for (final c in correcciones.take(6))
                        Text(
                          '#${c['Venta_Id'] ?? c['venta_id']} ${c['Metodo_Anterior'] ?? c['metodo_anterior']}→${c['Metodo_Nuevo'] ?? c['metodo_nuevo']} ${cop.format(c['Monto'] ?? c['monto'] ?? 0)}',
                          style: TextStyle(color: Zx.muted(ctx), fontSize: 12),
                        ),
                    ],
                    const SizedBox(height: 12),
                    Text('Checklist', style: TextStyle(color: Zyntra.cyan, fontWeight: FontWeight.w800)),
                    for (final e in _checklistDefs)
                      CheckboxListTile(
                        dense: true,
                        value: chk[e.$1] ?? false,
                        onChanged: locked
                            ? null
                            : (v) => setLocal(() => chk[e.$1] = v ?? false),
                        title: Text(e.$2, style: TextStyle(color: Zx.text(ctx), fontSize: 13)),
                      ),
                    TextField(
                      controller: notaCtrl,
                      enabled: !locked,
                      decoration: const InputDecoration(labelText: 'Nota admin'),
                    ),
                    const SizedBox(height: 12),
                    if (!locked)
                      ElevatedButton(
                        onPressed: () => Navigator.pop(ctx, true),
                        child: const Text('Guardar checklist'),
                      ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
    if (saved != true || locked) return;
    setState(() => _busy = true);
    try {
      await _svc.cierreGeneralChecklist(
        cierreId: gid,
        cierreTurnoId: tid,
        checklist: chk,
        notaAdmin: notaCtrl.text.trim(),
      );
      await _abrir(gid);
      _toast('Checklist guardado');
    } catch (e) {
      _toast('$e', error: true);
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _consolidar() async {
    final gid = int.tryParse('${_detalle?['id']}') ?? 0;
    if (gid <= 0) return;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: Zx.card(ctx),
        title: Text('Consolidar', style: TextStyle(color: Zx.text(ctx))),
        content: Text(
          '¿Consolidar el cierre general #$gid?\n'
          'Se calculará la provisión administrativa y el ingreso al bolsillo de proveedores '
          '(efectivo sobrante + billetera; Datafono → billetera T+1 hábil 14:00).',
          style: TextStyle(color: Zx.muted(ctx)),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Consolidar')),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _busy = true);
    try {
      final res = await _svc.cierreGeneralConsolidar(gid);
      await _abrir(gid);
      await _load();
      _toast(res['mensaje']?.toString() ?? 'Consolidado');
      final prov = res['provision'];
      if (prov is Map && mounted) {
        await showDialog(
          context: context,
          builder: (ctx) => AlertDialog(
            backgroundColor: Zx.card(ctx),
            title: Text('Provisión aplicada', style: TextStyle(color: Zx.text(ctx))),
            content: SingleChildScrollView(
              child: _provisionCard(Map<String, dynamic>.from(prov)),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cerrar')),
            ],
          ),
        );
      }
      final bp = res['proveedores'];
      if (bp is Map && mounted) {
        await showDialog(
          context: context,
          builder: (ctx) => AlertDialog(
            backgroundColor: Zx.card(ctx),
            title: Text('Bolsillo proveedores', style: TextStyle(color: Zx.text(ctx))),
            content: Text(
              'Efectivo sobrante: ${bp['efectivo']}\n'
              'Nequi: ${bp['nequi']}\n'
              'Datafono: ${bp['datafono']}\n'
              'Total: ${bp['total']}',
              style: TextStyle(color: Zx.text(ctx)),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cerrar')),
            ],
          ),
        );
      }
    } catch (e) {
      _toast('$e', error: true);
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _provisionCard(Map<String, dynamic> p) {
    Widget kv(String k, dynamic v) => Padding(
          padding: const EdgeInsets.only(bottom: 4),
          child: Row(
            children: [
              Expanded(child: Text(k, style: TextStyle(color: Zx.muted(context), fontSize: 12))),
              Text(cop.format(v ?? 0), style: TextStyle(color: Zx.text(context), fontSize: 12)),
            ],
          ),
        );
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Zx.elevated(context),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Zyntra.cyan.withOpacity(0.5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Provisión administrativa', style: TextStyle(color: Zyntra.cyan, fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          kv('Ventas generales', p['ventas_generales']),
          kv('30%', p['treinta_porciento']),
          kv('Redondeo (obj. día)', p['provision_objetivo']),
          kv('Saldo pendiente ant.', p['saldo_pendiente_anterior']),
          kv('Objetivo total', p['objetivo_total']),
          kv('Efectivo disponible', p['efectivo_disponible']),
          kv('Efectivo provisionado', p['efectivo_provisionado']),
          kv('Nuevo saldo pendiente', p['nuevo_saldo_pendiente']),
        ],
      ),
    );
  }

  Future<void> _anular() async {
    final gid = int.tryParse('${_detalle?['id']}') ?? 0;
    if (gid <= 0) return;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: Zx.card(ctx),
        title: Text('Anular', style: TextStyle(color: Zx.text(ctx))),
        content: Text('¿Anular cierre general #$gid?', style: TextStyle(color: Zx.muted(ctx))),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Anular')),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _busy = true);
    try {
      await _svc.cierreGeneralAnular(gid, motivo: 'Anulado desde Flutter');
      await _load();
      await _abrir(gid);
      _toast('Anulado');
    } catch (e) {
      _toast('$e', error: true);
      if (mounted) setState(() => _busy = false);
    }
  }

  void _toast(String msg, {bool error = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg), backgroundColor: error ? Colors.red : null),
    );
  }

  @override
  Widget build(BuildContext context) {
    final dias = ((_detalle?['dias'] as List?) ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    final estado = '${_detalle?['estado'] ?? ''}';
    final canAct = estado.isNotEmpty && estado != 'CONSOLIDADO' && estado != 'ANULADO';

    return Scaffold(
      backgroundColor: Zx.bg(context),
      appBar: AppBar(
        title: const Text('Cierre general'),
        actions: [
          IconButton(onPressed: _busy ? null : _load, icon: const Icon(Icons.refresh)),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _busy ? null : _nuevo,
        icon: const Icon(Icons.add),
        label: const Text('Nuevo'),
      ),
      body: _busy && _lista.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
                children: [
                  if (_error != null)
                    Text(_error!, style: const TextStyle(color: Colors.redAccent)),
                  Text(
                    'Cierres generales',
                    style: TextStyle(color: Zx.text(context), fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 8),
                  if (_lista.isEmpty)
                    Text('Sin registros', style: TextStyle(color: Zx.muted(context))),
                  for (final g in _lista)
                    ListTile(
                      tileColor: Zx.card(context),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                      title: Text(
                        '#${g['id']}  ${g['titulo'] ?? ''}  ·  ${g['estado']}',
                        style: TextStyle(color: Zx.text(context), fontSize: 14),
                      ),
                      subtitle: Text(
                        'Días ${g['dias']} · Ventas ${cop.format(g['total_ventas'] ?? 0)} · Diff ${cop.format(g['total_diferencia'] ?? 0)}',
                        style: TextStyle(color: Zx.muted(context), fontSize: 12),
                      ),
                      onTap: () => _abrir(int.parse('${g['id']}')),
                    ),
                  if (_detalle != null) ...[
                    const SizedBox(height: 16),
                    Text(
                      'Detalle #${_detalle!['id']} · ${_detalle!['estado']}',
                      style: const TextStyle(color: Zyntra.cyan, fontWeight: FontWeight.w800),
                    ),
                    Text(
                      'Ventas ${cop.format(_detalle!['total_ventas'] ?? 0)} · Ef ${cop.format(_detalle!['total_efectivo'] ?? 0)} · Nequi ${cop.format(_detalle!['total_nequi'] ?? 0)} · Data ${cop.format(_detalle!['total_datafono'] ?? 0)} · Diff ${cop.format(_detalle!['total_diferencia'] ?? 0)}',
                      style: TextStyle(color: Zx.muted(context), fontSize: 12),
                    ),
                    if (_detalle!['provision'] is Map) ...[
                      const SizedBox(height: 10),
                      _provisionCard(Map<String, dynamic>.from(_detalle!['provision'] as Map)),
                    ],
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        if (canAct)
                          ElevatedButton(
                            onPressed: _busy ? null : _consolidar,
                            child: const Text('Consolidar'),
                          ),
                        const SizedBox(width: 8),
                        if (canAct)
                          OutlinedButton(
                            onPressed: _busy ? null : _anular,
                            child: const Text('Anular'),
                          ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    for (final d in dias)
                      Builder(
                        builder: (ctx) {
                          final chk = Map<String, dynamic>.from(
                            (d['checklist'] as Map?) ?? const {},
                          );
                          final completo = _checklistDefs.every((e) => chk[e.$1] == true);
                          return Card(
                            color: Zx.elevated(context),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(10),
                              side: BorderSide(
                                color: completo ? Zyntra.success : Colors.transparent,
                                width: completo ? 1.5 : 0,
                              ),
                            ),
                            child: ListTile(
                              leading: completo
                                  ? const Icon(Icons.check_circle, color: Zyntra.success, size: 28)
                                  : Icon(Icons.radio_button_unchecked, color: Zx.muted(context)),
                              title: Text(
                                '#${d['cierre_turno_id']} ${d['fecha']} · ${d['vendedor']} · ${d['estado_dia']}',
                                style: TextStyle(color: Zx.text(context), fontSize: 13),
                              ),
                              subtitle: Text(
                                completo
                                    ? 'REVISADO · Ventas ${cop.format(d['ventas'] ?? 0)} Diff ${cop.format(d['diferencia'] ?? 0)}'
                                    : 'Ventas ${cop.format(d['ventas'] ?? 0)} Diff ${cop.format(d['diferencia'] ?? 0)} Corr ${d['correcciones'] ?? 0}',
                                style: TextStyle(
                                  color: completo ? Zyntra.success : Zx.muted(context),
                                  fontSize: 12,
                                ),
                              ),
                              trailing: Icon(
                                completo ? Icons.verified : Icons.checklist,
                                color: completo ? Zyntra.success : null,
                              ),
                              onTap: () => _checklistDia(d),
                            ),
                          );
                        },
                      ),
                  ],
                ],
              ),
            ),
    );
  }
}
