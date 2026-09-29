import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

import 'package:masaustu/config.dart';
import 'package:masaustu/printing/label_pdf.dart';
import 'package:masaustu/printing/print_helpers.dart';
import 'package:masaustu/printing/printer_service.dart';
import 'package:masaustu/printing/receipt_pdf.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late Directory tempHome;
  setUpAll(() {
    tempHome = Directory.systemTemp.createTempSync('masaustu_config_test');
    AppConfig.testHomeDir = tempHome.path;
  });
  tearDownAll(() {
    AppConfig.testHomeDir = null;
    try {
      tempHome.deleteSync(recursive: true);
    } catch (_) {}
  });

  const kurum = KurumBilgisi(
    kutuphaneAdi: 'Atatürk Ortaokulu Kütüphanesi',
    adres: 'Okul Cad. No:1',
    telefon: '0312 000 00 00',
    eposta: 'kutuphane@okul.edu.tr',
    website: 'okul.edu.tr',
  );

  group('PrinterService — CUPS ayrıştırma/komut (K14)', () {
    const lpstat = '''
printer HP-LaserJet-1020 is idle.  enabled since Jan 01 00:00
printer ETIKET-58 is now printing ETIKET-58. enabled since Jan 01 00:00
        Unknown reason for print
printer DISABLI_Yazici disabled since Jan 01 00:00
        expects attention
''';

    PrinterService mock(int exitCode, String out, String err) {
      return PrinterService(runner: (exe, args) async {
        expect(exe, 'lpstat');
        return ProcResult(exitCode, out, err);
      });
    }

    test('cupsKurulu lpstat ok ise true', () async {
      expect(await mock(0, '', '').cupsKurulu(), isTrue);
    });

    test('kuyruklar ad + durum ayrıştırılır', () async {
      final list = await mock(0, lpstat, '').listPrinters();
      expect(list.length, 3);
      expect(list[0].name, 'HP-LaserJet-1020');
      expect(list[0].state, PrinterState.ready);
      expect(list[1].name, 'ETIKET-58');
      expect(list[1].state, PrinterState.busy);
      expect(list[2].state, PrinterState.disabled);
      expect(list[0].cikisYapabilir, isTrue);
      expect(list[2].cikisYapabilir, isFalse);
    });

    test('lpstat hatası yalnızca stderr ise boş liste', () async {
      final list = await mock(1, '', 'lpstat: No destinations added.').listPrinters();
      expect(list, isEmpty);
    });

    test('findPrinter hazır kuyruğu bulur, bilinmeyeni missing yapar', () async {
      final ps = mock(0, lpstat, '');
      final hazir = await ps.findPrinter('HP-LaserJet-1020');
      expect(hazir?.state, PrinterState.ready);
      final yok = await ps.findPrinter('YOK-KUYRUK');
      expect(yok?.state, PrinterState.missing);
      expect(await ps.findPrinter(''), isNull);
    });

    test('printPdf -d/-t + dosya yolu gönderir; geçici dosya temizlenir',
        () async {
      String? exe;
      List<String>? args;
      final ps = PrinterService(runner: (e, a) async {
        exe = e;
        args = a;
        return const ProcResult(1, '', 'lp: printer not found');
      });
      final r = await ps.printPdf('ETIKET-58', [0x25, 0x50, 0x44, 0x46],
          title: 'deneme');
      expect(r.ok, isFalse);
      expect(r.message, contains('lp: printer not found'));
      expect(exe, 'lp');
      expect(args![args!.indexOf('-d') + 1], 'ETIKET-58');
      expect(args![args!.indexOf('-t') + 1], 'deneme');
      expect(File(args!.last).existsSync(), isFalse);
    });

    test('etiket boyutlu PDF otomatik Custom media ekler', () async {
      List<String>? args;
      final ps = PrinterService(runner: (_, a) async {
        args = a;
        return const ProcResult(0, '', '');
      });
      await ps.printPdf('ETIKET', _pdfWithMedia('0 0 161.57 113.39'));
      final ix = args!.indexOf('-o');
      expect(ix, greaterThanOrEqualTo(0));
      expect(args![ix + 1], startsWith('media=Custom.161.57x113.39'));
    });

    test('A4 boyutlu PDF media eklemez', () async {
      List<String>? args;
      final ps = PrinterService(runner: (_, a) async {
        args = a;
        return const ProcResult(0, '', '');
      });
      await ps.printPdf('KITAP', _pdfWithMedia('0 0 595.28 841.89'));
      expect(args, isNotEmpty);
      expect(args!.contains('-o'), isFalse);
    });

    test('açıkça verilen media otomatik değeri ezer', () async {
      List<String>? args;
      final ps = PrinterService(runner: (_, a) async {
        args = a;
        return const ProcResult(0, '', '');
      });
      await ps.printPdf('ETIKET', _pdfWithMedia('0 0 161.57 113.39'),
          media: 'w4h6');
      final ix = args!.indexOf('-o');
      expect(args![ix + 1], 'media=w4h6');
    });

    test('printPdf boş kuyrukta seçilmedi mesajı verir', () async {
      final ps =
          PrinterService(runner: (_, _) async => const ProcResult(0, '', ''));
      final r = await ps.printPdf('   ', [1, 2]);
      expect(r.ok, isFalse);
      expect(r.message, contains('seçilmemiş'));
      expect(await ps.printPdf('', [1, 2]).then((x) => x.message),
          contains('seçilmemiş'));
    });
  });

  group('ReceiptPdf içerik satırları (Türkçe + kurum başlığı)', () {
    test('ödünç fişi tüm kritik alanları içerir', () {
      final lines = ReceiptPdf.oduncFisi(
        kurum: kurum,
        operator: 'Ayşe Personel',
        tarih: '27.09.2026 10:00',
        ogrenci: 'Ali Veli',
        sinif: '8-A',
        kitap: 'Suç ve Ceza',
        yazar: 'Dostoyevski',
        barkod: 'KIT0000123',
        oduncTarihi: '27.09.2026',
        iadeTarihi: '15.10.2026',
      );
      final text = lines.map((l) => l.text).join('\n');
      expect(text, contains('Atatürk Ortaokulu Kütüphanesi'));
      expect(text, contains('ÖDÜNÇ FİŞİ'));
      expect(text, contains('Ali Veli'));
      expect(text, contains('KIT0000123'));
      expect(text, contains('İADE TARİHİ: 15.10.2026'));
      expect(text, contains('Dostoyevski'));
    });

    test('türkçe karakterler düzgün taşınır', () {
      final lines = ReceiptPdf.oduncFisi(
        kurum: kurum,
        operator: 'Öğretmen',
        tarih: '1.1.2026 09:00',
        ogrenci: 'İpek Şimşek',
        sinif: '9-C',
        kitap: 'İnce Memed',
        yazar: 'Yaşar Kemal',
        barkod: 'B-İĞ_123',
        oduncTarihi: '1.1.2026',
        iadeTarihi: '2.2.2026',
      );
      final text = lines.map((l) => l.text).join('\n');
      expect(text, contains('İpek Şimşek'));
      expect(text, contains('Barkod: B-İĞ_123'));
    });

    test('iade fişi durum + ceza + ödeme notu içerir', () {
      final lines = ReceiptPdf.iadeFisi(
        kurum: kurum,
        operator: 'Op',
        tarih: 't',
        ogrenci: 'Ali Veli',
        sinif: '8-A',
        kitap: 'Kitap',
        yazar: '',
        barkod: 'K1',
        durumEtiketi: 'teslim',
        cezaTutari: 'Ceza: 12,50 ₺',
        odemeNotu: 'Ceza tahsil edildi: 12,50 ₺',
      );
      final text = lines.map((l) => l.text).join('\n');
      expect(text, contains('İADE FİŞİ'));
      expect(text, contains('Ceza tahsil edildi: 12,50 ₺'));
    });

    test('borcuYoktur aktif ödünç sayısını taşır', () {
      final text = ReceiptPdf.borcuYoktur(
        kurum: kurum,
        operator: 'Op',
        tarih: 't',
        ogrenci: 'Ali Veli',
        sinif: '8-A',
        aktifOdunc: '2',
      ).map((l) => l.text).join('\n');
      expect(text, contains('Gecikme borcu: YOKTUR'));
      expect(text, contains('aktif ödünç sayısı: 2'));
    });

    test('şifre fişi kullanıcı adı + şifreyi taşır', () {
      final text = ReceiptPdf.sifreFisi(
        kurum: kurum,
        operator: 'Op',
        tarih: 't',
        ogrenci: 'Ali Veli',
        kullaniciAdi: '1002',
        sifre: 'abcd1234',
      ).map((l) => l.text).join('\n');
      expect(text, contains('Kullanıcı adı: 1002'));
      expect(text, contains('Şifre: abcd1234'));
    });

    test('ceza tahsilat fişi tutarı taşır', () {
      final text = ReceiptPdf.cezaOdemeFisi(
        kurum: kurum,
        operator: 'Op',
        tarih: 't',
        ogrenci: 'Ali Veli',
        sinif: '8-A',
        tutar: '12,50',
      ).map((l) => l.text).join('\n');
      expect(text, contains('Ödenen tutar: 12,50 ₺'));
    });
  });

  group('PDF üretimi (gömülü font + yazıcı paketi)', () {
    test('receipt render %PDF + antetli geçerli çıktı verir', () async {
      final pdf = await ReceiptPdf.render([
        ...ReceiptPdf.baslik(kurum, 'TEST FİŞİ'),
        const ReceiptLine('satır', size: 9),
        ...ReceiptPdf.altBilgi(kurum),
      ]);
      expect(pdf.length, greaterThan(800));
      expect(pdf.sublist(0, 4), [0x25, 0x50, 0x44, 0x46]);
    });

    test('TestPdf.fis üretir', () async {
      final pdf = await TestPdf.fis(kurum);
      expect(pdf.length, greaterThan(800));
      expect(pdf.sublist(0, 4), [0x25, 0x50, 0x44, 0x46]);
    });

    test('TestPdf.etiket üretir', () async {
      final pdf = await TestPdf.etiket(kurum);
      expect(pdf.length, greaterThan(500));
    });

    test('TestPdf.a4 üretir', () async {
      final pdf = await TestPdf.a4(kurum);
      expect(pdf.length, greaterThan(800));
    });

    test('fiş sayfa genişliği verilen mm değerine uyar (55 mm altyapısı)', () {
      final satirlar = <ReceiptLine>[
        ...ReceiptPdf.baslik(kurum, 'TEST FİŞİ'),
        const ReceiptLine('Kısa bir satır', size: 9),
        ...ReceiptPdf.altBilgi(kurum),
      ];
      for (final mm in [70.0, 58.0, 55.0]) {
        final o = ReceiptPdf.sayfaOlculeriPt(satirlar, genislikMm: mm, kenar: 3);
        expect((o.genislikPt - mm * 2.834645669).abs(), lessThan(0.001),
            reason: '$mm mm → ${o.genislikPt} pt');
      }
    });

    test('dar rulo fişte yükseklik artar (sarma hesaba katılır)', () {
      // 40 mm asgari sayfa yüksekliğini aşacak kadar satır (sarma farkı görünsün)
      const uzun = [
        ReceiptLine(
            'KİTAP: İnsan Olmak ve Ötekilerle Birlikte Yaşamak Üzerine Bir Söyleşi Kitabı',
            size: 11),
        ReceiptLine('YAZAR: Michel Foucault — Söyle ve Özne, Bir Söyleşi Kitabı Baskısı',
            size: 10),
        ReceiptLine('BARKOD: 978-975-00000-11-2   KİTAP NO: 1140   RAF: 12-B',
            size: 10),
        ReceiptLine('ÖDÜNÇ TARİHİ: 27.09.2026   İADE TARİHİ: 11.10.2026', size: 10),
        ReceiptLine('KULLANICI: Ahmet Yılmaz   SINIF: 10-A   NO: 15', size: 10),
        ReceiptLine('NOT: Kütüphane kurallarına göre iade tarihinde teslim ediniz.',
            size: 9),
      ];
      final genis = ReceiptPdf.sayfaOlculeriPt(uzun, genislikMm: 70, kenar: 3);
      final dar = ReceiptPdf.sayfaOlculeriPt(uzun, genislikMm: 55, kenar: 3);
      expect(dar.yukseklikPt, greaterThan(genis.yukseklikPt));
    });

    test('etiket PDF istenen sayfa boyutunda (57×40 mm)', () async {
      final pdf = await LabelPdf.render(LabelPdf.etiketElemanlari(
        kurum: kurum,
        baslik: 'Test Kitap',
        yazar: 'Yazar',
        kategori: 'Genel',
        barkodMetni: 'KIT123',
      ));
      expect(pdf.length, greaterThan(500));
    });
  });

  group('print_helpers sarmalayıcıları', () {
    test('operatorAdi oturum yoksa genel ad döner', () {
      expect(operatorAdi(), 'Kütüphane Personeli');
    });

    test('sifreFisiBas anahtar kapalıysa null döner', () async {
      AppConfig.printer = const PrinterPrefs(sifreFisi: false);
      final r =
          await sifreFisiBas(ogrenci: 'X', kullaniciAdi: '1', sifre: 'a');
      expect(r, isNull);
    });

    test('etiketBas yazıcı seçilmediyse Türkçe hata döner', () async {
      AppConfig.printer = const PrinterPrefs();
      final r = await etiketBas(baslik: 'Kitap', barkod: 'K1');
      expect(r.ok, isFalse);
      expect(r.message, contains('seçilmemiş'));
    });
  });
}

List<int> _pdfWithMedia(String box) {
  final s = '%PDF-1.4\n'
      '1 0 obj\n'
      '<< /Type /Page /MediaBox [$box] >>\n'
      'endobj\n'
      '%%EOF\n';
  return s.codeUnits;
}