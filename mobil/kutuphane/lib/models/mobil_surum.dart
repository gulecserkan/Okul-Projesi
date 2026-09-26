/// Sunucudan gelen mobil sürüm bilgisi (GET /api/mobil/surum/).
class MobilSurum {
  const MobilSurum({
    required this.surum,
    required this.surumKodu,
    required this.minSurumKodu,
    required this.apkUrl,
  });

  final String surum;
  final int surumKodu;
  final int minSurumKodu;
  final String apkUrl;

  factory MobilSurum.fromJson(Map<String, dynamic> json) {
    return MobilSurum(
      surum: (json["surum"] ?? "").toString(),
      surumKodu: (json["surumKodu"] as num?)?.toInt() ?? 0,
      minSurumKodu: (json["minSurumKodu"] as num?)?.toInt() ?? 0,
      apkUrl: (json["apkUrl"] ?? "").toString(),
    );
  }
}

/// Güncelleme gerekip gerekmediğinin sonucu.
class GuncellemeKarari {
  const GuncellemeKarari({required this.guncellemeVar, required this.zorunlu});

  final bool guncellemeVar;

  /// true ise kullanıcı güncelleyene kadar uygulama kilitlenir.
  final bool zorunlu;
}

/// Kurulu sürüm kodu ile sunucudaki sürümü karşılaştırır.
GuncellemeKarari guncellemeKarari({
  required int kuruluKod,
  required MobilSurum? uzak,
}) {
  if (uzak == null || uzak.surumKodu <= kuruluKod) {
    return const GuncellemeKarari(guncellemeVar: false, zorunlu: false);
  }
  return GuncellemeKarari(
    guncellemeVar: true,
    zorunlu: kuruluKod < uzak.minSurumKodu,
  );
}
