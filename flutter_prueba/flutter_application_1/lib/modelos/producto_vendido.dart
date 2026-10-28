class ProductoVendido {
  final String nombre;
  final int cantidad;
  final double precio;

  ProductoVendido({
    required this.nombre,
    required this.cantidad,
    required this.precio,
  });

  factory ProductoVendido.fromJson(Map<String, dynamic> json) {
    return ProductoVendido(
      nombre: json['Nombre_Producto']?.toString() ?? 'Producto',
      cantidad: int.tryParse('${json['Cantidad'] ?? 0}') ?? 0,
      precio: double.tryParse('${json['Precio'] ?? 0}') ?? 0,
    );
  }
}
