import 'dart:convert';
import 'package:http/http.dart' as http;
import '/modelos/empleado_model.dart';

class EmpleadosService {
  final String baseUrl = 'https://api-production-b438.up.railway.app';

  Future<List<Empleado>> fetchEmpleados() async {
    final response = await http.get(Uri.parse('$baseUrl/empleados'));

    if (response.statusCode == 200) {
      List<dynamic> body = json.decode(response.body);
      return body.map((e) => Empleado.fromJson(e)).toList();
    } else {
      throw Exception('Error al cargar los empleados');
    }
  }
}
