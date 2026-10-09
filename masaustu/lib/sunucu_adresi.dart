import 'dart:async';

import 'api/auth_api.dart';
import 'config.dart';

/// Sunucu adaylarını **öncelik sırasıyla** yoklar.
///
/// Önce listenin ilk adayı (alan adı + SSL) tek başına denenir; başarılıysa
/// doğrudan döner. Yalnız ilk aday ulaşılamazsa kalan adaylar **paralel**
/// yoklanır ve ilk yanıt veren döner. Böylece alan adı kesin önceliklidir;
/// alan adı ölüyse genel IP'ye düşülür. Hiçbiri ulaşmazsa `null`.
Future<String?> enIyiSunucuAdresiYokla({
  List<String>? adaylar,
  Future<bool> Function(String baseUrl)? saglikKontrol,
}) async {
  final liste = (adaylar ?? AppConfig.serverCandidates)
      .map((s) => s.trim())
      .where((s) => s.isNotEmpty)
      .toSet()
      .toList();
  if (liste.isEmpty) return null;

  final kontrol = saglikKontrol ??
      (String baseUrl) => AuthApi(baseUrl: baseUrl).healthCheck();

  // 1) En öncelikli aday: kesin öncelik için tek başına dene.
  try {
    if (await kontrol(liste.first)) return liste.first;
  } catch (_) {
    // ilk aday ulaşılamaz → kalan adaylara düş
  }

  // 2) Kalan adaylar: paralel yokla, ilk yanıt vereni dön.
  final kalan = liste.sublist(1);
  if (kalan.isEmpty) return null;
  final completer = Completer<String?>();
  var bekleyen = kalan.length;

  for (final aday in kalan) {
    kontrol(aday)
        .then((ok) {
          if (ok && !completer.isCompleted) completer.complete(aday);
        })
        .catchError((Object _) {
          // yoklama hatası: ilgili aday elenir
        })
        .whenComplete(() {
          bekleyen--;
          if (bekleyen == 0 && !completer.isCompleted) completer.complete(null);
        });
  }
  return completer.future;
}
