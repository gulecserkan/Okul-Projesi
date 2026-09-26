#!/usr/bin/env bash
#
# Masaüstü (Linux) paket yükleme betiği.
#
#   Kullanım: bash masaustu/yukle_masaustu.sh <tag> <surumKodu> <minSurumKodu> [--build-yok]
#   Örnek   : bash masaustu/yukle_masaustu.sh 1.1.7 1 1
#
# Release derler, tar.gz paketler, sunucudaki /srv/kutuphane-masaustu/ dizinine
# yükler; surum.json + index.html üretir.
#   - GET /api/masaustu/surum/  → sürüm bilgisi (uygulama güncelleme kontrolü)
#   - GET /masaustu/            → indirme sayfası
#   - GET /masaustu/kutuphane-masaustu-vX-linux-x64.tar.gz
#
set -euo pipefail

TAG="${1:?kullanım: yukle_masaustu.sh <tag> <surumKodu> <minSurumKodu> [--build-yok]}"
TAG="${TAG#v}"
KOD="${2:?surumKodu gerekli}"
MIN="${3:?minSurumKodu gerekli}"
BUILD="${4:-}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/masaustu"
SUNUCU="${KUTUPHANE_SSH:-cenuta}"
BASE_URL="${KUTUPHANE_MASAUSTU_URL:-http://89.252.153.171}"
DIZIN=/srv/kutuphane-masaustu
AD="kutuphane-masaustu-v${TAG}-linux-x64.tar.gz"

if [[ "$BUILD" != "--build-yok" ]]; then
  echo "Release derleniyor (APP_VERSION=$TAG, kod=$KOD)..."
  ( cd "$APP" && flutter build linux --release \
      --dart-define=APP_VERSION="$TAG" --dart-define=APP_VERSION_CODE="$KOD" )
fi

BUNDLE="$APP/build/linux/x64/release/bundle"
[[ -x "$BUNDLE/masaustu" ]] || { echo "Hata: bundle bulunamadı: $BUNDLE" >&2; exit 1; }

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp -a "$BUNDLE/." "$STAGE/"
cp -f "$APP/kur.sh" "$STAGE/kur.sh"
chmod +x "$STAGE/kur.sh" "$STAGE/masaustu"
printf '%s\n' "$TAG" > "$STAGE/VERSION"

PAKET="/tmp/$AD"
tar -C "$STAGE" -czf "$PAKET" .
SHA="$(sha256sum "$PAKET" | awk '{print $1}')"
echo "Paket: $AD ($(du -h "$PAKET" | cut -f1)) sha256=$SHA"

scp -q "$PAKET" "$SUNUCU:/tmp/$AD"
ssh "$SUNUCU" "sudo install -o kutuphane -g kutuphane -m 644 /tmp/$AD $DIZIN/$AD && rm -f /tmp/$AD"

cat > /tmp/kutuphane-masaustu-surum.json <<JSON
{"surum": "${TAG}", "surumKodu": ${KOD}, "minSurumKodu": ${MIN}, "url": "/masaustu/${AD}", "sha256": "${SHA}"}
JSON

cat > /tmp/kutuphane-masaustu-index.html <<HTML
<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kütüphane Masaüstü Uygulaması</title>
<style>
  body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;
       background:#f4f6f8;color:#1f2933;display:flex;justify-content:center}
  main{max-width:560px;padding:32px 20px}
  h1{font-size:1.4rem;margin:0 0 4px}
  .surum{color:#52606d;font-size:.95rem;margin-bottom:20px}
  a.btn{display:block;text-align:center;background:#7a3e2e;color:#fff;
        text-decoration:none;padding:14px;border-radius:10px;font-weight:600}
  pre{background:#1f2933;color:#f4f6f8;padding:14px;border-radius:10px;
      overflow-x:auto;font-size:.85rem;line-height:1.5}
  .not{background:#fff;border:1px solid #e4e7eb;border-radius:10px;padding:16px;
       margin-top:18px;font-size:.92rem;color:#3e4c59}
</style>
</head>
<body>
<main>
  <h1>Kütüphane Masaüstü Uygulaması</h1>
  <p class="surum">Sürüm ${TAG} · Linux (x64)</p>
  <a class="btn" href="/masaustu/${AD}" download>Paketi indir (.tar.gz)</a>
  <div class="not">
    <strong>Kurulum (personel/admin bilgisayarı):</strong>
    <pre>mkdir -p ~/.local/share/kutuphane-masaustu
tar -xzf ~/İndirilenler/${AD} -C ~/.local/share/kutuphane-masaustu
bash ~/.local/share/kutuphane-masaustu/kur.sh</pre>
    Kurulumdan sonra uygulama menüde <em>Kütüphane Yönetim Sistemi</em> olarak görünür.
    Giriş ekranından sunucu adresini girin. Sonraki sürümler uygulama açılışında
    otomatik kontrol edilip bu klasöre uygulanır.
  </div>
</main>
</body>
</html>
HTML

scp -q /tmp/kutuphane-masaustu-surum.json "$SUNUCU:/tmp/kutuphane-masaustu-surum.json"
scp -q /tmp/kutuphane-masaustu-index.html "$SUNUCU:/tmp/kutuphane-masaustu-index.html"
ssh "$SUNUCU" "sudo install -o kutuphane -g kutuphane -m 644 /tmp/kutuphane-masaustu-surum.json $DIZIN/surum.json && \
              sudo install -o kutuphane -g kutuphane -m 644 /tmp/kutuphane-masaustu-index.html $DIZIN/index.html && \
              rm -f /tmp/kutuphane-masaustu-surum.json /tmp/kutuphane-masaustu-index.html"
rm -f /tmp/kutuphane-masaustu-surum.json /tmp/kutuphane-masaustu-index.html "$PAKET"

echo "Yüklendi. Doğrulama:"
echo -n "  surum.json: "; curl -fsS "${BASE_URL}/api/masaustu/surum/"; echo
echo -n "  sayfa     : "; curl -fsS -o /dev/null -w "%{http_code}\n" "${BASE_URL}/masaustu/"
echo -n "  paket     : "; curl -fsS -o /dev/null -w "%{http_code}\n" "${BASE_URL}/masaustu/${AD}"
