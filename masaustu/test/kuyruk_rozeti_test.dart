import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:masaustu/config.dart';
import 'package:masaustu/printing/printer_service.dart';
import 'package:masaustu/screens/settings_screen.dart';

/// `lpstat -p` çıktısı: iki kuyruk.
const _lpstat = 'printer Hewlett-Packard-HP-LaserJet-1020 is idle. enabled '
    'since Jan 01 00:00\n'
    'printer Tazga-PRN-400D is idle. enabled since Jan 01 00:00\n';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late Directory tempHome;
  setUpAll(() {
    tempHome = Directory.systemTemp.createTempSync('kuyruk_rozeti');
    AppConfig.testHomeDir = tempHome.path;
    PrinterServices.instance = PrinterService(
      runner: (exe, args) async => switch (exe) {
        'lpstat' => ProcResult(0, _lpstat, ''),
        _ => const ProcResult(0, '', ''),
      },
    );
  });
  tearDownAll(() {
    AppConfig.testHomeDir = null;
    PrinterServices.instance = PrinterService();
    try {
      tempHome.deleteSync(recursive: true);
    } catch (_) {}
  });

  Future<void> acAyarlar(WidgetTester tester) async {
    tester.view.physicalSize = const Size(1500, 1400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(
      const MaterialApp(home: Scaffold(body: SettingsScreen())),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('Yazıcılar'));
    await tester.pumpAndSettle();
  }

  setUp(() {
    AppConfig.printer = AppConfig.printer.copyWith(
        fisYazici: 'Tazga-PRN-400D',
        etiketYazici: 'Tazga-PRN-400D',
        a4Yazici: 'Tazga-PRN-400D');
  });

  testWidgets('kuyruk listede yoksa rozet "Seçilmedi" değil "Bulunamadı"',
      (tester) async {
    AppConfig.printer = AppConfig.printer.copyWith(a4Yazici: 'HP-LaserJet-1020');
    await acAyarlar(tester);

    expect(find.text('Bulunamadı'), findsOneWidget);
    expect(find.text('Seçilmedi'), findsNothing);
    // Gerçek kuyruk önerilir (kuyruk yeniden adlandırılmış/yeni kurulmuş olabilir).
    expect(find.text('Düzelt: Hewlett-Packard-HP-LaserJet-1020'), findsOneWidget);
  });

  testWidgets('düzelt düğmesi kayıtlı kuyruğu gerçek adla değiştirir',
      (tester) async {
    AppConfig.printer = AppConfig.printer.copyWith(a4Yazici: 'HP-LaserJet-1020');
    await acAyarlar(tester);

    await tester.tap(find.text('Düzelt: Hewlett-Packard-HP-LaserJet-1020'));
    await tester.pumpAndSettle();

    expect(AppConfig.printer.a4Yazici, 'Hewlett-Packard-HP-LaserJet-1020');
    expect(find.text('Hazır'), findsNWidgets(3));
  });

  testWidgets('hiç kuyruk seçilmemişse rozet "Seçilmedi" kalır', (tester) async {
    AppConfig.printer = AppConfig.printer.copyWith(
        a4Yazici: '', fisYazici: '', etiketYazici: '');
    await acAyarlar(tester);

    expect(find.text('Seçilmedi'), findsNWidgets(3));
    expect(find.text('Bulunamadı'), findsNothing);
  });
}
