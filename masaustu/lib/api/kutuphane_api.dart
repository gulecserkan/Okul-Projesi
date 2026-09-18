import 'dart:convert';

import 'package:http/http.dart' as http;

import '../api_client.dart';
import '../models.dart';

/// Liste ve arama uç noktaları (öğrenci / kitap / sınıf).
class KutuphaneApi {
  final ApiClient _client;

  KutuphaneApi({ApiClient? client}) : _client = client ?? ApiClient();

  static List<dynamic> _extractList(http.Response resp) {
    final data = jsonDecode(resp.body);
    if (data is List) return data;
    if (data is Map && data['results'] is List) return data['results'] as List;
    return const [];
  }

  /// Tüm sayfaları çeker (koşullu sayfalama: sayfa yoksa düz dizi döner).
  Future<List<dynamic>> _fetchAllPages(String path) async {
    final results = <dynamic>[];
    var url = path;
    for (var i = 0; i < 50; i++) {
      final resp = await _client.request('GET', url, auth: true);
      if (resp.statusCode != 200) break;
      final data = jsonDecode(resp.body);
      if (data is List) {
        results.addAll(data);
        break;
      }
      if (data is Map) {
        results.addAll(data['results'] as List<dynamic>? ?? const []);
        final next = data['next'] as String?;
        if (next == null || next.isEmpty) break;
        if (i == 49) break;
        url = Uri.parse(next).path + (Uri.parse(next).query.isEmpty ? '' : '?${Uri.parse(next).query}');
      }
    }
    return results;
  }

  Future<List<Ogrenci>> students() async {
    final data = await _fetchAllPages('ogrenciler/');
    return data
        .whereType<Map<String, dynamic>>()
        .map(Ogrenci.fromJson)
        .toList();
  }

  Future<List<Kitap>> books() async {
    final data = await _fetchAllPages('kitaplar/');
    return data
        .whereType<Map<String, dynamic>>()
        .map(Kitap.fromJson)
        .toList();
  }

  Future<List<Sinif>> siniflar() async {
    final resp = await _client.request('GET', 'siniflar/', auth: true);
    if (resp.statusCode != 200) return const [];
    return _extractList(resp)
        .whereType<Map<String, dynamic>>()
        .map(Sinif.fromJson)
        .toList();
  }
}