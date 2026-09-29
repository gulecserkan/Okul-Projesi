import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:masaustu/config.dart';
import 'package:masaustu/printing/printer_service.dart';
import 'package:masaustu/printing/rulo_durum.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late Directory tempHome;
  setUp(() {
    tempHome = Directory.systemTemp.createTempSync('etiket_kalib');
    AppConfig.testHomeDir = tempHome.path;
    AppConfig.printer = AppConfig.printer.copyWith(
      fisYazici: 'Tazga-PRN-400D',
      etiketYazici: 'Tazga-PRN-400D',
      etiketGenislikMm: 57,
      etiketYukseklikMm: 40,
      etiketKurulumYapildi: true,
    );
  });
  tearDown(() {
    AppConfig.testHomeDir = null;
    PrinterServices.instance = PrinterService();
    try {
      tempHome.deleteSync(recursive: true);
    } catch (_) {}
  });

  void sahteServis(String model) {
    PrinterServices.instance = PrinterService(
      runner: (exe, args) async => switch (exe) {
        'lpoptions' => ProcResult(0, 'printer-make-and-model=$model\n', ''),
        _ => const ProcResult(0, '', ''),
      },
    );
  }

  test('termal etiket yazıcısı modeli tanınır', () {
    expect(termalEtiketYazici('4B-2074C'), isTrue);
    expect(termalEtiketYazici('Tazga PRN-400D'), isTrue);
    expect(termalEtiketYazici('Hewlett-Packard HP LaserJet 1020'), isFalse);
    expect(termalEtiketYazici(''), isFalse);
  });

  testWidgets('"Etiketi taktım" sonrası Tazga kalibrasyon adımları çıkar',
      (tester) async {
    sahteServis('4B-2074C');
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: Builder(builder: (ctx) => TextButton(
              onPressed: () =>
                  ruloBildir(ctx, RuloTipi.etiket, kalibrasyonGoster: true),
              child: const Text('etiket'),
            )),
      ),
    ));

    await tester.tap(find.text('etiket'));
    await tester.pumpAndSettle();

    expect(AppConfig.printer.rulo, 'etiket');
    expect(find.text('Etiket rulosunu kalibre et'), findsOneWidget);
    expect(find.textContaining('panel tuşu'), findsOneWidget);
    expect(find.textContaining('fabrika ayarı'), findsOneWidget);
    expect(find.textContaining('sensörü kalibrasyonu'), findsOneWidget);

    await tester.tap(find.text('Anladım'));
    await tester.pumpAndSettle();
    expect(find.text('Etiket rulosunu kalibre et'), findsNothing);
  });

  testWidgets('bilinmeyen modelde genel yönerge gösterilir', (tester) async {
    sahteServis('Hewlett-Packard HP LaserJet 1020');
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: Builder(builder: (ctx) => TextButton(
              onPressed: () =>
                  ruloBildir(ctx, RuloTipi.etiket, kalibrasyonGoster: true),
              child: const Text('etiket'),
            )),
      ),
    ));

    await tester.tap(find.text('etiket'));
    await tester.pumpAndSettle();

    expect(find.text('Etiket rulosunu kalibre et'), findsOneWidget);
    expect(find.textContaining('panel tuşu basılı'), findsOneWidget);
  });

  testWidgets('fiş bildiriminde kalibrasyon penceresi açılmaz', (tester) async {
    sahteServis('4B-2074C');
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: Builder(builder: (ctx) => TextButton(
              onPressed: () => ruloBildir(ctx, RuloTipi.fis),
              child: const Text('fis'),
            )),
      ),
    ));

    await tester.tap(find.text('fis'));
    await tester.pumpAndSettle();

    expect(AppConfig.printer.rulo, 'fis');
    expect(find.text('Etiket rulosunu kalibre et'), findsNothing);
  });
}
