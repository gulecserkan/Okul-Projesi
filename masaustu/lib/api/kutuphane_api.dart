import 'dart:convert';

import 'package:http/http.dart' as http;

import '../api_client.dart';
import '../models.dart';

/// Kayıt bloklandığında (K8.1) dönen mevcut eşleşme satırı.
typedef BenzerKitapDetay = ({int id, String baslik, int nushaSayisi});

/// Liste ve arama uç noktaları (üye / kitap / sınıf).
class KutuphaneApi {
  final ApiClient _client;

  KutuphaneApi({ApiClient? client}) : _client = client ?? ApiClient();

  static List<dynamic> _extractList(http.Response resp) {
    final data = jsonDecode(resp.body);
    if (data is List) return data;
    if (data is Map && data['results'] is List) return data['results'] as List;
    return const [];
  }

  /// Sayfalı liste sonucu.
  Future<Page<Map<String, dynamic>>> _page(
    String path, {
    int page = 1,
    int pageSize = 50,
    String? q,
    String? ordering,
  }) async {
    final params = <String, String>{
      'page': '$page',
      'page_size': '$pageSize',
      if (q != null && q.isNotEmpty) 'q': q,
      if (ordering != null && ordering.isNotEmpty) 'ordering': ordering,
    };
    final resp = await _client.request(
      'GET',
      '$path?${Uri(queryParameters: params).query}',
      auth: true,
    );
    if (resp.statusCode != 200) {
      return const Page(items: [], total: 0);
    }
    final data = jsonDecode(resp.body);
    final items = data is List
        ? data.whereType<Map<String, dynamic>>().toList()
        : ((data['results'] as List<dynamic>?) ?? const [])
            .whereType<Map<String, dynamic>>()
            .toList();
    final total = data is Map ? (data['count'] as int? ?? items.length) : items.length;
    final hasNext = data is Map && (data['next'] as String?)?.isNotEmpty == true;
    return Page(
      items: items,
      total: total,
      nextPage: hasNext ? page + 1 : null,
    );
  }

  Future<Page<Uye>> studentsPage({
    int page = 1,
    int pageSize = 50,
    String? q,
    String? ordering,
  }) async {
    final res = await _page('uyeler',
        page: page, pageSize: pageSize, q: q, ordering: ordering);
    return Page(
      items: res.items.map(Uye.fromJson).toList(),
      total: res.total,
      nextPage: res.nextPage,
    );
  }

  Future<Page<Kitap>> booksPage({
    int page = 1,
    int pageSize = 50,
    String? q,
    String? ordering,
  }) async {
    final res = await _page('kitaplar',
        page: page, pageSize: pageSize, q: q, ordering: ordering);
    return Page(
      items: res.items.map(Kitap.fromJson).toList(),
      total: res.total,
      nextPage: res.nextPage,
    );
  }

  /// Tüm sayfaları çeker (koşullu sayfalama: sayfa yoksa düz dizi döner).
  Future<List<dynamic>> _fetchAllPages(String path) async {
    final results = <dynamic>[];
    var url = path;
    for (var i = 0; i < 50; i++) {
      final resp = await _client.request('GET', url, auth: true);
      if (resp.statusCode != 200) break;
      final data = jsonDecode(resp.body);
      if (data is List) {
        results.addAll(data);
        break;
      }
      if (data is Map) {
        results.addAll(data['results'] as List<dynamic>? ?? const []);
        final next = data['next'] as String?;
        if (next == null || next.isEmpty) break;
        if (i == 49) break;
        url = Uri.parse(next).path + (Uri.parse(next).query.isEmpty ? '' : '?${Uri.parse(next).query}');
      }
    }
    return results;
  }

  /// Kamuya açık sayfalama-sız liste (yazar/kategori/raf vb.).
  Future<List<dynamic>> fetchAllPages(String path) => _fetchAllPages(path);

