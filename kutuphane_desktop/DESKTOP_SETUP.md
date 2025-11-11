## Masaüstü (PyQt) İstemci Kurulumu

Bu uygulama PyQt5 tabanlıdır ve Linux üzerinde test edilmiştir. Windows/macOS için de aynı Python adımlarını takip edebilirsiniz, sadece komutları kendi kabuğunuza uyarlayın.

### 1. Ön gereksinimler

- Python 3.11
- Qt kütüphaneleri için sistem paketleri (Linux’ta `sudo apt install libqt5gui5 libqt5widgets5 libxcb-cursor0` yeterlidir)
- Git

### 2. Kaynak kodu alın

```bash
git clone <repo-url> kutuphane_desktop
cd kutuphane_desktop
```

### 3. Sanal ortam ve bağımlılıklar

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

> Bağımlılıklar `requirements.txt` içinde listelidir (PyQt5, requests vb.). Farklı platformda çalıştıracaksanız aynı dosyayı kullanmanız yeterli.

### 4. Backend adresini ayarlayın

İlk çalıştırmadan önce backend API adresini belirtmeniz gerekir:

1. Uygulamayı `python main.py` ile başlatın.
2. Giriş ekranında **Ayarlar → Sunucu** sekmesine gidin.
3. `API Temel URL` alanına backend’inizin tam yolunu yazın (örnek: `http://sunucu-adresi:8000/api`).
4. Kaydedip çıkın.

> Alternatif olarak `settings.json` içinde `api.base_url` anahtarını düzenleyebilirsiniz; dosya yoksa uygulama ilk açılışta oluşturur.

### 5. Uygulamayı çalıştırma

```bash
python main.py
```

Giriş için backend’de tanımlı kullanıcı adı/şifreyi kullanın. Tüm işlemler (sayım, öğrenci yönetimi, hızlı erişim vb.) backend API’leri ile senkron çalışır.

### 6. Paketleme / dağıtım (isteğe bağlı)

- PyInstaller ile tek dosya hazırlamak isterseniz: `pip install pyinstaller` ardından `pyinstaller --name kutuphane --onefile main.py`.
- Platform bağımlı Qt kütüphaneleri gerekeceği için hedef sistemde ilgili Qt bağımlılıklarını sağladığınızdan emin olun.

### 7. Menü girişi oluşturma

Masaüstü uygulamasını sistem menüsünde görmek için depo kökündeki `install_desktop_entry.sh` scriptini çalıştırın:

```bash
./install_desktop_entry.sh
```
 adlı bir çalıştırılabilir oluşturur, `resources/icons/library.png` ikonunu `~/.local/share/icons/hicolor/...` içine kopyalar ve `~/.local/share/applications/kutuphane.desktop` dosyasını üretir. Ardından menü veritabanını yenileyerek uygulamayı GNOME/KDE menülerinde “Kütüphane” adıyla görünür hâle getirir.

Script, kullanıcı dizininizde `~/.local/bin/kutuphane`
### 8. Güncellemeler

Kod güncellendiğinde:

```bash
git pull
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Bu adımlar masaüstü istemcisini yeni backend’e bağlayarak sıfır veriden başlayan kurulumlar için yeterlidir.
