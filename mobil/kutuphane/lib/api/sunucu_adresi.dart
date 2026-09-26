import 'dart:async';

import '../app_config.dart';
import 'library_api.dart';

/// Sunucu adaylarını **paralel** yoklar ve ilk yanıt veren adresi döner.
///
/// Amaç: alan adı (SSL) öncelikli, alan adı yoksa genel IP'ye otomatik düşmek.
/// İlk başarılı aday gelir gelmez döner; başarısız adaylar arka planda elenir
/// (bu sayede ölü alan adı ek gecikme yaratmaz). Hiçbiri ulaşmazsa `null`.
Future<String?> enIyiSunucuAdresiYokla({
  List<String>? adaylar,
  LibraryApiClient Function(String baseUrl)? clientFactory,
}) {
  final liste = (adaylar ?? AppConfig.effectiveServerCandidates)
      .map((s) => s.trim())
      .where((s) => s.isNotEmpty)
      .toSet()
      .toList();
  if (liste.isEmpty) return Future.value(null);

  final factory =
      clientFactory ?? (String baseUrl) => LibraryApiClient(baseUrl: baseUrl);
  final completer = Completer<String?>();
  var bekleyen = liste.length;

  for (final aday in liste) {
    factory(aday)
        .handshake()
        .then((sonuc) {
          if (sonuc.ok && !completer.isCompleted) completer.complete(aday);
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
