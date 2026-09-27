import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:masaustu/config.dart';
import 'package:masaustu/printing/printer_service.dart';
import 'package:masaustu/printing/rulo_durum.dart';

const _lpstatIdle = 'printer TEST-Q is idle. enabled since Jan 01 00:00\n';
const _lpstatDisabled =
    'printer TEST-Q disabled since Jan 01 00:00\n        expects attention\n';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late Directory tempHome;
  setUpAll(() {
    tempHome = Directory.systemTemp.createTempSync('masaustu_rulo_test');
    AppConfig.testHomeDir = tempHome.path;
  });
  tearDownAll(() {
    AppConfig.testHomeDir = null;
    PrinterServices.instance = PrinterService();
    try {
      tempHome.deleteSync(recursive: true);
    } catch (_) {}
  });

  PrinterService sahte({
    String lpstat = _lpstatIdle,
    List<String>? komutlar,
  }) {
    return PrinterService(runner: (exe, args) async {
      komutlar?.add(exe);
      switch (exe) {
        case 'lpstat':
          return ProcResult(0, lpstat, '');
        case 'lp':
          return const ProcResult(0, '', '');
        default:
          return const ProcResult(0, '', '');
      }
    });
  }

  group('PrinterPrefs yeni alanları (K14.9/10/11)', () {
    test('toJson/fromJson round-trip', () {
      const p = PrinterPrefs(
        fisYazici: 'Q1',
        etiketYazici: 'Q2',
        a4Yazici: 'Q3',
        rulo: 'etiket',
        a4Dosya: true,
        etiketKurulumYapildi: true,
        etiketGenislikMm: 50,
        etiketYukseklikMm: 30,
        fisGenislikMm: 80,
      );
      final g = PrinterPrefs.fromJson(p.toJson());
      expect(g.rulo, 'etiket');
      expect(g.a4Dosya, isTrue);
      expect(g.etiketKurulumYapildi, isTrue);
      expect(g.etiketGenislikMm, 50);
      expect(g.etiketYukseklikMm, 30);
      expect(g.fisGenislikMm, 80);
    });

    test('boş/varsayılan json geçerli (geriye uyumlu)', () {
      final g = PrinterPrefs.fromJson(const {});
      expect(g.rulo, 'tanimsiz');
      expect(g.a4Dosya, isFalse);
      expect(g.etiketKurulumYapildi, isFalse);
      expect(g.etiketGenislikMm, 57);
      expect(g.etiketYukseklikMm, 40);
      expect(g.fisGenislikMm, 70);
    });

    test('eski configdeki gap/kağıt tipi anahtarları yoksayılır', () {
      final g = PrinterPrefs.fromJson(const {
        'etiket_gap_mm': 2.5,
        'etiket_kagit_tipi': 'LabelMark',
        'etiket_genislik_mm': 45,
      });
      expect(g.etiketGenislikMm, 45);
      expect(g.etiketYukseklikMm, 40);
    });
  });

  group('ortakKuyruk — rulo kapsamı (K14.9)', () {
    test('farklı veya boş kuyruklarda null', () {
      AppConfig.printer = const PrinterPrefs(fisYazici: 'A', etiketYazici: 'B');
      expect(ortakKuyruk(), isNull);
      AppConfig.printer = const PrinterPrefs(fisYazici: 'A', etiketYazici: '');
      expect(ortakKuyruk(), isNull);
      AppConfig.printer = const PrinterPrefs(fisYazici: '', etiketYazici: 'B');
      expect(ortakKuyruk(), isNull);
    });

    test('aynı kuyruk ortak sayılır', () {
      AppConfig.printer = const PrinterPrefs(fisYazici: 'T', etiketYazici: 'T');
      expect(ortakKuyruk(), 'T');
    });
  });

  group('Kağıt tipi zorlanmaz (K14.11)', () {
    test('printPdf yalnız media gönderir, PaperType/GapsHeight yok', () async {
      List<String>? args;
      final ps = PrinterService(runner: (_, a) async {
        args = a;
        return const ProcResult(0, '', '');
      });
      await ps.printPdf('Q', [0x25, 0x50, 0x44, 0x46]);
      expect(args!.contains('PaperType=Continue'), isFalse);
      expect(args!.contains('GapsHeight=0'), isFalse);
      expect(args!.where((a) => a.startsWith('PaperType')), isEmpty);
    });

    test('lpoptions/lpadmin hiç çağrılmaz', () async {
      final komutlar = <String>[];
      final ps = sahte(komutlar: komutlar);
      await ps.printPdf('TEST-Q', [0x25, 0x50, 0x44, 0x46]);
      expect(komutlar, isNot(contains('lpoptions')));
      expect(komutlar, isNot(contains('lpadmin')));
    });
  });

  group('guncelRuloDurumu (K14.9)', () {
    test('ortak değilse tanimsiz', () async {
      AppConfig.printer =
          const PrinterPrefs(fisYazici: 'A', etiketYazici: 'B');
      PrinterServices.instance = sahte();
      expect(await guncelRuloDurumu(), RuloDurum.tanimsiz);
    });

    test('bildirilen rulo ve hazır yazıcı', () async {
      PrinterServices.instance = sahte();
      AppConfig.printer = const PrinterPrefs(
          fisYazici: 'TEST-Q', etiketYazici: 'TEST-Q', rulo: 'fis');
      expect(await guncelRuloDurumu(), RuloDurum.fis);
      AppConfig.printer = const PrinterPrefs(
          fisYazici: 'TEST-Q', etiketYazici: 'TEST-Q', rulo: 'etiket');
      expect(await guncelRuloDurumu(), RuloDurum.etiket);
      AppConfig.printer = const PrinterPrefs(
          fisYazici: 'TEST-Q', etiketYazici: 'TEST-Q');
      expect(await guncelRuloDurumu(), RuloDurum.tanimsiz);
    });

    test('yazıcı kapalı/devre dışı → pasif', () async {
      PrinterServices.instance = sahte(lpstat: _lpstatDisabled);
      AppConfig.printer = const PrinterPrefs(
          fisYazici: 'TEST-Q', etiketYazici: 'TEST-Q', rulo: 'fis');
      expect(await guncelRuloDurumu(), RuloDurum.pasif);
    });
  });

  group('ruloOnay — basım öncesi onay (K14.9)', () {
    Widget host(Future<bool> Function(BuildContext) call, void Function(bool) al) {
      late StateSetter setter;
      return MaterialApp(
        home: StatefulBuilder(
          builder: (context, setState) {
            setter = setState;
            return Scaffold(
              body: Center(
                child: ElevatedButton(
                  onPressed: () async {
                    final s = await call(context);
                    setter(() {});
                    al(s);
                  },
                  child: const Text('Basla'),
                ),
              ),
            );
          },
        ),
      );
    }

    testWidgets('ortak değilse diyalog açılmaz, doğrudan devam', (tester) async {
      AppConfig.printer =
          const PrinterPrefs(fisYazici: 'A', etiketYazici: 'B');
      final komutlar = <String>[];
      PrinterServices.instance = sahte(komutlar: komutlar);
      bool? sonuc;
      await tester.pumpWidget(host(
          (ctx) => ruloOnay(ctx, RuloTipi.etiket), (s) => sonuc = s));
      await tester.tap(find.text('Basla'));
      await tester.pumpAndSettle();
      expect(sonuc, isTrue);
      expect(komutlar, isNot(contains('lpadmin')));
    });

    testWidgets('uyuşmazlıkta onay ister; "taktım" durumu günceller',
        (tester) async {
      AppConfig.printer = const PrinterPrefs(
          fisYazici: 'TEST-Q',
          etiketYazici: 'TEST-Q',
          rulo: 'fis',
          etiketKurulumYapildi: true);
      final komutlar = <String>[];
      PrinterServices.instance = sahte(komutlar: komutlar);
      bool? sonuc;
      await tester.pumpWidget(host(
          (ctx) => ruloOnay(ctx, RuloTipi.etiket), (s) => sonuc = s));
      await tester.tap(find.text('Basla'));
      await tester.pumpAndSettle();
      expect(find.textContaining('Etiket rulosu taktım'), findsOneWidget);

      await tester.tap(find.text('Etiket rulosu taktım → yazdır'));
      await tester.pumpAndSettle();
      expect(sonuc, isTrue);
      expect(AppConfig.printer.rulo, 'etiket');
      expect(komutlar, isNot(contains('lpadmin')));
    });

    testWidgets('Vazgeç basımı iptal eder, durum değişmez', (tester) async {
      AppConfig.printer = const PrinterPrefs(
          fisYazici: 'TEST-Q',
          etiketYazici: 'TEST-Q',
          rulo: 'etiket',
          etiketKurulumYapildi: true);
      PrinterServices.instance = sahte();
      bool? sonuc;
      await tester.pumpWidget(host(
          (ctx) => ruloOnay(ctx, RuloTipi.fis), (s) => sonuc = s));
      await tester.tap(find.text('Basla'));
      await tester.pumpAndSettle();
      expect(find.textContaining('Fiş rulosu taktım'), findsOneWidget);

      await tester.tap(find.text('Vazgeç'));
      await tester.pumpAndSettle();
      expect(sonuc, isFalse);
      expect(AppConfig.printer.rulo, 'etiket');
    });

    testWidgets('bildirilen rulo istenenle eş ve hazır → sessiz devam',
        (tester) async {
      AppConfig.printer = const PrinterPrefs(
          fisYazici: 'TEST-Q',
          etiketYazici: 'TEST-Q',
          rulo: 'etiket',
          etiketKurulumYapildi: true);
      final komutlar = <String>[];
      PrinterServices.instance = sahte(komutlar: komutlar);
      bool? sonuc;
      await tester.pumpWidget(host(
          (ctx) => ruloOnay(ctx, RuloTipi.etiket), (s) => sonuc = s));
      await tester.tap(find.text('Basla'));
      await tester.pumpAndSettle();
      expect(sonuc, isTrue);
      expect(komutlar, isNot(contains('lpadmin')));
    });

    testWidgets('yazıcı pasifse "Yine de dene" / "Vazgeç" (K14.5)', (tester) async {
      AppConfig.printer = const PrinterPrefs(
          fisYazici: 'TEST-Q',
          etiketYazici: 'TEST-Q',
          rulo: 'fis',
          etiketKurulumYapildi: true);
      PrinterServices.instance = sahte(lpstat: _lpstatDisabled);
      bool? sonuc;
      await tester.pumpWidget(host(
          (ctx) => ruloOnay(ctx, RuloTipi.fis), (s) => sonuc = s));
      await tester.tap(find.text('Basla'));
      await tester.pumpAndSettle();
      expect(find.text('Yine de dene'), findsOneWidget);

      await tester.tap(find.text('Vazgeç'));
      await tester.pumpAndSettle();
      expect(sonuc, isFalse);
    });
  });
}
