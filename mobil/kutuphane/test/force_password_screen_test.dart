import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:kutuphane/api/library_api.dart';
import 'package:kutuphane/models/auth.dart';
import 'package:kutuphane/screens/force_password_screen.dart';

import 'support/mock_api.dart';

const _tokens = AuthTokens(
  accessToken: 'acc',
  refreshToken: 'ref',
  tip: 'uye',
  uyeNo: '100',
  parolaDegistirilsin: true,
);

Widget _screen({required Future<void> Function() onDone, int status = 200}) {
  return MaterialApp(
    home: ForcePasswordScreen(
      baseUrl: 'http://test.local',
      tokens: _tokens,
      onDone: onDone,
      api: LibraryApiClient(
        baseUrl: 'http://test.local',
        tokens: _tokens,
        httpClient: routingClient(changePasswordStatus: status),
      ),
    ),
  );
}

void main() {
  testWidgets('şifre değiştirme alanları görünür', (tester) async {
    await tester.pumpWidget(_screen(onDone: () async {}));

    expect(find.text('Mevcut şifre'), findsOneWidget);
    expect(find.text('Yeni şifre'), findsOneWidget);
    expect(find.text('Yeni şifre (tekrar)'), findsOneWidget);
    expect(find.text('Şifreyi Değiştir'), findsOneWidget);
  });

  testWidgets('boş alanlarda uyarı verir', (tester) async {
    await tester.pumpWidget(_screen(onDone: () async {}));

    await tester.tap(find.text('Şifreyi Değiştir'));
    await tester.pump();

    expect(find.text('Tüm alanlar zorunludur.'), findsOneWidget);
  });

  testWidgets('uyuşmayan şifrelerde uyarı verir', (tester) async {
    await tester.pumpWidget(_screen(onDone: () async {}));

    await tester.enterText(find.byType(TextField).at(0), 'eski');
    await tester.enterText(find.byType(TextField).at(1), 'yeni1');
    await tester.enterText(find.byType(TextField).at(2), 'yeni2');
    await tester.tap(find.text('Şifreyi Değiştir'));
    await tester.pump();

    expect(find.text('Yeni şifreler uyuşmuyor.'), findsOneWidget);
  });

  testWidgets('başarılı değişimde onDone çağrılır', (tester) async {
    var done = false;
    await tester.pumpWidget(_screen(onDone: () async => done = true));

    await tester.enterText(find.byType(TextField).at(0), 'eski');
    await tester.enterText(find.byType(TextField).at(1), 'yeni');
    await tester.enterText(find.byType(TextField).at(2), 'yeni');
    await tester.tap(find.text('Şifreyi Değiştir'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(done, isTrue);
  });
}
