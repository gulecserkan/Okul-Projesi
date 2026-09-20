/// Uygulama geneli sabitler.
class AppConfig {
  AppConfig._();

  /// Kayıtlı sunucu adresi yoksa önerilen varsayılan adres.
  ///
  /// Derleme sırasında değiştirilebilir:
  ///   flutter run --dart-define=KUTUPHANE_SERVER=http://10.0.0.5:8000
  static const String defaultServerUrl = String.fromEnvironment(
    'KUTUPHANE_SERVER',
    defaultValue: 'http://192.168.1.12:8000',
  );
}
