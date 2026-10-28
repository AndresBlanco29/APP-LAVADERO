import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../services/rotacion_service.dart';

class RotacionPage extends StatefulWidget {
  const RotacionPage({super.key});

  @override
  State<RotacionPage> createState() => _RotacionPageState();
}

class _RotacionPageState extends State<RotacionPage> {
  final service = RotacionService();
  late Future<List<ProductoRotado>> _productosDia;
  late Future<List<ProductoRotado>> _productosMes;
  // Variables para productos mas vendidos
  late Future<List<ProductoRotado>> _productosMasDia;
  late Future<List<ProductoRotado>> _productosMasMes;

  @override
  void initState() {
    super.initState();
    _productosDia = service.fetchMenosVendidos(periodo: 'dia');
    _productosMes = service.fetchMenosVendidos(periodo: 'mes');
    // Inicialización de nuevos futuros para mas vendidos
    _productosMasDia = service.fetchMasVendidos(periodo: 'dia');
    _productosMasMes = service.fetchMasVendidos(periodo: 'mes');
  }

  // Función que construye un Card con un título y el gráfico
  Widget _buildChartSection(String title, Future<List<ProductoRotado>> future) {
    final screenHeight = MediaQuery.of(context).size.height;
    return Card(
      color: const Color(0xFF161A24), // fondo de la gráfica establecido
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      elevation: 4,
      margin: const EdgeInsets.symmetric(vertical: 12),
      child: Padding(
        padding: const EdgeInsets.all(10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white)),
            const SizedBox(height: 12),
            FutureBuilder<List<ProductoRotado>>(
              future: future,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return SizedBox(
                      height: screenHeight * 0.3,
                      child: const Center(child: CircularProgressIndicator()));
                } else if (snapshot.hasError) {
                  return SizedBox(
                      height: screenHeight * 0.3,
                      child: Center(child: Text('Error: ${snapshot.error}', style: const TextStyle(color: Colors.white))));
                } else if (snapshot.data == null || snapshot.data!.isEmpty) {
                  return SizedBox(
                      height: screenHeight * 0.3,
                      child: const Center(child: Text('No hay datos disponibles.', style: TextStyle(color: Colors.white))));
                }
                // Depuración para secciones del día
                if (title.contains('Día')) {
                  print("Datos para $title: ${snapshot.data}");
                  // Se usará la data completa sin filtrar por cantidad > 0
                  return SizedBox(
                      height: screenHeight * 0.3,
                      child: _buildChart(snapshot.data!));
                }
                return SizedBox(
                    height: screenHeight * 0.3,
                    child: _buildChart(snapshot.data!));
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildChart(List<ProductoRotado> productos) {
    final barColors = [
      Colors.blueAccent,
      Colors.redAccent,
      Colors.green,
      Colors.orange,
      Colors.purpleAccent,
      Colors.teal,
    ];
    
    List<BarChartGroupData> barGroups = productos.asMap().entries.map((entry) {
      int index = entry.key;
      final p = entry.value;
      return BarChartGroupData(
        x: index,
        barRods: [
          BarChartRodData(
            toY: p.cantidad.toDouble(),
            color: p.cantidad == 0 ? Colors.grey : barColors[index % barColors.length],
            width: 24,
            borderRadius: BorderRadius.circular(4),
          ),
        ],
      );
    }).toList();

    return BarChart(
      BarChartData(
        backgroundColor: const Color(0xFF161A24), // fondo de la gráfica establecido
        barGroups: barGroups,
        titlesData: FlTitlesData(
          topTitles: AxisTitles(
            sideTitles: SideTitles(showTitles: false),
            // axisNameWidget eliminado
            axisNameSize: 0,
          ),
          rightTitles: AxisTitles(
            sideTitles: SideTitles(showTitles: false),
            // axisNameWidget eliminado
            axisNameSize: 0,
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 60, // Reservar espacio para los títulos y evitar que se tapen
              getTitlesWidget: (double value, TitleMeta meta) {
                int index = value.toInt();
                if (index < 0 || index >= productos.length) return const SizedBox();
                return SideTitleWidget(
                  axisSide: meta.axisSide,
                  space: 4,
                  child: Container(
                    width: 60,  // ancho ajustado
                    height: 40, // altura reducida para evitar choque con el borde
                    padding: const EdgeInsets.only(bottom: 8), // mayor padding inferior para separar el texto
                    alignment: Alignment.center,
                    child: Text(
                      productos[index].nombre,
                      style: const TextStyle(fontSize: 10, color: Colors.white),
                      textAlign: TextAlign.center,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                );
              },
            ),
            axisNameWidget: const Text("Productos", style: TextStyle(color: Colors.white, fontSize: 12)),
            axisNameSize: 30,
          ),
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              getTitlesWidget: (double value, TitleMeta meta) {
                return Text(
                  value.toStringAsFixed(0),
                  style: const TextStyle(color: Colors.white),
                );
              },
              reservedSize: 28,
            ),
            axisNameWidget: const Text("Cantidad", style: TextStyle(color: Colors.white, fontSize: 12)),
            axisNameSize: 30,
          ),
        ),
        borderData: FlBorderData(show: false),
        gridData: FlGridData(show: false),
        minY: 0, // Asegura que el gráfico comience en 0
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        iconTheme: const IconThemeData(color: Colors.white),
        title: const Text('Rotación de Productos', style: TextStyle(color: Colors.white)),
      ),
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFF0B0E14), Color(0xFF161A24)],
          ),
        ),
        child: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 24),
            child: Column(
              children: [
                _buildChartSection('Menos Vendidos Día', _productosDia),
                _buildChartSection('Menos Vendidos Mes', _productosMes),
                _buildChartSection('Más Vendidos Día', _productosMasDia),
                _buildChartSection('Más Vendidos Mes', _productosMasMes),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
