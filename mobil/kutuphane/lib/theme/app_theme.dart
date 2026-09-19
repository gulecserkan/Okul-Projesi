import 'package:flutter/material.dart';

enum AppTheme {
  defaultLight,
  darkBlue,
  darkPink,
  lightBlue,
  lightPink,
}

class AppThemeConfig {
  const AppThemeConfig({
    required this.label,
    required this.icon,
    required this.themeData,
  });

  final String label;
  final IconData icon;
  final ThemeData themeData;
}

Map<AppTheme, AppThemeConfig> appThemes = {
  AppTheme.defaultLight: AppThemeConfig(
    label: "Varsayılan",
    icon: Icons.style,
    themeData: _buildTheme(seed: Colors.teal, brightness: Brightness.light),
  ),
  AppTheme.darkBlue: AppThemeConfig(
    label: "Gece Mavi",
    icon: Icons.nightlight_round,
    themeData: _buildTheme(seed: Colors.indigo, brightness: Brightness.dark),
  ),
  AppTheme.darkPink: AppThemeConfig(
    label: "Gece Pembe",
    icon: Icons.nightlight,
    themeData: _buildTheme(seed: Colors.pinkAccent, brightness: Brightness.dark),
  ),
  AppTheme.lightBlue: AppThemeConfig(
    label: "Gündüz Mavi",
    icon: Icons.wb_sunny_outlined,
    themeData: _buildTheme(seed: Colors.blue.shade800, brightness: Brightness.light),
  ),
  AppTheme.lightPink: AppThemeConfig(
    label: "Gündüz Pembe",
    icon: Icons.wb_twighlight,
    themeData: _buildTheme(seed: Colors.pink, brightness: Brightness.light),
  ),
};

ThemeData _buildTheme({required Color seed, required Brightness brightness}) {
  final scheme = ColorScheme.fromSeed(seedColor: seed, brightness: brightness);
  return ThemeData(
    colorScheme: scheme,
    brightness: brightness,
    scaffoldBackgroundColor: scheme.surface,
    appBarTheme: AppBarTheme(
      backgroundColor: scheme.surface,
      foregroundColor: scheme.onSurface,
      elevation: 0,
      centerTitle: false,
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: scheme.primary.withOpacity(brightness == Brightness.dark ? 0.18 : 0.12),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: scheme.primary.withOpacity(0.2)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: scheme.primary, width: 1.6),
      ),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: scheme.primary,
        foregroundColor: scheme.onPrimary,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
      ),
    ),
    chipTheme: ChipThemeData(
      backgroundColor: scheme.surfaceVariant.withOpacity(0.7),
      selectedColor: scheme.primary.withOpacity(0.16),
      labelStyle: TextStyle(color: scheme.onSurface),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
    ),
  );
}
