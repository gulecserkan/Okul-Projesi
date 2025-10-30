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
- [ ] backups/ klasörünü periyodik yedekle (cron job)

## 8. Test
- [ ] Admin paneli açılıyor mu?
- [ ] API endpointleri çalışıyor mu?
- [ ] Öğrenci içe/dışa aktarma çalışıyor mu?
- [ ] Arşivleme fonksiyonu çalışıyor mu?
- [ ] Backup/restore fonksiyonları çalışıyor mu?
