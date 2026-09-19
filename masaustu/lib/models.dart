class Sinif {
  final int id;
  final String ad;

  const Sinif({required this.id, required this.ad});

  factory Sinif.fromJson(Map<String, dynamic> json) =>
      Sinif(id: json['id'] as int, ad: json['ad'] as String? ?? '');
}

class Yazar {
  final int id;
  final String adSoyad;

  const Yazar({required this.id, required this.adSoyad});

  factory Yazar.fromJson(Map<String, dynamic> json) => Yazar(
      id: json['id'] as int, adSoyad: json['ad_soyad'] as String? ?? '');
}

class Kategori {
  final int id;
  final String ad;

  const Kategori({required this.id, required this.ad});

  factory Kategori.fromJson(Map<String, dynamic> json) =>
      Kategori(id: json['id'] as int, ad: json['ad'] as String? ?? '');
}

class Ogrenci {
  final int id;
  final String ad;
  final String soyad;
  final String ogrenciNo;
  final Sinif? sinif;
  final String? telefon;
  final String? eposta;
  final bool aktif;
  final String? kayitTarihi;

  const Ogrenci({
    required this.id,
    required this.ad,
    required this.soyad,
    required this.ogrenciNo,
    this.sinif,
    this.telefon,
    this.eposta,
    this.aktif = true,
    this.kayitTarihi,
  });

  String get adSoyad => '$ad $soyad';

  factory Ogrenci.fromJson(Map<String, dynamic> json) => Ogrenci(
        id: json['id'] as int,
        ad: json['ad'] as String? ?? '',
        soyad: json['soyad'] as String? ?? '',
        ogrenciNo: json['ogrenci_no'] as String? ?? '',
        sinif: json['sinif'] is Map<String, dynamic>
            ? Sinif.fromJson(json['sinif'] as Map<String, dynamic>)
            : null,
        telefon: json['telefon'] as String?,
        eposta: json['eposta'] as String?,
        aktif: json['aktif'] as bool? ?? true,
        kayitTarihi: json['kayit_tarihi'] as String?,
      );
}

class Kitap {
  final int id;
  final String baslik;
  final int? yayinYili;
  final String isbn;
  final Yazar? yazar;
  final Kategori? kategori;
  final int nushaSayisi;
  final List<String> rafKodlari;

  const Kitap({
    required this.id,
    required this.baslik,
    this.yayinYili,
    this.isbn = '',
    this.yazar,
    this.kategori,
    this.nushaSayisi = 0,
    this.rafKodlari = const [],
  });

  factory Kitap.fromJson(Map<String, dynamic> json) => Kitap(
        id: json['id'] as int,
        baslik: json['baslik'] as String? ?? '',
        yayinYili: json['yayin_yili'] as int?,
        isbn: json['isbn'] as String? ?? '',
        yazar: json['yazar'] is Map<String, dynamic>
            ? Yazar.fromJson(json['yazar'] as Map<String, dynamic>)
            : null,
        kategori: json['kategori'] is Map<String, dynamic>
            ? Kategori.fromJson(json['kategori'] as Map<String, dynamic>)
            : null,
        nushaSayisi: json['nusha_sayisi'] as int? ?? 0,
        rafKodlari: (json['raf_kodlari'] as List<dynamic>? ?? [])
            .whereType<String>()
            .toList(),
      );
}

/// Kitap nüshası (barkod, durum, raf).
class Nusha {
  final int id;
  final String barkod;
  final String durum;
  final String? rafKodu;

  const Nusha({
    required this.id,
    required this.barkod,
    required this.durum,
    this.rafKodu,
  });

  factory Nusha.fromJson(Map<String, dynamic> json) => Nusha(
        id: json['id'] as int,
        barkod: json['barkod'] as String? ?? '',
        durum: json['durum'] as String? ?? '',
        rafKodu: json['raf_kodu'] as String?,
      );
}

/// Ödünç kaydı (öğrenci geçmişi / tarihçe satırı).
class OduncKaydi {
  final int id;
  final String kitapBaslik;
  final String barkod;
  final String? oduncTarihi;
  final String? iadeTarihi;
  final String? teslimTarihi;
  final String durum;
  final String? gecikmeCezasi;

  const OduncKaydi({
    required this.id,
    required this.kitapBaslik,
    required this.barkod,
    this.oduncTarihi,
    this.iadeTarihi,
    this.teslimTarihi,
    required this.durum,
    this.gecikmeCezasi,
  });

  factory OduncKaydi.fromJson(Map<String, dynamic> json) {
    final nusha = json['kitap_nusha'];
    final kitap = nusha is Map<String, dynamic> ? nusha['kitap'] : null;
    return OduncKaydi(
      id: json['id'] as int,
      kitapBaslik: kitap is Map<String, dynamic> ? kitap['baslik'] as String? ?? '' : '',
      barkod: nusha is Map<String, dynamic> ? nusha['barkod'] as String? ?? '' : '',
      oduncTarihi: json['odunc_tarihi'] as String?,
      iadeTarihi: json['iade_tarihi'] as String?,
      teslimTarihi: json['teslim_tarihi'] as String?,
      durum: json['durum'] as String? ?? '',
      gecikmeCezasi: json['gecikme_cezasi'] as String?,
    );
  }
}

/// Ödenmemiş gecikme cezası girişi.
class PenaltyEntry {
  final int id;
  final String kitap;
  final String barkod;
  final String? teslimTarihi;
  final String gecikmeCezasi;

  const PenaltyEntry({
    required this.id,
    required this.kitap,
    required this.barkod,
    this.teslimTarihi,
    required this.gecikmeCezasi,
  });

