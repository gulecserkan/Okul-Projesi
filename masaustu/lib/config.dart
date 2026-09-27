import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart' show ValueNotifier, visibleForTesting;

/// Uygulama yapılandırması + oturum (token) saklaması.
///
/// Masaüstünde ~/.config/kutuphane_masaustu/config.json içinde tutulur
/// (eski PyQt sürümü gibi dosya tabanlı).
class AppConfig {
  /// Öncelik sıralı sunucu adayları (masaüstü API kökü, `/api` dahil):
  ///   1) alan adı — SSL aktif olunca öne geçer
  ///   2) genel IP — geçici erişim
  /// Uygulama açılışta adayları paralel yoklar; ilk ulaşanı kullanır.
  static const List<String> serverCandidates = [
    'https://okulkitapligi.tr/api',
    'http://89.252.153.171/api',
  ];

  /// Kayıtlı adres yoksa önerilen varsayılan adres (aday listesinin ilki).
  static const String defaultBaseUrl = 'https://okulkitapligi.tr/api';

  /// Uygulama sürümü (derlemede `--dart-define=APP_VERSION=...` ile verilir).
  static const String appVersion =
      String.fromEnvironment('APP_VERSION', defaultValue: '0.1.0');

  /// Sürüm kodu (derlemede `--dart-define=APP_VERSION_CODE=...`).
  static const int appVersionCode =
      int.fromEnvironment('APP_VERSION_CODE', defaultValue: 1);

  /// Test izolasyonu: verilirse config bu dizin altında tutulur (gerçek
  /// kullanıcı ayarlarına dokunulmaz).
  @visibleForTesting
  static String? testHomeDir;

  static String get _dirPath =>
      testHomeDir ?? '${Platform.environment['HOME'] ?? '.'}/.config/kutuphane_masaustu';

  static File get _file => File('$_dirPath/config.json');

  static Map<String, dynamic> _read() {
    try {
      if (_file.existsSync()) {
        return jsonDecode(_file.readAsStringSync()) as Map<String, dynamic>;
      }
    } catch (_) {}
    return {};
  }

  static void _write(Map<String, dynamic> data) {
    Directory(_dirPath).createSync(recursive: true);
    _file.writeAsStringSync(jsonEncode(data));
  }

  static String get apiBaseUrl {
    final data = _read();
    final url = (data['api']?['base_url'] as String?)?.trim();
    return (url == null || url.isEmpty) ? defaultBaseUrl : url;
  }

  /// Kullanıcı/ayarlar tarafından kaydedilmiş bir sunucu adresi var mı?
  static bool get hasSavedBaseUrl {
    final url = (_read()['api']?['base_url'] as String?)?.trim();
    return url != null && url.isNotEmpty;
  }

  static set apiBaseUrl(String url) {
    final data = _read();
    data['api'] = {'base_url': url.trim()};
    _write(data);
  }

  /// Seçili tema adı (AppTheme.name). Varsayılan: 'standart'.
  static String get themeName {
    final data = _read();
    final name = data['theme'] as String?;
    return (name == null || name.isEmpty) ? 'standart' : name;
  }

  static set themeName(String value) {
    final data = _read();
    data['theme'] = value;
    _write(data);
  }

  /// Sol menü açık mı? (varsayılan: açık)
  static bool get menuAcik {
    final data = _read();
    return data['menu_acik'] as bool? ?? true;
  }

  static set menuAcik(bool value) {
    final data = _read();
    data['menu_acik'] = value;
    _write(data);
  }

  static Session? get session {
    final data = _read();
    final s = data['session'];
    if (s is! Map) return null;
    return Session(
      accessToken: s['access'] as String? ?? '',
      refreshToken: s['refresh'] as String? ?? '',
      username: s['username'] as String? ?? '',
      fullName: s['full_name'] as String? ?? '',
      role: s['role'] as String? ?? '',
      tip: s['tip'] as String? ?? 'personel',
    );
  }

  static set session(Session? session) {
    final data = _read();
    if (session == null) {
      data.remove('session');
    } else {
      data['session'] = {
        'access': session.accessToken,
        'refresh': session.refreshToken,
        'username': session.username,
        'full_name': session.fullName,
        'role': session.role,
        'tip': session.tip,
      };
    }
    _write(data);
  }

