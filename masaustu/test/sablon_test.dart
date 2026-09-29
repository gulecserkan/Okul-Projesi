import 'package:flutter_test/flutter_test.dart';
import 'package:masaustu/config.dart';
import 'package:masaustu/printing/label_pdf.dart';
import 'package:masaustu/printing/receipt_pdf.dart';
import 'package:masaustu/printing/sablon.dart';

/// K14.12: fiş/etiket içerik şablonu.
void main() {
  ruloGenislikTestleri();
  const kurum = KurumBilgisi(
    kutuphaneAdi: 'Okul Kütüphanesi',
    adres: 'Atatürk Mah. Gazi Cad. No:1',
    telefon: '0312 123 45 67',
    eposta: 'kutuphane@okul.edu.tr',
    website: 'www.okul.edu.tr',
  );

  List<ReceiptLine> oduncFisi() => ReceiptPdf.oduncFisi(
        kurum: kurum,
        operator: 'Kütüphane Personeli',
        tarih: '27.09.2026 22:31',
        ogrenci: 'Ali Yılmaz',
        sinif: '10-A',
        kitap: 'Sefere Seven Yedi Kule',
        yazar: 'Tolga Özçelik',
        barkod: 'B-2026-000123',
        oduncTarihi: '27.09.2026',
        iadeTarihi: '11.10.2026',
      );

  BasimSablonu sablonAl(String sahne, Map<String, bool> kapali,
      {Map<String, List<SahneAlanDurumu>>? alanlar}) {
    return BasimSablonu(
      alanlar: alanlar ?? {
        sahne: [
          for (final a in Sablon.alanlar(sahne))
            SahneAlanDurumu(a.kod, acik: !(kapali[a.kod] ?? false)),
        ],
      },
    );
  }

  group('varsayılan şablon', () {
    test('şablon uygulanmasa satır sırası ve içeriği değişmez', () {
      final lines = oduncFisi();
      final sonuc = ReceiptPdf.sablonla(lines, Sahne.odunc.kod,
          const BasimSablonu());
      expect(sonuc.length, lines.length);
      expect(sonuc.map((l) => l.text).toList(),
          lines.map((l) => l.text).toList());
    });

    test('her sahnede zorunlu alanlar mevcut', () {
      expect(
        Sablon.alanlar(Sahne.odunc.kod).where((a) => a.zorunlu).map((a) => a.kod),
        containsAll(<String>['unvan', 'ogrenci', 'kitap', 'barkod', 'iadeTarihi']),
      );
      expect(Sablon.alanlar(Sahne.sifre.kod).where((a) => a.zorunlu).map((a) => a.kod),
          containsAll(<String>['kullaniciAdi', 'sifre']));
      expect(Sablon.alanlar(Sahne.etiket.kod).where((a) => a.zorunlu).map((a) => a.kod),
          containsAll(<String>['baslik', 'barkodMetni', 'barkodCubugu']));
    });
  });

  group('alan kapatma', () {
    test('kapalı alanın satırları ve ayracı düşer', () {
      final sablon = sablonAl(Sahne.odunc.kod, {
        'sinif': true,
        'yazar': true,
      });
      final sonuc = ReceiptPdf.sablonla(oduncFisi(), Sahne.odunc.kod, sablon);
      final metinler = sonuc.map((l) => l.text).toList();
      expect(metinler.any((t) => t.contains('10-A')), isFalse);
      expect(metinler.any((t) => t.contains('Tolga')), isFalse);
      // sinif alanının ardından gelen ayraç da düşmüş olmalı
      final sinifAyrac = oduncFisi().where((l) => l.kod == 'sinif' && l.divider);
      expect(sinifAyrac, isNotEmpty);
      expect(sonuc.where((l) => l.kod == 'sinif'), isEmpty);
      // barkod ayracı durur
      expect(sonuc.where((l) => l.kod == 'barkod' && l.divider), isNotEmpty);
    });

    test('zorunlu alan kapatma isteği yok sayılır', () {
      final sablon = sablonAl(Sahne.odunc.kod, {
        'unvan': true,
        'ogrenci': true,
        'kitap': true,
        'barkod': true,
        'iadeTarihi': true,
      });
      final durum = Sablon.durum(Sahne.odunc.kod, sablon);
      expect(durum.where((d) => d.kod == 'unvan').first.acik, isTrue);
      expect(durum.where((d) => d.kod == 'iadeTarihi').first.acik, isTrue);
      final sonuc = ReceiptPdf.sablonla(oduncFisi(), Sahne.odunc.kod, sablon);
      expect(sonuc.any((l) => l.text == 'ÖDÜNÇ FİŞİ'), isTrue);
      expect(sonuc.any((l) => l.text == 'Ali Yılmaz'), isTrue);
    });

    test('alt bilgi alanları tek tek kapatılabilir', () {
      final tumu = ReceiptPdf.sablonla(
          oduncFisi(), Sahne.odunc.kod, const BasimSablonu());
      expect(tumu.any((l) => l.text.contains('@')), isTrue);
      expect(tumu.any((l) => l.text.contains('www.')), isTrue);

      final kapali = ReceiptPdf.sablonla(oduncFisi(), Sahne.odunc.kod,
          sablonAl(Sahne.odunc.kod, {'eposta': true, 'website': true}));
      expect(kapali.any((l) => l.text.contains('@')), isFalse);
      expect(kapali.any((l) => l.text.contains('www.')), isFalse);
      expect(kapali.any((l) => l.text.contains('Tel:')), isTrue);
    });

    test('alt bilginin tamamı kapanırsa ayraç da düşer', () {
      final sablon = BasimSablonu(alanlar: {
        Sahne.odunc.kod: [
          for (final a in Sablon.alanlar(Sahne.odunc.kod))
            SahneAlanDurumu(a.kod,
                acik: !altBilgiKodlari.contains(a.kod)),
        ],
      });
      final sonuc = ReceiptPdf.sablonla(oduncFisi(), Sahne.odunc.kod, sablon);
      expect(sonuc.where((l) => l.kod == 'altBilgiAyrac'), isEmpty);
      expect(sonuc.where((l) => l.kod == 'operator').first.divider, isFalse);
    });
  });

  group('sıralama', () {
    test('kullanıcı sırası basıma yansır', () {
      final varsayilan = Sablon.durum(Sahne.odunc.kod, const BasimSablonu());
      final yeni = [
        varsayilan.firstWhere((d) => d.kod == 'ogrenci'),
        ...varsayilan.where((d) => d.kod != 'ogrenci'),
      ];
      final sablon = BasimSablonu(alanlar: {Sahne.odunc.kod: yeni});
      final sonuc = ReceiptPdf.sablonla(oduncFisi(), Sahne.odunc.kod, sablon);
      final ilkAlan =
          sonuc.firstWhere((l) => l.kod.isNotEmpty && l.kod != 'altBilgiAyrac');
      expect(ilkAlan.kod, 'ogrenci');
      expect(ilkAlan.text, 'Ali Yılmaz');
    });

    test('katalogda olmayan alan kodu yok sayılır', () {
      final sablon = BasimSablonu(alanlar: {
        Sahne.odunc.kod: [
          const SahneAlanDurumu('olmayanAlan', acik: false),
          ...Sablon.durum(Sahne.odunc.kod, const BasimSablonu()),
        ],
      });
      final durum = Sablon.durum(Sahne.odunc.kod, sablon);
      expect(durum.any((d) => d.kod == 'olmayanAlan'), isFalse);
      expect(ReceiptPdf.sablonla(oduncFisi(), Sahne.odunc.kod, sablon), isNotEmpty);
    });

    test('eksik alanlar varsayılan açık olarak eklenir', () {
      final sablon = BasimSablonu(alanlar: {
        Sahne.odunc.kod: [const SahneAlanDurumu('yazar', acik: false)],
      });
      final durum = Sablon.durum(Sahne.odunc.kod, sablon);
      expect(durum.where((d) => d.kod == 'yazar').first.acik, isFalse);
      expect(durum.where((d) => d.kod == 'ogrenci').first.acik, isTrue);
    });
  });

  group('etiket şablonu', () {
    List<LabelElement> etiket() => LabelPdf.etiketElemanlari(
          kurum: kurum,
          baslik: 'Sefere Seven Yedi Kule',
          yazar: 'Tolga Özçelik',
          kategori: 'Genel',
          barkodMetni: 'B-2026-000123',
        );

    test('varsayılan şablon çıktıyı değiştirmez', () {
      final sonuc = LabelPdf.sablonla(etiket(), const BasimSablonu());
      expect(sonuc.length, etiket().length);
    });

    test('kategori kapatılınca yazar ve barkod kalır', () {
      final sablon = BasimSablonu(alanlar: {
        Sahne.etiket.kod: [
          for (final a in Sablon.alanlar(Sahne.etiket.kod))
            SahneAlanDurumu(a.kod, acik: a.kod != 'kategori'),
        ],
      });
      final sonuc = LabelPdf.sablonla(etiket(), sablon);
      expect(sonuc.any((e) => e.kod == 'kategori'), isFalse);
      expect(sonuc.any((e) => e.kod == 'yazar'), isTrue);
      expect(sonuc.any((e) => e.kod == 'barkodCubugu'), isTrue);
    });
  });

  group('kenar boşluğu', () {
    test('varsayılan 3 mm', () {
      expect(const BasimSablonu().fisKenarMm, 3);
      expect(const BasimSablonu().etiketKenarMm, 3);
    });

    test('JSON round-trip ve sınır değerler', () {
      const s = BasimSablonu(fisKenarMm: 1.5, etiketKenarMm: 8);
      final y = BasimSablonu.fromJson(s.toJson());
      expect(y.fisKenarMm, 1.5);
      expect(y.etiketKenarMm, 8);
      // sınır dışı değerler kırpılır
      final z = BasimSablonu.fromJson(
          {'fis_kenar_mm': 99, 'etiket_kenar_mm': -4});
      expect(z.fisKenarMm, BasimSablonu.kenarMaxMm);
      expect(z.etiketKenarMm, BasimSablonu.kenarMinMm);
    });

    test('alan listesi JSON round-trip', () {
      final s = BasimSablonu(alanlar: {
        Sahne.odunc.kod: [
          const SahneAlanDurumu('ogrenci'),
          const SahneAlanDurumu('sinif', acik: false),
        ],
      });
      final y = BasimSablonu.fromJson(s.toJson());
      final d = Sablon.durum(Sahne.odunc.kod, y);
      expect(d.first.kod, 'ogrenci');
      expect(d[1].kod, 'sinif');
      expect(d[1].acik, isFalse);
    });

    test('eski config (sablon anahtarı yok) varsayılana düşer', () {
      final y = BasimSablonu.fromJson(const {});
      expect(y.fisKenarMm, 3);
      expect(y.alanlar, isEmpty);
    });

    test('yarım kenar boşluğu sayfa yüksekliğine yansır', () {
      final az = ReceiptPdf.sayfaYuksekligiMm(oduncFisi(), kenar: 0);
      final cok = ReceiptPdf.sayfaYuksekligiMm(oduncFisi(), kenar: 8);
      expect(cok, greaterThan(az));
    });
  });
}

