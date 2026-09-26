import 'dart:convert';
import 'dart:io';

/// Uygulama yapılandırması + oturum (token) saklaması.
///
/// Masaüstünde ~/.config/kutuphane_masaustu/config.json içinde tutulur
/// (eski PyQt sürümü gibi dosya tabanlı).
class AppConfig {
  static const String defaultBaseUrl = 'http://127.0.0.1:8000/api';

  /// Uygulama sürümü (derlemede `--dart-define=APP_VERSION=...` ile verilir).
  static const String appVersion =
      String.fromEnvironment('APP_VERSION', defaultValue: '0.1.0');

  /// Sürüm kodu (derlemede `--dart-define=APP_VERSION_CODE=...`).
  static const int appVersionCode =
      int.fromEnvironment('APP_VERSION_CODE', defaultValue: 1);

  static String get _dirPath =>
      '${Platform.environment['HOME'] ?? '.'}/.config/kutuphane_masaustu';

  static File get _file => File('$_dirPath/config.json');

  static Map<String, dynamic> _read() {
    try {
      if (_file.existsSync()) {
        return jsonDecode(_file.readAsStringSync()) as Map<String, dynamic>;
      }
    } catch (_) {}
    return {};
  }

  static void _write(Map<String, dynamic> data) {
    Directory(_dirPath).createSync(recursive: true);
    _file.writeAsStringSync(jsonEncode(data));
  }

  static String get apiBaseUrl {
    final data = _read();
    final url = (data['api']?['base_url'] as String?)?.trim();
    return (url == null || url.isEmpty) ? defaultBaseUrl : url;
  }

  static set apiBaseUrl(String url) {
    final data = _read();
    data['api'] = {'base_url': url.trim()};
    _write(data);
  }

  /// Seçili tema adı (AppTheme.name). Varsayılan: 'standart'.
  static String get themeName {
    final data = _read();
    final name = data['theme'] as String?;
    return (name == null || name.isEmpty) ? 'standart' : name;
  }

  static set themeName(String value) {
    final data = _read();
    data['theme'] = value;
    _write(data);
  }

  /// Sol menü açık mı? (varsayılan: açık)
  static bool get menuAcik {
    final data = _read();
    return data['menu_acik'] as bool? ?? true;
  }

  static set menuAcik(bool value) {
    final data = _read();
    data['menu_acik'] = value;
    _write(data);
  }

  static Session? get session {
    final data = _read();
    final s = data['session'];
    if (s is! Map) return null;
    return Session(
      accessToken: s['access'] as String? ?? '',
      refreshToken: s['refresh'] as String? ?? '',
      username: s['username'] as String? ?? '',
      fullName: s['full_name'] as String? ?? '',
      role: s['role'] as String? ?? '',
      tip: s['tip'] as String? ?? 'personel',
    );
  }

  static set session(Session? session) {
    final data = _read();
    if (session == null) {
      data.remove('session');
    } else {
      data['session'] = {
        'access': session.accessToken,
        'refresh': session.refreshToken,
        'username': session.username,
        'full_name': session.fullName,
        'role': session.role,
        'tip': session.tip,
      };
    }
    _write(data);
  }
}

class Session {
  final String accessToken;
  final String refreshToken;
  final String username;
  final String fullName;
  final String role;

  /// K9: hesap tipi — 'personel' (operatör/admin) veya 'uye'; masaüstü yalnız personel.
  final String tip;

  const Session({
    required this.accessToken,
    required this.refreshToken,
    required this.username,
    this.fullName = '',
    this.role = '',
    this.tip = 'personel',
  });

  bool get isValid => accessToken.isNotEmpty;

  bool get isPersonel => tip != 'uye';
}