import 'package:flutter_application_1/api/api_client.dart';
import 'ventas_model.dart';

class VentasService {
  Future<List<Venta>> obtenerVentas() async {
    final data = await ApiClient.getJson('/ventas');
    final list = data is List ? data : <dynamic>[];
    final ventas =
        list
            .whereType<Map>()
            .map((ventaJson) => Venta.fromJson(Map<String, dynamic>.from(ventaJson)))
            .toList();

    ventas.sort((a, b) {
      try {
        return DateTime.parse(b.fecha).compareTo(DateTime.parse(a.fecha));
      } catch (_) {
        return 0;
      }
    });
    return ventas;
  }
}
