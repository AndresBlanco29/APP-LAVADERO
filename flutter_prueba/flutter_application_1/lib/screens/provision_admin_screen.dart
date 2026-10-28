import 'package:flutter/material.dart';
import 'package:flutter_application_1/screens/bolsillos_hub_screen.dart';
import 'package:flutter_application_1/services/comando_service.dart';
import 'package:flutter_application_1/theme/zyntra_theme.dart';

class ProvisionAdminScreen extends StatefulWidget {
  const ProvisionAdminScreen({super.key});

  @override
  State<ProvisionAdminScreen> createState() => _ProvisionAdminScreenState();
}

class _ProvisionAdminScreenState extends State<ProvisionAdminScreen> {
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
      final data = await _svc.provisionAdminResumen();
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

  @override
  Widget build(BuildContext context) {
    final hist = ((_data?['historial'] as List?) ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    final saldo = (_data?['saldo_pendiente'] as num?)?.toDouble() ?? 0;

    return Scaffold(
      backgroundColor: Zx.bg(context),
      appBar: AppBar(
        title: const Text('Provisión administrativa'),
        actions: [
          IconButton(
            tooltip: 'Obligaciones',
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const BolsillosHubScreen(initialTab: 1)),
              );
            },
            icon: const Icon(Icons.assignment_outlined),
          ),
          IconButton(onPressed: _busy ? null : _load, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: _busy && _data == null
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
                children: [
                  if (_error != null)
                    Text(_error!, style: const TextStyle(color: Colors.redAccent)),
                  Text(
                    '30% de ventas generales · financiada solo con efectivo',
                    style: TextStyle(color: Zx.muted(context)),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Redondeo: siempre hacia arriba a \$10.000',
                    style: TextStyle(color: Zx.muted(context), fontSize: 12),
                  ),
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: Zx.card(context),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: saldo == 0 ? Zyntra.success : Zyntra.warning,
                      ),
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: Text(
                            'Saldo pendiente acumulado',
                            style: TextStyle(color: Zx.text(context), fontWeight: FontWeight.w700),
                          ),
                        ),
                        Text(
                          cop.format(saldo),
                          style: TextStyle(
                            color: saldo == 0 ? Zyntra.success : Zyntra.warning,
                            fontWeight: FontWeight.w800,
                            fontSize: 18,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Historial',
                    style: TextStyle(color: Zx.text(context), fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 8),
                  if (hist.isEmpty)
                    Text('Sin provisiones registradas', style: TextStyle(color: Zx.muted(context))),
                  for (final p in hist)
                    Card(
                      color: Zx.elevated(context),
                      child: ExpansionTile(
                        title: Text(
                          'CG #${p['cierre_general_id']} · ${p['estado']}',
                          style: TextStyle(color: Zx.text(context), fontSize: 14),
                        ),
                        subtitle: Text(
                          'Prov ${cop.format(p['efectivo_provisionado'] ?? 0)} · Pend ${cop.format(p['nuevo_saldo_pendiente'] ?? 0)}',
                          style: TextStyle(color: Zx.muted(context), fontSize: 12),
                        ),
                        children: [
                          _kv('Ventas generales', cop.format(p['ventas_generales'] ?? 0)),
                          _kv('30%', cop.format(p['treinta_porciento'] ?? 0)),
                          _kv('Redondeo (obj. día)', cop.format(p['provision_objetivo'] ?? 0)),
                          _kv('Saldo pendiente ant.', cop.format(p['saldo_pendiente_anterior'] ?? 0)),
                          _kv('Objetivo total', cop.format(p['objetivo_total'] ?? 0)),
                          _kv('Efectivo disponible', cop.format(p['efectivo_disponible'] ?? 0)),
                          _kv('Efectivo provisionado', cop.format(p['efectivo_provisionado'] ?? 0)),
                          _kv('Nuevo saldo pendiente', cop.format(p['nuevo_saldo_pendiente'] ?? 0)),
                          const SizedBox(height: 8),
                        ],
                      ),
                    ),
                ],
              ),
            ),
    );
  }

  Widget _kv(String k, String v) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 3),
      child: Row(
        children: [
          Expanded(child: Text(k, style: TextStyle(color: Zx.muted(context), fontSize: 13))),
          Text(v, style: TextStyle(color: Zx.text(context), fontSize: 13)),
        ],
      ),
    );
  }
}
