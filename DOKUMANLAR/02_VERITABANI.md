# 02. Veritabanı Modelleri

Tek uygulama: `kutuphane_app`. Tüm tablolar tek PostgreSQL veritabanında. Trigram indeksi (`pg_trgm`) gerekli.

## Model Şeması

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    Sinif     │◄────│   Ogrenci   │────►│     Rol      │
│  (Sınıflar)  │     │ (Öğrenciler)│     │  (Roller)    │
└─────────────┘     └─────────────┘     └──────┬───────┘
                                                │ 1:1
                                         ┌──────┴───────┐
                                         │RoleLoanPolicy│
                                         │(Rol Politikası)│
                                         └──────────────┘
                                                ▲
┌─────────────┐     ┌─────────────┐             │
│   Yazar      │────►│    Kitap    │             │
│  (Yazarlar)  │     │  (Kitaplar) │─────────────┘
└─────────────┘     └──────┬──────┘  tekil singleton (global varsayılanlar)
                           │ 1:N
                    ┌──────┴──────┐
                    │ KitapNusha  │
                    │  (Nüshalar) │
                    └──────┬──────┘
                           │ 1:N
                    ┌──────┴──────┐
                    │ OduncKaydi  │
                    │(Ödünç Kayıtları)│
                    └─────────────┘

┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Inventory   │────►│ Inventory   │     │  Personel   │
│  Session    │     │    Item     │     │(↔DjangoUser)│
│(Sayım Oturumu)│     │(Sayım Kalemi)│     └─────────────┘
└─────────────┘     └─────────────┘

┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ ArsivBatch  │────►│ ArsivOgrenci│     │ ArsivOdunc  │
│(Arşiv Partisi)│     │(Arşiv Öğr.)│     │(Arşiv Ödünç)│
└─────────────┘     └─────────────┘     └─────────────┘

┌─────────────┐     ┌──────────────────┐
│  AuditLog   │     │  Notification    │
│(Denetim Günlüğü)│     │    Settings      │
└─────────────┘     │(Bildirim Ayarları)│
                    └──────────────────┘

