import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:kutuphane/api/library_api.dart';
import 'package:kutuphane/screens/connection_screen.dart';

import 'support/mock_api.dart';

Widget _screen({
  required Future<void> Function(String) onConnected,
  http.Client? mock,
  int healthStatus = 200,
}) {
  return MaterialApp(
    home: ConnectionScreen(
      onConnected: onConnected,
      clientFactory: (base) => LibraryApiClient(
        baseUrl: base,
        httpClient: mock ?? routingClient(healthStatus: healthStatus),
      ),
    ),
  );
}

void main() {
  testWidgets('bağlantı ekranı başlığı ve alanı görünür', (tester) async {
    await tester.pumpWidget(_screen(onConnected: (_) async {}));

    expect(find.textContaining('Kütüphane sunucusuna bağlan'), findsOneWidget);
    expect(find.byType(TextField), findsOneWidget);
    expect(find.text('Bağlantıyı kontrol et'), findsOneWidget);
  });

  testWidgets('başarılı el sıkışmada onConnected çağrılır', (tester) async {
    String? connected;
    await tester.pumpWidget(_screen(onConnected: (url) async => connected = url));

    await tester.tap(find.text('Bağlantıyı kontrol et'));
    await tester.pumpAndSettle();

    expect(connected, 'https://okulkitapligi.tr');
  });

  testWidgets('başarısız el sıkışmada hata gösterilir', (tester) async {
    String? connected;
    await tester.pumpWidget(
      _screen(onConnected: (url) async => connected = url, healthStatus: 500),
    );

    await tester.tap(find.text('Bağlantıyı kontrol et'));
    await tester.pumpAndSettle();

    expect(connected, isNull);
    expect(find.textContaining('Sunucu yanıtı 500'), findsOneWidget);
  });

  testWidgets('geçersiz adreste ağ hatası gösterilir', (tester) async {
    await tester.pumpWidget(
      _screen(
        onConnected: (_) async {},
        mock: MockClient((_) async => throw Exception('ağ yok')),
      ),
    );

    await tester.tap(find.text('Bağlantıyı kontrol et'));
    await tester.pumpAndSettle();

    expect(find.textContaining('Exception'), findsOneWidget);
  });
}
