import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:kutuphane/api/library_api.dart';
import 'package:kutuphane/models/auth.dart';
import 'package:kutuphane/screens/query_screen.dart';

import 'support/mock_api.dart';

const _tokens = AuthTokens(
  accessToken: 'acc',
  refreshToken: 'ref',
  role: 'personel',
  tip: 'personel',
);

Widget _screen({
  Map<String, dynamic>? fastQuery,
  void Function()? onUnauthorized,
}) {
  return MaterialApp(
    home: QueryScreen(
      api: LibraryApiClient(
        baseUrl: 'http://test.local',
        tokens: _tokens,
        onUnauthorized: onUnauthorized,
        httpClient: routingClient(fastQueryResponse: fastQuery),
      ),
    ),
  );
}

Future<void> _query(WidgetTester tester, String q) async {
  await tester.enterText(find.byType(TextField).first, q);
  await tester.tap(find.text('Sorgula'));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('öğrenci sonucu ve aktif ödünçler gösterilir', (tester) async {
    await tester.pumpWidget(_screen(
      fastQuery: studentResult(
        ad: 'Ayşe',
        soyad: 'Kaya',
        activeLoans: [loanJson(baslik: 'Sefiller')],
      ),
    ));
    await _query(tester, '70001');

    expect(find.text('Ayşe Kaya'), findsOneWidget);
    expect(find.text('Sefiller'), findsOneWidget);
  });

  testWidgets('pasif üye uyarısı gösterilir', (tester) async {
    await tester.pumpWidget(_screen(fastQuery: studentResult(aktif: false)));
    await _query(tester, '70001');

    expect(find.textContaining('Pasif üye'), findsOneWidget);
  });

  testWidgets('ödünç ver / iade işlem butonları yoktur', (tester) async {
    await tester.pumpWidget(_screen(
      fastQuery: studentResult(
        ad: 'Ayşe',
        soyad: 'Kaya',
        activeLoans: [loanJson(baslik: 'Sefiller')],
      ),
    ));
    await _query(tester, '70001');

    expect(find.text('Ödünç Ver'), findsNothing);
    expect(find.text('İade'), findsNothing);
    expect(find.textContaining('masaüstü uygulamasında'), findsOneWidget);
  });

  testWidgets('ödünçteki nüsha ve tutan üye gösterilir', (tester) async {
    await tester.pumpWidget(_screen(
      fastQuery: copyResult(
        baslik: 'Sefiller',
        durum: 'oduncte',
        loan: {
          'id': 7,
          'uye': {'ad': 'Ayşe', 'soyad': 'Kaya', 'uye_no': '70001'},
        },
      ),
    ));
    await _query(tester, 'KIT00009');

    expect(find.text('Sefiller'), findsOneWidget);
    expect(find.text('Durum: Ödünçte'), findsOneWidget);
    expect(find.textContaining('Ayşe Kaya'), findsOneWidget);
  });

  testWidgets('mevcut nüsha durumu gösterilir', (tester) async {
    await tester.pumpWidget(_screen(
      fastQuery: copyResult(baslik: 'Sefiller', barkod: 'KIT00009'),
    ));
    await _query(tester, 'KIT00009');

    expect(find.text('Durum: Mevcut'), findsOneWidget);
    expect(find.text('Ödünç Ver'), findsNothing);
  });

  testWidgets('bulunamayan kayıt mesajı gösterilir', (tester) async {
    await tester.pumpWidget(_screen(fastQuery: {'type': 'not_found'}));
    await _query(tester, 'yok');

    expect(find.text('Kayıt bulunamadı.'), findsOneWidget);
  });

  testWidgets('boş sorguda uyarı gösterilir', (tester) async {
    await tester.pumpWidget(_screen(fastQuery: studentResult()));
    await tester.tap(find.text('Sorgula'));
    await tester.pump();

    expect(find.text('Barkod veya üye no girin.'), findsOneWidget);
  });
}