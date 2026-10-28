import 'modelos/producto_vendido.dart';

bool ventaEstaAnulada(Map<String, dynamic> json) {
  final raw = json['Anulada'] ?? json['anulada'] ?? json['Estado'] ?? json['estado'];
  if (raw == true || raw == 1) return true;
  if (raw is num && raw.toInt() == 1) return true;
  if (raw is String) {
    final t = raw.trim().toUpperCase();
    return t == '1' || t == 'TRUE' || t.contains('ANUL');
  }
  return false;
}

class Venta {
  final int id;
  final double total;
  final String fecha;
  final String nombreEmpleado;
  final double ganancia;
  final List<ProductoVendido> productosVendidos;
  final bool anulada;
  final bool lavadero;
  final String placa;
  final String cliente;
  final String telefono;
  final String sucursal;
  final String zona;
  final String vehiculo;
  final String hora;
  final String cobradoPor;
  final String nota;
  final double comisiones;
  final List<Map<String, dynamic>> muchachos;
  final List<Map<String, dynamic>> pagos;

  Venta({
    required this.id,
    required this.total,
    required this.fecha,
    required this.nombreEmpleado,
    required this.ganancia,
    required this.productosVendidos,
    this.anulada = false,
    this.lavadero = false,
    this.placa = '',
    this.cliente = '',
    this.telefono = '',
    this.sucursal = '',
    this.zona = '',
    this.vehiculo = '',
    this.hora = '',
    this.cobradoPor = '',
    this.nota = '',
    this.comisiones = 0,
    this.muchachos = const [],
    this.pagos = const [],
  });

  factory Venta.fromJson(Map<String, dynamic> json) {
    List<Map<String, dynamic>> mapas(dynamic crudo) {
      if (crudo is! List) return [];
      return crudo.whereType<Map>().map((item) => Map<String, dynamic>.from(item)).toList();
    }

    final lavadero = json['Lavadero'] == 1 || json['Lavadero'] == true;
    return Venta(
      id: json['Id_Venta'] ?? 0,
      total: (json['Total'] ?? 0.0).toDouble(),
      fecha: json['Fecha_Venta']?.toString() ?? '',
      nombreEmpleado: json['empleados']?['Nombres'] ?? '',
      ganancia: (json['Ganancia'] ?? 0.0).toDouble(),
      anulada: ventaEstaAnulada(json),
      lavadero: lavadero,
      placa: json['Placa']?.toString() ?? '',
      cliente: json['Cliente']?.toString() ?? '',
      telefono: json['Telefono']?.toString() ?? '',
      sucursal: json['Sucursal']?.toString() ?? '',
      zona: json['Zona']?.toString() ?? '',
      vehiculo: json['Vehiculo']?.toString() ?? '',
      hora: json['Hora']?.toString() ?? '',
      cobradoPor: json['Cobrado_por']?.toString() ?? '',
      nota: json['Nota']?.toString() ?? '',
      comisiones: (json['Comisiones'] ?? 0).toDouble(),
      muchachos: mapas(json['Muchachos']),
      pagos: mapas(json['Pagos']),
      productosVendidos: (json['productos_vendidos'] is List)
          ? (json['productos_vendidos'] as List)
              .map((item) => ProductoVendido.fromJson(item as Map<String, dynamic>))
              .toList()
          : [],
    );
  }
}
