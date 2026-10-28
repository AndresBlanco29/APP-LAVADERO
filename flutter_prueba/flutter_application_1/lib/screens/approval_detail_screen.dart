import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_application_1/services/comando_service.dart';
import 'package:flutter_application_1/theme/zyntra_theme.dart';

class ApprovalDetailScreen extends StatefulWidget {
  final Map<String, dynamic> solicitud;
  final bool asModal;

  const ApprovalDetailScreen({
    super.key,
    required this.solicitud,
    this.asModal = false,
  });

  static Future<bool?> show(BuildContext context, Map<String, dynamic> sol) {
    return showGeneralDialog<bool>(
      context: context,
      barrierDismissible: false,
      barrierColor: Colors.black.withOpacity(0.72),
      pageBuilder: (_, __, ___) => ApprovalDetailScreen(
        solicitud: sol,
        asModal: true,
      ),
    );
  }

  @override
  State<ApprovalDetailScreen> createState() => _ApprovalDetailScreenState();
}

class _ApprovalDetailScreenState extends State<ApprovalDetailScreen> {
  final _nota = TextEditingController();
  final _pin = TextEditingController();
  final _svc = ComandoService();
  bool _busy = false;

  Future<void> _playAlert() async {
    try {
      HapticFeedback.heavyImpact();
      await AudioPlayer().play(AssetSource('sounds/notificacion.wav'));
    } catch (_) {
      try {
        await AudioPlayer().play(AssetSource('sounds/notificacion.mp3'));
      } catch (_) {}
    }
  }

  @override
  void initState() {
    super.initState();
    _playAlert();
  }

  @override
  void dispose() {
    _nota.dispose();
    _pin.dispose();
    super.dispose();
  }

  Future<void> _responder(String estado) async {
    if (estado == 'RECHAZADO' && _nota.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Indica un motivo para rechazar')),
      );
      return;
    }
    final pinGuardado = await _svc.approvalPin();
    if (pinGuardado.isNotEmpty && _pin.text.trim() != pinGuardado) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('PIN de seguridad incorrecto')),
      );
      return;
    }
    setState(() => _busy = true);
    try {
      await _svc.responder(
        id: int.parse('${widget.solicitud['id']}'),
        estado: estado,
        nota: _nota.text.trim(),
      );
      if (estado == 'APROBADO') {
        HapticFeedback.mediumImpact();
      } else {
        HapticFeedback.vibrate();
      }
      if (!mounted) return;
      if (widget.asModal) {
        Navigator.pop(context, true);
      } else {
        Navigator.pop(context, true);
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => _busy = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('No se pudo resolver: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.solicitud;
    final items = (s['items'] as List?) ?? const [];
    final body = SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            Container(
              width: 44,
              height: 4,
              decoration: BoxDecoration(
                color: Zyntra.warning,
                borderRadius: BorderRadius.circular(4),
              ),
            ).animate(onPlay: (c) => c.repeat(reverse: true)).fade(duration: 700.ms),
            const SizedBox(height: 16),
            Text(
              s['parcial'] == true ? 'Devolución parcial' : 'Devolución pendiente',
              style: TextStyle(
                color: Zx.text(context),
                fontSize: 22,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              'Ticket #${s['venta_id']} · ${s['cajero'] ?? 'Cajero'}',
              style: TextStyle(color: Zx.muted(context)),
            ),
            const SizedBox(height: 16),
            Expanded(
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Zx.card(context),
                  borderRadius: BorderRadius.circular(18),
                  border: Border.all(color: Zyntra.warning.withOpacity(0.35)),
                ),
                child: ListView(
                  children: [
                    _kv(context, 'Cliente', '${s['cliente'] ?? 'Mostrador'}'),
                    _kv(context, 'Hora', '${s['fecha'] ?? ''}'),
                    _kv(context, 'Motivo', '${s['motivo'] ?? 'Sin motivo'}'),
                    _kv(context, 'Monto', cop.format(s['total'] ?? 0)),
                    const Divider(height: 28),
                    Text(
                      'Ítems a reingresar',
                      style: TextStyle(
                        color: Zx.text(context),
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 8),
                    for (final raw in items)
                      _item(context, Map<String, dynamic>.from(raw as Map)),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _nota,
                      maxLines: 2,
                      decoration: const InputDecoration(
                        hintText: 'Nota o motivo (requerido al rechazar)',
                      ),
                    ),
                    const SizedBox(height: 10),
                    TextField(
                      controller: _pin,
                      obscureText: true,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        hintText: 'PIN de seguridad',
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: _busy ? null : () => _responder('RECHAZADO'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Zyntra.danger,
                      side: const BorderSide(color: Zyntra.danger),
                      padding: const EdgeInsets.symmetric(vertical: 14),
                    ),
                    child: const Text('Rechazar'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton(
                    onPressed: _busy ? null : () => _responder('APROBADO'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Zyntra.success,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                    ),
                    child: _busy
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.white,
                            ),
                          )
                        : const Text('Aprobar devolución'),
                  ),
                ),
              ],
            ),
            if (widget.asModal)
              TextButton(
                onPressed: _busy ? null : () => Navigator.pop(context, false),
                child: const Text('Resolver después'),
              ),
          ],
        ),
      ),
    );
    return widget.asModal
        ? Material(color: Zx.bg(context), child: body)
        : Scaffold(backgroundColor: Zx.bg(context), body: body);
  }

  Widget _kv(BuildContext context, String k, String v) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 88,
            child: Text(k, style: TextStyle(color: Zx.muted(context))),
          ),
          Expanded(
            child: Text(
              v,
              style: TextStyle(
                color: Zx.text(context),
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _item(BuildContext context, Map<String, dynamic> it) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${it['producto']}',
                  style: TextStyle(color: Zx.text(context)),
                ),
                Text(
                  '${it['presentacion']} · ${it['cantidad']}  (base ${it['cantidad_base']})',
                  style: TextStyle(color: Zx.muted(context), fontSize: 12),
                ),
              ],
            ),
          ),
          Text(
            cop.format(it['subtotal'] ?? 0),
            style: const TextStyle(
              color: Zyntra.cyan,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}