  // ------------------------------------------------------------- Yazıcı (K14)

  /// Yazıcı ayarları değişincе üst çubuk çipini vb. anlık güncellemek için
  /// dinleyici (K14.9).
  static final ValueNotifier<PrinterPrefs> printerNotifier =
      ValueNotifier<PrinterPrefs>(PrinterPrefs());

  static PrinterPrefs get printer {
    final data = _read();
    final p = data['printer'];
    return p is Map<String, dynamic> ? PrinterPrefs.fromJson(p) : PrinterPrefs();
  }

  static set printer(PrinterPrefs prefs) {
    final data = _read();
    data['printer'] = prefs.toJson();
    _write(data);
    printerNotifier.value = prefs;
  }

  /// Fiş/etiket başlığı için son alınan kurum bilgisi yerel yedeği (K14.1).
  static KurumBilgisi? get kurumYedek {
    final data = _read();
    final k = data['kurum'];
    return k is Map<String, dynamic> ? KurumBilgisi.fromJson(k) : null;
  }

  static set kurumYedek(KurumBilgisi? kurum) {
    final data = _read();
    if (kurum == null) {
      data.remove('kurum');
    } else {
      data['kurum'] = kurum.toJson();
    }
    _write(data);
  }
}

/// Fiş/etiket yazdırma ayarları (yerel; her bilgisayarda kendi donanımı).
class PrinterPrefs {
  /// CUPS kuyruk adları; boş = seçilmemiş.
  final String fisYazici;
  final String etiketYazici;
  final String a4Yazici;

  final bool otomatikOduncFisi;
  final bool otomatikIadeFisi;
  final bool sifreFisi;

  /// Ortak (fiş==etiket) termal yazıcıda takılı rulo: `tanimsiz`/`fis`/`etiket` (K14.9).
  final String rulo;

  /// A4 çıktısı dosyaya yazılsın mı (K14.10).
  final bool a4Dosya;

  /// Etiket rulo ölçüleri kurulum diyaloğu bir kez yapıldı mı (K14.11).
  final bool etiketKurulumYapildi;

  /// Termal rulo ölçüleri (mm) — K14.11. Besleme/boşluk ölçümü yazıcının kendi
  /// sensör kalibrasyonuna bırakılır; bu değerler yalnız PDF içerik yerleşimi içindir.
  final double etiketGenislikMm;
  final double etiketYukseklikMm;
  final double fisGenislikMm;

  const PrinterPrefs({
    this.fisYazici = '',
    this.etiketYazici = '',
    this.a4Yazici = '',
    this.otomatikOduncFisi = true,
    this.otomatikIadeFisi = true,
    this.sifreFisi = true,
    this.rulo = 'tanimsiz',
    this.a4Dosya = false,
    this.etiketKurulumYapildi = false,
    this.etiketGenislikMm = 57,
    this.etiketYukseklikMm = 40,
    this.fisGenislikMm = 70,
  });

  PrinterPrefs copyWith({
    String? fisYazici,
    String? etiketYazici,
    String? a4Yazici,
    bool? otomatikOduncFisi,
    bool? otomatikIadeFisi,
    bool? sifreFisi,
    String? rulo,
    bool? a4Dosya,
    bool? etiketKurulumYapildi,
    double? etiketGenislikMm,
    double? etiketYukseklikMm,
    double? fisGenislikMm,
  }) =>
      PrinterPrefs(
        fisYazici: fisYazici ?? this.fisYazici,
        etiketYazici: etiketYazici ?? this.etiketYazici,
        a4Yazici: a4Yazici ?? this.a4Yazici,
        otomatikOduncFisi: otomatikOduncFisi ?? this.otomatikOduncFisi,
        otomatikIadeFisi: otomatikIadeFisi ?? this.otomatikIadeFisi,
        sifreFisi: sifreFisi ?? this.sifreFisi,
        rulo: rulo ?? this.rulo,
        a4Dosya: a4Dosya ?? this.a4Dosya,
        etiketKurulumYapildi: etiketKurulumYapildi ?? this.etiketKurulumYapildi,
        etiketGenislikMm: etiketGenislikMm ?? this.etiketGenislikMm,
        etiketYukseklikMm: etiketYukseklikMm ?? this.etiketYukseklikMm,
        fisGenislikMm: fisGenislikMm ?? this.fisGenislikMm,
      );

