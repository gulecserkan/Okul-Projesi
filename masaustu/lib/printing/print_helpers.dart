import 'dart:io';

import 'package:file_selector/file_selector.dart';
import 'package:flutter/widgets.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;

import '../api/kutuphane_api.dart';
import '../config.dart';
import 'label_pdf.dart';
import 'print_fonts.dart';
import 'printer_service.dart';
import 'receipt_pdf.dart';

/// Açılışta kurum bilgisini getirir (çekilemezse yerel yedek; yoksa boş).
/// Başarılıysa yedeği de günceller (K14.1).
Future<KurumBilgisi> kurumGetir() async {
  try {
    final res = await KutuphaneApi().kurumAyarlariGet();
    if (res.data != null) {
      final k = KurumBilgisi.fromJson(res.data!);
      AppConfig.kurumYedek = k;
      return k;
    }
  } catch (_) {}
  return AppConfig.kurumYedek ?? const KurumBilgisi();
}

/// Fiş/etiketlerde kullanılacak operatör (masaüstü hesabı) adı.
String operatorAdi() {
  final s = AppConfig.session;
  final ad = s?.fullName.trim() ?? '';
  return ad.isNotEmpty ? ad : (s?.username.trim().isNotEmpty ?? false ? s!.username : 'Kütüphane Personeli');
}

/// Fiş yazdırma yardımcısı.
class FisYazdir {
  /// Belirtilen kuyruk varsayılandan geliyorsa geçerli ayarı kullanır.
  static Future<PrintResult> yazdir(
    List<ReceiptLine> lines, {
    String? kuyruk,
    String title = 'kutuphane-fis',
  }) async {
    final q = kuyruk?.trim().isNotEmpty ?? false
        ? kuyruk!.trim()
        : AppConfig.printer.fisYazici;
    if (q.isEmpty) {
      return const PrintResult(false,
          'Yazıcı seçilmemiş. Ayarlar › Yazıcılar sekmesinden bir fiş yazıcısı seçin.');
    }
    final prefs = AppConfig.printer;
    final pdf = await ReceiptPdf.render(lines,
        genislikMm: prefs.fisGenislikMm);
    return PrinterServices.instance.printPdf(q, pdf, title: title);
  }
}

/// Etiket yazdırma yardımcısı.
class EtiketYazdir {
  static Future<PrintResult> yazdir(
    KurumBilgisi kurum,
    String baslik,
    String yazar,
    String kategori,
    String barkod, {
    String? kuyruk,
  }) async {
    final q = kuyruk?.trim().isNotEmpty ?? false
        ? kuyruk!.trim()
        : AppConfig.printer.etiketYazici;
    if (q.isEmpty) {
      return const PrintResult(false,
          'Yazıcı seçilmemiş. Ayarlar › Yazıcılar sekmesinden bir etiket yazıcısı seçin.');
    }
    final prefs = AppConfig.printer;
    final pdf = await LabelPdf.render(
      kurum: kurum,
      baslik: baslik,
      yazar: yazar,
      kategori: kategori,
      barkodMetni: barkod,
      genislikMm: prefs.etiketGenislikMm,
      yukseklikMm: prefs.etiketYukseklikMm,
    );
    return PrinterServices.instance
        .printPdf(q, pdf, title: 'kutuphane-etiket');
  }
}

