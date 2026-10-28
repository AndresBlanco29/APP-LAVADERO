import 'package:flutter/material.dart';
import 'package:flutter_application_1/modelos/producto_vendido.dart';
import 'package:flutter_application_1/theme/zyntra_theme.dart';
import 'package:intl/intl.dart';

class DetallesVentas extends StatelessWidget {
  final String numeroVenta;
  final String fecha;
  final String Empleado;
  final List<ProductoVendido> productos;
  final double total;
  final bool anulada;
  final double ganancia;
  final bool lavadero;
  final String placa;
  final String cliente;
  final String telefono;
  final String sucursal;
  final String zona;
  final String vehiculo;
  final String cobradoPor;
  final String nota;
  final double comisiones;
  final List<Map<String, dynamic>> muchachos;
  final List<Map<String, dynamic>> pagos;

  const DetallesVentas({
    super.key,
    required this.numeroVenta,
    required this.fecha,
    required this.Empleado,
    required this.productos,
    required this.total,
    this.anulada = false,
    this.ganancia = 0,
    this.lavadero = false,
    this.placa = '',
    this.cliente = '',
    this.telefono = '',
    this.sucursal = '',
    this.zona = '',
    this.vehiculo = '',
    this.cobradoPor = '',
    this.nota = '',
    this.comisiones = 0,
    this.muchachos = const [],
    this.pagos = const [],
  });

  Widget _dato(String titulo, String valor) {
    if (valor.trim().isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 110,
            child: Text(
              titulo,
              style: const TextStyle(color: Zyntra.muted, fontSize: 15),
            ),
          ),
          Expanded(
            child: Text(
              valor,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 16,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _plata(num valor) => '\$${NumberFormat('#,###', 'es_ES').format(valor)}';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Zyntra.bg,
      appBar: AppBar(
        backgroundColor: Zyntra.header,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.white),
          onPressed: () => Navigator.pop(context),
        ),
        title: const Text(
          'Detalles de venta',
          style: TextStyle(
            color: Colors.white,
            fontWeight: FontWeight.bold,
            fontSize: 22,
          ),
        ),
      ),
      body: Column(
        children: [
          if (anulada)
            Container(
              width: double.infinity,
              color: Zyntra.danger,
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: const Text(
                'VENTA ANULADA  ·  no suma en reportes ni dashboard',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: anulada ? Zyntra.anuladaBg : Zyntra.card,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: anulada ? Zyntra.danger.withOpacity(0.5) : Zyntra.border,
                ),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Venta #$numeroVenta',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                            fontSize: 20,
                            decoration: anulada
                                ? TextDecoration.lineThrough
                                : TextDecoration.none,
                          ),
                        ),
                        Text(
                          DateFormat("EEEE d 'de' MMMM 'de' y", 'es_ES').format(
                            DateFormat("dd/MM/yyyy, h:mm a").parse(fecha),
                          ),
                          style: const TextStyle(
                            color: Zyntra.muted,
                            fontSize: 15,
                          ),
                        ),
                        Text(
                          lavadero && placa.isNotEmpty ? placa : Empleado,
                          style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            color: Zyntra.muted,
                            fontSize: 16,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Text(
                    '\$${NumberFormat('#,###', 'es_ES').format(total)}',
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: anulada ? Zyntra.anuladaFg : Colors.white,
                      decoration: anulada
                          ? TextDecoration.lineThrough
                          : TextDecoration.none,
                    ),
                  ),
                ],
              ),
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (lavadero) ...[
                      _dato('Placa', placa),
                      _dato('Vehículo', vehiculo),
                      _dato('Cliente', cliente),
                      _dato('Teléfono', telefono),
                      _dato('Sucursal', sucursal),
                      _dato('Zona', zona),
                      _dato('Cobró', cobradoPor),
                      _dato(
                        'Pago',
                        pagos
                            .map((p) => '${p['medio'] ?? ''} ${_plata((p['monto'] as num?) ?? 0)}')
                            .where((t) => t.trim().isNotEmpty)
                            .join('\n'),
                      ),
                      _dato('Nota', nota),
                      if (muchachos.isNotEmpty) ...[
                        const Text(
                          'Muchachos',
                          style: TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                            fontSize: 18,
                          ),
                        ),
                        const SizedBox(height: 8),
                        ...muchachos.map(
                          (persona) => _dato(
                            '${persona['nombre'] ?? ''}',
                            _plata((persona['monto'] as num?) ?? 0),
                          ),
                        ),
                      ],
                      const SizedBox(height: 8),
                    ],
                    Text(
                      lavadero ? 'Lo vendido' : 'Productos vendidos',
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                        fontSize: 18,
                      ),
                    ),
                    const SizedBox(height: 10),
                    ...productos.map((p) => productoItem(p)),
                    const SizedBox(height: 20),
                    const Divider(color: Zyntra.border),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'Total',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        Text(
                          anulada
                              ? '\$0'
                              : '\$${NumberFormat('#,###', 'es_ES').format(total)}',
                          style: TextStyle(
                            color: anulada ? Zyntra.danger : Zyntra.warning,
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                    if (!anulada && lavadero && comisiones > 0) ...[
                      const SizedBox(height: 8),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text(
                            'Muchachos',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          Text(
                            _plata(comisiones),
                            style: const TextStyle(
                              color: Color(0xFFF97316),
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                    ],
                    if (!anulada && (lavadero || ganancia > 0)) ...[
                      const SizedBox(height: 8),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text(
                            'Ganancia',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          Text(
                            '\$${NumberFormat('#,###', 'es_ES').format(ganancia)}',
                            style: const TextStyle(
                              color: Zyntra.success,
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                    ],
                    const SizedBox(height: 24),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget productoItem(ProductoVendido p) {
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 4),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: Zyntra.elevated,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            child: Text(p.nombre, style: const TextStyle(color: Colors.white)),
          ),
          Text(
            '${p.cantidad}x \$${NumberFormat('#,###', 'es_ES').format(p.precio)}',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 15,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}