  Future<List<Uye>> students() async {
    final data = await _fetchAllPages('uyeler/');
    return data
        .whereType<Map<String, dynamic>>()
        .map(Uye.fromJson)
        .toList();
  }

  Future<List<Kitap>> books() async {
    final data = await _fetchAllPages('kitaplar/');
    return data
        .whereType<Map<String, dynamic>>()
        .map(Kitap.fromJson)
        .toList();
  }

  Future<List<Sinif>> siniflar() async {
    final resp = await _client.request('GET', 'siniflar/', auth: true);
    if (resp.statusCode != 200) return const [];
    return _extractList(resp)
        .whereType<Map<String, dynamic>>()
        .map(Sinif.fromJson)
        .toList();
  }

  Future<List<Nusha>> copies(int kitapId) async {
    final resp = await _client.request('GET', 'nushalar/?kitap=$kitapId', auth: true);
    if (resp.statusCode != 200) return const [];
    return _extractList(resp)
        .whereType<Map<String, dynamic>>()
        .map(Nusha.fromJson)
        .toList();
  }

  Future<List<OduncKaydi>> studentHistory(String uyeNo) async {
    final resp = await _client
        .request('GET', 'uye-gecmis/$uyeNo/', auth: true);
    if (resp.statusCode != 200) return const [];
    return _extractList(resp)
        .whereType<Map<String, dynamic>>()
        .map(OduncKaydi.fromJson)
        .toList();
  }

  Future<PenaltySummary> studentPenalties(String uyeNo) async {
    final resp = await _client
        .request('GET', 'uye-ceza/$uyeNo/', auth: true);
    if (resp.statusCode != 200) return const PenaltySummary();
    try {
      return PenaltySummary.fromJson(
          jsonDecode(resp.body) as Map<String, dynamic>);
    } catch (_) {
      return const PenaltySummary();
    }
  }

  /// Ana sayfa: aktif (ödünçte + gecikmiş) ödünç kayıtları.
  Future<List<OduncKaydi>> aktifOduncler() async {
    final data = <dynamic>[];
    for (final durum in ['oduncte', 'gecikmis']) {
      data.addAll(await _fetchAllPages('oduncler/?durum=$durum'));
    }
    return data
        .whereType<Map<String, dynamic>>()
        .map(OduncKaydi.fromJson)
        .toList();
  }

  /// Bir liste ucunun toplam kayıt sayısı (pagination `count`).
  Future<int> count(String path) async {
    final resp = await _client.request('GET', path, auth: true);
    if (resp.statusCode != 200) return 0;
    try {
      final data = jsonDecode(resp.body);
      if (data is Map && data['count'] is int) return data['count'] as int;
      if (data is List) return data.length;
    } catch (_) {}
    return 0;
  }

  /// Hızlı tarama: barkod / üye no / ISBN / başlık. Ham JSON döner.
  Future<Map<String, dynamic>?> fastQuery(String q) async {
    final resp = await _client.request(
      'GET',
      'fast-query/?q=${Uri.encodeQueryComponent(q)}',
      auth: true,
    );
    if (resp.statusCode != 200) return null;
    try {
      return jsonDecode(resp.body) as Map<String, dynamic>?;
    } catch (_) {
      return null;
    }
  }

  /// Ödünç ver: POST /api/checkout/ {uye_no, barkod}.
  Future<http.Response> checkout(String uyeNo, String barkod) {
    return _client.request(
      'POST',
      'checkout/',
      auth: true,
      body: {'uye_no': uyeNo, 'barkod': barkod},
    );
  }

