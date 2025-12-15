import 'dart:convert';

class BookSummary {
  BookSummary({
    required this.id,
    required this.baslik,
    this.yazar,
    this.kategori,
    this.nushaSayisi,
    this.yayinYili,
    this.isbn,
    this.imageCount = 0,
    this.aciklamaVar = false,
    this.shelfCodes = const [],
  });

  final int id;
  final String baslik;
  final String? yazar;
  final String? kategori;
  final int? nushaSayisi;
  final int? yayinYili;
  final String? isbn;
  final int imageCount;
  final bool aciklamaVar;
  final List<String> shelfCodes;

  factory BookSummary.fromJson(Map<String, dynamic> json) {
    final yazarRaw = json["yazar"];
    final kategoriRaw = json["kategori"];
    final rafListe = <String>[];
    if (json["raf_kodlari"] is List) {
      rafListe.addAll(
        (json["raf_kodlari"] as List)
            .where((e) => e != null)
            .map((e) => e.toString())
            .where((e) => e.isNotEmpty),
      );
    }
    return BookSummary(
      id: _toInt(json["id"]),
      baslik: (json["baslik"] ?? "").toString(),
      yazar: _extractName(yazarRaw, "ad_soyad"),
      kategori: _extractName(kategoriRaw, "ad"),
      nushaSayisi: _toNullableInt(json["nusha_sayisi"]),
      yayinYili: _toNullableInt(json["yayin_yili"]),
      isbn: json["isbn"]?.toString(),
      imageCount: _toNullableInt(json["image_count"]) ?? 0,
      aciklamaVar: _toBool(json["aciklama_var"]),
      shelfCodes: rafListe,
    );
  }

  BookSummary copyWith({
    String? baslik,
    String? yazar,
    String? kategori,
    int? nushaSayisi,
    int? yayinYili,
    String? isbn,
    int? imageCount,
    bool? aciklamaVar,
    List<String>? shelfCodes,
  }) {
    return BookSummary(
      id: id,
      baslik: baslik ?? this.baslik,
      yazar: yazar ?? this.yazar,
      kategori: kategori ?? this.kategori,
      nushaSayisi: nushaSayisi ?? this.nushaSayisi,
      yayinYili: yayinYili ?? this.yayinYili,
      isbn: isbn ?? this.isbn,
      imageCount: imageCount ?? this.imageCount,
      aciklamaVar: aciklamaVar ?? this.aciklamaVar,
      shelfCodes: shelfCodes ?? this.shelfCodes,
    );
  }
}

class BookDetail extends BookSummary {
  BookDetail({
    required super.id,
    required super.baslik,
    super.yazar,
    super.kategori,
    super.nushaSayisi,
    super.yayinYili,
    super.isbn,
    super.imageCount = 0,
    super.aciklamaVar = false,
    super.shelfCodes = const [],
    this.aciklama,
    this.resimler = const [],
  });

  final String? aciklama;
  final List<BookImageSlot> resimler;

  BookDetail copyWith({
    String? baslik,
    String? yazar,
    String? kategori,
    int? nushaSayisi,
    int? yayinYili,
    String? isbn,
    int? imageCount,
    bool? aciklamaVar,
    List<String>? shelfCodes,
    String? aciklama,
    List<BookImageSlot>? resimler,
  }) {
    return BookDetail(
      id: id,
      baslik: baslik ?? this.baslik,
      yazar: yazar ?? this.yazar,
      kategori: kategori ?? this.kategori,
      nushaSayisi: nushaSayisi ?? this.nushaSayisi,
      yayinYili: yayinYili ?? this.yayinYili,
      isbn: isbn ?? this.isbn,
      imageCount: imageCount ?? this.imageCount,
      aciklamaVar: aciklamaVar ?? this.aciklamaVar,
      shelfCodes: shelfCodes ?? this.shelfCodes,
      aciklama: aciklama ?? this.aciklama,
      resimler: resimler ?? this.resimler,
    );
  }

  factory BookDetail.fromJson(Map<String, dynamic> json) {
    final summary = BookSummary.fromJson(json);
    final images = <BookImageSlot>[];
    for (var i = 1; i <= 5; i++) {
      images.add(BookImageSlot(index: i, url: json["resim$i"]?.toString()));
    }

    return BookDetail(
      id: summary.id,
      baslik: summary.baslik,
      yazar: summary.yazar,
      kategori: summary.kategori,
      nushaSayisi: summary.nushaSayisi,
      yayinYili: summary.yayinYili,
      isbn: summary.isbn,
      imageCount: summary.imageCount,
      aciklamaVar: summary.aciklamaVar,
      shelfCodes: summary.shelfCodes,
      aciklama: json["aciklama"]?.toString(),
      resimler: images,
    );
  }
}

class BookImageSlot {
  const BookImageSlot({required this.index, this.url});

  final int index;
  final String? url;

  bool get hasImage => url != null && url!.isNotEmpty;

  BookImageSlot copyWith({String? url}) {
    return BookImageSlot(index: index, url: url ?? this.url);
  }
}

class Category {
  const Category({required this.id, required this.ad});

  final int id;
  final String ad;

  factory Category.fromJson(Map<String, dynamic> json) {
    return Category(id: _toInt(json["id"]), ad: (json["ad"] ?? "").toString());
  }
}

class Author {
  const Author({required this.id, required this.adSoyad});

  final int id;
  final String adSoyad;

  factory Author.fromJson(Map<String, dynamic> json) {
    return Author(
      id: _toInt(json["id"]),
      adSoyad: (json["ad_soyad"] ?? "").toString(),
    );
  }
}

class BookListResponse {
  const BookListResponse({required this.books, required this.totalCount});

  final List<BookSummary> books;
  final int totalCount;
}

int _toInt(dynamic value) {
  if (value is int) return value;
  return int.tryParse(value.toString()) ?? 0;
}

int? _toNullableInt(dynamic value) {
  if (value == null) return null;
  if (value is int) return value;
  return int.tryParse(value.toString());
}

String? _extractName(dynamic raw, String key) {
  if (raw == null) return null;
  if (raw is String) return raw;
  if (raw is int) return raw.toString();
  if (raw is Map<String, dynamic>) {
    if (raw.containsKey(key)) {
      return raw[key]?.toString();
    }
    if (raw.containsKey("name")) {
      return raw["name"]?.toString();
    }
    return raw.values.isNotEmpty ? raw.values.first.toString() : null;
  }
  return jsonEncode(raw);
}

bool _toBool(dynamic value) {
  if (value is bool) return value;
  if (value == null) return false;
  final normalized = value.toString().toLowerCase().trim();
  return normalized == "1" || normalized == "true" || normalized == "yes" || normalized == "evet";
}
