import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:intl/date_symbol_data_local.dart';

class DetallesFinanzas extends StatelessWidget {
  final Map<String, dynamic> item;

  const DetallesFinanzas({Key? key, required this.item}) : super(key: key);
  @override
  Widget build(BuildContext context) {
    final DateTime fecha = DateTime.parse(item['fecha']);

    // Ensure locale data is initialized
    initializeDateFormatting('es_ES', null);

    final String formattedDate = DateFormat(
      "dd/MM/yyyy, h:mm a",
      "es_ES",
    ).format(fecha);

    return Scaffold(
      backgroundColor: const Color(0xFF0B0E14),
      appBar: PreferredSize(
        preferredSize: const Size.fromHeight(90),
        child: AppBar(
          backgroundColor: const Color(0xFF0B0E14),
          elevation: 0,
          leading: IconButton(
            icon: const Icon(Icons.arrow_back, color: Colors.white),
            onPressed: () => Navigator.pop(context),
          ),
          title: const Padding(
            padding: EdgeInsets.only(top: 36.0),
            child: Text(
              'Detalles Finanzas',
              style: TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.bold,
                fontSize: 28,
              ),
            ),
          ),
          centerTitle: true,
        ),
      ),
      body: Column(
        children: [
          Container(
            color: Colors.white,
            child: Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: 30.0,
                vertical: 20.0,
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Container(
                    width: 350,
                    height: 102,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: const Color(0xFF0B0E14),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Row(
                              children: [
                                if (item['tipo'] == 'Entrada')
                                  Image.asset(
                                    'lib/imagenes/flecha_verde.png',
                                    width: 45,
                                    height: 45,
                                  )
                                else if (item['tipo'] == 'Salida')
                                  Image.asset(
                                    'lib/imagenes/flecha_roja.png',
                                    width: 45,
                                    height: 45,
                                  ),
                                const SizedBox(width: 8),
                                Text(
                                  item['tipo'],
                                  style: const TextStyle(
                                    fontWeight: FontWeight.bold,
                                    color: Colors.white,
                                    fontSize: 20,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 4),
                            Text(
                              item['descripcion'] ?? "Sin descripción",
                              style: const TextStyle(
                                color: Colors.white70,
                                fontSize: 16,
                              ),
                            ),
                          ],
                        ),
                        Text(
                          '\$${NumberFormat("#,###.##", "es_ES").format(item['monto'])}',
                          style: TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                            color:
                                item['tipo'] == 'Entrada'
                                    ? Colors.green
                                    : Colors.red,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SizedBox(height: 10),
                    detalleItem("Fecha", formattedDate),
                    const SizedBox(height: 10),
                    detalleItem(
                      "Monto",
                      "\$${NumberFormat("#,###.##", "es_ES").format(item['monto'])}",
                      color:
                          item['tipo'] == 'Entrada' ? Colors.green : Colors.red,
                    ),
                    const SizedBox(height: 10),
                    detalleItem("Tipo", item['tipo']),
                    if (item['tipo'] == "Venta") ...[
                      const SizedBox(height: 10),
                      detalleItem("Categoría", "Venta"),
                    ],
                    const SizedBox(height: 10),
                    detalleItem("Método de pago", "Efectivo"),
                    const SizedBox(height: 10),
                    detalleItem("Cajero", item['cajero'] ?? "No especificado"),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget detalleItem(String titulo, String valor, {Color? color}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF1C2130),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            titulo,
            style: const TextStyle(color: Colors.white70, fontSize: 16),
          ),
          Text(
            valor,
            style: TextStyle(
              color: color ?? Colors.white,
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}
