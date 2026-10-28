import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_application_1/modelos/producto_model.dart';

class ProductoService {
  final String baseUrl = 'https://api-production-b438.up.railway.app/productos';

  Future<List<Producto>> obtener_productos() async {
    final response = await http.get(Uri.parse(baseUrl));

    if (response.statusCode == 200) {
      List<dynamic> data = json.decode(response.body);
      return data.map((json) => Producto.fromJson(json)).toList();
    } else {
      throw Exception('Error al cargar los productos');
    }
  }
}