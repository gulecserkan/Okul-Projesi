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
  test('401 alınca refresh ile yeniler ve isteği tekrarlar', () async {
    var kategoriCalls = 0;
    var refreshCalls = 0;

    final client = MockClient((request) async {
      final path = request.url.path;
      if (path.endsWith('/api/token/refresh/')) {
        refreshCalls++;
        return _json(
          '{"access":"new-access","refresh":"new-refresh","tip":"uye","role":"Öğrenci"}',
          200,
        );
      }
      if (path.endsWith('/api/kategoriler/')) {
        kategoriCalls++;
        if (kategoriCalls == 1) {
          return _json('{"detail":"expired"}', 401);
        }
        final auth =
            request.headers['Authorization'] ?? request.headers['authorization'];
        expect(auth, 'Bearer new-access');
        return _json('[]', 200);
      }
      return _json('{}', 404);
    });

    var unauthorized = false;
    final api = LibraryApiClient(
      baseUrl: 'http://example.test',
      tokens: const AuthTokens(
        accessToken: 'old',
        refreshToken: 'r1',
        tip: 'uye',
      ),
      httpClient: client,
      onUnauthorized: () => unauthorized = true,
    );

    final list = await api.fetchCategories();

    expect(list, isEmpty);
    expect(refreshCalls, 1);
    expect(kategoriCalls, 2);
    expect(unauthorized, isFalse);
  });

  test('refresh de başarısızsa onUnauthorized çağrılır', () async {
    final client = MockClient((request) async {
      final path = request.url.path;
      if (path.endsWith('/api/token/refresh/')) {
        return _json('{"detail":"invalid refresh"}', 401);
      }
      return _json('{"detail":"expired"}', 401);
    });

    var unauthorized = false;
    final api = LibraryApiClient(
      baseUrl: 'http://example.test',
      tokens: const AuthTokens(
        accessToken: 'old',
        refreshToken: 'r1',
        tip: 'uye',
      ),
      httpClient: client,
      onUnauthorized: () => unauthorized = true,
    );

    await expectLater(api.fetchCategories(), throwsA(isA<ApiException>()));
    expect(unauthorized, isTrue);
  });

  test('refresh token yoksa doğrudan onUnauthorized çağrılır', () async {
    final client = MockClient((request) async => _json('{"detail":"x"}', 401));

    var unauthorized = false;
    final api = LibraryApiClient(
      baseUrl: 'http://example.test',
      tokens: const AuthTokens(accessToken: 'old', refreshToken: '', tip: 'uye'),
      httpClient: client,
      onUnauthorized: () => unauthorized = true,
    );

    await expectLater(api.fetchCategories(), throwsA(isA<ApiException>()));
    expect(unauthorized, isTrue);
  });
}
