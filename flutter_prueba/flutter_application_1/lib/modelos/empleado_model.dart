class Empleado {
  final int id;
  final String nombres;
  final String telefono;
  final String correo;
  final String fechaNacimiento;
  final String fechaIngreso;
  final String cargo;

  Empleado({
    required this.id,
    required this.nombres,
    required this.telefono,
    required this.correo,
    required this.fechaNacimiento,
    required this.fechaIngreso,
    required this.cargo,
  });

  factory Empleado.fromJson(Map<String, dynamic> json) {
    return Empleado(
      id: json['Id_Empleados'],
      nombres: json['Nombres'],
      telefono: json['Telefono'] ?? '',
      correo: json['Correo'] ?? '',
      fechaNacimiento: json['Fecha_nacimiento'] ?? '',
      fechaIngreso: json['Fecha_ingreso'] ?? '',
      cargo: json['Cargo'] ?? '',
    );
  }
}
