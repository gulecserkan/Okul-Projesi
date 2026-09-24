# Sonraki Oturum — Sunucu Kurulumu ve Sistemi Taşıma

Bu dosyadaki metni, **yeni bir opencode oturumunun ilk mesajı** olarak kopyalayıp
yapıştır. Amaç: bulut Ubuntu sunucusunu hazırlayıp çalışan sistemi oraya taşımak.

---

## ▼▼▼ AŞAĞIDAKİ METNİ KOPYALA ▼▼▼

Merhaba. **Kütüphane Yönetim Sistemi'ni bulut Ubuntu sunucusuna kurup çalıştırmak
istiyorum.** Monorepo: `/home/serkan/Kutuphane/Okul-Projesi`, aktif dal `V2.0`,
son commit `c4d70b7`.

**Başlamadan önce şu dosyaları oku:**
- `docs/DEPLOY_CLOUD.md` — tüm kurulum rehberi (prod + staging + prod-kopya)
- `docs/SUNUCU_ISLETIM_SAFETY.md` — bu VPS'te güvenli işletim protokolü (ZORUNLU)
- `AGENTS.md` — çalışma kuralları (lokal DB kuralı, yayın akışı)
- `docs/CHANGELOG.md`, `kutuphane/scripts/deploy.sh`, `kutuphane/scripts/rollback.sh`

**Bu oturumun hedefi — Faz A:** sunucuyu hazırla ve sistemi IP üzerinden HTTP ile
yayına al. Mimari:
- PostgreSQL **native (apt)**, yalnız `127.0.0.1:5432` (internete kapalı; Docker yok)
- Django native: venv + Gunicorn + systemd (`127.0.0.1:8000`)
- Nginx ters proxy: kök `/` → genel kitap kataloğu (K11), `/api/*` → DRF/JWT API
- Kurulum: `docs/DEPLOY_CLOUD.md` bölüm **1–11** sırayla uygulanır
- Yayın: `v1.0.0` etiketi oluştur → sunucuda `git clone` → `scripts/deploy.sh prod v1.0.0`

