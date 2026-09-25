import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:kutuphane/api/library_api.dart';
import 'package:kutuphane/models/auth.dart';
import 'package:kutuphane/screens/login_screen.dart';

import 'support/mock_api.dart';

LibraryApiClient _client(http.Client mock) =>
    LibraryApiClient(baseUrl: 'http://test.local', httpClient: mock);

Widget _screen({
  required Future<void> Function(AuthTokens) onAuthenticated,
  String? initialMessage,
  bool initialRememberMe = false,
  Future<void> Function(bool)? onRememberMeChanged,
  http.Client? mock,
}) {
  return MaterialApp(
    home: LoginScreen(
      baseUrl: 'http://test.local',
      onAuthenticated: onAuthenticated,
      onChangeServer: () async {},
      initialMessage: initialMessage,
      initialRememberMe: initialRememberMe,
      onRememberMeChanged: onRememberMeChanged,
      api: _client(mock ?? routingClient()),
    ),
  );
}

void main() {
  testWidgets('giriş alanları ve butonu görünür', (tester) async {
    await tester.pumpWidget(_screen(onAuthenticated: (_) async {}));

    expect(find.text('Üye No'), findsOneWidget);
    expect(find.text('Şifre'), findsOneWidget);
    expect(find.text('Giriş yap'), findsOneWidget);
  });

  testWidgets('boş alanlarda uyarı verir', (tester) async {
    await tester.pumpWidget(_screen(onAuthenticated: (_) async {}));

    await tester.tap(find.text('Giriş yap'));
    await tester.pump();

    expect(find.text('Üye no ve şifre zorunlu.'), findsOneWidget);
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

  testWidgets('sunucu erişilebilirse sunucu değiştir ayarı belirgin değildir', (tester) async {
    await tester.pumpWidget(_screen(onAuthenticated: (_) async {}));
    await tester.pumpAndSettle();

    expect(find.text('Sunucu değiştir'), findsNothing);
    expect(find.textContaining('Sunucu: '), findsOneWidget);
  });

  testWidgets('kayıtlı sunucuya erişilemezse ayar belirginleşir', (tester) async {
    await tester.pumpWidget(_screen(
      onAuthenticated: (_) async {},
      mock: routingClient(healthStatus: 500),
    ));
    await tester.pumpAndSettle();

    expect(find.text('Kayıtlı sunucuya erişilemiyor'), findsOneWidget);
    expect(find.text('Sunucu değiştir'), findsOneWidget);
  });

  testWidgets('sunucu açıkken kapanırsa ayar belirginleşir', (tester) async {
    var down = false;
    final client = MockClient((request) async {
      if (request.url.path.endsWith('/api/health/')) {
        return down
            ? jsonResponse({'detail': 'hata'}, status: 500)
            : jsonResponse({'status': 'ok'});
      }
      return jsonResponse({'detail': 'bulunamadı'}, status: 404);
    });

    await tester.pumpWidget(_screen(onAuthenticated: (_) async {}, mock: client));
    await tester.pumpAndSettle();
    expect(find.text('Sunucu değiştir'), findsNothing);

    down = true;
    await tester.pump(const Duration(seconds: 5));
    await tester.pumpAndSettle();

    expect(find.text('Kayıtlı sunucuya erişilemiyor'), findsOneWidget);
    expect(find.text('Sunucu değiştir'), findsOneWidget);
  });

  testWidgets('Beni hatırla anahtarı varsayılan ve değişince bildirilir (K9.11)', (tester) async {
    bool? reported;
    await tester.pumpWidget(_screen(
      onAuthenticated: (_) async {},
      initialRememberMe: true,
      onRememberMeChanged: (v) async => reported = v,
    ));

    expect(find.byType(CheckboxListTile), findsOneWidget);

    await tester.tap(find.byType(CheckboxListTile));
    await tester.pumpAndSettle();
    expect(reported, isFalse);

    await tester.tap(find.byType(CheckboxListTile));
    await tester.pumpAndSettle();
    expect(reported, isTrue);
  });
}
