import 'package:shared_preferences/shared_preferences.dart';

import '../models/auth.dart';

class SessionStorage {
  static const _baseUrlKey = "server_base_url";
  static const _accessKey = "access_token";
  static const _refreshKey = "refresh_token";
  static const _fullNameKey = "user_full_name";
  static const _roleKey = "user_role";
  static const _tipKey = "user_tip";
  static const _uyeNoKey = "user_uye_no";
  static const _parolaDegistirKey = "user_parola_degistirilsin";
  static const _lastAuthKey = "last_auth_at";
  static const _themeKey = "app_theme";

  Future<String?> loadBaseUrl() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_baseUrlKey);
  }

  Future<void> saveBaseUrl(String url) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_baseUrlKey, url);
  }

  Future<void> clearBaseUrl() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_baseUrlKey);
  }

  Future<AuthTokens?> loadTokens() async {
    final prefs = await SharedPreferences.getInstance();
    final access = prefs.getString(_accessKey);
    final refresh = prefs.getString(_refreshKey);
    if (access == null || refresh == null) {
      return null;
    }
    return AuthTokens(
      accessToken: access,
      refreshToken: refresh,
      fullName: prefs.getString(_fullNameKey),
      role: prefs.getString(_roleKey),
      tip: prefs.getString(_tipKey) ?? "personel",
      uyeNo: prefs.getString(_uyeNoKey),
      parolaDegistirilsin: prefs.getBool(_parolaDegistirKey) ?? false,
    );
  }

  Future<void> saveTokens(AuthTokens tokens) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_accessKey, tokens.accessToken);
    await prefs.setString(_refreshKey, tokens.refreshToken);
    await prefs.setString(_fullNameKey, tokens.fullName ?? "");
    await prefs.setString(_roleKey, tokens.role ?? "");
    await prefs.setString(_tipKey, tokens.tip);
    await prefs.setString(_uyeNoKey, tokens.uyeNo ?? "");
    await prefs.setBool(_parolaDegistirKey, tokens.parolaDegistirilsin);
  }

  Future<DateTime?> loadLastAuthAt() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_lastAuthKey);
    if (raw == null || raw.isEmpty) return null;
    return DateTime.tryParse(raw);
  }

  Future<void> saveLastAuthAt(DateTime dt) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_lastAuthKey, dt.toIso8601String());
  }

  Future<void> clearTokens() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_accessKey);
    await prefs.remove(_refreshKey);
    await prefs.remove(_fullNameKey);
    await prefs.remove(_roleKey);
    await prefs.remove(_tipKey);
    await prefs.remove(_uyeNoKey);
    await prefs.remove(_parolaDegistirKey);
    await prefs.remove(_lastAuthKey);
  }

  Future<void> clearAll() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_baseUrlKey);
    await clearTokens();
  }

  Future<void> saveTheme(String themeName) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_themeKey, themeName);
  }

  Future<String?> loadTheme() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_themeKey);
  }
}
