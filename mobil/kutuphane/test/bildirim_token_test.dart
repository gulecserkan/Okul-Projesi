import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:kutuphane/api/library_api.dart';
import 'package:kutuphane/models/auth.dart';

http.Response _json(Object body, int status) => http.Response(
      body is String ? body : '$body',
      status,
      headers: const {'content-type': 'application/json; charset=utf-8'},
    );

void main() {
  const tokens = AuthTokens(
    accessToken: 'acc',
    refreshToken: 'ref',
    tip: 'uye',
  );

  test('K15: token POST uca gonderilir', () async {
    String? method;
    String? path;
    Map<String, dynamic>? govde;

    final client = MockClient((request) async {
      method = request.method;
      path = request.url.path;
      govde = jsonDecode(request.body) as Map<String, dynamic>;
      return _json('{"ok":true}', 200);
    });

    final api = LibraryApiClient(
      baseUrl: 'http://example.test',
      tokens: tokens,
      httpClient: client,
    );
    await api.registerBildirimToken('tok-1');

    expect(method, 'POST');
    expect(path, '/api/mobil/bildirim-token/');
    expect(govde!['token'], 'tok-1');
    expect(govde!['platform'], 'android');
  });

  test('K15: token DELETE uca gonderilir', () async {
    String? method;
    Map<String, dynamic>? govde;

    final client = MockClient((request) async {
      method = request.method;
      govde = jsonDecode(request.body) as Map<String, dynamic>;
      return _json('{"ok":true}', 200);
    });

    final api = LibraryApiClient(
      baseUrl: 'http://example.test',
      tokens: tokens,
      httpClient: client,
    );
    await api.deleteBildirimToken('tok-1');

    expect(method, 'DELETE');
    expect(govde!['token'], 'tok-1');
  });

  test('K15: hata yanitinda ApiException firlatilir', () async {
    final client = MockClient((request) async => _json('{"detail":"yok"}', 400));
    final api = LibraryApiClient(
      baseUrl: 'http://example.test',
      tokens: tokens,
      httpClient: client,
    );
    await expectLater(
      api.registerBildirimToken('tok-1'),
      throwsA(isA<ApiException>()),
    );
  });
}
