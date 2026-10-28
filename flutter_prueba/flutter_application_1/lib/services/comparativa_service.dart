import 'dart:convert';
import 'package:http/http.dart' as http;

class ComparativaService {
  final String baseUrl = "https://api-production-b438.up.railway.app";

  Future<List<Map<String, dynamic>>> fetchSalesData({
    required DateTime startDate,
    required DateTime endDate,
    required String aggregation,
  }) async {
    final url = Uri.parse(
      "$baseUrl/sales?start=${startDate.toIso8601String()}&end=${endDate.toIso8601String()}&aggregation=$aggregation"
    );
    final response = await http.get(url);
    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return List<Map<String, dynamic>>.from(data);
    } else {
      throw Exception('Error al cargar datos de ventas');
    }
  }
}

