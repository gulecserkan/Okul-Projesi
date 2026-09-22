import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config.dart';

/// Kimlik doğrulama (login / logout / sağlık kontrolü).
class AuthApi {
  final String baseUrl;

  AuthApi({String? baseUrl}) : baseUrl = baseUrl ?? AppConfig.apiBaseUrl;

  Future<bool> healthCheck() async {
    try {
      final resp = await http
          .get(Uri.parse('$baseUrl/health/'))
          .timeout(const Duration(seconds: 4));
      return resp.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  /// Başarılıysa oturumu kaydedip true döner.
  Future<({bool ok, String error})> login(String username, String password) async {
    try {
      final resp = await http
          .post(
            Uri.parse('$baseUrl/token/'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'username': username, 'password': password}),
          )
          .timeout(const Duration(seconds: 8));
      if (resp.statusCode == 200) {
        final data = jsonDecode(resp.body) as Map<String, dynamic>;
        // K9: masaüstü yalnız personel/admin hesabına açık (üye hesapları mobilde).
        final tip = (data['tip'] ?? 'personel').toString();
        if (tip != 'personel') {
          return (
            ok: false,
            error: 'Bu hesap üye (öğrenci/öğretmen/editör) uygulamasına aittir; '
                'masaüstüne yalnız personel/admin girişi yapabilir.',
          );
        }
        AppConfig.session = Session(
          accessToken: data['access'] as String? ?? '',
          refreshToken: data['refresh'] as String? ?? '',
          username: username,
          fullName: data['full_name'] as String? ?? '',
          role: data['role'] as String? ?? '',
          tip: tip,
        );
        return (ok: true, error: '');
      }
      final detail = _detail(resp.body);
      return (ok: false, error: detail);
    } catch (_) {
      return (ok: false, error: 'Sunucuya ulaşılamadı. Sunucu adresini kontrol edin.');
    }
  }

  String _detail(String body) {
    try {
      final data = jsonDecode(body);
      if (data is Map) {
        final d = data['detail'] ?? data['error'];
        if (d is String && d.isNotEmpty) return d;
        if (d is List) return d.join(' ');
      }
    } catch (_) {}
    return 'Kullanıcı adı veya şifre hatalı.';
  }
}