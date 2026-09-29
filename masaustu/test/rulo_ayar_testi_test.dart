import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:masaustu/config.dart';
import 'package:masaustu/screens/settings_screen.dart';

/// R1.9 — termal rulo ölçüleri: metin alanı kaydedilmemiş değişikliği bildirir,
/// Enter / alandan çıkış kaydeder, açık kaydetme düğmesi yalnızca kirliyken
/// etkindir ve geçersiz giriş kaydedilen değere döner.
void main() {
  late PrinterPrefs prefs;
  late List<PrinterPrefs> kayitlar;

  setUp(() {
    prefs = const PrinterPrefs(
      fisYazici: 'Tazga-PRN-400D',
      etiketYazici: 'Tazga-PRN-400D',
      a4Yazici: 'HP-LaserJet-1020',
      rulo: 'fis',
      etiketGenislikMm: 57,
      etiketYukseklikMm: 40,
      fisGenislikMm: 70,
    );
    kayitlar = [];
  });

  Future<void> ekraniKur(WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: StatefulBuilder(
            builder: (context, setState) {
              return SingleChildScrollView(
                child: TermalRuloBolumu(
                  prefs: prefs,
                  onRulo: (_) {},
                  onKaydet: (p) {
                    kayitlar.add(p);
                    setState(() => prefs = p);
                  },
                ),
              );
            },
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  Finder alan(String etiket) =>
      find.ancestor(of: find.text(etiket), matching: find.byType(TextField));

  Finder kaydetDugmesi() =>
      find.widgetWithText(FilledButton, 'Rulo ayarlarını kaydet');

  Finder uyari() => find.textContaining('Kaydedilmemiş değişiklik var');

  testWidgets('ilk durumda temiz: uyarı yok, düğme pasif', (tester) async {
    await ekraniKur(tester);
    expect(uyari(), findsNothing);
    expect(
      tester.widget<FilledButton>(kaydetDugmesi()).onPressed,
      isNull,
      reason: 'değişiklik yokken kaydetmeye gerek yok',
    );
    expect(find.textContaining('55 mm de çalışır'), findsOneWidget);
  });

  testWidgets('değer değişince uyarı çıkar ve düğme etkinleşir', (
    tester,
  ) async {
    await ekraniKur(tester);
    await tester.enterText(alan('Fiş genişliği (mm)'), '55');
    await tester.pumpAndSettle();
    expect(uyari(), findsOneWidget);
    expect(tester.widget<FilledButton>(kaydetDugmesi()).onPressed, isNotNull);
    expect(kayitlar, isEmpty, reason: 'yazmak kaydetmez');
  });

  testWidgets('Enter (onSubmitted) kaydeder', (tester) async {
    await ekraniKur(tester);
    await tester.enterText(alan('Fiş genişliği (mm)'), '55');
    await tester.pumpAndSettle();
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pumpAndSettle();
    expect(kayitlar.last.fisGenislikMm, 55);
    expect(
      uyari(),
      findsNothing,
      reason: 'kaydedildikten sonra uyarı kalkmalı',
    );
  });

  testWidgets('alandan çıkınca (focus kaybı) kaydeder', (tester) async {
    await ekraniKur(tester);
    await tester.enterText(alan('Etiket genişliği (mm)'), '50');
    await tester.pumpAndSettle();
    FocusManager.instance.primaryFocus?.unfocus();
    await tester.pumpAndSettle();
    expect(kayitlar.last.etiketGenislikMm, 50);
    expect(kayitlar.last.fisGenislikMm, 70, reason: 'diğer alanlar korunur');
  });

  testWidgets('kaydet düğmesi de kaydeder', (tester) async {
    await ekraniKur(tester);
    await tester.enterText(alan('Fiş genişliği (mm)'), '58');
    await tester.pumpAndSettle();
    await tester.tap(kaydetDugmesi());
    await tester.pumpAndSettle();
    expect(kayitlar.last.fisGenislikMm, 58);
  });

  testWidgets('geçersiz giriş kaydedilen değere döner', (tester) async {
    await ekraniKur(tester);
    await tester.enterText(alan('Fiş genişliği (mm)'), 'abc');
    await tester.pumpAndSettle();
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pumpAndSettle();
    expect(kayitlar, isEmpty, reason: 'geçersiz giriş kaydedilmez');
    expect(
      tester.widget<TextField>(alan('Fiş genişliği (mm)')).controller!.text,
      '70',
    );
    expect(uyari(), findsNothing);
  });

  testWidgets('aynı değeri yazmak kaydetmez (temiz kalır)', (tester) async {
    await ekraniKur(tester);
    await tester.enterText(alan('Fiş genişliği (mm)'), '70');
    await tester.pumpAndSettle();
    expect(uyari(), findsNothing);
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pumpAndSettle();
    expect(kayitlar, isEmpty);
  });

  testWidgets('virgüllü ondalık (55,5) kabul edilir', (tester) async {
    await ekraniKur(tester);
    await tester.enterText(alan('Fiş genişliği (mm)'), '55,5');
    await tester.pumpAndSettle();
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pumpAndSettle();
    expect(kayitlar.last.fisGenislikMm, 55.5);
  });
}
