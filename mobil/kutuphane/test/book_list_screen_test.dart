import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'package:kutuphane/api/library_api.dart';
import 'package:kutuphane/models/auth.dart';
import 'package:kutuphane/screens/book_list_screen.dart';
import 'package:kutuphane/theme/app_theme.dart';

import 'support/mock_api.dart';

const _tokens = AuthTokens(
  accessToken: 'acc',
  refreshToken: 'ref',
  role: 'personel',
  tip: 'personel',
);

Widget _screen({
  List<Map<String, dynamic>> books = const [],
  void Function(http.Request)? onRequest,
}) {
  return MaterialApp(
    home: BookListScreen(
      baseUrl: 'http://test.local',
      tokens: _tokens,
      onLogout: () async {},
      onChangeServer: () async {},
      currentTheme: AppTheme.defaultLight,
      onThemeChange: (_) async {},
      api: LibraryApiClient(
        baseUrl: 'http://test.local',
        tokens: _tokens,
        httpClient: routingClient(
          books: books,
          categories: const [
            {'id': 1, 'ad': 'Roman'},
          ],
          authors: const [
            {'id': 1, 'ad_soyad': 'Victor Hugo'},
          ],
          shelfCodes: const ['A-1'],
          onRequest: onRequest,
        ),
      ),
    ),
  );
}

void main() {
  testWidgets('kitap listesi yüklenir', (tester) async {
    await tester.pumpWidget(_screen(books: [bookJson(baslik: 'Sefiller')]));
    await tester.pumpAndSettle();

    expect(find.text('Sefiller'), findsOneWidget);
  });

  testWidgets('sonuç yoksa boş durum gösterilir', (tester) async {
    await tester.pumpWidget(_screen());
    await tester.pumpAndSettle();

    expect(find.text('Kriterlere uyan kitap bulunamadı.'), findsOneWidget);
  });

  testWidgets('arama sorgusu sunucuya iletilir', (tester) async {
    final queries = <String?>[];
    await tester.pumpWidget(_screen(
      books: [bookJson(baslik: 'Sefiller')],
      onRequest: (req) {
        if (req.url.path.endsWith('/api/kitaplar/')) {
          queries.add(req.url.queryParameters['q']);
        }
      },
    ));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField).first, 'sefiller');
    await tester.tap(find.byIcon(Icons.check));
    await tester.pumpAndSettle();

    expect(queries.contains('sefiller'), isTrue);
  });
}
