# Mobil Uygulama Yayın ve Güncelleme (Android)

Android uygulaması Google Play dışında, **kendi sunucumuzdan** dağıtılır. Üyeler
uygulamayı ilk kez `/mobil/` sayfasından kurar; sonraki sürümlerde uygulama
açılışta sunucuyu kontrol edip güncelleme bildirir.

## Bileşenler

| Parça | Yer | Görev |
|---|---|---|
| Release keystore | `mobil/keystore/kutuphane-release.jks` (git dışı) | APK imzası (kalıcı) |
| İmza ayarları | `mobil/kutuphane/android/key.properties` (git dışı) | şifre + dosya yolu |
| Sürüm tabanlı dağıtım | sunucu `/srv/kutuphane-mobil/` | APK + `surum.json` + `index.html` |
| Sürüm ucu | `GET /api/mobil/surum/` | uygulama güncelleme kontrolü |
| İndirme sayfası | `GET /mobil/` | ilk kurulum / indirme |
| Yükleme betiği | `mobil/yukle_apk.sh` | APK + metadata'yı sunucuya atar |

### `surum.json` biçimi

```json
{"surum": "1.1.4", "surumKodu": 1, "minSurumKodu": 1,
 "apkUrl": "/mobil/kutuphane-v1.1.4.apk"}
```

- `surumKodu` = APK `versionCode` (`pubspec.yaml` → `version: 1.1.4+1` → kod **1**).
- Kurulu sürüm `< minSurumKodu` → **zorunlu** güncelleme (uygulama kilitlenir).
- Kurulu sürüm `< surumKodu` → **opsiyonel** bildirim.
- `surumKodu` her yayında **mutlaka artırılır** (Android aksi halde güncellemeyi kabul etmez).

## Sunucu adresi (K13.11)

- Uygulama açılışta `serverCandidates` listesini **paralel** yoklar:
  `https://okulkitapligi.tr` → `http://89.252.153.171`. İlk ulaşan kaydedilir;
  hiçbiri yoksa bağlantı ekranı açılır.
- Alan adı + SSL aktif olunca uygulama **güncellenmeden** otomatik `https`'ye geçer.
- Derlemede adres zorlamak için: `--dart-define=KUTUPHANE_SERVER=http://<adres>`.

## Android cleartext (K13.12)

HTTPS öncesi genel IP'ye `http` ile erişilebilmesi için `AndroidManifest.xml`'de
`android:usesCleartextTraffic="true"` ayarlıdır. SSL (Let's Encrypt) aktif olunca
`networkSecurityConfig` ile yalnız alan adına `https` izni verilecek şekilde
daraltılabilir.

## Kritik: imza

Android, bir uygulamanın güncellemesini ancak **aynı imza** ile kurar. Bu yüzden:

- İlk dağıtılan APK **release keystore** ile imzalanır; debug APK dağıtılmaz.
- `mobil/keystore/kutuphane-release.jks` ve şifresi **kaybolmamalı**; güvenli bir
  yerde (şifre yöneticisi + yedek disk) saklanır. Kaybolursa güncelleme dağıtılamaz.
- Farklı imza ile kurulum denenirse kullanıcı **uygulamayı silip yeniden kurmalıdır**.

## Yayın akışı (yeni mobil sürüm)

1. `mobil/kutuphane/pubspec.yaml` → `version: X.Y.Z+<kod>` (kod +1).
2. `cd mobil/kutuphane && flutter analyze && flutter test`.
3. `flutter build apk --release` (çıktı: `build/app/outputs/flutter-apk/app-release.apk`).
4. İmzayı doğrula:
   `$ANDROID_HOME/build-tools/<v>/apksigner verify --print-certs build/.../app-release.apk`
   (imzalayan `CN=Kutuphane` olmalı).
5. `bash mobil/yukle_apk.sh <X.Y.Z> <kod> <minKod>` (repo kökünden).
   Betik APK'yı sunucuya kopyalar, `surum.json` + `index.html`'i yeniler ve doğrular.
6. Test için telefonu: `/mobil/` sayfasından indir → eski sürümün üzerine kurulur.

> Backend'e dokunmadan yalnızca mobil güncellenebilir. Backend sürümü
> (`VERSION`, `deploy.sh`) ayrıdır; birlikte çıkıyorsa ikisini de yayınla.

## Sunucu kurulumu (bir kez)

```bash
# Dizin (repo dışı; git checkout bunu silmez)
sudo install -d -o kutuphane -g kutuphane -m 755 /srv/kutuphane-mobil

# nginx: /mobil/ → dizin (server bloğunda location / öncesine)
#   location /mobil/ { alias /srv/kutuphane-mobil/; autoindex off; }
sudo cp /etc/nginx/sites-available/kutuphane{,.bak}
# ... ilgili blok eklenir ...
sudo nginx -t && sudo systemctl reload nginx

# Django dağıtım dizinini bilsin
echo 'MOBIL_DIST_DIR=/srv/kutuphane-mobil' | sudo tee -a /etc/kutuphane/.env
sudo systemctl restart kutuphane-backend
```

## Geri alma

Eski bir APK'yı yeniden sunmak için: `bash mobil/yukle_apk.sh <eskiX.Y.Z> <eskiKod> <minKod>`
(sunucudaki eski `kutuphane-v*.apk` dosyaları silinmediği sürece). `surumKodu`
düşürülmez; geri dönüşte kullanıcılar yeni kodu görmezse güncelleme bildirimi
almaz, APK elle paylaşılır.

## iOS

iOS'ta bu yöntem çalışmaz: uygulama yalnızca **App Store** (veya okul için Apple
School Manager özel dağıtım) ile kurulur. Şimdilik desteklenmiyor; iOS eklenirse
"Güncelle" düğmesi App Store sayfasına yönlendirilir ve macOS/Xcode + Apple
Developer hesabı + HTTPS gerekir.
