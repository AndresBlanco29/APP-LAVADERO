import 'package:flutter/material.dart';
import 'package:flutter_application_1/services/comando_service.dart';
import 'package:flutter_application_1/theme/zyntra_theme.dart';

class FefoAlertsScreen extends StatefulWidget {
  const FefoAlertsScreen({super.key});

  @override
  State<FefoAlertsScreen> createState() => _FefoAlertsScreenState();
}

class _FefoAlertsScreenState extends State<FefoAlertsScreen> {
  final _svc = ComandoService();
  final _lab = TextEditingController();
  Map<String, dynamic>? _data;
  String _filtro = 'todos';

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _lab.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final data = await _svc.fefo(laboratorio: _lab.text.trim());
    if (!mounted) return;
    setState(() => _data = data);
  }

  @override
  Widget build(BuildContext context) {
    final items = ((_data?['items'] as List?) ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .where((e) => _filtro == 'todos' || e['nivel'] == _filtro)
        .toList();
    return Scaffold(
      backgroundColor: Zx.bg(context),
      appBar: AppBar(title: const Text('Control FEFO')),
      body: _data == null
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  TextField(
                    controller: _lab,
                    decoration: InputDecoration(
                      hintText: 'Filtrar laboratorio o proveedor',
                      suffixIcon: IconButton(
                        icon: const Icon(Icons.search),
                        onPressed: _load,
                      ),
                    ),
                    onSubmitted: (_) => _load(),
                  ),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      _badge('Vencidos', _data?['vencidos'] ?? 0, Zyntra.danger, 'vencido'),
                      _badge('< 30 días', _data?['d30'] ?? 0, Zyntra.warning, 'd30'),
                      _badge('< 60 días', _data?['d60'] ?? 0, Zyntra.accent, 'd60'),
                      _badge('< 90 días', _data?['d90'] ?? 0, Zyntra.cyan, 'd90'),
                    ],
                  ),
                  const SizedBox(height: 16),
                  if (items.isEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 40),
                      child: Text(
                        'No hay lotes en este filtro',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Zx.muted(context)),
                      ),
                    ),
                  for (final it in items)
                    Container(
                      margin: const EdgeInsets.only(bottom: 10),
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: Zx.card(context),
                        borderRadius: BorderRadius.circular(14),
                        border: Border(
                          left: BorderSide(color: _nivelColor(it['nivel']), width: 4),
                        ),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '${it['producto']}',
                            style: TextStyle(
                              color: Zx.text(context),
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'Lote ${it['lote'] ?? '-'} · ${it['cantidad']} und. · vence ${it['vence']}',
                            style: TextStyle(color: Zx.muted(context), fontSize: 13),
                          ),
                          Text(
                            '${it['laboratorio'] ?? ''} ${it['proveedor'] ?? ''}'.trim(),
                            style: TextStyle(color: Zx.muted(context), fontSize: 12),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            (it['dias'] as num) < 0
                                ? 'Vencido hace ${(it['dias'] as num).abs()} días'
                                : 'Quedan ${it['dias']} días',
                            style: TextStyle(
                              color: _nivelColor(it['nivel']),
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),
    );
  }

  Widget _badge(String label, dynamic count, Color color, String nivel) {
    final on = _filtro == nivel;
    return GestureDetector(
      onTap: () => setState(() => _filtro = on ? 'todos' : nivel),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: color.withOpacity(on ? 0.28 : 0.12),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color.withOpacity(0.7)),
        ),
        child: Column(
          children: [
            Text(
              '$count',
              style: TextStyle(
                color: color,
                fontSize: 20,
                fontWeight: FontWeight.w800,
              ),
            ),
            Text(label, style: TextStyle(color: Zx.muted(context), fontSize: 11)),
          ],
        ),
      ),
    );
  }

  Color _nivelColor(dynamic nivel) {
    switch ('$nivel') {
      case 'vencido':
        return Zyntra.danger;
      case 'd30':
        return Zyntra.warning;
      case 'd60':
        return Zyntra.accent;
      default:
        return Zyntra.cyan;
    }
  }
}