  /// Ödünç kaydını kapatır (atomik: ödünç + nüsha + ceza).
  /// `POST /api/oduncler/{id}/kapat/`
  Future<http.Response> closeLoan(
    int loanId, {
    required String durum,
    required String teslimTarihi,
    String? gecikmeCezasi,
    bool odendi = false,
    String? kapanisNotu,
  }) {
    return _client.request(
      'POST',
      'oduncler/$loanId/kapat/',
      auth: true,
      body: {
        'durum': durum,
        'teslim_tarihi': teslimTarihi,
        if (gecikmeCezasi != null && gecikmeCezasi.trim().isNotEmpty)
          'gecikme_cezasi': gecikmeCezasi.trim(),
        if (odendi) 'gecikme_cezasi_odendi': true,
        if (kapanisNotu != null && kapanisNotu.trim().isNotEmpty)
          'kapanis_notu': kapanisNotu.trim(),
      },
    );
  }

  /// Üye aktif/pasif değişimi (yalnızca admin). Uyarıları döndürür.
  Future<({bool ok, List<String> warnings, String error})> setStudentStatus(
    int studentId,
    bool aktif,
  ) async {
    try {
      final resp = await _client.request(
        'POST',
        'uyeler/$studentId/durum/',
        auth: true,
        body: {'aktif': aktif},
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final data = jsonDecode(utf8.decode(resp.bodyBytes));
        final warnings = data is Map && data['warnings'] is List
            ? (data['warnings'] as List).whereType<String>().toList()
            : <String>[];
        return (ok: true, warnings: warnings, error: '');
      }
      return (ok: false, warnings: const <String>[], error: extractError(resp));
    } catch (_) {
      return (ok: false, warnings: const <String>[], error: 'İşlem yapılamadı.');
    }
  }