  Map<String, dynamic> toJson() => {
        'fis': fisYazici,
        'etiket': etiketYazici,
        'a4': a4Yazici,
        'otomatik_odunc_fisi': otomatikOduncFisi,
        'otomatik_iade_fisi': otomatikIadeFisi,
        'sifre_fisi': sifreFisi,
        'rulo': rulo,
        'a4_dosya': a4Dosya,
        'etiket_kurulum_yapildi': etiketKurulumYapildi,
        'etiket_genislik_mm': etiketGenislikMm,
        'etiket_yukseklik_mm': etiketYukseklikMm,
        'fis_genislik_mm': fisGenislikMm,
      };

  factory PrinterPrefs.fromJson(Map<String, dynamic> json) => PrinterPrefs(
        fisYazici: json['fis'] as String? ?? '',
        etiketYazici: json['etiket'] as String? ?? '',
        a4Yazici: json['a4'] as String? ?? '',
        otomatikOduncFisi: json['otomatik_odunc_fisi'] as bool? ?? true,
        otomatikIadeFisi: json['otomatik_iade_fisi'] as bool? ?? true,
        sifreFisi: json['sifre_fisi'] as bool? ?? true,
        rulo: json['rulo'] as String? ?? 'tanimsiz',
        a4Dosya: json['a4_dosya'] as bool? ?? false,
        etiketKurulumYapildi: json['etiket_kurulum_yapildi'] as bool? ?? false,
        etiketGenislikMm: (json['etiket_genislik_mm'] as num?)?.toDouble() ?? 57,
        etiketYukseklikMm: (json['etiket_yukseklik_mm'] as num?)?.toDouble() ?? 40,
        fisGenislikMm: (json['fis_genislik_mm'] as num?)?.toDouble() ?? 70,
      );
}

/// Kurum bilgisi (fiş/etiket başlığı + iletişim) — yerel yedek (K14.1).
class KurumBilgisi {
  final String kutuphaneAdi;
  final String okulAdi;
  final String adres;
  final String telefon;
  final String eposta;
  final String website;
  final String logoUrl;

  const KurumBilgisi({
    this.kutuphaneAdi = '',
    this.okulAdi = '',
    this.adres = '',
    this.telefon = '',
    this.eposta = '',
    this.website = '',
    this.logoUrl = '',
  });

  /// Fiş/etiket üst başlığı (kütüphane adı; yoksa okul adı).
  String get baslik =>
      [kutuphaneAdi.trim(), okulAdi.trim()].where((s) => s.isNotEmpty).join(' • ');

  Map<String, dynamic> toJson() => {
        'kutuphane_adi': kutuphaneAdi,
        'okul_adi': okulAdi,
        'adres': adres,
        'telefon': telefon,
        'eposta': eposta,
        'website': website,
        'logo_url': logoUrl,
      };

  factory KurumBilgisi.fromJson(Map<String, dynamic> json) => KurumBilgisi(
        kutuphaneAdi: json['kutuphane_adi'] as String? ?? '',
        okulAdi: json['okul_adi'] as String? ?? '',
        adres: json['adres'] as String? ?? '',
        telefon: json['telefon'] as String? ?? '',
        eposta: json['eposta'] as String? ?? '',
        website: json['website'] as String? ?? '',
        logoUrl: json['logo_url'] as String? ?? '',
      );
}

class Session {
  final String accessToken;
  final String refreshToken;
  final String username;
  final String fullName;
  final String role;

  /// K9: hesap tipi — 'personel' (operatör/admin) veya 'uye'; masaüstü yalnız personel.
  final String tip;

  const Session({
    required this.accessToken,
    required this.refreshToken,
    required this.username,
    this.fullName = '',
    this.role = '',
    this.tip = 'personel',
  });

  bool get isValid => accessToken.isNotEmpty;

  bool get isPersonel => tip != 'uye';
}