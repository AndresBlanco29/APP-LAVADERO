import 'package:flutter/material.dart';
import 'package:flutter_application_1/screens/bolsillo_proveedores_screen.dart';
import 'package:flutter_application_1/screens/provision_obligaciones_screen.dart';
import 'package:flutter_application_1/theme/zyntra_theme.dart';

/// Módulo unificado: Proveedores | Administrativo (separados por pestaña).
class BolsillosHubScreen extends StatefulWidget {
  const BolsillosHubScreen({super.key, this.initialTab = 0});

  final int initialTab;

  @override
  State<BolsillosHubScreen> createState() => _BolsillosHubScreenState();
}

class _BolsillosHubScreenState extends State<BolsillosHubScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabs;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(
      length: 2,
      vsync: this,
      initialIndex: widget.initialTab.clamp(0, 1),
    );
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Zx.bg(context),
      appBar: AppBar(
        title: const Text('Bolsillos financieros'),
        bottom: TabBar(
          controller: _tabs,
          tabs: const [
            Tab(text: 'Proveedores'),
            Tab(text: 'Administrativo'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabs,
        children: const [
          BolsilloProveedoresScreen(embedded: true),
          ProvisionObligacionesScreen(embedded: true),
        ],
      ),
    );
  }
}
