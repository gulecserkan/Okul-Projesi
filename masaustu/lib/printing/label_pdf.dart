import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;

import '../config.dart';
import 'print_fonts.dart';

/// Code-128 (Set B) desenleri — eski `kutuphane_desktop/printing/label_maker_qt.py`
/// referansından taşındı (K14.4).
const List<String> _code128Patterns = [
  '212222','222122','222221','121223','121322','131222','122213','122312','132212','221213',
  '221312','231212','112232','122132','122231','113222','123122','123221','223211','221132',
  '221231','213212','223112','312131','311222','321122','321221','312212','322112','322211',
  '212123','212321','232121','111323','131123','131321','112313','132113','132311','211313',
  '231113','231311','112133','112331','132131','113123','113321','133121','313121','211331',
  '231131','213113','213311','213131','311123','311321','331121','312113','312311','332111',
  '314111','221411','431111','111224','111422','121124','121421','141122','141221','112214',
  '112412','122114','122411','142112','142211','241211','221114','413111','241112','134111',
  '111242','121142','121241','114212','124112','124211','411212','421112','421211','212141',
  '214121','412121','111143','111341','131141','114113','114311','411113','411311','113141',
  '114131','311141','411131','211412','211214','211232','2331112'
];

List<int> _code128Codes(String text) {
  final codes = <int>[104];
  for (final ch in text.codeUnits) {
    if (ch >= 32 && ch <= 126) {
      codes.add(ch - 32);
    } else {
      codes.add(0);
    }
  }
  var checksum = 104;
  for (var i = 1; i < codes.length; i++) {
    checksum += codes[i] * i;
  }
  codes.add(checksum % 103);
  codes.add(106);
  return codes;
}

int _patternModules(int code) {
  if (code < 0 || code >= _code128Patterns.length) return 11;
  var total = 0;
  for (final c in _code128Patterns[code].codeUnits) {
    total += c - 0x30;
  }
  return total;
}

/// Toplam modül sayısı (stop sonrası 2 modüllük kapanış barı dahil).
int _totalModules(List<int> codes) {
  var total = 0;
  for (final c in codes) {
    total += _patternModules(c);
  }
  total += 2; // stop kapanış barı
  return total;
}

/// Etiket PDF üretimi (K14.4). `genislikMm`/`yukseklikMm` verilmezse
/// varsayılan 57×40 mm (K14.8) kullanılır; ayarlardan değiştirilebilir.
class LabelPdf {
  static const double mm = PdfPageFormat.mm;
  static const double genislikMm = 57;
  static const double yukseklikMm = 40;
  static const double kenarMm = 3;

  static Future<List<int>> render({
    required KurumBilgisi kurum,
    required String baslik,
    required String yazar,
    required String kategori,
    required String barkodMetni,
    double? genislikMm,
    double? yukseklikMm,
  }) async {
    final regular = await PrintFonts.regular();
    final bold = await PrintFonts.bold();

    final w = (genislikMm ?? LabelPdf.genislikMm) * mm;
    final h = (yukseklikMm ?? LabelPdf.yukseklikMm) * mm;
    final margin = kenarMm * mm;

    final doc = pw.Document();
    doc.addPage(pw.Page(
      pageFormat: PdfPageFormat(w, h, marginAll: margin),
      build: (_) => pw.Column(
        crossAxisAlignment: pw.CrossAxisAlignment.start,
        mainAxisSize: pw.MainAxisSize.min,
        children: [
          if (kurum.baslik.trim().isNotEmpty)
            pw.Container(
              margin: const pw.EdgeInsets.only(bottom: 2),
              child: pw.Text(kurum.baslik.trim(),
                  style: pw.TextStyle(font: bold, fontSize: 8)),
            ),
          pw.Container(
            margin: const pw.EdgeInsets.only(bottom: 2),
            child: pw.Text(baslik.trim(),
                maxLines: 2,
                style: pw.TextStyle(font: bold, fontSize: 12)),
          ),
          if (yazar.trim().isNotEmpty)
            pw.Container(
              margin: const pw.EdgeInsets.only(bottom: 1),
              child: pw.Text(yazar.trim(),
                  style: pw.TextStyle(font: regular, fontSize: 8)),
            ),
          if (kategori.trim().isNotEmpty)
            pw.Container(
              margin: const pw.EdgeInsets.only(bottom: 3),
              child: pw.Text(kategori.trim(),
                  style: pw.TextStyle(font: regular, fontSize: 8)),
            ),
          pw.Container(
            alignment: pw.Alignment.centerLeft,
            margin: const pw.EdgeInsets.only(bottom: 2),
            child: pw.Text(barkodMetni.trim(),
                style: pw.TextStyle(font: bold, fontSize: 10)),
          ),
          pw.Spacer(),
          _BarcodeView(barkodMetni.trim(), bottom: 0, genislikMm: w / mm),
        ],
      ),
    ));
    return doc.save();
  }
}

/// Code-128 barkod görseli (dikdörtgenlerle çizilir).
class _BarcodeView extends pw.StatelessWidget {
  _BarcodeView(this.text, {this.bottom = 0, double? genislikMm})
      : _genislikMm = genislikMm ?? LabelPdf.genislikMm;

  final String text;
  final double bottom;
  final double _genislikMm;

  @override
  pw.Widget build(pw.Context context) {
    final codes = _code128Codes(text.isEmpty ? ' ' : text);
    final total = _totalModules(codes);
    final available = _genislikMm * LabelPdf.mm - 2 * LabelPdf.kenarMm * LabelPdf.mm;
    double module = available / total;
    if (module > 1.2) module = 1.2;
    final barHeight = 30.0;

    final children = <pw.Widget>[];
    var isBar = true;
    for (final code in codes) {
      for (final c in _code128Patterns[code].codeUnits) {
        final width = (c - 0x30) * module;
        children.add(pw.Container(
          width: width,
          height: barHeight,
          color: isBar ? PdfColors.black : PdfColors.white,
        ));
        isBar = !isBar;
      }
    }
    // stop 2-modül kapanış barı
    children.add(pw.Container(
      width: 2 * module,
      height: barHeight,
      color: PdfColors.black,
    ));

    return pw.Row(
      mainAxisSize: pw.MainAxisSize.min,
      children: children,
    );
  }
}