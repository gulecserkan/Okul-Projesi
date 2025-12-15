import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

enum AppTheme { breeze, sunset, midnight, rainbow }

class AppThemeOption {
  const AppThemeOption({
    required this.label,
    required this.icon,
    required this.themeData,
  });

  final String label;
  final IconData icon;
  final ThemeData themeData;
}

ThemeData _buildTheme({
  required Color seed,
  required Color background,
  required Color cardColor,
  Brightness brightness = Brightness.light,
}) {
  final base = ThemeData(
    useMaterial3: true,
    brightness: brightness,
    colorScheme: ColorScheme.fromSeed(
      seedColor: seed,
      brightness: brightness,
      background: background,
    ),
  );

  final textTheme = GoogleFonts.manropeTextTheme(base.textTheme);
  final fgColor =
      brightness == Brightness.dark ? Colors.white : const Color(0xFF0F172A);

  return base.copyWith(
    textTheme: textTheme,
    scaffoldBackgroundColor: background,
    appBarTheme: AppBarTheme(
      elevation: 0,
      backgroundColor: Colors.transparent,
      foregroundColor: fgColor,
    ),
    cardTheme: CardThemeData(
      color: cardColor,
      surfaceTintColor: Colors.transparent,
      elevation: 1.5,
      shadowColor: brightness == Brightness.dark
          ? Colors.black54
          : Colors.black.withOpacity(0.08),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
    ),
  );
}

final Map<AppTheme, AppThemeOption> appThemes = {
  AppTheme.breeze: AppThemeOption(
    label: 'Meltem',
    icon: Icons.bubble_chart_outlined,
    themeData: _buildTheme(
      seed: const Color(0xFF22D3EE),
      background: const Color(0xFFF7F8FE),
      cardColor: const Color(0xFFFDFBFF),
    ),
  ),
  AppTheme.sunset: AppThemeOption(
    label: 'Gün Batımı',
    icon: Icons.wb_sunny_outlined,
    themeData: _buildTheme(
      seed: const Color(0xFFFB8C00),
      background: const Color(0xFFFFF6EC),
      cardColor: const Color(0xFFFFFBF5),
    ),
  ),
  AppTheme.midnight: AppThemeOption(
    label: 'Gece',
    icon: Icons.nightlight_round,
    themeData: _buildTheme(
      seed: const Color(0xFF0EA5E9),
      background: const Color(0xFF0B1220),
      cardColor: const Color(0xFF111C2E),
      brightness: Brightness.dark,
    ),
  ),
  AppTheme.rainbow: AppThemeOption(
    label: 'Rengarenk',
    icon: Icons.color_lens_outlined,
    themeData: _buildTheme(
      seed: const Color(0xFFEA5E8B),
      background: const Color(0xFFFFF7FB),
      cardColor: const Color(0xFFFFFCFF),
    ),
  ),
};
