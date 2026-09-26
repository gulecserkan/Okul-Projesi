#!/usr/bin/env bash
#
# Mobil APK yükleme betiği.
#
#   Kullanım: bash mobil/yukle_apk.sh <tag> <surumKodu> <minSurumKodu> [apk]
#   Örnek   : bash mobil/yukle_apk.sh 1.1.4 1 1
#
# APK'yı sunucudaki /srv/kutuphane-mobil/ dizinine kopyalar; surum.json ve
# index.html dosyalarını üretir. Böylece:
#   - GET /api/mobil/surum/         → sürüm bilgisi (uygulama güncelleme kontrolü)
#   - GET /mobil/                   → kurulum sayfası (indirme)
#   - GET /mobil/kutuphane-vX.apk   → APK dosyası
#
# Ortam değişkenleri (isteğe bağlı):
#   KUTUPHANE_SSH      SSH hedefi (varsayılan: cenuta)
#   KUTUPHANE_MOBIL_URL Doğrulama için taban adres (varsayılan: genel adres)
#
set -euo pipefail

TAG="${1:?kullanım: yukle_apk.sh <tag> <surumKodu> <minSurumKodu> [apk]}"
TAG="${TAG#v}"
KOD="${2:?surumKodu gerekli}"
MIN="${3:?minSurumKodu gerekli}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APK="${4:-$ROOT/mobil/kutuphane/build/app/outputs/flutter-apk/app-release.apk}"
SUNUCU="${KUTUPHANE_SSH:-cenuta}"
BASE_URL="${KUTUPHANE_MOBIL_URL:-http://89.252.153.171}"
DIZIN=/srv/kutuphane-mobil
AD="kutuphane-v${TAG}.apk"

[[ -f "$APK" ]] || { echo "Hata: APK bulunamadı: $APK" >&2; exit 1; }

echo "APK yükleniyor: $AD ($(du -h "$APK" | cut -f1)) → $SUNUCU:$DIZIN"
scp -q "$APK" "$SUNUCU:/tmp/$AD"
ssh "$SUNUCU" "sudo install -o kutuphane -g kutuphane -m 644 /tmp/$AD $DIZIN/$AD && rm -f /tmp/$AD"

cat > /tmp/kutuphane-surum.json <<JSON
{"surum": "${TAG}", "surumKodu": ${KOD}, "minSurumKodu": ${MIN}, "apkUrl": "/mobil/${AD}"}
JSON

cat > /tmp/kutuphane-mobil-index.html <<HTML
<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kütüphane Uygulaması</title>
<style>
  body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;
       background:#f4f6f8;color:#1f2933;display:flex;justify-content:center}
  main{max-width:520px;padding:32px 20px}
  h1{font-size:1.5rem;margin:0 0 4px}
  .surum{color:#52606d;font-size:.95rem;margin-bottom:20px}
  a.btn{display:block;text-align:center;background:#0b6e4f;color:#fff;
        text-decoration:none;padding:14px;border-radius:10px;font-weight:600;
        font-size:1.05rem}
  ol{line-height:1.7;padding-left:1.2rem}
  .not{background:#fff;border:1px solid #e4e7eb;border-radius:10px;padding:16px;
       margin-top:20px;font-size:.92rem;color:#3e4c59}
  code{background:#eef1f4;padding:1px 5px;border-radius:4px}
</style>
</head>
<body>
<main>
  <h1>Kütüphane Uygulaması</h1>
  <p class="surum">Sürüm ${TAG} (Android)</p>
  <a class="btn" href="/mobil/${AD}" download>APK'yı indir</a>
  <div class="not">
    <strong>Kurulum:</strong>
    <ol>
      <li>Yukarıdaki düğmeyle APK dosyasını indirin.</li>
      <li>Telefonda <em>Bilinmeyen kaynaklara izin ver</em> seçeneğini açın
          (Ayarlar → Güvenlik).</li>
      <li>İndirilen dosyayı açıp <em>Kur</em> deyin.</li>
    </ol>
    Uygulamayı açınca sunucu adresini girin ve üye numaranız + şifrenizle giriş yapın.
  </div>
</main>
</body>
</html>
HTML

scp -q /tmp/kutuphane-surum.json "$SUNUCU:/tmp/kutuphane-surum.json"
scp -q /tmp/kutuphane-mobil-index.html "$SUNUCU:/tmp/kutuphane-mobil-index.html"
ssh "$SUNUCU" "sudo install -o kutuphane -g kutuphane -m 644 /tmp/kutuphane-surum.json $DIZIN/surum.json && \
              sudo install -o kutuphane -g kutuphane -m 644 /tmp/kutuphane-mobil-index.html $DIZIN/index.html && \
              rm -f /tmp/kutuphane-surum.json /tmp/kutuphane-mobil-index.html"
rm -f /tmp/kutuphane-surum.json /tmp/kutuphane-mobil-index.html

echo "Yüklendi. Doğrulama:"
echo -n "  surum.json: "; curl -fsS "${BASE_URL}/api/mobil/surum/"; echo
echo -n "  sayfa     : "; curl -fsS -o /dev/null -w "%{http_code}\n" "${BASE_URL}/mobil/"
echo -n "  apk       : "; curl -fsS -o /dev/null -w "%{http_code}\n" "${BASE_URL}/mobil/${AD}"
