import 'package:flutter_application_1/ventas_model.dart';

// Lista global para almacenar las transacciones financieras
List<Map<String, dynamic>> transaccionesFinancieras = [];

// Método para agregar una venta como entrada
void agregarVentaComoEntrada(Venta venta) {
  transaccionesFinancieras.add({
    'tipo': 'Entrada',
    'descripcion':
        'Venta #${venta.id ?? "0"} realizada por ${venta.nombreEmpleado ?? "Desconocido"}',
    'monto': venta.total ?? 0,
    'esEntrada': true,
  });
}
