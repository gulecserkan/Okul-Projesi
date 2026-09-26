import 'package:flutter_test/flutter_test.dart';

import 'package:kutuphane/models/mobil_surum.dart';
import 'package:kutuphane/widgets/update_dialog.dart';

MobilSurum surum({int kod = 2, int min = 1}) => MobilSurum(
  surum: "1.1.4",
  surumKodu: kod,
  minSurumKodu: min,
  apkUrl: "/mobil/kutuphane-v1.1.4.apk",
);

void main() {
  group('MobilSurum.fromJson', () {
    test('alanları okur', () {
      final s = MobilSurum.fromJson({
        "surum": "1.1.4",
        "surumKodu": 3,
        "minSurumKodu": 2,
        "apkUrl": "/mobil/kutuphane-v1.1.4.apk",
      });
      expect(s.surum, "1.1.4");
      expect(s.surumKodu, 3);
      expect(s.minSurumKodu, 2);
      expect(s.apkUrl, "/mobil/kutuphane-v1.1.4.apk");
    });

    test('eksik alanlara dayanıklı', () {
      final s = MobilSurum.fromJson({});
      expect(s.surum, "");
      expect(s.surumKodu, 0);
      expect(s.minSurumKodu, 0);
    });
  });

  group('guncellemeKarari', () {
    test('uzak sürüm yoksa güncelleme yok', () {
      final k = guncellemeKarari(kuruluKod: 1, uzak: null);
      expect(k.guncellemeVar, isFalse);
      expect(k.zorunlu, isFalse);
    });

    test('aynı sürümde güncelleme yok', () {
      final k = guncellemeKarari(kuruluKod: 2, uzak: surum(kod: 2, min: 1));
      expect(k.guncellemeVar, isFalse);
    });

    test('yeni sürüm var, min üstünde ise opsiyonel', () {
      final k = guncellemeKarari(kuruluKod: 1, uzak: surum(kod: 2, min: 1));
      expect(k.guncellemeVar, isTrue);
      expect(k.zorunlu, isFalse);
    });

    test('kurulu sürüm min altındaysa zorunlu', () {
      final k = guncellemeKarari(kuruluKod: 1, uzak: surum(kod: 5, min: 2));
      expect(k.guncellemeVar, isTrue);
      expect(k.zorunlu, isTrue);
    });
  });

  group('guncellemeUri', () {
    test('bağıl yolu taban adresle birleştirir', () {
      final uri = guncellemeUri(
        "http://89.252.153.171",
        "/mobil/kutuphane-v1.1.4.apk",
      );
      expect(uri.toString(), "http://89.252.153.171/mobil/kutuphane-v1.1.4.apk");
    });

    test('sondaki eğik çizgiyi yönetir', () {
      final uri = guncellemeUri(
        "http://sunucu/",
        "/mobil/kutuphane-v1.1.4.apk",
      );
      expect(uri.toString(), "http://sunucu/mobil/kutuphane-v1.1.4.apk");
    });

    test('mutlak adresi korur', () {
      final uri = guncellemeUri(
        "http://sunucu",
        "https://ornek/mobil/a.apk",
      );
      expect(uri.toString(), "https://ornek/mobil/a.apk");
    });
  });
}
