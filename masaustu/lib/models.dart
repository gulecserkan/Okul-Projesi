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

  const Ogrenci({
    required this.id,
    required this.ad,
    required this.soyad,
    required this.ogrenciNo,
    this.sinif,
    this.telefon,
    this.eposta,
    this.aktif = true,
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