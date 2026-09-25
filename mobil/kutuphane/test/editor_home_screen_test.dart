import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:kutuphane/api/library_api.dart';
import 'package:kutuphane/models/auth.dart';
import 'package:kutuphane/screens/book_list_screen.dart';
import 'package:kutuphane/screens/editor_home_screen.dart';
import 'package:kutuphane/screens/uye_home_screen.dart';
import 'package:kutuphane/theme/app_theme.dart';

import 'support/mock_api.dart';

const _editorTokens = AuthTokens(
  accessToken: 'acc',
  refreshToken: 'ref',
  role: 'editor',
  tip: 'uye',
  uyeNo: '100',
  fullName: 'Editör Öğretmen',
);

Widget _screen() {
  return MaterialApp(
    home: EditorHomeScreen(
      baseUrl: 'http://test.local',
      tokens: _editorTokens,
      onLogout: () async {},
      currentTheme: AppTheme.defaultLight,
      onThemeChange: (_) async {},
      api: LibraryApiClient(
        baseUrl: 'http://test.local',
        tokens: _editorTokens,
        httpClient: routingClient(
          books: [bookJson(baslik: 'Sefiller')],
          categories: const [
            {'id': 1, 'ad': 'Roman'},
          ],
          authors: const [
            {'id': 1, 'ad_soyad': 'Victor Hugo'},
          ],
        ),
      ),
    ),
  );
}

Future<void> _pump(WidgetTester tester) async {
  tester.view.physicalSize = const Size(1200, 2400);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(_screen());
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('editör ekranı iki bölüm sunar: Editör + Üye', (tester) async {
    await _pump(tester);

    expect(find.byType(BookListScreen), findsOneWidget);
    expect(find.byType(UyeHomeScreen, skipOffstage: false), findsOneWidget);
    expect(find.text('Editör'), findsOneWidget);
    expect(find.text('Üye'), findsOneWidget);
  });

  testWidgets('varsayılan bölüm editördür (üst başlık üye adı)', (tester) async {
    await _pump(tester);
    expect(find.text('Editör Öğretmen'), findsOneWidget);
  });

  testWidgets('üye bölümüne geçilince üç sekme görünür', (tester) async {
    await _pump(tester);

    await tester.tap(find.text('Üye'));
    await tester.pumpAndSettle();

    expect(find.text('Kitaplar'), findsOneWidget);
    expect(find.text('Ödünçlerim'), findsOneWidget);
    expect(find.text('Ceza'), findsOneWidget);
  });
}