  factory PenaltyEntry.fromJson(Map<String, dynamic> json) => PenaltyEntry(
        id: json['id'] as int,
        kitap: json['kitap'] as String? ?? '',
        barkod: json['barkod'] as String? ?? '',
        teslimTarihi: json['teslim_tarihi'] as String?,
        gecikmeCezasi: json['gecikme_cezasi'] as String? ?? '0.00',
      );
}

class PenaltySummary {
  final String outstandingTotal;
  final int outstandingCount;
  final List<PenaltyEntry> entries;

  const PenaltySummary({
    this.outstandingTotal = '0.00',
    this.outstandingCount = 0,
    this.entries = const [],
  });

  factory PenaltySummary.fromJson(Map<String, dynamic> json) => PenaltySummary(
        outstandingTotal: json['outstanding_total'] as String? ?? '0.00',
        outstandingCount: json['outstanding_count'] as int? ?? 0,
        entries: (json['entries'] as List<dynamic>? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(PenaltyEntry.fromJson)
            .toList(),
      );
}

/// fast-query'den dönen ödünç kaydı (aktif ödünç / geçmiş / nüsha sahibi).
class FastLoan {
  final int id;
  final int? copyId;
  final String durum;
  final String? oduncTarihi;
  final String? iadeTarihi;
  final String? teslimTarihi;
  final bool isOverdue;
  final int overdueDays;
  final String? penaltyPreview;
  final String? barkod;
  final String? rafKodu;
  final String? kitapBaslik;
  final String? ogrenciNo;
  final String? ogrenciAdSoyad;

  const FastLoan({
    required this.id,
    this.copyId,
    required this.durum,
    this.oduncTarihi,
    this.iadeTarihi,
    this.teslimTarihi,
    this.isOverdue = false,
    this.overdueDays = 0,
    this.penaltyPreview,
    this.barkod,
    this.rafKodu,
    this.kitapBaslik,
    this.ogrenciNo,
    this.ogrenciAdSoyad,
  });

  FastLoan copyWith({int? copyId}) => FastLoan(
        id: id,
        copyId: copyId ?? this.copyId,
        durum: durum,
        oduncTarihi: oduncTarihi,
        iadeTarihi: iadeTarihi,
        teslimTarihi: teslimTarihi,
        isOverdue: isOverdue,
        overdueDays: overdueDays,
        penaltyPreview: penaltyPreview,
        barkod: barkod,
        rafKodu: rafKodu,
        kitapBaslik: kitapBaslik,
        ogrenciNo: ogrenciNo,
        ogrenciAdSoyad: ogrenciAdSoyad,
      );

  factory FastLoan.fromJson(Map<String, dynamic> json) {
    final nusha = json['kitap_nusha'];
    final kitap = nusha is Map<String, dynamic> ? nusha['kitap'] : null;
    final ogr = json['ogrenci'];
    final fullNushaId =
        nusha is Map<String, dynamic> ? nusha['id'] as int? : null;
    return FastLoan(
      id: json['id'] as int,
      copyId: json['kitap_nusha_id'] as int? ?? fullNushaId,
      durum: json['durum'] as String? ?? '',
      oduncTarihi: json['odunc_tarihi'] as String?,
      iadeTarihi: json['iade_tarihi'] as String?,
      teslimTarihi: json['teslim_tarihi'] as String?,
      isOverdue: json['is_overdue'] as bool? ?? false,
      overdueDays: json['overdue_days'] as int? ?? 0,
      penaltyPreview: json['penalty_preview'] as String?,
      barkod: json['barkod'] as String? ??
          (nusha is Map<String, dynamic> ? nusha['barkod'] as String? : null),
      rafKodu:
          nusha is Map<String, dynamic> ? nusha['raf_kodu'] as String? : null,
      kitapBaslik: kitap is Map<String, dynamic>
          ? kitap['baslik'] as String? ?? ''
          : json['kitap'] as String?,
      ogrenciNo: ogr is Map<String, dynamic> ? ogr['ogrenci_no'] as String? : null,
      ogrenciAdSoyad: (ogr is Map<String, dynamic>)
          ? '${ogr['ad'] ?? ''} ${ogr['soyad'] ?? ''}'.trim()
          : null,
    );
  }
}

/// fast-query "student" sonucundaki öğrenci özeti.
class FastStudent {
  final int id;
  final String ad;
  final String soyad;
  final String no;
  final String? sinif;
  final String? rol;
  final bool aktif;

  const FastStudent({
    required this.id,
    required this.ad,
    required this.soyad,
    required this.no,
    this.sinif,
    this.rol,
    this.aktif = true,
  });

  String get adSoyad => '$ad $soyad';

  factory FastStudent.fromJson(Map<String, dynamic> json) => FastStudent(
        id: json['id'] as int,
        ad: json['ad'] as String? ?? '',
        soyad: json['soyad'] as String? ?? '',
        no: json['no'] as String? ?? json['ogrenci_no'] as String? ?? '',
        sinif: json['sinif'] as String?,
        rol: json['rol'] as String?,
        aktif: json['aktif'] as bool? ?? true,
      );
}

/// fast-query "book_availability" nüsha satırı (varsa aktif ödünç bilgisiyle).
class FastCopy {
  final int id;
  final String barkod;
  final String durum;
  final String? rafKodu;
  final FastLoan? loan;

  const FastCopy({
    required this.id,
    required this.barkod,
    required this.durum,
    this.rafKodu,
    this.loan,
  });

  factory FastCopy.fromJson(Map<String, dynamic> json) => FastCopy(
        id: json['id'] as int,
        barkod: json['barkod'] as String? ?? '',
        durum: json['durum'] as String? ?? '',
        rafKodu: json['raf_kodu'] as String?,
        loan: json['loan'] is Map<String, dynamic>
            ? FastLoan.fromJson(json['loan'] as Map<String, dynamic>)
            : null,
      );
}