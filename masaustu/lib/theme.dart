import 'package:flutter/material.dart';

import 'config.dart';

/// Uygulama renk temaları.
///
/// Tüm temalar Material 3 `ColorScheme.fromSeed` üzerine kuruludur; böylece
/// açık/koyu her temada buton, snackbar, kart gibi yüzeylerde metin roller
/// (onPrimary, onSecondaryContainer, onSurface...) otomatik okunabilir kontrast
/// garantisiyle üretilir.
enum AppTheme {
  standart(
    'Standart',
    'Mor (varsayılan)',
    Color(0xFF6750A4),
  ),
  canli(
    'Canlı',
    'Pembe-kırmızı canlı tonlar',
    Color(0xFFE91E63),
  ),
  cocuk(
    'Anaokulu',
    'Cıvıl cıvıl turkuaz-sarı-pembe',
    Color(0xFF00ACC1),
  ),
  pastel(
    'Pastel',
    'Yumuşak mavi pastel tonlar',
    Color(0xFF8FA6C0),
  ),
  koyu(
    'Koyu',
    'Koyu zemin, mor vurgu',
    Color(0xFF9489F5),
    isDark: true,
  );

  const AppTheme(this.label, this.description, this.seed, {this.isDark = false});

  final String label;
  final String description;
  final Color seed;
  final bool isDark;
}

/// Uygulama genelinde paylaşılan tema kontrolü (kalıcı, config.json'da saklanır).
class AppThemeController extends ValueNotifier<AppTheme> {
  AppThemeController() : super(AppTheme.values.byName(AppConfig.themeName));

  void select(AppTheme theme) {
    value = theme;
    AppConfig.themeName = theme.name;
  }
}

final AppThemeController appThemeController = AppThemeController();

ThemeData buildAppTheme(AppTheme theme) {
  if (theme == AppTheme.cocuk) {
    return ThemeData(
      useMaterial3: true,
      colorScheme: _cocukScheme(),
      scaffoldBackgroundColor: const Color(0xFFFFFCF5),
      snackBarTheme: const SnackBarThemeData(behavior: SnackBarBehavior.floating),
      chipTheme: ChipThemeData(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        side: const BorderSide(color: Color(0xFFCBC0AF)),
      ),
    );
  }
  final scheme = ColorScheme.fromSeed(
    seedColor: theme.seed,
    brightness: theme.isDark ? Brightness.dark : Brightness.light,
  );
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: scheme.surface,
    snackBarTheme: const SnackBarThemeData(behavior: SnackBarBehavior.floating),
    chipTheme: ChipThemeData(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      side: BorderSide(color: scheme.outlineVariant),
    ),
  );
}

/// Anaokulu teması: yumuşak krem zemin üzerinde turkuaz + sarı + pembe.
/// Tüm metin rolleri, yazıların her parlak yüzeyde okunabilmesi için
/// koyu tonlarla (veya beyaz + yeterli kontrast) eşleştirilmiştir.
ColorScheme _cocukScheme() {
  return const ColorScheme.light(
    primary: Color(0xFF00695C),
    onPrimary: Colors.white,
    primaryContainer: Color(0xFFB2DFDB),
    onPrimaryContainer: Color(0xFF004940),
    secondary: Color(0xFFF9A825),
    onSecondary: Color(0xFF1E1500),
    secondaryContainer: Color(0xFFFFE082),
    onSecondaryContainer: Color(0xFF4B3200),
    tertiary: Color(0xFFC2185B),
    onTertiary: Colors.white,
    tertiaryContainer: Color(0xFFF8BBD0),
    onTertiaryContainer: Color(0xFF3E0022),
    error: Color(0xFFB3261E),
    onError: Colors.white,
    errorContainer: Color(0xFFF9DEDC),
    onErrorContainer: Color(0xFF410E0B),
    surface: Color(0xFFFFFCF5),
    onSurface: Color(0xFF302C28),
    surfaceContainerLowest: Colors.white,
    surfaceContainerLow: Color(0xFFFFFDF7),
    surfaceContainer: Color(0xFFF8F2E6),
    surfaceContainerHigh: Color(0xFFF3EDE1),
    surfaceContainerHighest: Color(0xFFEDE5D6),
    onSurfaceVariant: Color(0xFF5E5645),
    outline: Color(0xFF807867),
    outlineVariant: Color(0xFFCBC0AF),
    inverseSurface: Color(0xFF332D2B),
    onInverseSurface: Color(0xFFF6EEE0),
    inversePrimary: Color(0xFF6CD9CE),
    surfaceTint: Color(0xFF00695C),
    shadow: Colors.black,
    scrim: Colors.black,
  );
}

/// Tema uyumlu, okunabilir snackbar gösterir.
///
/// Arka plan ve metin rengi aynı şemanın eşleşen rollerinden seçilir
/// (error => onErrorContainer, normal => onSecondaryContainer), böylece
/// koyu/pastel temalarda da metin okunaklı kalır.
void showAppSnack(BuildContext context, String message, {bool error = false}) {
  final scheme = Theme.of(context).colorScheme;
  ScaffoldMessenger.of(context)
    ..clearSnackBars()
    ..showSnackBar(SnackBar(
      content: Text(
        message,
        style: TextStyle(color: error ? scheme.onErrorContainer : scheme.onSecondaryContainer),
      ),
      backgroundColor: error ? scheme.errorContainer : scheme.secondaryContainer,
    ));
}

/// Yüzey üstünde güvenle okunan 'başarı' rengi (açık/koyu duyarlı).
Color successColor(BuildContext context) {
  final dark = Theme.of(context).brightness == Brightness.dark;
  return dark ? const Color(0xFF7BD88F) : const Color(0xFF1B873B);
}

/// Yüzey üstünde güvenle okunan 'uyarı' rengi (açık/koyu duyarlı).
Color warningColor(BuildContext context) {
  final dark = Theme.of(context).brightness == Brightness.dark;
  return dark ? const Color(0xFFE8C05A) : const Color(0xFF8A6100);
}

/// Yüzey üstünde güvenle okunan 'hata' metin rengi (açık/koyu duyarlı).
Color dangerColor(BuildContext context) {
  final dark = Theme.of(context).brightness == Brightness.dark;
  return dark ? const Color(0xFFF2B8B5) : const Color(0xFFB3261E);
}

/// Uyarı/pano kutuları için yüzeyle uyumlu arka plan (açık/koyu duyarlı).
Color layerColor(BuildContext context, Color tone, {double alpha = 0.10}) {
  return tone.withValues(alpha: alpha);
}