import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';
import 'package:fl_chart/fl_chart.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:flutter_application_1/ventas_model.dart';

class ComparativaPage extends StatefulWidget {
  const ComparativaPage({super.key});

  @override
  State<ComparativaPage> createState() => _ComparativaPageState();
}

class SalesData {
  final String day;
  final int sales;
  SalesData(this.day, this.sales);
}

class _ComparativaPageState extends State<ComparativaPage> {
  DateTime? _startDate;
  DateTime? _endDate;
  String _aggregation = 'Diario';
  List<Map<String, dynamic>> _salesData = [];

  @override
  void initState() {
    super.initState();
    initializeDateFormatting('es_ES', null);
  }

  Widget buildFechaItem(String label, DateTime? date, VoidCallback onTap) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 16,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 8),
        Container(
          decoration: BoxDecoration(
            color: const Color(0xFF1A1F2C),
            borderRadius: BorderRadius.circular(12),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                date != null
                    ? DateFormat('dd MMM yyyy', 'es_ES').format(date)
                    : 'Seleccionar fecha',
                style: const TextStyle(color: Colors.white),
              ),
              IconButton(
                onPressed: onTap,
                icon: Image.asset(
                  'lib/imagenes/calendario.png',
                  width: 35,
                  height: 35,
                ),
              ),
            ],
          ),
        ),
      ],
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
        title: const Text(
          'Comparativas',
          style: TextStyle(color: Colors.white),
        ),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () {
            Navigator.pop(context);
          },
        ),
      ),
      body: Container(
        decoration: const BoxDecoration(color: Color(0xFF0B0E14)),
        child: SafeArea(
          child: RefreshIndicator(
            onRefresh: _loadSalesData,
            child: SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              child: ConstrainedBox(
                constraints: BoxConstraints(
                  minHeight: MediaQuery.of(context).size.height,
                ),
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: const [
                          Text(
                            'Comparativa de Ventas',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 26,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          CircleAvatar(
                            backgroundColor: Colors.white,
                            child: Icon(
                              Icons.compare_arrows,
                              color: Colors.black,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 20),
                      const Text(
                        'Selecciona el tipo de comparación que quieres ver',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 16),
                      Container(
                        decoration: BoxDecoration(
                          color: Colors.indigo.shade600,
                          border: Border.all(color: Colors.indigo.shade600),
                          borderRadius: BorderRadius.zero,
                        ),
                        padding: EdgeInsets.zero,
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Expanded(
                              child: ElevatedButton(
                                style: ElevatedButton.styleFrom(
                                  backgroundColor:
                                      _aggregation == 'Diario'
                                          ? Colors.indigo.shade800
                                          : Colors.indigo.shade600,
                                  foregroundColor: Colors.white,
                                  padding: EdgeInsets.symmetric(vertical: 12),
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.zero,
                                  ),
                                ),
                                onPressed: () {
                                  setState(() {
                                    _aggregation = 'Diario';
                                  });
                                },
                                child: const Text('Diario'),
                              ),
                            ),
                            Expanded(
                              child: ElevatedButton(
                                style: ElevatedButton.styleFrom(
                                  backgroundColor:
                                      _aggregation == 'Semanal'
                                          ? Colors.indigo.shade800
                                          : Colors.indigo.shade600,
                                  foregroundColor: Colors.white,
                                  padding: EdgeInsets.symmetric(vertical: 12),
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.zero,
                                  ),
                                ),
                                onPressed: () {
                                  setState(() {
                                    _aggregation = 'Semanal';
                                  });
                                },
                                child: const Text('Semanal'),
                              ),
                            ),
                            Expanded(
                              child: ElevatedButton(
                                style: ElevatedButton.styleFrom(
                                  backgroundColor:
                                      _aggregation == 'Mensual'
                                          ? Colors.indigo.shade800
                                          : Colors.indigo.shade600,
                                  foregroundColor: Colors.white,
                                  padding: EdgeInsets.symmetric(vertical: 12),
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.zero,
                                  ),
                                ),
                                onPressed: () {
                                  setState(() {
                                    _aggregation = 'Mensual';
                                  });
                                },
                                child: const Text('Mensual'),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16.0),
                      Column(
                        children: [
                          buildFechaItem(
                            'Día 1',
                            _startDate,
                            () => _selectDate(context, true),
                          ),
                          const SizedBox(height: 16),
                          buildFechaItem(
                            'Día 2',
                            _endDate,
                            () => _selectDate(context, false),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16.0),
                      ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.indigo.shade600,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(
                            horizontal: 16,
                            vertical: 12,
                          ),
                        ),
                        onPressed: _loadSalesData,
                        child: const Text('Comparar Ventas'),
                      ),
                      const SizedBox(height: 16.0),
                      _salesData.isEmpty
                          ? const Center(
                            child: Text(
                              'No hay datos para mostrar',
                              style: TextStyle(color: Colors.white),
                            ),
                          )
                          : Card(
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(10),
                            ),
                            elevation: 4,
                            color: const Color(0xFF161A24),
                            child: Padding(
                              padding: const EdgeInsets.all(12),
                              child: Column(
                                children: [
                                  const Text(
                                    'COMPARATIVA DE VENTAS',
                                    style: TextStyle(
                                      color: Colors.white,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                  const SizedBox(height: 10),
                                  SizedBox(
                                    height:
                                        MediaQuery.of(context).size.height *
                                        0.4,
                                    child: _buildChart(),
                                  ),
                                ],
                              ),
                            ),
                          ),
                      const SizedBox(height: 16.0),
                      ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.indigo.shade600,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(
                            horizontal: 20,
                            vertical: 12,
                          ),
                        ),
                        onPressed: () => Navigator.pop(context),
                        child: const Text('Volver'),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _selectDate(BuildContext context, bool isStart) async {
    DateTime initialDate = DateTime.now();
    final DateTime? picked = await showDatePicker(
      context: context,
      initialDate:
          isStart ? (_startDate ?? initialDate) : (_endDate ?? initialDate),
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
    );
    if (picked != null) {
      setState(() {
        if (isStart) {
          _startDate = picked;
        } else {
          _endDate = picked;
        }
        _salesData = [];
      });
    }
  }

  Future<void> _loadSalesData() async {
    if (_startDate == null || _endDate == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Por favor, seleccione ambas fechas')),
      );
      return;
    }

    final String baseUrl = "https://api-production-b438.up.railway.app";
    // Modificación según la agregación:
    Uri url;
    if (_aggregation == 'Mensual') {
      // Para el mes de inicio se toma el primer día, y para el de fin el primer día del siguiente mes
      final monthStart = DateTime(_startDate!.year, _startDate!.month, 1);
      final nextMonth = DateTime(_endDate!.year, _endDate!.month + 1, 1);
      print("Cargando ventas (Mensual) desde: ${monthStart.toIso8601String()} hasta: ${nextMonth.toIso8601String()}");
      url = Uri.parse(
        "$baseUrl/sales?start=${monthStart.toIso8601String()}&end=${nextMonth.toIso8601String()}&aggregation=$_aggregation",
      );
    } else {
      final adjustedEndDate = _endDate!.add(Duration(days: 1));
      print("Cargando ventas desde: ${_startDate!.toIso8601String()} hasta: ${adjustedEndDate.toIso8601String()}");
      url = Uri.parse(
        "$baseUrl/sales?start=${_startDate!.toIso8601String()}&end=${adjustedEndDate.toIso8601String()}&aggregation=$_aggregation",
      );
    }
    
    try {
      final response = await http.get(url).timeout(Duration(seconds: 10));
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        if (!mounted) return;
        setState(() {
          _salesData = List<Map<String, dynamic>>.from(data)
              .where((item) => !ventaEstaAnulada(item))
              .toList();
        });
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Error al cargar datos de ventas')),
          );
        }
      }
    } on TimeoutException catch (e) {
      print("Timeout error: $e");
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              "La solicitud ha tardado demasiado tiempo. Verifica la conexión o la disponibilidad del backend.",
            ),
          ),
        );
      }
    } catch (error) {
      print("Error completo: $error");
      String errorMsg;
      if (error.toString().contains("Failed to fetch")) {
        errorMsg =
            "Error de conexión: No se pudo acceder al backend. Verifica la URL y tu conexión.";
      } else {
        errorMsg = 'Error: $error';
      }
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(errorMsg)));
      }
    }
  }

  bool isSameDay(DateTime a, DateTime b) {
    return a.year == b.year && a.month == b.month && a.day == b.day;
  }

  // Nueva función para comparar meses
  bool isSameMonth(DateTime a, DateTime b) {
    return a.year == b.year && a.month == b.month;
  }

  Widget _buildChart() {
    if (_salesData.isEmpty) {
      return Container(
        height: MediaQuery.of(context).size.height * 0.4,
        color: const Color(0xFF161A24),
        child: const Center(
          child: Text(
            'Sin datos',
            style: TextStyle(color: Colors.white, fontSize: 16),
          ),
        ),
      );
    }

    List<SalesData> data = [];
    if (_aggregation == 'Diario') {
      final DateTime startNorm = DateTime(
        _startDate!.year,
        _startDate!.month,
        _startDate!.day,
      );
      final DateTime endNorm = DateTime(
        _endDate!.year,
        _endDate!.month,
        _endDate!.day,
      );
      Map<DateTime, int> grouped = {};
      grouped[startNorm] = 0;
      if (!isSameDay(startNorm, endNorm)) {
        grouped[endNorm] = 0;
      }
      for (var item in _salesData) {
        String? dateStr =
            item.containsKey('Fecha_Venta')
                ? item['Fecha_Venta'] as String
                : item.containsKey('date')
                ? item['date'] as String
                : null;
        if (dateStr == null) continue;
        num? salesValue =
            item.containsKey('Total')
                ? item['Total'] as num
                : item.containsKey('ventas')
                ? item['ventas'] as num
                : null;
        if (salesValue == null) continue;
        DateTime day = DateTime.parse(dateStr);
        DateTime normalized = DateTime(day.year, day.month, day.day);
        for (final key in grouped.keys) {
          if (isSameDay(key, normalized)) {
            grouped[key] = (grouped[key] ?? 0) + salesValue.toInt();
          }
        }
      }
      final sortedKeys = grouped.keys.toList()..sort();
      data =
          sortedKeys
              .map(
                (d) => SalesData(
                  DateFormat('MMMM d/yyyy', 'es_ES').format(d),
                  grouped[d]!,
                ),
              )
              .toList();
    } else if (_aggregation == 'Semanal') {
      Map<DateTime, int> grouped = {};
      for (var item in _salesData) {
        String? dateStr =
            item.containsKey('Fecha_Venta')
                ? item['Fecha_Venta'] as String
                : item.containsKey('date')
                ? item['date'] as String
                : null;
        if (dateStr == null) continue;
        num? salesValue =
            item.containsKey('Total')
                ? item['Total'] as num
                : item.containsKey('ventas')
                ? item['ventas'] as num
                : null;
        if (salesValue == null) continue;
        DateTime day = DateTime.parse(dateStr);
        DateTime normalized = DateTime(day.year, day.month, day.day);
        grouped[normalized] = (grouped[normalized] ?? 0) + salesValue.toInt();
      }
      final sortedKeys = grouped.keys.toList()..sort();
      data =
          sortedKeys
              .map(
                (d) => SalesData(
                  "${DateFormat('EEE', 'es_ES').format(d)}/${DateFormat('dd/MM').format(d)}",
                  grouped[d]!,
                ),
              )
              .toList();
    } else if (_aggregation == 'Mensual') {
      // Exclusivo: si las fechas seleccionadas pertenecen a meses diferentes
      if (isSameMonth(_startDate!, _endDate!)) {
        return Container(
          height: MediaQuery.of(context).size.height * 0.4,
          color: Colors.white,
          child: const Center(
            child: Text(
              'Seleccione fechas de dos meses diferentes para visualizar la comparación mensual',
              style: TextStyle(color: Colors.black, fontSize: 16),
            ),
          ),
        );
      } else {
        // Calcular totales para la totalidad del mes de cada fecha seleccionada
        DateTime key1 = DateTime(_startDate!.year, _startDate!.month);
        DateTime key2 = DateTime(_endDate!.year, _endDate!.month);
        Map<DateTime, int> grouped = {key1: 0, key2: 0};
        for (var item in _salesData) {
          String? dateStr =
              item.containsKey('Fecha_Venta')
                  ? item['Fecha_Venta'] as String
                  : item.containsKey('date')
                  ? item['date'] as String
                  : null;
          if (dateStr == null) continue;
          num? salesValue =
              item.containsKey('Total')
                  ? item['Total'] as num
                  : item.containsKey('ventas')
                  ? item['ventas'] as num
                  : null;
          if (salesValue == null) continue;
          DateTime saleDate = DateTime.parse(dateStr);
          DateTime saleMonth = DateTime(saleDate.year, saleDate.month);
          if (isSameMonth(saleMonth, key1)) {
            grouped[key1] = (grouped[key1] ?? 0) + salesValue.toInt();
          }
          if (isSameMonth(saleMonth, key2)) {
            grouped[key2] = (grouped[key2] ?? 0) + salesValue.toInt();
          }
        }
        final sortedKeys =
            grouped.keys.toList()..sort((a, b) => a.compareTo(b));
        data =
            sortedKeys
                .map(
                  (d) => SalesData(
                    DateFormat('MMMM yyyy', 'es_ES').format(d),
                    grouped[d]!,
                  ),
                )
                .toList();
      }
    }

    final List<Color> barColors = [
      Colors.blue,
      Colors.green,
      Colors.orange,
      Colors.red,
      Colors.purple,
    ];

    final barGroups = List.generate(data.length, (index) {
      return BarChartGroupData(
        x: index,
        barRods: [
          BarChartRodData(
            toY: data[index].sales.toDouble(),
            color: barColors[index % barColors.length],
            width: _aggregation == 'Diario' ? 50 : 16,
            borderRadius: BorderRadius.zero,
          ),
        ],
      );
    });

    double maxY =
        data.isNotEmpty
            ? data
                .map((d) => d.sales)
                .reduce((a, b) => a > b ? a : b)
                .toDouble()
            : 0;
    final double fontSize = MediaQuery.of(context).size.width * 0.03;
    final double bottomReservedSize =
        _aggregation == 'Semanal' ? fontSize * 4 : fontSize * 3;
    return BarChart(
      BarChartData(
        maxY: maxY + 10,
        barTouchData: BarTouchData(enabled: true),
        titlesData: FlTitlesData(
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: bottomReservedSize,
              getTitlesWidget: (double value, TitleMeta meta) {
                int index = value.toInt();
                if (index >= 0 && index < data.length) {
                  final double angle =
                      _aggregation == 'Semanal'
                          ? -0.8
                          : (_aggregation == 'Diario' ||
                                  _aggregation == 'Mensual'
                              ? 0
                              : -0.3);
                  return SideTitleWidget(
                    axisSide: meta.axisSide,
                    child: Padding(
                      padding: const EdgeInsets.only(top: 8.0),
                      child: Transform.rotate(
                        angle: angle,
                        child: Text(
                          data[index].day,
                          style: TextStyle(
                            fontSize: fontSize,
                            color: Colors.white,
                          ),
                        ),
                      ),
                    ),
                  );
                }
                return Container();
              },
            ),
          ),
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 60,
              getTitlesWidget: (double value, TitleMeta meta) {
                return Container(
                  alignment: Alignment.centerRight,
                  width: 60,
                  child: FittedBox(
                    fit: BoxFit.scaleDown,
                    child: Text(
                      value.toInt().toString(),
                      style: TextStyle(fontSize: fontSize, color: Colors.white),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                );
              },
            ),
          ),
          topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
        ),
        borderData: FlBorderData(show: false),
        barGroups: barGroups,
      ),
      swapAnimationDuration: const Duration(milliseconds: 250),
    );
  }
}
