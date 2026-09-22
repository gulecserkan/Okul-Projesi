import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'package:kutuphane/api/library_api.dart';
import 'package:kutuphane/models/auth.dart';
import 'package:kutuphane/screens/login_screen.dart';

import 'support/mock_api.dart';

LibraryApiClient _client(http.Client mock) =>
    LibraryApiClient(baseUrl: 'http://test.local', httpClient: mock);

Widget _screen({
  required Future<void> Function(AuthTokens) onAuthenticated,
  String? initialMessage,
  http.Client? mock,
}) {
  return MaterialApp(
    home: LoginScreen(
      baseUrl: 'http://test.local',
      onAuthenticated: onAuthenticated,
      onChangeServer: () async {},
      initialMessage: initialMessage,
      api: _client(mock ?? routingClient()),
    ),
  );
}

void main() {
  testWidgets('giriş alanları ve butonu görünür', (tester) async {
    await tester.pumpWidget(_screen(onAuthenticated: (_) async {}));

    expect(find.text('Kullanıcı adı'), findsOneWidget);
    expect(find.text('Şifre'), findsOneWidget);
    expect(find.text('Giriş yap'), findsOneWidget);
  });

  testWidgets('boş alanlarda uyarı verir', (tester) async {
    await tester.pumpWidget(_screen(onAuthenticated: (_) async {}));

    await tester.tap(find.text('Giriş yap'));
    await tester.pump();

    expect(find.text('Kullanıcı adı ve şifre zorunlu.'), findsOneWidget);
  });

  testWidgets('başarılı girişte token döner', (tester) async {
    AuthTokens? captured;
    await tester.pumpWidget(_screen(onAuthenticated: (t) async => captured = t));

    await tester.enterText(find.byType(TextField).at(0), 'admin');
    await tester.enterText(find.byType(TextField).at(1), 'gizli');
    await tester.tap(find.text('Giriş yap'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(captured, isNotNull);
    expect(captured!.accessToken, 'acc');
    expect(captured!.tip, 'uye');
  });

  testWidgets('personel hesabı mobilde reddedilir', (tester) async {
    await tester.pumpWidget(_screen(
      onAuthenticated: (_) async {},
      mock: routingClient(
        loginResponse: {
          'access': 'acc',
          'refresh': 'ref',
          'full_name': 'Personel',
          'role': 'personel',
          'tip': 'personel',
        },
      ),
    ));

    await tester.enterText(find.byType(TextField).at(0), 'person');
    await tester.enterText(find.byType(TextField).at(1), 'gizli');
    await tester.tap(find.text('Giriş yap'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.textContaining('masaüstü'), findsOneWidget);
  });

  testWidgets('hatalı girişte sunucu mesajı gösterilir', (tester) async {
    await tester.pumpWidget(_screen(
      onAuthenticated: (_) async {},
      mock: routingClient(
        loginStatus: 401,
        loginResponse: {'detail': 'Kimlik bilgileri hatalı'},
      ),
    ));

    await tester.enterText(find.byType(TextField).at(0), 'admin');
    await tester.enterText(find.byType(TextField).at(1), 'yanlis');
    await tester.tap(find.text('Giriş yap'));
    await tester.pumpAndSettle();

    expect(find.text('Kimlik bilgileri hatalı'), findsOneWidget);
  });

  testWidgets('oturum süresi mesajı gösterilir', (tester) async {
    await tester.pumpWidget(_screen(
      onAuthenticated: (_) async {},
      initialMessage: 'Oturum süresi doldu, lütfen tekrar giriş yapın.',
    ));

    expect(find.textContaining('Oturum süresi doldu'), findsOneWidget);
  });

  testWidgets('Şifrem yok bilgilendirmesi gösterilir', (tester) async {
    await tester.pumpWidget(_screen(onAuthenticated: (_) async {}));

    expect(find.text('Şifrem yok'), findsOneWidget);

    await tester.tap(find.text('Şifrem yok'));
    await tester.pumpAndSettle();

    expect(find.textContaining('kütüphane sorumlusu'), findsOneWidget);
    expect(find.text('Tamam'), findsOneWidget);
  });
}