/// A4 çıktısını yazıcıya ya da dosyaya yönlendirir (K14.10):
/// - A4 kuyruğu hazırsa `lp` ile basılır,
/// - aksi halde ("Dosyaya yaz" modu, kuyruk boş/pasif) dosya kayıt diyaloğu açar.
Future<PrintResult> a4Bas(
  BuildContext context,
  Future<List<int>> Function() uretici, {
  String dosyaOnAdi = 'kutuphane_belge.pdf',
  String? kuyruk,
}) async {
  final q = (kuyruk?.trim().isNotEmpty ?? false)
      ? kuyruk!.trim()
      : AppConfig.printer.a4Yazici;
  final pdf = await uretici();
  final prefs = AppConfig.printer;

  if (!prefs.a4Dosya && q.isNotEmpty) {
    final info = await PrinterServices.instance.findPrinter(q);
    if (info?.cikisYapabilir ?? false) {
      return PrinterServices.instance.printPdf(q, pdf, title: dosyaOnAdi);
    }
  }
  if (!context.mounted) {
    return PrintResult(false, 'Ekran kapatıldı; kaydetme yapılamadı.');
  }
  return _pdfDosyayaKaydet(context, pdf, dosyaOnAdi);
}

/// PDF'i `getSaveLocation` ile kullanıcıya kaydettirir (K14.10).
Future<PrintResult> _pdfDosyayaKaydet(
  BuildContext context,
  List<int> pdf,
  String onAd,
) async {
  final hedef = onAd.toLowerCase().endsWith('.pdf') ? onAd : '$onAd.pdf';
  final location = await getSaveLocation(
    suggestedName: hedef,
    acceptedTypeGroups: const [XTypeGroup(label: 'PDF', extensions: ['pdf'])],
  );
  if (location == null) {
    return const PrintResult(false, 'PDF kaydetme iptal edildi.');
  }
  try {
    final f = File(location.path);
    await f.writeAsBytes(pdf, flush: true);
    return PrintResult(true, 'PDF dosyası kaydedildi: ${f.path}');
  } on FileSystemException catch (e) {
    return PrintResult(false, 'Dosyaya yazılamadı: ${e.message}');
  }
}

/// "Test et" için örnek PDF'ler (K14.5). Test A4, boyut dışında fiş motorundan
/// bağımsız çizilir.
class TestPdf {
  static Future<List<int>> fis(KurumBilgisi kurum) {
    final lines = <ReceiptLine>[
      ...ReceiptPdf.baslik(kurum, 'TEST FİŞİ'),
      const ReceiptLine('Bu fiş bir deneme basımıdır.', size: 10, spaceAfter: 3),
      const ReceiptLine(
          'Doğru yazıcıya bastıysa ortam hazırdır.', size: 9, spaceAfter: 3),
      ReceiptLine('Tarih: ${formatTarihNow()}', size: 9, spaceAfter: 2),
      const ReceiptLine('Türkçe: ş ğ ı İ Ç Ö Ü', size: 9, spaceAfter: 2),
      ...ReceiptPdf.altBilgi(kurum),
    ];
    return ReceiptPdf.render(lines,
        genislikMm: AppConfig.printer.fisGenislikMm);
  }

  static Future<List<int>> etiket(KurumBilgisi kurum) {
    return LabelPdf.render(
      kurum: kurum,
      baslik: 'TEST ETİKETİ',
      yazar: 'Deneme Yazarı',
      kategori: 'Genel',
      barkodMetni: 'TEST-001',
      genislikMm: AppConfig.printer.etiketGenislikMm,
      yukseklikMm: AppConfig.printer.etiketYukseklikMm,
    );
  }

  static Future<List<int>> a4(KurumBilgisi kurum) async {
    final regular = await PrintFonts.regular();
    final bold = await PrintFonts.bold();
    final doc = pw.Document();
    doc.addPage(pw.Page(
      pageFormat: PdfPageFormat.a4,
      build: (_) => pw.Center(
        child: pw.Column(
          mainAxisSize: pw.MainAxisSize.min,
          children: [
            if (kurum.baslik.trim().isNotEmpty)
              pw.Text(kurum.baslik.trim(),
                  style: pw.TextStyle(font: bold, fontSize: 18)),
            pw.Text('TEST BASIMI',
                style: pw.TextStyle(font: bold, fontSize: 26)),
            pw.Text('A4 yazıcı bağlantısı doğrulandı.',
                style: pw.TextStyle(font: regular, fontSize: 12)),
          ],
        ),
      ),
    ));
    return doc.save();
  }
}

