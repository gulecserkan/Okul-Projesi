import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'package:kutuphane/api/library_api.dart';
import 'package:kutuphane/models/auth.dart';
import 'package:kutuphane/screens/loan_screen.dart';

import 'support/mock_api.dart';

const _tokens = AuthTokens(
  accessToken: 'acc',
  refreshToken: 'ref',
  role: 'personel',
  tip: 'personel',
);

Widget _screen({
  Map<String, dynamic>? fastQuery,
  int checkoutStatus = 201,
  Map<String, dynamic>? checkoutError,
  void Function(http.Request)? onRequest,
}) {
  return MaterialApp(
    home: LoanScreen(
      api: LibraryApiClient(
        baseUrl: 'http://test.local',
        tokens: _tokens,
        httpClient: routingClient(
          fastQueryResponse: fastQuery,
          checkoutStatus: checkoutStatus,
          checkoutError: checkoutError,
          onRequest: onRequest,
        ),
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
    expect(find.text('Ödünç Ver'), findsOneWidget);
  });

  testWidgets('pasif üye uyarısı gösterilir', (tester) async {
    await tester.pumpWidget(_screen(fastQuery: studentResult(aktif: false)));
    await _query(tester, '70001');

    expect(find.textContaining('Pasif üye'), findsOneWidget);
  });

  testWidgets('ödünç verme isteği doğru gönderilir', (tester) async {
    final bodies = <Map<String, dynamic>>[];
    await tester.pumpWidget(_screen(
      fastQuery: studentResult(no: '70001'),
      onRequest: (req) {
        if (req.url.path.endsWith('/api/checkout/')) {
          bodies.add(jsonDecode(req.body) as Map<String, dynamic>);
        }
      },
    ));
    await _query(tester, '70001');

    await tester.enterText(find.byType(TextField).at(1), 'KIT00042');
    await tester.tap(find.text('Ödünç Ver'));
    await tester.pumpAndSettle();

    expect(bodies, hasLength(1));
    expect(bodies.first['uye_no'], '70001');
    expect(bodies.first['barkod'], 'KIT00042');
    expect(find.text('Ödünç verildi.'), findsOneWidget);
  });

  testWidgets('ödünç hatası kullanıcıya gösterilir', (tester) async {
    await tester.pumpWidget(_screen(
      fastQuery: studentResult(),
      checkoutStatus: 400,
      checkoutError: {'error': 'Bu nüsha zaten ödünçte'},
    ));
    await _query(tester, '70001');

    await tester.enterText(find.byType(TextField).at(1), 'KIT00042');
    await tester.tap(find.text('Ödünç Ver'));
    await tester.pumpAndSettle();

    expect(find.text('Bu nüsha zaten ödünçte'), findsOneWidget);
  });

  testWidgets('mevcut nüsha için ödünç alanı gösterilir', (tester) async {
    await tester.pumpWidget(_screen(
      fastQuery: copyResult(baslik: 'Sefiller', barkod: 'KIT00009'),
    ));
    await _query(tester, 'KIT00009');

    expect(find.text('Sefiller'), findsOneWidget);
    expect(find.text('Üye no'), findsOneWidget);
    expect(find.text('Ödünç Ver'), findsOneWidget);
  });

  testWidgets('ödünçteki nüsha için iade alınır', (tester) async {
    final closePaths = <String>[];
    await tester.pumpWidget(_screen(
      fastQuery: copyResult(
        durum: 'oduncte',
        loan: {
          'id': 7,
          'uye': {'ad': 'Ayşe', 'soyad': 'Kaya', 'uye_no': '70001'},
          'penalty_preview': null,
        },
      ),
      onRequest: (req) {
        if (req.url.path.contains('/kapat/')) closePaths.add(req.url.path);
      },
    ));
    await _query(tester, 'KIT00009');

    expect(find.text('İade Al'), findsOneWidget);
    await tester.tap(find.text('İade Al'));
    await tester.pumpAndSettle();

    // Diyalogda iadeyi onayla.
    await tester.tap(find.text('İade Al').last);
    await tester.pumpAndSettle();

    expect(closePaths, contains('/api/oduncler/7/kapat/'));
    expect(find.textContaining('İade alındı'), findsOneWidget);
  });

  testWidgets('bulunamayan kayıt mesajı gösterilir', (tester) async {
    await tester.pumpWidget(_screen(fastQuery: {'type': 'not_found'}));
    await _query(tester, 'yok');

    expect(find.text('Kayıt bulunamadı.'), findsOneWidget);
  });
}
