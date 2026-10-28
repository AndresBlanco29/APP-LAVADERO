import 'package:flutter/material.dart';
import 'package:flutter_application_1/screens/approval_detail_screen.dart';
import 'package:flutter_application_1/services/comando_service.dart';
import 'package:flutter_application_1/theme/zyntra_theme.dart';

class PendientesListScreen extends StatefulWidget {
  const PendientesListScreen({super.key});

  @override
  State<PendientesListScreen> createState() => _PendientesListScreenState();
}

class _PendientesListScreenState extends State<PendientesListScreen> {
  final _svc = ComandoService();
  List<Map<String, dynamic>> _items = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final data = await _svc.pendientes();
    if (!mounted) return;
    setState(() {
      _items = data;
      _loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Zx.bg(context),
      appBar: AppBar(title: const Text('Devoluciones pendientes')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: _items.isEmpty
                  ? ListView(
                      children: [
                        const SizedBox(height: 80),
                        Icon(Icons.check_circle_outline, color: Zx.muted(context), size: 48),
                        const SizedBox(height: 12),
                        Text(
                          'No hay devoluciones esperando',
                          textAlign: TextAlign.center,
                          style: TextStyle(color: Zx.muted(context)),
                        ),
                      ],
                    )
                  : ListView.separated(
                      padding: const EdgeInsets.all(16),
                      itemCount: _items.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 10),
                      itemBuilder: (_, i) {
                        final s = _items[i];
                        return ListTile(
                          onTap: () async {
                            await Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (_) => ApprovalDetailScreen(solicitud: s),
                              ),
                            );
                            await _load();
                          },
                          tileColor: Zx.card(context),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(14),
                          ),
                          title: Text(
                            '${s['parcial'] == true ? 'Parcial · ' : ''}Ticket #${s['venta_id']} · ${s['cajero'] ?? 'Caja'}',
                            style: TextStyle(
                              color: Zx.text(context),
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          subtitle: Text(
                            '${s['cliente'] ?? 'Mostrador'} · ${s['motivo'] ?? ''}',
                            style: TextStyle(color: Zx.muted(context)),
                          ),
                          trailing: Text(
                            cop.format(s['total'] ?? 0),
                            style: const TextStyle(
                              color: Zyntra.warning,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        );
                      },
                    ),
            ),
    );
  }
}
