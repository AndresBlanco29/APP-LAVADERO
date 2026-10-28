import 'package:flutter/material.dart';
import 'package:flutter_application_1/screens/empleados_page.dart';
import '../screens/dashboard_page.dart';
import '../screens/inventario_page.dart';
import '../screens/empleado_detalle_page.dart';
import '../screens/finanzas_page.dart';
import '../screens/ventas_page.dart';
import '../screens/financial_buckets_screen.dart';

class CustomBottomNavigationBar extends StatefulWidget {
  final int currentIndex;
  
  const CustomBottomNavigationBar({required this.currentIndex, Key? key}) : super(key: key);

  @override
  _CustomBottomNavigationBarState createState() => _CustomBottomNavigationBarState();
}

class _CustomBottomNavigationBarState extends State<CustomBottomNavigationBar> {
  late int _selectedIndex;
  
  @override
  void initState() {
    super.initState();
    _selectedIndex = widget.currentIndex;
  }
  
  @override
  Widget build(BuildContext context) {
    return Container(
      height: 80,
      decoration: BoxDecoration(
        color: const Color(0xFF12151D),
        borderRadius: BorderRadius.only(
          topLeft: Radius.circular(20),
          topRight: Radius.circular(20),
        ),
      ),
      child: Row(
        children: List.generate(5, (index) {
          final iconPaths = [
            'lib/imagenes/dash.png',
            'lib/imagenes/inventario.png',
            'lib/imagenes/cv.png',
            'lib/imagenes/presupuesto.png',
            'lib/imagenes/ventas.png',
          ];
          final labels = [
            'Dashboard',
            'Inventario',
            'Empleados',
            'Bolsillos',
            'Ventas',
          ];
          final isSelected = _selectedIndex == index;
          return Expanded(
            child: GestureDetector(
              onTap: () {
                setState(() {
                  _selectedIndex = index;
                });
                if (index == 0) {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (context) => DashboardPage()),
                  );
                } else if (index == 1) {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (context) => InventarioPage()),
                  );
                } else if (index == 2) {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (context) => EmpleadosPage()),
                  );
                } else if (index == 3) {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (context) => const FinancialBucketsScreen()),
                  );
                } else if (index == 4) {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (context) => VentasScreen()),
                  );
                }
              },
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 4, vertical: 8),
                padding: const EdgeInsets.symmetric(vertical: 6),
                decoration: isSelected
                    ? BoxDecoration(
                        color: const Color(0xFF3077FF),
                        borderRadius: BorderRadius.circular(20),
                      )
                    : null,
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Image.asset(iconPaths[index], width: 29, height: 29),
                    const SizedBox(height: 4),
                    Text(
                      labels[index],
                      style: const TextStyle(fontSize: 13, color: Colors.white),
                    ),
                  ],
                ),
              ),
            ),
          );
        }),
      ),
    );
  }
}