/// Yazdırma akışları için ortak veri sözlüğü (testlerde JSON ile beslenir).
class FisVerisi {
  const FisVerisi._();

  /// Ödünç fişi için checkout yanıtı → satırlar.
  static List<ReceiptLine> oduncFromJson(
    Map<String, dynamic> json, {
    required KurumBilgisi kurum,
    required String operator,
  }) {
    final uye = json['uye'] is Map<String, dynamic>
        ? json['uye'] as Map<String, dynamic>
        : <String, dynamic>{};
    final nusha = json['kitap_nusha'] is Map<String, dynamic>
        ? json['kitap_nusha'] as Map<String, dynamic>
        : <String, dynamic>{};
    final kitap = nusha['kitap'] is Map<String, dynamic>
        ? nusha['kitap'] as Map<String, dynamic>
        : <String, dynamic>{};
    final yazar = kitap['yazar'] is Map<String, dynamic>
        ? kitap['yazar'] as Map<String, dynamic>
        : <String, dynamic>{};
    final sinifObj = uye['sinif'];
    final sinif = sinifObj is Map<String, dynamic>
        ? sinifObj['ad'] as String? ?? ''
        : (sinifObj is String ? sinifObj : '');

    return ReceiptPdf.oduncFisi(
      kurum: kurum,
      operator: operator,
      tarih: formatTarihNow(),
      ogrenci: '${uye['ad'] ?? ''} ${uye['soyad'] ?? ''}'.trim(),
      sinif: sinif,
      kitap: kitap['baslik'] as String? ?? '',
      yazar: yazar['ad_soyad'] as String? ?? '',
      barkod: nusha['barkod'] as String? ?? '',
      oduncTarihi: dt(json['odunc_tarihi']),
      iadeTarihi: dt(json['iade_tarihi']),
    );
  }

  /// İade fişi için kapatma yanıtı → satırlar.
  static List<ReceiptLine> iadeFromJson(
    Map<String, dynamic> json, {
    required KurumBilgisi kurum,
    required String operator,
    required String durumEtiketi,
    String cezaTutari = '',
    String odemeNotu = '',
  }) {
    final uye = json['uye'] is Map<String, dynamic>
        ? json['uye'] as Map<String, dynamic>
        : <String, dynamic>{};
    final nusha = json['kitap_nusha'] is Map<String, dynamic>
        ? json['kitap_nusha'] as Map<String, dynamic>
        : <String, dynamic>{};
    final kitap = nusha['kitap'] is Map<String, dynamic>
        ? nusha['kitap'] as Map<String, dynamic>
        : <String, dynamic>{};
    final yazar = kitap['yazar'] is Map<String, dynamic>
        ? kitap['yazar'] as Map<String, dynamic>
        : <String, dynamic>{};
    final sinifObj = uye['sinif'];
    final sinif = sinifObj is Map<String, dynamic>
        ? sinifObj['ad'] as String? ?? ''
        : (sinifObj is String ? sinifObj : '');
    return ReceiptPdf.iadeFisi(
      kurum: kurum,
      operator: operator,
      tarih: formatTarihNow(),
      ogrenci: '${uye['ad'] ?? ''} ${uye['soyad'] ?? ''}'.trim(),
      sinif: sinif,
      kitap: kitap['baslik'] as String? ?? '',
      yazar: yazar['ad_soyad'] as String? ?? '',
      barkod: nusha['barkod'] as String? ?? '',
      durumEtiketi: durumEtiketi,
      cezaTutari: cezaTutari,
      odemeNotu: odemeNotu,
    );
  }
}

