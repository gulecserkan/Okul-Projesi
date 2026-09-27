import 'package:flutter/services.dart' show rootBundle;
import 'package:pdf/widgets.dart' as pw;

/// Fiş/etiket PDF'lerinde kullanılan gömülü fontlar (K14).
///
/// Standart PDF fontları (Helvetica vb.) Latin-1'dir; ş/ğ/İ/ı içermediklerinden
/// Türkçe çıktı için Liberation Sans (Arial benzeri) gömülür. Fontlar uygulama
/// paketiyle geldiğinden yazıcı bilgisayarda ek kurulum gerekmez.
class PrintFonts {
  static pw.Font? _regular;
  static pw.Font? _bold;

  static Future<pw.Font> regular() async => _regular ??=
      pw.Font.ttf(await rootBundle.load('assets/fonts/LiberationSans-Regular.ttf'));

  static Future<pw.Font> bold() async => _bold ??=
      pw.Font.ttf(await rootBundle.load('assets/fonts/LiberationSans-Bold.ttf'));
}