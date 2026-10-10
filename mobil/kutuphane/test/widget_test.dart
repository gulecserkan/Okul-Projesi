// KutuphaneApp açılış akışı testleri.
import 'package:flutter_test/flutter_test.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:kutuphane/main.dart';

import 'support/mock_api.dart';

void main() {
  testWidgets('Uygulama açılışı bağlantı ekranını gösterir', (
    WidgetTester tester,
  ) async {
    SharedPreferences.setMockInitialValues({});

    await tester.pumpWidget(const KutuphaneApp());
    await tester.pumpAndSettle();

    expect(find.textContaining('Kütüphane sunucusuna bağlan'), findsOneWidget);
  });

  testWidgets('Yeni sürüm varsa açılışta güncelleme diyaloğu açılır (K13.4)', (
    WidgetTester tester,
  ) async {
    PackageInfo.setMockInitialValues(
      appName: 'Kutuphane',
      packageName: 'tr.okulkitapligi',
      version: '1.1.6',
      buildNumber: '4',
      buildSignature: '',
    );
    SharedPreferences.setMockInitialValues({
      'server_base_url': 'http://test.local',
    });

    await tester.pumpWidget(
      KutuphaneApp(
        httpClient: routingClient(
          mobilSurum: {
            'surum': '9.9.9',
            'surumKodu': 999,
            'minSurumKodu': 0,
            'apkUrl': '/mobil/kutuphane.apk',
          },
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Yeni sürüm mevcut'), findsOneWidget);
    expect(find.text('Güncelle'), findsOneWidget);
  });
}
