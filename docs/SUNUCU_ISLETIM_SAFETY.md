# Sunucu İşletim Güvenlik Protokolü (Faz A)

Hedef: 1 vCPU / 1.9 GiB RAM'lik küçük VPS'te (89.252.153.171, Cenuta) kurulumu
ve yayını **bizim işlemlerimizden kaynaklanacak kilitlenme/kesinti olmadan**
yapmak. Bu protokol, `docs/DEPLOY_CLOUD.md` ile birlikte uygulanır.

---

## 1. Geçmişten çıkarılan dersler

| Yaşanan sorun | Kök neden (bizden kaynaklanan kısım) | Yeni kural |
|---|---|---|
| Tek uzun SSH komutu 15 dk sonra timeout → görüş kaybı | Ağır `apt-get install` tek çağrıda, izlemesiz | Uzun işler idi `tmux`/`nohup + log`; küçük adımlar |
| Swap thrashing / sshd banner üretememek | 1 vCPU'da ağır yük + büyük swap | Swappiness düşük; adımlar arası `uptime`/`free` kontrol |
| Kernel yükseltmesi sonrası boot takılması (şüphe) | `apt-get upgrade` farkında olmadan kernel çekti | Kernel taşıyan upgrade ayrı, planlı adım |
| Sık SSH denemesi → "reset / no route" | Sağlayıcı tarafı koruma + panik denemeler | Panik yok; bekle + tekrar; nadir yokla |

## 2. Zorunlu oturum kuralları

1. **Adımlar küçük ve bölünmüş:** Bir SSH çağrısında yalnızca bir konu.
   Her çağrı kısa sürmeli (< ~3 dk).
2. **Uzun işlem = arka plan + log + poll.** 2 dk'dan uzun sürebilecek işler
   (apt kurulumu, `pip install`, `migrate`, `collectstatic`, `systemctl restart postgresql`):
   ```
   nohup sudo bash -c '<komut>; echo EXIT=$?' >/var/log/kutuphane/bootstrap_<ad>.log 2>&1 &
   ```
   Ardından kısa aralıklarla log sondunu ve `ps` durumunu izle. Bitince healthcheck.
3. **Her adımın sonunda teyit:** `systemctl is-active <servis>`, `curl` health,
   `uptime` + `free -h | head -2`.
4. **Şüpheli belirtide panik yok.** `banner timeout`/`reset` görünce üst üste
   SSH deneme; 30-60 sn bekle, tek dene. Sağlayıcı korumasını tetiklememek için
   sık deneme yapma.
5. **Yük kontrolü:** Ağır işe başlamadan önce `uptime` (yük < 1.5 hedef, zaten
   düşükken) ve `free` (swap dolu değilse). Yük yüksekse bekler, başlatmaz.

## 3. Kritik işlem listesi ve güvenli uygulama sırası

Kurulum bölüm 1–10'daki adımlar şu şekilde güvenli hale getirilir:

0. **Format sonrası ilk iş:** SSH anahtarıyla giriş doğrula; `sudo -n` testi.
1. `apt-get update` → ayrı, küçük adım.
2. **Kernel/upgrade kararı:** `apt-get -y --with-new-pkgs upgrade` ayrı adım,
   tmux/nohup ile. Kernel indiyse kapatma **bilinçli tek reboot** konsoldan
   gözlenerek. Değilse devam.
3. Paket kurulumu **gruplar halinde**:
   - Grup A (temel): `python3 python3-venv python3-dev build-essential libpq-dev git curl rsync`
   - Grup B (servis): `nginx ufw fail2ban unattended-upgrades`
   - Grup C (DB): `postgresql`
   Her grup sonrası `uptime` + `systemctl` teyit.
4. **Swap:** Anında 1 GiB yerine **alsız başla**; `vm.swappiness=10` ayarla
   (`/etc/sysctl.d/`). Gerekirse sadece 512 MiB ekle. (Karar: kurulum bitip
   bellek profili görülünce.)
5. Kullanıcı/dizinler → `.env` → PostgreSQL (native) → deploy key (kullanıcı
   etkileşimi) → clone → venv/pip/migrate/collectstatic/createsuperuser →
   systemd → nginx → firewall → Faz A doğrulama. Her adım 2. bölümdeki teyitle.

## 4. Yayın (deploy) güvenlik kuralları

1. **Önce staging** (aynı sunucu, 8001), sonra prod. Kullan: 
   `sudo bash /srv/kutuphane-staging/kutuphane/scripts/deploy.sh staging <tag>`
2. Migration öncesi yedek **zorunlu** — `deploy.sh` içinde var (doğrulandı).
3. `deploy.sh` sadece **etiketli** sürüm çeker; el dosyası kopyalama yok.
4. Healthcheck başarısızsa rollback: `rollback.sh <ortam> <ønceki-tag>`.
5. Kesinti: gunicorn restart ~1-2 sn — kabul; yedeğe dayan.

## 5. Tekrarlanabilirlik

- Tüm sunucu yapılandırması (`DEPLOY_CLOUD.md` + bu doküman + deploy/rollback
  betikleri) depoda. Format sonrası aynı protokolle aynı sonuç.
- Sırlar (`SECRET_KEY`, `FIELD_ENCRYPTION_KEY`, `DB_PASSWORD`) veri yokken
  yeniden üretilebilir — kritik değer yok.
- `.env` izni: `root:kutuphane 640` (ayrıntı: `DEPLOY_CLOUD.md` bölüm 3).

## 6. Acil durum (banner gelmezse)

1. 30-60 sn bekle → tek SSH denemesi.
2. Ping+port 22/80 yokla (tek komut).
3. Panel durumuna bak (Çalışıyor/Kapalı/Başlatılıyor).
4. Sağlayıcı konsolu/reinstall gerekirse **destek kaydı** aç; bizim verimiz yok,
   yeniden kurulum düşük maliyetli.
5. Bu dokümandaki adımları birebir uygula; ayrımsama yapma.