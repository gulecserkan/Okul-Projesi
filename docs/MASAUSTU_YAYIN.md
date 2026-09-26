# Masaüstü Uygulama Yayın ve Güncelleme (Linux)

Masaüstü uygulaması (personel/admin) **kullanıcı klasörüne** kurulur ve
güncellemeleri açılışta sunucudan **otomatik** çeker.

## Bileşenler

| Parça | Yer | Görev |
|---|---|---|
| Paket | sunucu `/srv/kutuphane-masaustu/kutuphane-masaustu-vX-linux-x64.tar.gz` | kurulum/güncelleme dosyası |
| Sürüm bilgisi | aynı dizin `surum.json` | `surum`, `surumKodu`, `minSurumKodu`, `url`, `sha256` |
| Sürüm ucu | `GET /api/masaustu/surum/` | uygulama güncelleme kontrolü |
| İndirme sayfası | `GET /masaustu/` | ilk kurulum |
| Kurulum betiği | paket içi `kur.sh` | `~/.local/share/kutuphane-masaustu` + `.desktop` |
| Yükleme betiği | `masaustu/yukle_masaustu.sh` | derle, paketle, sunucuya at |

Kurulum yeri: `~/.local/share/kutuphane-masaustu` (uygulama, `lib/`, `data/`, `kur.sh`, `VERSION`).
Kısayol: `~/.local/share/applications/kutuphane-masaustu.desktop`.

## İlk kurulum (hedef bilgisayar)

```bash
mkdir -p ~/.local/share/kutuphane-masaustu
tar -xzf ~/İndirilenler/kutuphane-masaustu-vX.Y.Z-linux-x64.tar.gz \
        -C ~/.local/share/kutuphane-masaustu
bash ~/.local/share/kutuphane-masaustu/kur.sh
```

Menüde **Kütüphane Yönetim Sistemi** olarak görünür. Giriş ekranından sunucu
adresi girilir (varsayılan `http://127.0.0.1:8000/api`).

## Güncelleme davranışı

- Açılışta `GET /api/masaustu/surum/` sorulur. Kurulu kod < `minSurumKodu` → **zorunlu**;
  `minSurumKodu ≤ kurulu < surumKodu` → **opsiyonel** bildirim.
- "Güncelle": paket indirilir, **sha256** doğrulanır, uygulama kapanır; yardımcı
  betik `~/.local/share/kutuphane-masaustu` içeriğini değiştirir ve uygulamayı
  yeniden başlatır.
- **Otomatik güncelleme yalnız** uygulama `~/.local/share/kutuphane-masaustu`
  altından çalışıyorsa etkindir. Geliştirme derlemesinden veya `/opt` gibi
  root'a ait bir yerden çalışıyorsa yalnız bildirim + indirme bağlantısı gösterilir.

## Yayın akışı (yeni masaüstü sürüm)

1. `masaustu/yukle_masaustu.sh` sürüm argümanlarıyla çalıştırılır (release
   derleme + `--dart-define=APP_VERSION/APP_VERSION_CODE` otomatik).
2. `cd masaustu && flutter analyze && flutter test` (yayın öncesi kontrol).
3. `bash masaustu/yukle_masaustu.sh <X.Y.Z> <kod> <minKod>`
   → derler, `sha256` hesaplar, sunucuya yükler, `surum.json` + `index.html` üretir.
4. Test: hedef makinede uygulamayı aç → bildirim → "Güncelle" → otomatik yeniden başlat.

> Backend'e dokunmadan sadece masaüstü güncellenebilir (mobildeki gibi bağımsız).

## Sunucu kurulumu (bir kez)

```bash
sudo install -d -o kutuphane -g kutuphane -m 755 /srv/kutuphane-masaustu
# nginx server bloğuna (location / öncesine):
#   location /masaustu/ { alias /srv/kutuphane-masaustu/; autoindex off; }
echo 'MASAUSTU_DIST_DIR=/srv/kutuphane-masaustu' | sudo tee -a /etc/kutuphane/.env
sudo systemctl restart kutuphane-backend
```

## Notlar

- Paket `tar.gz` git'e girmez; sunucuda repo dışında tutulur (`deploy.sh` silmez).
- `kur.sh` `.desktop` dosyasını yeniden yazar; `Exec` kurulum klasörünü gösterir,
  güncelleme sonrası değişmez.
- Otomatik güncelleme başarısız olursa (yetki/disk) uygulama açık kalır ve hata
  diyaloğu gösterilir; elle kurulum her zaman mümkündür.
