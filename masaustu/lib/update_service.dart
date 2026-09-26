import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:http/http.dart' as http;

import 'config.dart';

/// Kurulumun (kur.sh ile) yerleştirildiği klasör parçası. Otomatik güncelleme
/// yalnız bu konumdan çalışan uygulamalarda etkindir (geliştirme ortamında
/// kendi derleme klasörünü değiştirmemek için).
const String kKurulumDiziniParcasi = '.local/share/kutuphane-masaustu';

/// Sunucudan gelen masaüstü sürüm bilgisi (GET /api/masaustu/surum/).
class MasaustuSurum {
  const MasaustuSurum({
    required this.surum,
    required this.surumKodu,
    required this.minSurumKodu,
    required this.url,
    required this.sha256,
  });

  final String surum;
  final int surumKodu;
  final int minSurumKodu;
  final String url;
  final String sha256;

  factory MasaustuSurum.fromJson(Map<String, dynamic> json) {
    return MasaustuSurum(
      surum: (json['surum'] ?? '').toString(),
      surumKodu: (json['surumKodu'] as num?)?.toInt() ?? 0,
      minSurumKodu: (json['minSurumKodu'] as num?)?.toInt() ?? 0,
      url: (json['url'] ?? '').toString(),
      sha256: (json['sha256'] ?? '').toString(),
    );
  }
}

class GuncellemeKarari {
  const GuncellemeKarari({required this.guncellemeVar, required this.zorunlu});

  final bool guncellemeVar;
  final bool zorunlu;
}

/// Kurulu sürüm kodu ile sunucudaki sürümü karşılaştırır.
GuncellemeKarari guncellemeKarari({
  required int kuruluKod,
  required MasaustuSurum? uzak,
}) {
  if (uzak == null || uzak.surumKodu <= kuruluKod) {
    return const GuncellemeKarari(guncellemeVar: false, zorunlu: false);
  }
  return GuncellemeKarari(
    guncellemeVar: true,
    zorunlu: kuruluKod < uzak.minSurumKodu,
  );
}

/// Göreli paket yolunu sunucunun kök adresiyle birleştirir.
/// `baseUrl` sonunda `/api` olabilir; kök (`scheme://host[:port]`) alınır.
String indirmeAdresi(String baseUrl, String url) {
  if (url.isEmpty) return url;
  final parsed = Uri.parse(url);
  if (parsed.hasScheme) return url;
  final base = Uri.parse(baseUrl);
  final kok = Uri(
    scheme: base.scheme,
    host: base.host,
    port: base.hasPort ? base.port : null,
  );
  final path = url.startsWith('/') ? url : '/$url';
  return '$kok$path';
}

/// Otomatik güncelleme (kendini değiştirme) bu kurulumda destekli mi?
bool otomatikGuncellemeDestekli() {
  final exe = File(Platform.resolvedExecutable).parent.path;
  return exe.contains(kKurulumDiziniParcasi);
}

/// Sunucudan sürüm bilgisini okur; ulaşılamaz/yoksa null.
Future<MasaustuSurum?> sunucudanSurumOku({http.Client? client}) async {
  final c = client ?? http.Client();
  try {
    final uri = Uri.parse('${AppConfig.apiBaseUrl}/masaustu/surum/');
    final resp = await c.get(uri).timeout(const Duration(seconds: 6));
    if (resp.statusCode == 200) {
      return MasaustuSurum.fromJson(
        jsonDecode(resp.body) as Map<String, dynamic>,
      );
    }
  } catch (_) {
    // sessiz geç: sürüm kontrolü uygulamayı engellemez
  } finally {
    if (client == null) c.close();
  }
  return null;
}

/// Paketi indirir, sha256 doğrular, çıkarır; uygulama kapanınca kurulum
/// klasörünü değiştirip uygulamayı yeniden başlatan yardımcı bir betik başlatır
/// ve mevcut süreçten çıkar.
Future<void> guncellemeyiIndirVeBaslat(
  MasaustuSurum bilgi, {
  void Function(double ilerleme)? ilerleme,
}) async {
  final uri = Uri.parse(indirmeAdresi(AppConfig.apiBaseUrl, bilgi.url));
  final client = http.Client();
  final gecici = await Directory.systemTemp.createTemp('kutuphane-guncelle-');

  try {
    final resp = await client.send(http.Request('GET', uri));
    if (resp.statusCode != 200) {
      throw Exception('İndirme başarısız (HTTP ${resp.statusCode})');
    }
    final total = resp.contentLength ?? 0;
    final parcalar = <List<int>>[];
    var alinan = 0;
    await for (final parca in resp.stream) {
      parcalar.add(parca);
      alinan += parca.length;
      if (total > 0 && ilerleme != null) ilerleme(alinan / total);
    }
    final veri = <int>[for (final p in parcalar) ...p];

    if (bilgi.sha256.isNotEmpty) {
      final ozet = sha256.convert(veri).toString().toLowerCase();
      if (ozet != bilgi.sha256.toLowerCase()) {
        throw Exception('Paket bütünlüğü doğrulanamadı (sha256 uyuşmuyor).');
      }
    }

    final arsiv = File('${gecici.path}/paket.tar.gz');
    await arsiv.writeAsBytes(veri);

    final yeni = Directory('${gecici.path}/yeni');
    await yeni.create();
    final cikar = await Process.run('tar', ['-xzf', arsiv.path, '-C', yeni.path]);
    if (cikar.exitCode != 0) {
      throw Exception('Arşiv çıkarılamadı: ${cikar.stderr}');
    }

    final install = File(Platform.resolvedExecutable).parent.path;
    final helper = File('${gecici.path}/uygula.sh');
    await helper.writeAsString('''#!/usr/bin/env bash
set -e
PID="\$1"; INSTALL="\$2"; YENI="\$3"
while kill -0 "\$PID" 2>/dev/null; do sleep 0.5; done
sleep 0.5
rm -rf "\$INSTALL"
mkdir -p "\$INSTALL"
cp -a "\$YENI"/. "\$INSTALL"/
chmod +x "\$INSTALL/masaustu" 2>/dev/null || true
nohup "\$INSTALL/masaustu" >/dev/null 2>&1 &
rm -rf "\$(dirname "\$YENI")"
''');

    await Process.start(
      'bash',
      [helper.path, pid.toString(), install, yeni.path],
      mode: ProcessStartMode.detached,
    );
  } finally {
    client.close();
  }

  exit(0);
}