  /// Üye oluşturur veya düzenler (id verilirse PATCH). Faz B.
  /// Yalnızca profil alanları; aktif/pasif değişimi `setStudentStatus` ile yapılır.
  Future<({Uye? uye, String? error})> saveStudent({
    int? id,
    required String ad,
    required String soyad,
    required String uyeNo,
    int? sinifId,
    String? telefon,
    String? eposta,
    String? sifre,
    int? rolId,
  }) async {
    final trimmedTel = telefon?.trim();
    final trimmedEposta = eposta?.trim();
    final trimmedSifre = sifre?.trim();
    final body = <String, dynamic>{
      'ad': ad.trim(),
      'soyad': soyad.trim(),
      'uye_no': uyeNo.trim(),
      'sinif_id': ?sinifId,
      'rol_id': ?rolId,
      if (trimmedTel != null && trimmedTel.isNotEmpty) 'telefon': trimmedTel,
      if (trimmedEposta != null && trimmedEposta.isNotEmpty)
        'eposta': trimmedEposta,
      // K9: üye mobil girişi için başlangıç/yeni şifre (boşsa değişmez).
      if (trimmedSifre != null && trimmedSifre.isNotEmpty) 'sifre': trimmedSifre,
    };
    try {
      final resp = id == null
          ? await _client.request('POST', 'uyeler/', auth: true, body: body)
          : await _client.request(
              'PATCH', 'uyeler/$id/', auth: true, body: body);
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        return (
          uye: Uye.fromJson(jsonDecode(utf8.decode(resp.bodyBytes))),
          error: null,
        );
      }
      return (uye: null, error: extractError(resp));
    } catch (_) {
      return (uye: null, error: 'İşlem yapılamadı.');
    }
  }

  /// Üye siler (yalnızca admin; ödünç geçmişi varsa backend reddeder). Faz B.
  Future<({bool ok, String? error})> deleteStudent(int id) async {
    try {
      final resp =
          await _client.request('DELETE', 'uyeler/$id/', auth: true);
      if (resp.statusCode == 204 || resp.statusCode == 200) {
        return (ok: true, error: null);
      }
      return (ok: false, error: extractError(resp));
    } catch (_) {
      return (ok: false, error: 'Silme yapılamadı.');
    }
  }

  /// K9: üye mobil giriş şifresini verir/sıfırlar. Backend ilk girişte
  /// değiştirme zorunluluğu getirir (parola_degistirilsin).
  Future<({bool ok, String? error})> setPassword(int id, String sifre) async {
    try {
      final resp = await _client.request(
        'PATCH',
        'uyeler/$id/',
        auth: true,
        body: {'sifre': sifre.trim()},
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        return (ok: true, error: null);
      }
      return (ok: false, error: extractError(resp));
    } catch (_) {
      return (ok: false, error: 'Şifre güncellenemedi.');
    }
  }

  /// Üye rolleri (Editör/Öğretmen/Öğrenci).
  Future<List<Map<String, dynamic>>> roller() async {
    final data = await _fetchAllPages('roller/');
    return data.whereType<Map<String, dynamic>>().toList();
  }

  /// K9.13: toplu öğrenci içe aktarma (CSV). `dryRun=true` yalnız önizleme
  /// döndürür, `false` uygular. `yenidenKullan` pasif (mezun) çakışmasını
  /// yeniden kullanır.
  Future<({Map<String, dynamic>? data, String? error})> ogrenciImport(
    String csv, {
    bool dryRun = true,
    bool yenidenKullan = false,
  }) async {
    try {
      final resp = await _client.request(
        'POST',
        'uyeler/import/',
        auth: true,
        body: {
          'csv': csv,
          'dry_run': dryRun,
          'yeniden_kullan': yenidenKullan,
        },
      );
      final data = jsonDecode(utf8.decode(resp.bodyBytes));
      if (resp.statusCode >= 200 &&
          resp.statusCode < 300 &&
          data is Map<String, dynamic>) {
        return (data: data, error: null);
      }
      return (data: null, error: extractError(resp));
    } catch (_) {
      return (data: null, error: 'İçe aktarma başlatılamadı.');
    }
  }

  /// Kayıp/hasarlı ceza önerisi dahil ödünç politikasını getirir.
  Future<(String? kayipHasarCezasi, String? error)> fetchLoanPolicy() async {
    try {
      final resp = await _client.request('GET', 'settings/loans/', auth: true);
      if (resp.statusCode < 200 || resp.statusCode >= 300) {
        return (null, 'Politika alınamadı (${resp.statusCode})');
      }
      final data = jsonDecode(utf8.decode(resp.bodyBytes));
      if (data is! Map<String, dynamic>) return (null, null);
      final val = data['kayip_hasar_cezasi'];
      if (val is num) return (val.toString(), null);
      if (val is String && val.trim().isNotEmpty) return (val.trim(), null);
      return (null, null);
    } catch (_) {
      return (null, 'Politika alınamadı');
    }
  }

  // --- Ayarlar (K10) ---

  Future<({Map<String, dynamic>? data, String? error})> _settingsGet(
      String path) async {
    try {
      final resp = await _client.request('GET', path, auth: true);
      if (resp.statusCode < 200 || resp.statusCode >= 300) {
        return (data: null, error: extractError(resp, fallback: 'Ayarlar alınamadı.'));
      }
      final data = jsonDecode(utf8.decode(resp.bodyBytes));
      if (data is Map<String, dynamic>) return (data: data, error: null);
      return (data: null, error: 'Beklenmeyen yanıt.');
    } catch (_) {
      return (data: null, error: 'Ayarlar alınamadı.');
    }
  }

  Future<({bool ok, String? error})> _settingsPut(
      String path, Object body) async {
    try {
      final resp = await _client.request('PUT', path, auth: true, body: body);
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        return (ok: true, error: null);
      }
      return (ok: false, error: extractError(resp, fallback: 'Ayarlar kaydedilemedi.'));
    } catch (_) {
      return (ok: false, error: 'Ayarlar kaydedilemedi.');
    }
  }

  Future<({Map<String, dynamic>? data, String? error})> loanPolicyGet() =>
      _settingsGet('settings/loans/');

  Future<({bool ok, String? error})> loanPolicyUpdate(
          Map<String, dynamic> body) =>
      _settingsPut('settings/loans/', body);

  Future<({List<dynamic>? data, String? error})> roleLoanPolicies() async {
    try {
      final resp =
          await _client.request('GET', 'settings/loans/roles/', auth: true);
      if (resp.statusCode < 200 || resp.statusCode >= 300) {
        return (data: null, error: extractError(resp, fallback: 'Rol ayarları alınamadı.'));
      }
      final data = jsonDecode(utf8.decode(resp.bodyBytes));
      if (data is List) return (data: data, error: null);
      return (data: null, error: 'Beklenmeyen yanıt.');
    } catch (_) {
      return (data: null, error: 'Rol ayarları alınamadı.');
    }
  }

  Future<({bool ok, String? error})> roleLoanPoliciesUpdate(
          List<dynamic> body) =>
      _settingsPut('settings/loans/roles/', body);

  Future<({Map<String, dynamic>? data, String? error})>
      notificationSettingsGet() => _settingsGet('settings/notifications/');

  Future<({bool ok, String? error})> notificationSettingsUpdate(
          Map<String, dynamic> body) =>
      _settingsPut('settings/notifications/', body);

  Future<({Map<String, dynamic>? data, String? error})> kurumAyarlariGet() =>
      _settingsGet('settings/kurum/');

  Future<({bool ok, String? error})> kurumAyarlariUpdate(
          Map<String, dynamic> body) =>
      _settingsPut('settings/kurum/', body);
