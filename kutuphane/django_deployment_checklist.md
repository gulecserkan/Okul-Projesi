# 📋 Django Deployment Checklist

## 1. Genel Hazırlık
- [ ] DEBUG=False, ALLOWED_HOSTS güncelle

## 2. Veritabanı
- [ ] Production DB ayarla
- [ ] migrate ve createsuperuser çalıştır

## 3. Statik/Medya Dosyaları
- [ ] STATIC_ROOT ve MEDIA_ROOT ayarla
- [ ] collectstatic çalıştır

## 4. Web Sunucusu
- [ ] gunicorn/uvicorn ile çalıştır
- [ ] systemd servisi ekle

## 5. Nginx Proxy
- [ ] /static ve /media alias ayarla
- [ ] / backend proxy_pass ayarla

## 6. Güvenlik
- [ ] SECRET_KEY environment variable olarak ayarla
- [ ] HTTPS aktif et (LetsEncrypt/Certbot)
- [ ] UFW/iptables ayarlarını yap

## 7. Yedekleme
- [ ] `/etc/kutuphane/.env` içine `YEDEK_SIFRE` eklendi mi?
- [ ] `scripts/cron.d/kutuphane-yedek` → `/etc/cron.d/kutuphane-yedek` kuruldu mu?
- [ ] `scripts/yedekle.sh` elle çalıştırılıp şifreli yedek doğrulandı mı?
- [ ] `scripts/geri-yukle.sh` geri yükleme provası (scratch DB) yapıldı mı?

## 8. Test
- [ ] Admin paneli açılıyor mu?
- [ ] API endpointleri çalışıyor mu?
- [ ] Masaüstü öğrenci içe aktarma (K9.13) çalışıyor mu?
- [ ] Arşivleme fonksiyonu çalışıyor mu?
