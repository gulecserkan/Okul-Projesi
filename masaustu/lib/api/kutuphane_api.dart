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

  /// Sayfalı liste sonucu.
  Future<Page<Map<String, dynamic>>> _page(
    String path, {
    int page = 1,
    int pageSize = 50,
    String? q,
  }) async {
    final params = <String, String>{
      'page': '$page',
      'page_size': '$pageSize',
      if (q != null && q.isNotEmpty) 'q': q,
    };
    final resp = await _client.request(
      'GET',
      '$path?${Uri(queryParameters: params).query}',
      auth: true,
    );
    if (resp.statusCode != 200) {
      return const Page(items: [], total: 0);
    }
    final data = jsonDecode(resp.body);
    final items = data is List
        ? data.whereType<Map<String, dynamic>>().toList()
        : ((data['results'] as List<dynamic>?) ?? const [])
            .whereType<Map<String, dynamic>>()
            .toList();
    final total = data is Map ? (data['count'] as int? ?? items.length) : items.length;
    final hasNext = data is Map && (data['next'] as String?)?.isNotEmpty == true;
    return Page(
      items: items,
      total: total,
      nextPage: hasNext ? page + 1 : null,
    );
  }

  Future<Page<Ogrenci>> studentsPage({
    int page = 1,
    int pageSize = 50,
    String? q,
  }) async {
    final res = await _page('ogrenciler', page: page, pageSize: pageSize, q: q);
    return Page(
      items: res.items.map(Ogrenci.fromJson).toList(),
      total: res.total,
      nextPage: res.nextPage,
    );
  }

  Future<Page<Kitap>> booksPage({
    int page = 1,
    int pageSize = 50,
    String? q,
  }) async {
    final res = await _page('kitaplar', page: page, pageSize: pageSize, q: q);
    return Page(
      items: res.items.map(Kitap.fromJson).toList(),
      total: res.total,
      nextPage: res.nextPage,
    );
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

  Future<List<Nusha>> copies(int kitapId) async {
    final resp = await _client.request('GET', 'nushalar/?kitap=$kitapId', auth: true);
    if (resp.statusCode != 200) return const [];
    return _extractList(resp)
        .whereType<Map<String, dynamic>>()
        .map(Nusha.fromJson)
        .toList();
  }

  Future<List<OduncKaydi>> studentHistory(String ogrenciNo) async {
    final resp = await _client
        .request('GET', 'student-history/$ogrenciNo/', auth: true);
    if (resp.statusCode != 200) return const [];
    return _extractList(resp)
        .whereType<Map<String, dynamic>>()
        .map(OduncKaydi.fromJson)
        .toList();
  }

  Future<PenaltySummary> studentPenalties(String ogrenciNo) async {
    final resp = await _client
        .request('GET', 'student-penalties/$ogrenciNo/', auth: true);
    if (resp.statusCode != 200) return const PenaltySummary();
    try {
      return PenaltySummary.fromJson(
          jsonDecode(resp.body) as Map<String, dynamic>);
    } catch (_) {
      return const PenaltySummary();
    }
  }
}

/// Sayfalı liste sonucu: satırlar + toplam kayıt + sonraki sayfa (yoksa null).
class Page<T> {
  final List<T> items;
  final int total;
  final int? nextPage;

  const Page({required this.items, required this.total, this.nextPage});
}