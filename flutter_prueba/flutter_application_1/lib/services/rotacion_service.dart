import 'dart:convert';
import 'package:http/http.dart' as http;

class ProductoRotado {
  final int id;
  final String nombre;
  final String marca;
  final String codigoBarras;
  final int cantidad;
  final double precio;
  final double total;

  ProductoRotado({
    required this.id,
    required this.nombre,
    required this.marca,
    required this.codigoBarras,
    required this.cantidad,
    required this.precio,
    required this.total,
  });

  factory ProductoRotado.fromJson(Map<String, dynamic> json) {
    return ProductoRotado(
      id: json['id'],
      nombre: json['nombre'],
      marca: json['marca'] ?? '',
      codigoBarras: json['codigo_barras'] ?? '',
      cantidad: json['cantidad'],
      precio: json['precio'],
      total: json['total'],
    );
  }
}

class RotacionService {
  final String baseUrl = "https://api-production-b438.up.railway.app";

  Future<List<ProductoRotado>> fetchMenosVendidos({required String periodo}) async {
    final url = Uri.parse("$baseUrl/rotacion/todos/$periodo?orden=asc&all=true");
    final response = await http.get(url);

    if (response.statusCode == 200) {
      List<dynamic> data = jsonDecode(response.body);
      return data.map((item) => ProductoRotado.fromJson(item)).toList();
    } else {
      throw Exception('Error al cargar los productos menos vendidos');
    }
  }

  Future<List<ProductoRotado>> fetchMasVendidos({required String periodo}) async {
    final url = Uri.parse("$baseUrl/rotacion/todos/$periodo?orden=desc&all=true");
    final response = await http.get(url);

    if (response.statusCode == 200) {
      List<dynamic> data = jsonDecode(response.body);
      return data.map((item) => ProductoRotado.fromJson(item)).toList();
    } else {
      throw Exception('Error al cargar los productos más vendidos');
    }
  }
}
