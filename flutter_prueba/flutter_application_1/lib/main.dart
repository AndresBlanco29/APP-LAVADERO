import 'package:flutter/material.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:flutter_application_1/screens/Login.dart';
import 'package:flutter_application_1/theme/zyntra_theme.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initializeDateFormatting('es_ES', null);
  await ThemeController.load();
  runApp(const ZyntraApp());
}

class ZyntraApp extends StatelessWidget {
  const ZyntraApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<ThemeMode>(
      valueListenable: ThemeController.mode,
      builder: (_, mode, __) {
        return MaterialApp(
          title: 'Zyntra POS',
          debugShowCheckedModeBanner: false,
          theme: zyntraLightTheme(),
          darkTheme: zyntraTheme(),
          themeMode: mode,
          home: const LoginPage(),
        );
      },
    );
  }
}
