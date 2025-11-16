# Paketleme Planı

Bu klasör, masaüstü ve sunucu bileşenleri için basit `.deb` paketlerini üretmek üzere betikler içerir. Varsayılan yaklaşım:

1. Kaynak kodu `/opt/...` altına yerleştirilen staging dizinine kopyalar (venv hariç).
2. `DEBIAN/control` ve `postinst` dosyalarını yazar.
3. `dpkg-deb --build` ile paketler.

## Masaüstü (.deb)
```
cd packaging
VERSION=1.0.0 ./build_desktop_deb.sh
```
- Çıktı: `packaging/dist/kutuphane-desktop_<version>.deb`
- Kurulum sonrası `install_desktop_entry.sh` otomatik çalışır; WM_CLASS ve kısayol oluşturulur.

## Sunucu (.deb)
```
cd packaging
VERSION=1.0.0 ./build_server_deb.sh ../kutuphane    # masaüstü klasörünü içeriyorsa otomatik hariç tutar
```
- Çıktı: `packaging/dist/kutuphane-server_<version>.deb`
- Postinst: `/etc/kutuphane/.env` yoksa otomatik oluşturur (varsayılan DB/admin bilgileriyle), migrate ve superuser (yoksa) çalıştırır. `setup_backend_service.sh` varsa systemd/cron kurulumunu çalıştırmayı dener; başarısız olursa log verir. .env içindeki parolaları güncellemeyi unutmayın.

## Basit apt deposu üretmek
```
cd packaging
./build_apt_repo.sh
```
- Gereksinim: `dpkg-scanpackages` (dpkg-dev paketi).
- Çıktı: `packaging/apt-repo/` altında apt dizin yapısı (pool + Packages/Packages.gz).
- Bu klasörü ayrı bir repoya veya gh-pages branşına koyup repo satırı olarak şunu ekleyebilirsiniz:
  `deb [trusted=yes] https://<kullanici>.github.io/<repo>/apt-repo stable main`

## Meta paket (opsiyonel)
- Sunucu ve masaüstü paketlerine bağımlı kılınmış basit bir paket üretmek isterseniz `build_meta_deb.sh` (henüz eklenmedi) içine iki paketi Depends olarak yazabilirsiniz.

## Notlar
- Betikler `venv`, `__pycache__`, `.git` gibi klasörleri kopyalamaz; çalıştığı ortamda sistem bağımlılıkları `Depends` ile talep edilir.
- Gizli bilgiler `.env` ile yönetilmeli; systemd unit veya cron job dosyaları bu `.env` dosyasını `EnvironmentFile` satırıyla okumalıdır.
- CI’de `debuild` veya `dpkg-deb` kullanılabilir; bu betikler lokal üretime hızlı başlangıç içindir.
