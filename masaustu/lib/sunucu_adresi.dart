import 'dart:async';

import 'api/auth_api.dart';
import 'config.dart';

/// Sunucu adaylarını **paralel** yoklar ve ilk yanıt veren adresi döner.
///
/// Amaç: alan adı (SSL) öncelikli, alan adı yoksa genel IP'ye otomatik düşmek.
/// İlk başarılı aday gelir gelmez döner; başarısız adaylar arka planda elenir
/// (ölü alan adı ek gecikme yaratmaz). Hiçbiri ulaşmazsa `null`.
Future<String?> enIyiSunucuAdresiYokla({
  List<String>? adaylar,
  Future<bool> Function(String baseUrl)? saglikKontrol,
}) {
  final liste = (adaylar ?? AppConfig.serverCandidates)
      .map((s) => s.trim())
      .where((s) => s.isNotEmpty)
      .toSet()
      .toList();
  if (liste.isEmpty) return Future.value(null);

  final kontrol = saglikKontrol ??
      (String baseUrl) => AuthApi(baseUrl: baseUrl).healthCheck();
  final completer = Completer<String?>();
  var bekleyen = liste.length;

  for (final aday in liste) {
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
