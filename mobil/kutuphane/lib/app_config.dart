/// Uygulama geneli sabitler.
class AppConfig {
  AppConfig._();

  /// Öncelik sıralı sunucu adayları (mobil API kökü = origin, `/api` yok):
  ///   1) alan adı — SSL aktif olunca öne geçer
  ///   2) genel IP — geçici erişim
  /// Uygulama açılışta adayları paralel yoklar; ilk ulaşanı kullanır.
  static const List<String> serverCandidates = [
    'https://okulkitapligi.tr',
    'http://89.252.153.171',
  ];

  /// Derlemede tek adresle sınırlamak için (opsiyonel):
  ///   flutter run --dart-define=KUTUPHANE_SERVER=http://10.0.0.5:8000
  static const String _serverOverride = String.fromEnvironment(
    'KUTUPHANE_SERVER',
    defaultValue: '',
  );

  /// Geçerli aday listesi (override varsa tek adres).
  static List<String> get effectiveServerCandidates {
    final override = _serverOverride.trim();
    if (override.isNotEmpty) return [override];
    return serverCandidates;
  }

  /// Kayıtlı adres yoksa önerilen varsayılan adres (aday listesinin ilki).
  static String get defaultServerUrl => effectiveServerCandidates.first;
}
