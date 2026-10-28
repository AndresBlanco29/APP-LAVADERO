import '../api/api_client.dart';
import '../ventas_model.dart';

class DashboardService {
  Future<List<dynamic>> fetchVentas() async {
    final data = await ApiClient.getJson('/ventas');
    if (data is List) return data;
    return [];
  }

  Future<Map<String, dynamic>> obtenerResumen() async {
    final ventas = await fetchVentas();
    final now = DateTime.now();
    double totalDia = 0;
    double totalMes = 0;
    double gananciaDia = 0;
    double gananciaMes = 0;
    int ticketsDia = 0;
    int ticketsMes = 0;
    int anuladasDia = 0;
    int anuladasMes = 0;
    final Map<String, double> ventasPorDia = {};

    for (final raw in ventas) {
      if (raw is! Map) continue;
      final map = Map<String, dynamic>.from(raw);
      DateTime fechaVenta;
      try {
        fechaVenta = DateTime.parse(map['Fecha_Venta'].toString());
      } catch (_) {
        continue;
      }
      final total = double.tryParse(map['Total'].toString()) ?? 0;
      final ganancia = double.tryParse('${map['Ganancia'] ?? 0}') ?? 0;
      final anulada = ventaEstaAnulada(map);
      final mismoDia = fechaVenta.year == now.year &&
          fechaVenta.month == now.month &&
          fechaVenta.day == now.day;
      final mismoMes = fechaVenta.year == now.year && fechaVenta.month == now.month;

      if (anulada) {
        if (mismoDia) anuladasDia += 1;
        if (mismoMes) anuladasMes += 1;
        continue;
      }

      if (mismoDia) {
        totalDia += total;
        gananciaDia += ganancia;
        ticketsDia += 1;
      }
      if (mismoMes) {
        totalMes += total;
        gananciaMes += ganancia;
        ticketsMes += 1;
      }

      final key =
          '${fechaVenta.year.toString().padLeft(4, '0')}-${fechaVenta.month.toString().padLeft(2, '0')}-${fechaVenta.day.toString().padLeft(2, '0')}';
      ventasPorDia[key] = (ventasPorDia[key] ?? 0) + total;
    }

    final keys = ventasPorDia.keys.toList()..sort();
    final ultimas = keys.length > 14 ? keys.sublist(keys.length - 14) : keys;
    final chart = <String, double>{};
    for (final k in ultimas) {
      final parts = k.split('-');
      chart['${int.parse(parts[2])}/${int.parse(parts[1])}'] = ventasPorDia[k]!;
    }

    return {
      'totalDia': totalDia,
      'totalMes': totalMes,
      'gananciaDia': gananciaDia,
      'gananciaMes': gananciaMes,
      'ticketsDia': ticketsDia,
      'ticketsMes': ticketsMes,
      'anuladasDia': anuladasDia,
      'anuladasMes': anuladasMes,
      'ventasPorDia': chart,
    };
  }
}
