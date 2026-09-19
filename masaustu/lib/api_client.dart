import 'dart:convert';

import 'package:http/http.dart' as http;

import 'config.dart';

/// Basit API istemcisi: 401 alınca refresh ile token yeniler ve isteği tekrarlar.
class ApiClient {
  ApiClient();

  String get baseUrl => AppConfig.apiBaseUrl;

  Uri _uri(String path) =>
      Uri.parse('$baseUrl/${path.replaceFirst(RegExp(r'^/+'), '')}');

  Map<String, String> _headers([String? accessToken]) => {
        'Content-Type': 'application/json',
        if (accessToken != null && accessToken.isNotEmpty)
          'Authorization': 'Bearer $accessToken',
      };

  Future<http.Response> _request(
    String method,
    String path, {
    Object? body,
    String? accessToken,
  }) async {
    final uri = _uri(path);
    final headers = _headers(accessToken);
    final payload = body == null ? null : jsonEncode(body);

    switch (method) {
      case 'GET':
        return http.get(uri, headers: headers);
      case 'POST':
        return http.post(uri, headers: headers, body: payload);
      case 'PUT':
        return http.put(uri, headers: headers, body: payload);
      case 'PATCH':
        return http.patch(uri, headers: headers, body: payload);
      case 'DELETE':
        return http.delete(uri, headers: headers);
      default:
        throw ArgumentError('Bilinmeyen method: $method');
    }
  }

  Future<http.Response> request(
    String method,
    String path, {
    Object? body,
    bool auth = false,
  }) async {
    final session = AppConfig.session;
    var resp = await _request(method, path,
        body: body, accessToken: auth ? session?.accessToken : null);

    // 401 → refresh dene, bir kez daha.
    if (auth && resp.statusCode == 401 && await tryRefresh()) {
      final newSession = AppConfig.session;
      resp = await _request(method, path,
          body: body, accessToken: newSession?.accessToken);
    }
    return resp;
  }

  Future<bool> tryRefresh() async {
    final session = AppConfig.session;
    if (session == null || session.refreshToken.isEmpty) return false;
    try {
      final resp = await http.post(
        _uri('token/refresh/'),
        headers: _headers(),
        body: jsonEncode({'refresh': session.refreshToken}),
      );
      if (resp.statusCode != 200) {
        AppConfig.session = null;
        return false;
      }
      final data = jsonDecode(resp.body) as Map<String, dynamic>;
      AppConfig.session = Session(
        accessToken: data['access'] as String? ?? '',
        refreshToken: session.refreshToken,
        username: session.username,
        fullName: data['full_name'] as String? ?? session.fullName,
        role: data['role'] as String? ?? session.role,
      );
      return true;
    } catch (_) {
      return false;
    }
  }
}

/// Sıra dışı JSON (backend hata mesajı) yanıtını yazıya çevirir.
String extractError(http.Response resp, {String fallback = 'İşlem başarısız'}) {
  try {
    final data = jsonDecode(resp.body);
    if (data is Map) {
      final detail = data['detail'];
      if (detail is String && detail.isNotEmpty) return detail;
      if (detail is List && detail.isNotEmpty) return detail.join(' ');
      if (data['error'] is String) return data['error'] as String;
      return data.values.first.toString();
    }
    if (data is String && data.isNotEmpty) return data;
  } catch (_) {}
  return fallback;
}