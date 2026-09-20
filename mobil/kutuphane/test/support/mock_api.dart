import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

/// UTF-8 kodlu JSON yanıtı üretir (Türkçe karakterler için charset şart).
http.Response jsonResponse(Object? data, {int status = 200}) => http.Response(
      jsonEncode(data),
      status,
      headers: const {'content-type': 'application/json; charset=utf-8'},
    );

/// Yol tabanlı sahte API istemcisi. Testler gerçek ağa çıkmaz.
MockClient routingClient({
  List<Map<String, dynamic>>? books,
  int? booksCount,
  List<Map<String, dynamic>> categories = const [],
  List<Map<String, dynamic>> authors = const [],
  List<String> shelfCodes = const [],
  List<Map<String, dynamic>> loans = const [],
  Map<String, dynamic>? bookDetail,
  Map<String, dynamic>? loginResponse,
  int loginStatus = 200,
  int changePasswordStatus = 200,
  int healthStatus = 200,
  void Function(http.Request request)? onRequest,
}) {
  return MockClient((request) async {
    onRequest?.call(request);
    final path = request.url.path;

    if (path.endsWith('/api/health/')) {
      return healthStatus == 200
          ? jsonResponse({'status': 'ok'})
          : jsonResponse({'detail': 'hata'}, status: healthStatus);
    }
    if (path.endsWith('/api/token/')) {
      return jsonResponse(
        loginResponse ??
            {
              'access': 'acc',
              'refresh': 'ref',
              'full_name': 'Test Kullanıcı',
              'role': 'personel',
              'tip': 'personel',
            },
        status: loginStatus,
      );
    }
    if (path.endsWith('/api/token/refresh/')) {
      return jsonResponse({'access': 'acc', 'refresh': 'ref'});
    }
    if (path.endsWith('/api/change-password/')) {
      return jsonResponse({'ok': true}, status: changePasswordStatus);
    }
    if (path.endsWith('/api/kategoriler/')) return jsonResponse(categories);
    if (path.endsWith('/api/yazarlar/')) return jsonResponse(authors);
    if (path.endsWith('/api/raf-kodlari/')) return jsonResponse(shelfCodes);
    if (path.contains('/api/uye-gecmis/')) return jsonResponse(loans);
    if (path.contains('/api/uye-ceza/')) return jsonResponse({});
    if (RegExp(r'/api/kitaplar/\d+/?$').hasMatch(path)) {
      return jsonResponse(bookDetail ?? {'id': 1, 'baslik': 'Detay Kitap'});
    }
    if (path.endsWith('/api/kitaplar/')) {
      final list = books ?? const <Map<String, dynamic>>[];
      return jsonResponse({'count': booksCount ?? list.length, 'results': list});
    }
    return jsonResponse({'detail': 'bulunamadı: $path'}, status: 404);
  });
}

Map<String, dynamic> bookJson({
  int id = 1,
  String baslik = 'Sefiller',
  String? yazar = 'Victor Hugo',
  String? kategori = 'Roman',
  int yayinYili = 1862,
}) {
  return {
    'id': id,
    'baslik': baslik,
    'yazar': yazar == null ? null : {'ad_soyad': yazar},
    'kategori': kategori == null ? null : {'ad': kategori},
    'yayin_yili': yayinYili,
    'image_count': 0,
  };
}
