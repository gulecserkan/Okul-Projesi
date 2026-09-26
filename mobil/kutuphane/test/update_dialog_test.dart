import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:kutuphane/models/mobil_surum.dart';
import 'package:kutuphane/widgets/update_dialog.dart';

const MobilSurum _surum = MobilSurum(
  surum: "1.1.4",
  surumKodu: 2,
  minSurumKodu: 1,
  apkUrl: "/mobil/kutuphane-v1.1.4.apk",
);

Future<void> _ac(
  WidgetTester tester, {
  required bool zorunlu,
}) async {
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: Builder(
          builder: (ctx) => ElevatedButton(
            onPressed: () => guncellemeDiyaloguGoster(
              ctx,
              surum: _surum,
              zorunlu: zorunlu,
              kuruluSurum: "1.0.0",
              baseUrl: "http://sunucu",
            ),
            child: const Text("aç"),
          ),
        ),
      ),
    ),
  );
  await tester.tap(find.text("aç"));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('zorunlu diyalogda "Daha sonra" yoktur', (tester) async {
    await _ac(tester, zorunlu: true);
    expect(find.text("Güncelleme gerekli"), findsOneWidget);
    expect(find.text("Güncelle"), findsOneWidget);
    expect(find.text("Daha sonra"), findsNothing);
  });

  testWidgets('opsiyonel diyalogda "Daha sonra" vardır', (tester) async {
    await _ac(tester, zorunlu: false);
    expect(find.text("Yeni sürüm mevcut"), findsOneWidget);
    expect(find.text("Güncelle"), findsOneWidget);
    expect(find.text("Daha sonra"), findsOneWidget);
  });
}
