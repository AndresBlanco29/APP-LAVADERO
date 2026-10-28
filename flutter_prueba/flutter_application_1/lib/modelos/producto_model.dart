class Producto {
  final int id;
  final String nombre;
  final int precioVenta;
  final int cantidad;
  final String? imagenUrl; 
  final String codigoBarras;
// opcional, si tienes la URL o nombre de imagen

  Producto({
    required this.id,
    required this.nombre,
    required this.precioVenta,
    required this.cantidad,
    required this.codigoBarras,

    this.imagenUrl,
  });

  factory Producto.fromJson(Map<String, dynamic> json) {
    return Producto(
      id: json['id'],
      nombre: json['nombre'],
      precioVenta: (json['precio_venta'] as num).toInt(), // por si viene como double
      cantidad: json['cantidad'],
      codigoBarras: json['codigo_barras'] ?? '',
      imagenUrl: json['url_imagen'], // o null si quieres dejarlo opcional
    );
  }

}