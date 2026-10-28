import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ThemeController {
  static final ValueNotifier<ThemeMode> mode = ValueNotifier(ThemeMode.system);

  static Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    switch (prefs.getString('theme_mode')) {
      case 'light':
        mode.value = ThemeMode.light;
        break;
      case 'dark':
        mode.value = ThemeMode.dark;
        break;
      default:
        mode.value = ThemeMode.system;
    }
  }

  static Future<void> set(ThemeMode next) async {
    mode.value = next;
    final prefs = await SharedPreferences.getInstance();
    final name = next == ThemeMode.light
        ? 'light'
        : next == ThemeMode.dark
            ? 'dark'
            : 'system';
    await prefs.setString('theme_mode', name);
  }
}

class Zyntra {
  static const bg = Color(0xFF0B0E14);
  static const header = Color(0xFF10131A);
  static const card = Color(0xFF161A24);
  static const elevated = Color(0xFF1C2130);
  static const input = Color(0xFF1A1F2C);
  static const nav = Color(0xFF12151D);
  static const accent = Color(0xFF3077FF);
  static const accentHover = Color(0xFF4C8CFF);
  static const purple = Color(0xFFA084E8);
  static const purpleDark = Color(0xFF6B4DE6);
  static const cyan = Color(0xFF5EC8FF);
  static const text = Color(0xFFFFFFFF);
  static const muted = Color(0xFFB8BCC8);
  static const dim = Color(0xFF8B90A0);
  static const border = Color(0xFF2A3142);
  static const danger = Color(0xFFEF4444);
  static const success = Color(0xFF22C55E);
  static const warning = Color(0xFFF59E0B);
  static const anuladaBg = Color(0xFF3F1717);
  static const anuladaFg = Color(0xFFFECACA);
}

ThemeData zyntraTheme() {
  return ThemeData(
    brightness: Brightness.dark,
    scaffoldBackgroundColor: Zyntra.bg,
    colorScheme: const ColorScheme.dark(
      primary: Zyntra.accent,
      secondary: Zyntra.cyan,
      surface: Zyntra.card,
      error: Zyntra.danger,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: Zyntra.header,
      foregroundColor: Zyntra.text,
      elevation: 0,
      centerTitle: false,
    ),
    snackBarTheme: const SnackBarThemeData(
      backgroundColor: Zyntra.elevated,
      contentTextStyle: TextStyle(color: Zyntra.text),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Zyntra.input,
      hintStyle: const TextStyle(color: Zyntra.dim),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide.none,
      ),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: Zyntra.accent,
        foregroundColor: Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    ),
    useMaterial3: false,
  );
}

ThemeData zyntraLightTheme() {
  return ThemeData(
    brightness: Brightness.light,
    scaffoldBackgroundColor: const Color(0xFFF3F5FA),
    colorScheme: const ColorScheme.light(
      primary: Zyntra.accent,
      secondary: Color(0xFF0EA5E9),
      surface: Colors.white,
      error: Zyntra.danger,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: Colors.white,
      foregroundColor: Color(0xFF0B0E14),
      elevation: 0,
      centerTitle: false,
    ),
    snackBarTheme: const SnackBarThemeData(
      backgroundColor: Color(0xFF1C2130),
      contentTextStyle: TextStyle(color: Colors.white),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: const Color(0xFFEEF1F7),
      hintStyle: const TextStyle(color: Color(0xFF8B90A0)),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide.none,
      ),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: Zyntra.accent,
        foregroundColor: Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    ),
    useMaterial3: false,
  );
}

class Zx {
  static bool dark(BuildContext context) =>
      Theme.of(context).brightness == Brightness.dark;

  static Color bg(BuildContext context) =>
      dark(context) ? Zyntra.bg : const Color(0xFFF3F5FA);

  static Color card(BuildContext context) =>
      dark(context) ? Zyntra.card : Colors.white;

  static Color elevated(BuildContext context) =>
      dark(context) ? Zyntra.elevated : const Color(0xFFEEF1F7);

  static Color text(BuildContext context) =>
      dark(context) ? Colors.white : const Color(0xFF0B0E14);

  static Color muted(BuildContext context) =>
      dark(context) ? Zyntra.muted : const Color(0xFF5C6370);

  static Color border(BuildContext context) =>
      dark(context) ? Zyntra.border : const Color(0xFFE2E6EF);
}