/// Kitap oluşturur/düzenler (id verilirse PATCH). Faz C.
/// K8.1: eşleşen mevcut kayıt olursa `benzerler`/`isbnEslesme` ile 409 bildirilir.
  Future<({
    Kitap? kitap,
    List<BenzerKitapDetay> benzerler,
    bool isbnEslesme,
    String? error,
  })> saveBook({
    int? id,
    required String baslik,
    int? yayinYili,
    String isbn = '',
    String aciklama = '',
    String? kapakUrl,
    int? yazarId,
    int? kategoriId,
    bool force = false,
  }) async {
    final trimmedIsbn = isbn.trim();
    final body = <String, dynamic>{
      'baslik': baslik.trim(),
      'yayin_yili': ?yayinYili,
      if (trimmedIsbn.isNotEmpty) 'isbn': trimmedIsbn,
      if (aciklama.trim().isNotEmpty) 'aciklama': aciklama.trim(),
      if (kapakUrl != null && kapakUrl.trim().isNotEmpty)
        'kapak_url': kapakUrl.trim(),
      'yazar_id': ?yazarId,
      'kategori_id': ?kategoriId,
      'force': force,
    };
    try {
      final resp = id == null
          ? await _client.request('POST', 'kitaplar/', auth: true, body: body)
          : await _client.request(
              'PATCH', 'kitaplar/$id/', auth: true, body: body);
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        return (
          kitap: Kitap.fromJson(jsonDecode(utf8.decode(resp.bodyBytes))),
          benzerler: const <BenzerKitapDetay>[],
          isbnEslesme: false,
          error: null,
        );
      }
      if (resp.statusCode == 409) {
        final benzerler = <BenzerKitapDetay>[];
        var isbnEslesme = false;
        try {
          final data = jsonDecode(utf8.decode(resp.bodyBytes));
          if (data is Map<String, dynamic>) {
            isbnEslesme = data['isbn_eslesme'] == true;
            final lst = data['benzerler'];
            if (lst is List) {
              for (final e in lst) {
                if (e is Map<String, dynamic>) {
                  benzerler.add((
                    id: (e['id'] as num).toInt(),
                    baslik: (e['baslik'] ?? '').toString(),
                    nushaSayisi: (e['nusha_sayisi'] as num?)?.toInt() ?? 0,
                  ));
                }
              }
            }
          }
        } catch (_) {}
        return (
          kitap: null,
          benzerler: benzerler,
          isbnEslesme: isbnEslesme,
          error: extractError(resp),
        );
      }
      return (
        kitap: null,
        benzerler: const <BenzerKitapDetay>[],
        isbnEslesme: false,
        error: extractError(resp),
      );
    } catch (_) {
      return (
        kitap: null,
        benzerler: const <BenzerKitapDetay>[],
        isbnEslesme: false,
        error: 'İşlem yapılamadı.',
      );
    }
  }

  /// Kitap siler (yalnızca admin; ödünç geçmişi varsa backend reddeder). Faz C.
  Future<({bool ok, String? error})> deleteBook(int id) async {
    try {
      final resp = await _client.request('DELETE', 'kitaplar/$id/', auth: true);
      if (resp.statusCode == 204 || resp.statusCode == 200) {
        return (ok: true, error: null);
      }
      return (ok: false, error: extractError(resp));
    } catch (_) {
      return (ok: false, error: 'Silme yapılamadı.');
    }
  }

  /// Nüsha ekler (barkod boşsa backend otomatik üretir). Faz C.
  Future<({Nusha? nusha, String? error})> addCopy(
    int kitapId, {
    String? barkod,
    int? rafId,
  }) async {
    try {
      final resp = await _client.request(
        'POST',
        'nushalar/',
        auth: true,
        body: {
          'kitap_id': kitapId,
          if (barkod != null && barkod.trim().isNotEmpty)
            'barkod': barkod.trim(),
          'raf_id': ?rafId,
        },
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        return (
          nusha: Nusha.fromJson(jsonDecode(utf8.decode(resp.bodyBytes))),
          error: null,
        );
      }
      return (nusha: null, error: extractError(resp));
    } catch (_) {
      return (nusha: null, error: 'Nüsha eklenemedi.');
    }
  }

  /// Nüsha rafını günceller (rafId null ile rafı kaldırır). Faz C.
  Future<({bool ok, String? error})> updateCopyRaf(int nushaId, int? rafId) async {
    try {
      final resp = await _client.request(
        'PATCH',
        'nushalar/$nushaId/',
        auth: true,
        body: {'raf_id': rafId},
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) return (ok: true, error: null);
      return (ok: false, error: extractError(resp));
    } catch (_) {
      return (ok: false, error: 'Raf güncellenemedi.');
    }
  }

  /// Nüsha siler (yalnızca admin; ödünç kaydı varsa backend reddeder). Faz C.
  Future<({bool ok, String? error})> deleteCopy(int nushaId) async {
    try {
      final resp = await _client.request('DELETE', 'nushalar/$nushaId/', auth: true);
      if (resp.statusCode == 204 || resp.statusCode == 200) {
        return (ok: true, error: null);
      }
      return (ok: false, error: extractError(resp));
    } catch (_) {
      return (ok: false, error: 'Nüsha silinemedi.');
    }
  }

  /// Nüsha durum düzeltmesi (mevcut/kayıp/hasarlı — yalnızca admin). Faz C K4.8.
  Future<({bool ok, String? error})> fixCopyDurum(int nushaId, String durum) async {
    try {
      final resp = await _client.request(
        'POST',
        'nushalar/$nushaId/durum_duzelt/',
        auth: true,
        body: {'durum': durum},
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) return (ok: true, error: null);
      return (ok: false, error: extractError(resp));
    } catch (_) {
      return (ok: false, error: 'Durum güncellenemedi.');
    }
  }

  // --- Merkezi Katalog (Faz C): yazar / kategori / raf ---

  Future<List<Yazar>> yazarlar() async {
    final data = await _fetchAllPages('yazarlar/');
    return data.whereType<Map<String, dynamic>>().map(Yazar.fromJson).toList();
  }

  Future<List<Kategori>> kategoriler() async {
    final data = await _fetchAllPages('kategoriler/');
    return data.whereType<Map<String, dynamic>>().map(Kategori.fromJson).toList();
  }

  Future<List<Raf>> raflar() async {
    final data = await _fetchAllPages('raflar/');
    return data.whereType<Map<String, dynamic>>().map(Raf.fromJson).toList();
  }

  Future<({int? id, String? error})> saveCatalogItem(
    String path, {
    int? id,
    required Map<String, dynamic> body,
  }) async {
    try {
      final resp = id == null
          ? await _client.request('POST', path, auth: true, body: body)
          : await _client.request('PATCH', '$path$id/', auth: true, body: body);
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final data = jsonDecode(utf8.decode(resp.bodyBytes));
        return (id: data is Map && data['id'] is int ? data['id'] as int : null, error: null);
      }
      return (id: null, error: extractError(resp));
    } catch (_) {
      return (id: null, error: 'Kayıt yapılamadı.');
    }
  }

  Future<({bool ok, String? error})> deleteCatalogItem(String path, int id) async {
    try {
      final resp = await _client.request('DELETE', '$path$id/', auth: true);
      if (resp.statusCode == 204 || resp.statusCode == 200) return (ok: true, error: null);
      return (ok: false, error: extractError(resp));
    } catch (_) {
      return (ok: false, error: 'Silme yapılamadı.');
    }
  }

  /// K6.2: kaynak kaydı hedefle birleştirir (admin).
  Future<({bool ok, String? error})> mergeCatalogItems(
    String path,
    int sourceId,
    int targetId,
  ) async {
    try {
      final resp = await _client.request(
        'POST',
        '$path$sourceId/birles/',
        auth: true,
        body: {'hedef_id': targetId},
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) return (ok: true, error: null);
      return (ok: false, error: extractError(resp));
    } catch (_) {
      return (ok: false, error: 'Birleştirme yapılamadı.');
    }
  }

  /// K6.2: kaynak kitabı hedefle birleştirir (nüshalar hedefe taşınır, admin).
  Future<({bool ok, String? error})> mergeBooks(int sourceId, int targetId) async {
    try {
      final resp = await _client.request(
        'POST',
        'kitaplar/$sourceId/birles/',
        auth: true,
        body: {'hedef_id': targetId},
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) return (ok: true, error: null);
      return (ok: false, error: extractError(resp));
    } catch (_) {
      return (ok: false, error: 'Birleştirme yapılamadı.');
    }
  }

  /// K6.1: çift kayıt (fold-normalize başlık) listesi.
  Future<List<Map<String, dynamic>>> bookDuplicates(String? q) async {
    try {
      final resp = await _client.request(
        'GET',
        'kitaplar/cift/${q == null || q.trim().isEmpty ? '' : '?q=${Uri.encodeQueryComponent(q)}'}',
        auth: true,
      );
      if (resp.statusCode != 200) return const [];
      final data = jsonDecode(utf8.decode(resp.bodyBytes));
      return data is List ? data.whereType<Map<String, dynamic>>().toList() : const [];
    } catch (_) {
      return const [];
    }
  }

  /// Çok kaynaklı kitap arama (Google Books + Open Library). Faz C / K7.
  /// ISBN doluysa `isbn` ile ISBN öncelikli arama yapılır.
  Future<({List<Map<String, dynamic>> results, String? error})> bookLookup(
    String q, {
    String isbn = '',
  }) async {
    try {
      final resp = await _client.request(
        'POST',
        'kitap-google/',
        auth: true,
        body: {'q': q, 'isbn': isbn},
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final data = jsonDecode(utf8.decode(resp.bodyBytes));
        final list = data is Map && data['results'] is List
            ? data['results'] as List
            : const [];
        return (
          results: list.whereType<Map<String, dynamic>>().toList(),
          error: null,
        );
      }
      return (results: <Map<String, dynamic>>[], error: extractError(resp));
    } catch (_) {
      return (results: <Map<String, dynamic>>[], error: 'Arama yapılamadı.');
    }
  }
}

/// Sayfalı liste sonucu: satırlar + toplam kayıt + sonraki sayfa (yoksa null).
class Page<T> {
  final List<T> items;
  final int total;
  final int? nextPage;

  const Page({required this.items, required this.total, this.nextPage});
}