┌─────────────┐
│ LoanPolicy  │  tek satırlık singleton
└─────────────┘
```

---

## Referans Modeller

### Sinif
| Alan | Tip | Açıklama |
|---|---|---|
| `id` | PK | Otomatik |
| `ad` | CharField(20, unique) | Örnek: "5-A", "12/B" |

### Rol
| Alan | Tip | Açıklama |
|---|---|---|
| `id` | PK | Otomatik |
| `ad` | CharField(50, unique) | "Öğrenci" / "Öğretmen" |

Önceki `odunc_suresi_gun`/`maksimum_kitap` alanları `RoleLoanPolicy`'ye taşındı (migration 0015). Yeni Rol eklendiğinde `RoleLoanPolicy` sinyal ile otomatik oluşturulur.

### Yazar
| Alan | Tip | Açıklama |
|---|---|---|
| `id` | PK | Otomatik |
| `ad_soyad` | CharField(100) | |

### Kategori
| Alan | Tip | Açıklama |
|---|---|---|
| `id` | PK | Otomatik |
| `ad` | CharField(50, unique) | |

---

## Öğrenci (Ogrenci)
| Alan | Tip | Açıklama |
|---|---|---|
| `id` | PK | Otomatik |
| `ad` | CharField(50) | |
| `soyad` | CharField(50) | |
| `ogrenci_no` | CharField(20, unique) | |
| `sinif` | FK → Sinif(SET_NULL, null=True) | |
| `rol` | FK → Rol(SET_NULL, null=True) | |
| `telefon` | CharField(20, blank) | |
| `eposta` | EmailField(blank) | |
| `kayit_tarihi` | DateTimeField(auto_now_add) | |
| `aktif` | BooleanField(default=True) | Aktif/pasif durumu |
| `pasif_tarihi` | DateTimeField(null=True, blank) | Pasife çekildiği tarih |

---

## Kitap & Nüsha

### Kitap (Kitap_work)
| Alan | Tip | Açıklama |
|---|---|---|
| `id` | PK | Otomatik |
| `baslik` | CharField(200) | **pg_trgm trigram indeks** |
| `yazar` | FK → Yazar(SET_NULL, null=True) | |
| `kategori` | FK → Kategori(SET_NULL, null=True) | |
| `yayin_yili` | PositiveIntegerField(null=True) | |
| `isbn` | CharField(20, blank) | |
| `aciklama` | TextField(blank) | |
| `resim1..resim5` | ImageField(upload_to="kitap_resimleri/", blank) | Eski resim silinir (pre_save hook) |

### KitapNusha
| Alan | Tip | Açıklama |
|---|---|---|
| `id` | PK | Otomatik |
| `kitap` | FK → Kitap(CASCADE, related_name="nushalar") | |
| `barkod` | CharField(50, unique) | Otomatik: "KIT" + 6-digit serial |
| `durum` | CharField choices: `mevcut` (varsayılan), `oduncte`, `kayip`, `hasarli` | |
| `raf_kodu` | CharField(20, blank) | |

---

## Ödünç Kaydı (OduncKaydi)
| Alan | Tip | Açıklama |
|---|---|---|
| `id` | PK | Otomatik |
| `ogrenci` | FK → Ogrenci(CASCADE) | |
| `kitap_nusha` | FK → KitapNusha(CASCADE) | |
| `odunc_tarihi` | DateTimeField(auto_now_add) | |
| `iade_tarihi` | DateTimeField | Hesaplanan son iade tarihi (rol süresi + hafta sonu kaydırma) |
| `teslim_tarihi` | DateTimeField(null=True) | Gerçekte iade tarihi; `None` ise hâlâ ödünçte |
| `durum` | CharField choices: `oduncte`, `teslim`, `gecikmis`, `kayip`, `hasarli`, `iptal` | |
| `gecikme_cezasi` | DecimalField(8,2, default=0) | Hesaplanan toplam ceza |
| `gecikme_cezasi_odendi` | BooleanField(default=False) | |
| `gecikme_odeme_tarihi` | DateTimeField(null=True) | |
| `gecikme_odeme_tutari` | DecimalField(8,2, default=0) | |

---

## Ödünç Politikası

### LoanPolicy (Global singleton — tek satır)
| Alan | Varsayılan | Açıklama |
|---|---|---|
| `default_duration` | 15 | Varsayılan ödünç süresi (gün) |
| `default_max_items` | 2 | Varsayılan maks. kitap |
| `delay_grace_days` | 0 | Gecikme grace süresi |
| `penalty_delay_days` | 0 | Ceza başlangıç gecikmesi |
| `shift_weekend` | False | Hafta sonu ne olursa olsun son tarihi ileri kaydır |
| `penalty_max_per_loan` | — | Ödünç başına maks. ceza |
| `penalty_max_per_student` | — | Öğrenci başına maks. ceza |
| `daily_penalty_rate` | — | Günlük ceza oranı |
| `quarantine_days` | — | Kayıp/hasarlıdan sonra bekleme |
| `require_damage_note` | — | Hasar notu zorunlu mu |
| `require_shelf_code` | — | Raf kodu zorunlu mu |
| `quiet_hours_start/end` | 22:00/08:00 | Sessiz saatler |

### RoleLoanPolicy (Rola göre override — 1:1 Rol ile)
| Alan | Açıklama |
|---|---|
| `role` | OneToOne → Rol (unique, `related_name="loan_policy"`) |
| `duration` | Bu rolün süresi (None ise global kullanılır) |
| `max_items` | |
| `delay_grace_days` | |
| `penalty_delay_days` | |
| `shift_weekend` | |
| `auto_extend_*` | |
| `penalty_max_per_loan` | |
| `penalty_max_per_student` | |
| `daily_penalty_rate` | |

---

## Arşiv (Snapshot — canlı veri değil)

### ArsivBatch
| Alan | Tip | Açıklama |
|---|---|---|
| `aciklama` | TextField | |
| `olusturma_tarihi` | DateTimeField | |
| `json_dosya` | FileField(upload_to="arsiv/") | JSON yedek dosyası |

### ArsivOgrenci
| Alan | Açıklama |
|---|---|
| `batch` | FK → ArsivBatch |
| `ogrenci_no`, `ad`, `soyad`, `sinif_ad`, `rol_ad`, `telefon`, `eposta` | Snapshot alanları (denormalize) |
| `kayit_tarihi`, `pasif_tarihi` | |

### ArsivOdunc
| Alan | Açıklama |
|---|---|
| `batch` | FK → ArsivBatch |
| `ogrenci_no`, `kitap_baslik`, `barkod`, `odunc_tarihi`, `iade_tarihi`, `teslim_tarihi` | |
| `durum`, `gecikme_cezasi` | |

---

## Sayım (Inventory)

### InventorySession
| Alan | Tip | Açıklama |
|---|---|---|
| `name` | CharField | |
| `description` | TextField(blank) | |
| `status` | `active` / `completed` / `canceled` | |
| `created_by` | FK → User | |
| `filters` | JSONField | Oluşturulurken filtre parametreleri |
| `total_items` / `seen_items` | IntegerField | `progress` property: `seen_items/total_items` (0-1 arası) |

### InventoryItem
| Alan | Tip | Açıklama |
|---|---|---|
| `session` | FK → InventorySession(CASCADE) | |
| `kitap_nusha` | FK → KitapNusha(CASCADE) | unique_together(session, kitap_nusha) |
| `barkod`, `kitap_baslik`, `raf_kodu`, `durum` | | Oluşturma anı snapshot |
| `seen` | BooleanField(default=False) | |
| `seen_at` | DateTimeField(null=True) | |
| `seen_by` | FK → User(null=True) | |
| `note` | TextField(blank) | |

---

## Bildirimler

### NotificationSettings (Singleton)
- Kanal açma/kapama: `printer_warning`, `due_reminder`, `overdue_alert` × (`email`, `sms`, `mobile`)
- Per kanal zamanlama: `*_hour`, `*_minute`, `*_timezone`
- E-posta ayarları: SMTP host, port, user, password, from_address
- SMS ayarları: API URL, key, provider, from_number
- Mesaj şablonları: `reminder_subject/body`, `overdue_subject/body`

---

## Denetim Günlüğü (AuditLog)
| Alan | Tip |
|---|---|
| `kullanici` | FK → User(SET_NULL, null=True) |
| `islem` | CharField (ör. "Ödünç Verme") |
| `detay` | TextField |
| `ip_adresi` | GenericIPAddressField(null=True) |
| `olusturma_zamani` | DateTimeField(auto_now_add) |

---

## Personel
| Alan | Tip | Açıklama |
|---|---|---|
| `ad_soyad` | CharField(100) | |
| `kullanici_adi` | CharField(50, unique) | |
| `sifre_hash` | CharField | Django `make_password` / `check_password` |
| `user` | OneToOne → AUTH_USER_MODEL(null=True) | Otomatik oluşturulur: `is_staff=True` |
| `rol` | `admin` / `personel` | |

---

## Önemli İndeksler

- `Kitap.baslik` → `GinIndex(gin_trgm_ops)` — PostgreSQL trigram benzerlik araması için
- `OduncKaydi` → `odunc_tarihi`, `teslim_tarihi`, `durum` alanlarında sıralama/outerjoin optimizasyonu
- `InventoryItem` → `unique_together("session", "kitap_nusha")`

---

## Ceza Formülü (loan_policy.py)

```
ceza_gun_sayisi = max(0, gecikme_gun - penalty_delay_days)
ceza = daily_penalty_rate × ceza_gun_sayisi
ceza = min(ceza, penalty_max_per_loan)
ceza = min(ceza, kalan_headroom(penalty_max_per_student - diger_aktif_cezalar))
```

Sonuç `0.01`'e yuvarlanır. `daily_penalty_rate=0` ise ceza hesaplanmaz.

**Hafta sonu kaydırma (`shift_weekend`):** `iade_tarihi` cumartesi/pazar gününe denk gelirse bir sonraki pazartesine kaydırılır.

**Grace süresi (`delay_grace_days`):** Gecikme hesabında bu gün kadar affedilir.