// ---------------------------------------------------------------- R1.10 testleri
// Dar rulo (55 mm) altyapısı: sayfa yüksekliği satır sarmasını hesaba katmalı.
void ruloGenislikTestleri() {
  const kurum = KurumBilgisi(kutuphaneAdi: 'Okul Kütüphanesi');

  List<ReceiptLine> fis({String kitap = 'Sefere Seven Yedi Kule'}) =>
      ReceiptPdf.oduncFisi(
        kurum: kurum,
        operator: 'Kütüphane Personeli',
        tarih: '27.09.2026 22:31',
        ogrenci: 'Ali Yılmaz',
        sinif: '10-A',
        kitap: kitap,
        yazar: 'Tolga Özçelik',
        barkod: 'B-2026-000123',
        oduncTarihi: '27.09.2026',
        iadeTarihi: '11.10.2026',
      );

  // 55 mm'de de sarmalanan uzun başlık
  const uzunKitap =
      'İnsan Olmak ve Ötekilerle Birlikte Yaşamak Üzerine Bir Söyleşi Kitabı';

  test('dar ruloda (55 mm) uzun satırlar sarmalandığı için yükseklik artar', () {
    final lines = fis(kitap: uzunKitap);
    final genis = ReceiptPdf.sayfaYuksekligiMm(lines, kenar: 3, genislikMm: 70);
    final dar = ReceiptPdf.sayfaYuksekligiMm(lines, kenar: 3, genislikMm: 55);
    expect(dar, greaterThan(genis),
        reason: 'sarma üst sınırla hesaplanır → taşma yerine boşluk bırakır');
  });

  test('sarma, varsayılan 70 mm genişliğe göre hesaplanır', () {
    final lines = fis(kitap: uzunKitap);
    final varsayilan = ReceiptPdf.sayfaYuksekligiMm(lines, kenar: 3);
    final dar = ReceiptPdf.sayfaYuksekligiMm(lines, kenar: 3, genislikMm: 55);
    final cokGenis =
        ReceiptPdf.sayfaYuksekligiMm(lines, kenar: 3, genislikMm: 500);
    expect(dar, greaterThan(varsayilan));
    expect(cokGenis, lessThan(varsayilan));
  });

  test('kısa satırlı standart fiş 55 mm genişliğe sığar (yükseklik değişmez)', () {
    final lines = fis();
    expect(
      ReceiptPdf.sayfaYuksekligiMm(lines, kenar: 3, genislikMm: 55),
      ReceiptPdf.sayfaYuksekligiMm(lines, kenar: 3, genislikMm: 70),
    );
  });

  test('kenar boşluğu hâlâ yüksekliğe yansır', () {
    final lines = fis(kitap: uzunKitap);
    final az = ReceiptPdf.sayfaYuksekligiMm(lines, kenar: 0, genislikMm: 55);
    final cok = ReceiptPdf.sayfaYuksekligiMm(lines, kenar: 8, genislikMm: 55);
    expect(cok, greaterThan(az));
  });
}