**Alınan kararlar (değiştirmeyelim):**
- Erişim önce IP + HTTP; Faz B sonra alan adı + HTTPS (Let's Encrypt)
- Temiz veritabanı: `migrate` + `createsuperuser` (veri taşıma yok)
- PostgreSQL native (apt); uygulama native (systemd + gunicorn + nginx). Docker **yok**.
- Kod aktarımı **git** (salt-okunur deploy key); rsync yalnız yedek seçenek
- Staging: aynı sunucuda `127.0.0.1:8001` + ayrı `kutuphane_staging` DB
- Kısa kesinti (gunicorn restart ~1-2 sn) kabul; migration öncesi yedek zorunlu
- Sunucudaki tüm uzun işlemler `SUNUCU_ISLETIM_SAFETY.md`'deki kurallara tabi

**Bilmen gerekenler:**
- Sunucu dizinleri: repo kökü `/srv/kutuphane`, uygulama `/srv/kutuphane/kutuphane`,
  venv `/srv/kutuphane/venv` (monorepo → Django alt klasörde)
- Sırlar: `/etc/kutuphane/.env` (prod), `/etc/kutuphane/staging.env` (staging)
- `settings.py` `KUTUPHANE_ENV_FILE` ile farklı `.env` okur (staging için)
- Geliştirme **lokal** Postgres kullanır; prod/staging DB'sine bu makineden bağlanılmaz
- Git `origin` = `github.com:gulecserkan/Okul-Projesi.git`; **commit/push yalnız ben istersem**
- Backend testleri: `cd kutuphane && DEBUG=true DB_PASSWORD=kutuphane_dev venv/bin/python manage.py test kutuphane_app` (şu an 106/106)
- İlk yayın etiketi henüz yok: `VERSION=1.0.0` → `v1.0.0` etiketi atılacak
- Sunucuya **bu makineden SSH ile** bağlanacağız (kurulum komutlarını sen çalıştıracaksın)

**Bana sor / benden al:**
1. Sunucu genel IP adresi (`SERVER_IP`)
2. SSH erişimi: root mı, sudo'lu kullanıcı mı? Şifre mi anahtar mı?
3. `DB_PASSWORD`: sen mi üreteceksin, ben mi üreteyim?
4. Alan adı (Faz B için) — yoksa "şimdilik yok" de
5. Sunucu işletim sistemi sürümü (Ubuntu 24.04 beklenir)

**Çalışma şeklin:** adım adım ilerle; her kritik komuttan önce ne yapacağını kısa
açıkla ve onay al. Eksik/riskli bir nokta görürsen başlamadan söyle. İş bitince
`deploy.sh prod v1.0.0` ile yayına alıp `/api/health/`, `/` katalog ve admin
girişini doğrula.

## ▲▲▲ KOPYALANACAK METNİN SONU ▲▲▲

---

## Hızlı kontrol listesi (bu oturumda tamamlanacak)

- [ ] Sunucu erişimi alındı, Ubuntu sürümü doğrulandı (format sonrası temiz kurulum gerekli — bkz. "Mevcut durum")
- [ ] Bölüm 1–4: sistem paketleri, kullanıcı, `.env`, PostgreSQL (native)
- [ ] Bölüm 5: deploy key + `git clone` (`/srv/kutuphane`)
- [ ] Bölüm 6–7: venv, migrate/collectstatic/createsuperuser, systemd
- [ ] Bölüm 8: nginx + cron (scheduler/backup)
- [ ] Bölüm 9–10: UFW + SSH sertleştirme; Faz A doğrulama
- [ ] `v1.0.0` etiketi + push; GitHub varsayılan dalı `V2.0`
- [ ] `deploy.sh prod v1.0.0` ile yayına alma ve doğrulama
- [ ] (İsteğe bağlı) Bölüm 13: staging ortamı

## Mevcut durum (bu dosya oluşturulurken)

- Dal: `V2.0` · Son commit: `c4d70b7` (push edildi)
- `VERSION`: 1.0.0 (etiket yok)
- Backend testleri: 106/106 · Mobil: 46/46 · Masaüstü: 11/11
- Yerel backend: `runserver 0.0.0.0:8000` (log `/tmp/opencode/runserver.log`)
- Yerel DB: PostgreSQL `127.0.0.1:5432`, DB `kutuphane`, `DB_PASSWORD=kutuphane_dev`
- Yerel değişiklikler (izlenmeyen, commit DEĞİL): `docs/SONRAKI_OTURUM.md`,
  `masaustu/flutter_01.png`, `masaustu/flutter_02.png`

## Sunucu olayı (2026-09-24) — format/reinstall gerekiyor

- Sunucu: Cenuta VPS `89.252.153.171` (Ubuntu 24.04.3, 1 vCPU, 1.9 GiB RAM).
- Açılış: 2690458+ dokümanlarıyla **Docker+compose** planı uygulanmaya başlandı,
  ancak sonra karar değişti → **PostgreSQL native (apt)** (bkz. DEPLOY_CLOUD.md).
  Docker yerine native; betikler buna göre.
- Olay: ilk kurulum sırasında (apt/kernel) sunucu SSH banner üretmez oldu;
  ping açık, nginx ara ara yanıtladı; support force reboot + önceki kernel ile
  açmayı denedi ancak makine erişilmez kaldı → **destek kaydı açıldı**.
- Karar: sunucu yeniden erişilebilir olursa mevcut kurulumu **koruyup devam**,
  değilse panelden **Ubuntu 24.04 LTS reinstall** (Docker-free). Reinstall
  kaybolan bir veri yok (DB/repo henüz kurulmadı).
- Her durumda `docs/SUNUCU_ISLETIM_SAFETY.md` protokolüne uy.
