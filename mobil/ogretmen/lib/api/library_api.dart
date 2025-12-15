import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';

import '../models/auth.dart';
import '../models/book.dart';

class ApiException implements Exception {
  ApiException(this.message, {this.statusCode, this.details});

  final String message;
  final int? statusCode;
  final dynamic details;

  @override
  String toString() => "ApiException($statusCode): $message";
}

class HandshakeResult {
  const HandshakeResult({required this.ok, required this.message});

  final bool ok;
  final String message;
}

class LibraryApiClient {
  LibraryApiClient({
    required String baseUrl,
    AuthTokens? tokens,
    http.Client? httpClient,
  })  : _baseUrl = _normalizeBaseUrl(baseUrl),
        _tokens = tokens,
        _client = httpClient ?? http.Client();

  final http.Client _client;
  final String _baseUrl;
  AuthTokens? _tokens;

  String get baseUrl => _baseUrl;
  AuthTokens? get tokens => _tokens;

  void updateTokens(AuthTokens? tokens) {
    _tokens = tokens;
  }

  Future<HandshakeResult> handshake() async {
    try {
      final response = await _client
          .get(_uri("/api/health/"), headers: _headers(jsonBody: false))
          .timeout(const Duration(seconds: 6));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        final status = (data["status"] ?? "").toString().toLowerCase();
        if (status == "ok") {
          return const HandshakeResult(ok: true, message: "Sunucu hazır");
        }
        return HandshakeResult(ok: false, message: "Health endpoint beklenen yanıtı döndürmedi.");
      }

      return HandshakeResult(
        ok: false,
        message: "Sunucu yanıtı ${response.statusCode}",
      );
    } on TimeoutException {
      return const HandshakeResult(ok: false, message: "Sunucuya ulaşılamıyor (zaman aşımı)");
    } catch (e) {
      return HandshakeResult(ok: false, message: e.toString());
    }
  }

  Future<AuthTokens> login(String username, String password) async {
    final uri = _uri("/api/token/");
    final response = await _client.post(
      uri,
      headers: _headers(),
      body: jsonEncode({"username": username.trim(), "password": password}),
    );
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      final tokens = AuthTokens.fromJson(data);
      updateTokens(tokens);
      return tokens;
    }
    _throwError(response);
    throw ApiException("Giriş başarısız"); // fallback
  }

  Future<AuthTokens> refreshToken(String refreshToken) async {
    final uri = _uri("/api/token/refresh/");
    final response = await _client.post(
      uri,
      headers: _headers(),
      body: jsonEncode({"refresh": refreshToken}),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      final refreshed = AuthTokens.fromJson({
        ...data,
        "refresh": data["refresh"] ?? refreshToken,
      });
      updateTokens(refreshed);
      return refreshed;
    }
    _throwError(response);
    throw ApiException("Token yenileme başarısız");
  }

  Future<List<Category>> fetchCategories() async {
    final response = await _authorizedGet("/api/kategoriler/");
    final data = _unwrapList(response);
    return data.map((e) => Category.fromJson(e)).toList();
  }

  Future<List<Author>> fetchAuthors() async {
    final response = await _authorizedGet("/api/yazarlar/");
    final data = _unwrapList(response);
    return data.map((e) => Author.fromJson(e)).toList();
  }

  Future<List<String>> fetchShelfCodes() async {
    final response = await _authorizedGet("/api/raf-kodlari/");
    final decoded = jsonDecode(response.body);
    if (decoded is List) {
      return decoded.where((e) => e != null).map((e) => e.toString()).toList();
    }
    throw ApiException("Beklenmeyen raf kodu yanıtı");
  }

  Future<void> changePassword({
    required String currentPassword,
    required String newPassword,
    required String newPasswordConfirm,
  }) async {
    _ensureAuthorized();
    final uri = _uri("/api/change-password/");
    final response = await _client.post(
      uri,
      headers: _headers(),
      body: jsonEncode({
        "current_password": currentPassword,
        "new_password": newPassword,
        "new_password_confirm": newPasswordConfirm,
      }),
    );
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return;
    }
    _throwError(response);
  }

  Future<BookListResponse> fetchBooks({
    String? query,
    int? kategoriId,
    int? yazarId,
    int? page,
    int? minImageCount,
    int? maxImageCount,
    bool? hasDescription,
    String? shelfQuery,
    String? shelfPrefix,
    String? isbnQuery,
    String? barcodeQuery,
  }) async {
    final params = <String, String>{};
    if (query != null && query.isNotEmpty) params["q"] = query;
    if (kategoriId != null) params["kategori"] = "$kategoriId";
    if (yazarId != null) params["yazar"] = "$yazarId";
    if (page != null) params["page"] = "$page";
    if (minImageCount != null) params["min_image_count"] = "$minImageCount";
    if (maxImageCount != null) params["max_image_count"] = "$maxImageCount";
    if (hasDescription != null) params["aciklama_var"] = hasDescription ? "1" : "0";
    if (shelfQuery != null && shelfQuery.isNotEmpty) params["raf_query"] = shelfQuery;
    if (shelfPrefix != null && shelfPrefix.isNotEmpty) params["raf_prefix"] = shelfPrefix;
    if (isbnQuery != null && isbnQuery.isNotEmpty) params["isbn"] = isbnQuery;
    if (barcodeQuery != null && barcodeQuery.isNotEmpty) params["barkod"] = barcodeQuery;

    final response = await _authorizedGet("/api/kitaplar/", query: params);
    final decoded = jsonDecode(response.body);
    List<dynamic> items;
    int? count;

    if (decoded is Map<String, dynamic>) {
      items = (decoded["results"] as List?) ?? (decoded["data"] as List? ?? []);
      count = decoded["count"] is int ? decoded["count"] as int : null;
      if (items.isEmpty && decoded["results"] == null && decoded["data"] == null) {
        items = decoded.values.whereType<List>().firstOrNull ?? [];
      }
    } else if (decoded is List) {
      items = decoded;
    } else {
      throw ApiException("Beklenmeyen kitap listesi yanıtı");
    }

    final books = items.map((e) => BookSummary.fromJson(e as Map<String, dynamic>)).toList();
    return BookListResponse(books: books, totalCount: count ?? books.length);
  }

  Future<BookDetail> fetchBookDetail(int id) async {
    final response = await _authorizedGet("/api/kitaplar/$id/");
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    return BookDetail.fromJson(data);
  }

  Future<BookDetail> updateBook({
    required int id,
    String? aciklama,
    XFile? imageFile,
    int imageSlot = 1,
    int? deleteImageSlot,
  }) async {
    _ensureAuthorized();
    final uri = _uri("/api/kitaplar/$id/");

    // 1) Resim yükleme varsa multipart
    if (imageFile != null) {
      final request = http.MultipartRequest("PATCH", uri);
      request.headers.addAll(_headers(jsonBody: false, authorized: true));

      if (aciklama != null) {
        request.fields["aciklama"] = aciklama;
      }
      final slot = imageSlot.clamp(1, 5);
      final fieldName = "resim$slot";
      request.files.add(await http.MultipartFile.fromPath(fieldName, imageFile.path));

      final streamed = await request.send();
      final response = await http.Response.fromStream(streamed);
      if (response.statusCode >= 200 && response.statusCode < 300) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return BookDetail.fromJson(data);
      }
      _throwError(response);
      throw ApiException("Kitap güncellenemedi");
    }

    // 2) Sadece açıklama veya resim silme varsa JSON PATCH
    final body = <String, dynamic>{};
    if (aciklama != null) body["aciklama"] = aciklama;
    if (deleteImageSlot != null) {
      final slot = deleteImageSlot.clamp(1, 5);
      body["resim$slot"] = null;
    }

    final response = await _client.patch(
      uri,
      headers: _headers(),
      body: jsonEncode(body),
    );

    if (response.statusCode >= 200 && response.statusCode < 300) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return BookDetail.fromJson(data);
    }
    _throwError(response);
    throw ApiException("Kitap güncellenemedi");
  }

  Future<http.Response> _authorizedGet(
    String path, {
    Map<String, String>? query,
  }) async {
    _ensureAuthorized();
    final uri = _uri(path, query);
    final response = await _client.get(uri, headers: _headers(jsonBody: false, authorized: true));
    if (response.statusCode == 401) {
      throw ApiException("Oturum süresi doldu, lütfen tekrar giriş yapın", statusCode: 401);
    }
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return response;
    }
    _throwError(response);
    throw ApiException("İstek başarısız");
  }

  Map<String, String> _headers({bool jsonBody = true, bool authorized = false}) {
    final headers = <String, String>{
      "Accept": "application/json",
    };
    if (jsonBody) {
      headers["Content-Type"] = "application/json";
    }
    if (authorized || _tokens != null) {
      final token = _tokens?.accessToken ?? "";
      headers["Authorization"] = "Bearer $token";
    }
    return headers;
  }

  Uri _uri(String path, [Map<String, String>? query]) {
    final cleanedPath = path.startsWith("/") ? path : "/$path";
    final uri = Uri.parse("$_baseUrl$cleanedPath");
    if (query == null || query.isEmpty) return uri;
    final filteredQuery = <String, String>{};
    query.forEach((key, value) {
      if (value.isNotEmpty) {
        filteredQuery[key] = value;
      }
    });
    return uri.replace(queryParameters: filteredQuery);
  }

  void _ensureAuthorized() {
    if (_tokens == null || _tokens!.accessToken.isEmpty) {
      throw ApiException("Kimlik doğrulaması gerekiyor", statusCode: 401);
    }
  }

  void _throwError(http.Response response) {
    try {
      final data = jsonDecode(response.body);
      if (data is Map<String, dynamic>) {
        final detail = data["detail"] ?? data["error"] ?? data["message"];
        if (detail != null) {
          throw ApiException(detail.toString(), statusCode: response.statusCode, details: data);
        }
      }
    } catch (_) {
      // ignore parse errors
    }
    throw ApiException("Sunucu hatası (${response.statusCode})", statusCode: response.statusCode);
  }

  List<Map<String, dynamic>> _unwrapList(http.Response response) {
    final decoded = jsonDecode(response.body);
    if (decoded is List) {
      return decoded.cast<Map<String, dynamic>>();
    }
    if (decoded is Map<String, dynamic>) {
      if (decoded["results"] is List) {
        return (decoded["results"] as List).cast<Map<String, dynamic>>();
      }
      if (decoded["data"] is List) {
        return (decoded["data"] as List).cast<Map<String, dynamic>>();
      }
    }
    throw ApiException("Beklenmeyen yanıt formatı");
  }

  static String _normalizeBaseUrl(String input) {
    final trimmed = input.trim().replaceAll(RegExp(r"/+$"), "");
    if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
      return trimmed;
    }
    return "http://$trimmed";
  }
}

extension<T> on Iterable<T> {
  T? get firstOrNull => isEmpty ? null : first;
}
