import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;

import '../config.dart';
import 'print_fonts.dart';

/// Tek fiş satırı.
class ReceiptLine {
  final String text;
  final bool bold;
  final double size;
  final bool center;
  final double spaceAfter;
  final bool divider;

  const ReceiptLine(
    this.text, {
    this.bold = false,
    this.size = 10,
    this.center = false,
    this.spaceAfter = 2,
    this.divider = false,
  });
}

/// 70 mm termal fiş PDF üretimi (K14).
///
/// İçerik satırları saf Dart'ta üretilir (`build*Fisi(...)`); test edilebilir.
/// `renderReceipt` bunları 70 mm genişliğinde (yükseklik otomatik) PDF yapar.
class ReceiptPdf {
  static const double mm = PdfPageFormat.mm;

  /// Fiş genişliği (mm).
  static const double genislikMm = 70;
  static const double minYukseklikMm = 40;
  static const double kenarMm = 3;

  // ------------------------------------------------------------ ortak başlık

  static List<ReceiptLine> baslik(KurumBilgisi kurum, String unvan) {
    final lines = <ReceiptLine>[];
    final bas = kurum.baslik.trim();
    if (bas.isNotEmpty) {
      lines.add(ReceiptLine(bas, bold: true, size: 12, center: true, spaceAfter: 1));
    }
    lines.add(ReceiptLine(unvan, size: 12, center: true, bold: true, spaceAfter: 6));
    lines.add(const ReceiptLine('', divider: true, spaceAfter: 4));
    return lines;
  }

  static List<ReceiptLine> altBilgi(KurumBilgisi kurum) {
    final lines = <ReceiptLine>[];
    lines.add(const ReceiptLine('', divider: true, spaceAfter: 2));
    final alt = <String>[
      if (kurum.adres.trim().isNotEmpty) kurum.adres.trim(),
      if (kurum.telefon.trim().isNotEmpty) 'Tel: ${kurum.telefon.trim()}',
      if (kurum.eposta.trim().isNotEmpty) kurum.eposta.trim(),
      if (kurum.website.trim().isNotEmpty) kurum.website.trim(),
    ];
    for (final s in alt.take(2)) {
      lines.add(ReceiptLine(s, size: 8, center: true, spaceAfter: 1));
    }
    return lines;
  }

  static List<ReceiptLine> _tarihSatiri(String etiket, String deger) {
    return [
      ReceiptLine(
          '${etiket.trim()}: ${deger.trim()}',
          size: 9,
          spaceAfter: 6),
    ];
  }

  // ----------------------------------------------------------------- fişler

  static List<ReceiptLine> oduncFisi({
    required KurumBilgisi kurum,
    required String operator,
    required String tarih,
    required String ogrenci,
    required String sinif,
    required String kitap,
    required String yazar,
    required String barkod,
    required String oduncTarihi,
    required String iadeTarihi,
  }) {
    return [
      ...baslik(kurum, 'ÖDÜNÇ FİŞİ'),
      ..._tarihSatiri('Tarih', tarih),
      ReceiptLine(ogrenci, bold: true, size: 11, spaceAfter: 1),
      if (sinif.trim().isNotEmpty)
        ReceiptLine(sinif, size: 9, spaceAfter: 5),
      const ReceiptLine('', divider: true, spaceAfter: 3),
      ReceiptLine(kitap, bold: true, size: 11, spaceAfter: 1),
      if (yazar.trim().isNotEmpty) ReceiptLine(yazar, size: 9, spaceAfter: 1),
      ReceiptLine('Barkod: ${barkod.trim()}', size: 10, spaceAfter: 5),
      const ReceiptLine('', divider: true, spaceAfter: 3),
      ..._tarihSatiri('Ödünç', oduncTarihi),
      ReceiptLine('İADE TARİHİ: ${iadeTarihi.trim()}',
          bold: true, size: 11, spaceAfter: 6),
      ReceiptLine('Operatör: ${operator.trim()}', size: 9, spaceAfter: 2),
      ...altBilgi(kurum),
    ];
  }

  static List<ReceiptLine> iadeFisi({
    required KurumBilgisi kurum,
    required String operator,
    required String tarih,
    required String ogrenci,
    required String sinif,
    required String kitap,
    required String yazar,
    required String barkod,
    required String durumEtiketi,
    String cezaTutari = '',
    String odemeNotu = '',
  }) {
    return [
      ...baslik(kurum, 'İADE FİŞİ'),
      ..._tarihSatiri('Tarih', tarih),
      ReceiptLine(ogrenci, bold: true, size: 11, spaceAfter: 1),
      if (sinif.trim().isNotEmpty)
        ReceiptLine(sinif, size: 9, spaceAfter: 5),
      const ReceiptLine('', divider: true, spaceAfter: 3),
      ReceiptLine(kitap, bold: true, size: 11, spaceAfter: 1),
      if (yazar.trim().isNotEmpty) ReceiptLine(yazar, size: 9, spaceAfter: 1),
      ReceiptLine('Barkod: ${barkod.trim()}', size: 10, spaceAfter: 5),
      ReceiptLine('İade durumu: ${durumEtiketi.trim()}',
          bold: true, size: 10, spaceAfter: 2),
      if (cezaTutari.trim().isNotEmpty)
        ReceiptLine(cezaTutari, size: 10, spaceAfter: 2),
      if (odemeNotu.trim().isNotEmpty)
        ReceiptLine(odemeNotu, size: 9, spaceAfter: 2),
      ReceiptLine('Operatör: ${operator.trim()}', size: 9, spaceAfter: 2),
      ...altBilgi(kurum),
    ];
  }