/// Ödünç/iade/şifre akışlarından çağrılan basım sarmalayıcıları (K14.2/14.3).
/// Kapalı anahtar → `null` döner; çağıran bu durumda hiçbir şey yapmaz.
Future<PrintResult?> oduncFisiBasJson(Map<String, dynamic> json) async {
  if (!AppConfig.printer.otomatikOduncFisi) return null;
  final kurum = await kurumGetir();
  return FisYazdir.yazdir(FisVerisi.oduncFromJson(json,
      kurum: kurum, operator: operatorAdi()));
}

Future<PrintResult?> iadeFisiBasJson(
  Map<String, dynamic> json, {
  required String durumEtiketi,
}) async {
  if (!AppConfig.printer.otomatikIadeFisi) return null;
  final kurum = await kurumGetir();
  final cezaVal = json['gecikme_cezasi'];
  final odendi = json['gecikme_cezasi_odendi'] == true;
  final ceza = (cezaVal is String ? cezaVal : cezaVal?.toString() ?? '').trim();
  final odemeNotu = (ceza.isNotEmpty && odendi)
      ? 'Ceza tahsil edildi: $ceza ₺'
      : '';
  return FisYazdir.yazdir(FisVerisi.iadeFromJson(json,
      kurum: kurum,
      operator: operatorAdi(),
      durumEtiketi: durumEtiketi,
      cezaTutari: ceza.isNotEmpty ? 'Ceza: $ceza ₺' : '',
      odemeNotu: odemeNotu));
}

Future<PrintResult?> sifreFisiBas({
  required String ogrenci,
  required String kullaniciAdi,
  required String sifre,
}) async {
  if (!AppConfig.printer.sifreFisi) return null;
  final kurum = await kurumGetir();
  return FisYazdir.yazdir(ReceiptPdf.sifreFisi(
    kurum: kurum,
    operator: operatorAdi(),
    tarih: formatTarihNow(),
    ogrenci: ogrenci,
    kullaniciAdi: kullaniciAdi,
    sifre: sifre,
  ));
}

/// K14.7: öğrenci detayından manuel "Borcu yoktur" belgesi.
Future<PrintResult?> borcuYokturBas({
  required String ogrenci,
  String sinif = '',
  required int aktifOdunc,
}) async {
  final kurum = await kurumGetir();
  return FisYazdir.yazdir(ReceiptPdf.borcuYoktur(
    kurum: kurum,
    operator: operatorAdi(),
    tarih: formatTarihNow(),
    ogrenci: ogrenci,
    sinif: sinif,
    aktifOdunc: '$aktifOdunc',
  ));
}

/// K14.4: tek/çoklu nüsha etiketi (kurum bilgisi içeriden çekilir).
Future<PrintResult> etiketBas({
  required String baslik,
  String yazar = '',
  String kategori = '',
  required String barkod,
}) async {
  final kurum = await kurumGetir();
  return EtiketYazdir.yazdir(kurum, baslik, yazar, kategori, barkod);
}

/// K14.7: ceza tahsilat fişi (ödemeyle birlikte — basım sonrası geçerli).
Future<PrintResult?> cezaOdemeFisiBas({
  required String ogrenci,
  String sinif = '',
  required String tutar,
}) async {
  final kurum = await kurumGetir();
  return FisYazdir.yazdir(ReceiptPdf.cezaOdemeFisi(
    kurum: kurum,
    operator: operatorAdi(),
    tarih: formatTarihNow(),
    ogrenci: ogrenci,
    sinif: sinif,
    tutar: tutar,
  ));
}

String formatTarihNow() {
  final now = DateTime.now();
  String p(int v) => v.toString().padLeft(2, '0');
  return '${p(now.day)}.${p(now.month)}.${now.year} ${p(now.hour)}:${p(now.minute)}';
}

String dt(Object? iso) {
  if (iso == null) return '—';
  final t = DateTime.tryParse(iso.toString());
  if (t == null) return iso.toString();
  String p(int v) => v.toString().padLeft(2, '0');
  return '${p(t.day)}.${p(t.month)}.${t.year}';
}