  static List<ReceiptLine> borcuYoktur({
    required KurumBilgisi kurum,
    required String operator,
    required String tarih,
    required String ogrenci,
    required String sinif,
    required String aktifOdunc,
  }) {
    return [
      ...baslik(kurum, 'BORÇSÜZLÜK BELGESİ'),
      ..._tarihSatiri('Tarih', tarih),
      ReceiptLine(
          '${ogrenci.trim()}${sinif.trim().isNotEmpty ? ' • ${sinif.trim()}' : ''}',
          bold: true,
          size: 11,
          spaceAfter: 6),
      ReceiptLine('Kütüphane kayıtlarımıza göre öğrencinin',
          size: 9, spaceAfter: 1),
      ReceiptLine('aktif ödünç sayısı: ${aktifOdunc.trim()}',
          size: 9, spaceAfter: 1),
      ReceiptLine('Gecikme borcu: YOKTUR', bold: true, size: 11, spaceAfter: 8),
      ReceiptLine('İmza/Kaşe:', size: 9, spaceAfter: 10),
      ReceiptLine('Operatör: ${operator.trim()}', size: 9, spaceAfter: 2),
      ...altBilgi(kurum),
    ];
  }

  static List<ReceiptLine> cezaOdemeFisi({
    required KurumBilgisi kurum,
    required String operator,
    required String tarih,
    required String ogrenci,
    required String sinif,
    required String tutar,
    String kalan = '',
  }) {
    return [
      ...baslik(kurum, 'CEZA TAHSİLAT FİŞİ'),
      ..._tarihSatiri('Tarih', tarih),
      ReceiptLine(
          '${ogrenci.trim()}${sinif.trim().isNotEmpty ? ' • ${sinif.trim()}' : ''}',
          bold: true,
          size: 11,
          spaceAfter: 5),
      const ReceiptLine('', divider: true, spaceAfter: 3),
      ReceiptLine('Ödenen tutar: ${tutar.trim()} ₺',
          bold: true, size: 12, spaceAfter: 3),
      if (kalan.trim().isNotEmpty)
        ReceiptLine('Kalan borç: ${kalan.trim()} ₺', size: 10, spaceAfter: 2),
      ReceiptLine('Operatör: ${operator.trim()}', size: 9, spaceAfter: 2),
      ...altBilgi(kurum),
    ];
  }

  static List<ReceiptLine> sifreFisi({
    required KurumBilgisi kurum,
    required String operator,
    required String tarih,
    required String ogrenci,
    required String kullaniciAdi,
    required String sifre,
  }) {
    return [
      ...baslik(kurum, 'ÜYE GİRİŞ BİLGİLERİ'),
      ..._tarihSatiri('Tarih', tarih),
      ReceiptLine(ogrenci, bold: true, size: 11, spaceAfter: 5),
      const ReceiptLine('', divider: true, spaceAfter: 3),
      ReceiptLine('Kullanıcı adı: ${kullaniciAdi.trim()}',
          bold: true, size: 11, spaceAfter: 2),
      ReceiptLine('Şifre: ${sifre.trim()}', bold: true, size: 11, spaceAfter: 6),
      ReceiptLine('İlk girişte şifrenizi değiştirmeniz istenir.',
          size: 8, center: true, spaceAfter: 2),
      ReceiptLine('Operatör: ${operator.trim()}', size: 9, spaceAfter: 2),
      ...altBilgi(kurum),
    ];
  }

  // --------------------------------------------------------------- PDF üretimi

  /// Fiş satırlarını fiş genişliğinde PDF yapar (yükseklik içeriğe göre).
  /// `genislikMm` verilmezse varsayılan 70 mm (K14.8) kullanılır.
  static Future<List<int>> render(List<ReceiptLine> lines,
      {double? genislikMm}) async {
    final regular = await PrintFonts.regular();
    final bold = await PrintFonts.bold();

    final w = (genislikMm ?? ReceiptPdf.genislikMm) * mm;
    final margin = kenarMm * mm;
    double h = margin * 2;
    for (final l in lines) {
      h += (l.divider ? 3.0 : l.size * 1.35) + l.spaceAfter;
    }
    final minH = minYukseklikMm * mm;
    final pageH = h < minH ? minH : h;

    final children = <pw.Widget>[];
    for (final l in lines) {
      if (l.divider) {
        children.add(pw.Container(
            height: 2,
            margin: const pw.EdgeInsets.symmetric(vertical: 1),
            color: PdfColors.black));
        continue;
      }
      final text = pw.Text(l.text,
          style: pw.TextStyle(font: l.bold ? bold : regular, fontSize: l.size));
      children.add(pw.Container(
        alignment: l.center ? pw.Alignment.center : pw.Alignment.centerLeft,
        margin: pw.EdgeInsets.only(bottom: l.spaceAfter),
        child: text,
      ));
    }

    final doc = pw.Document();
    doc.addPage(pw.Page(
      pageFormat: PdfPageFormat(w, pageH, marginAll: margin),
      build: (_) => pw.Column(
        crossAxisAlignment: pw.CrossAxisAlignment.stretch,
        mainAxisSize: pw.MainAxisSize.min,
        children: children,
      ),
    ));
    return doc.save();
  }
}