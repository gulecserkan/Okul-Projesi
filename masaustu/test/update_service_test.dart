import 'package:flutter_test/flutter_test.dart';

import 'package:masaustu/update_service.dart';

MasaustuSurum surum({int kod = 2, int min = 1}) => MasaustuSurum(
  surum: '1.1.7',
  surumKodu: kod,
  minSurumKodu: min,
  url: '/masaustu/kutuphane-v1.1.7-linux-x64.tar.gz',
  sha256: 'abc',
);

void main() {
  group('MasaustuSurum.fromJson', () {
    test('alanları okur', () {
      final s = MasaustuSurum.fromJson({
        'surum': '1.1.7',
        'surumKodu': 3,
        'minSurumKodu': 2,
        'url': '/masaustu/a.tar.gz',
        'sha256': 'deadbeef',
      });
      expect(s.surum, '1.1.7');
      expect(s.surumKodu, 3);
      expect(s.minSurumKodu, 2);
      expect(s.url, '/masaustu/a.tar.gz');
      expect(s.sha256, 'deadbeef');
    });

    test('eksik alanlara dayanıklı', () {
      final s = MasaustuSurum.fromJson({});
      expect(s.surum, '');
      expect(s.surumKodu, 0);
      expect(s.sha256, '');
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

  group('indirmeAdresi', () {
    test('api tabanından kökü alır ve yolu ekler', () {
      final a = indirmeAdresi(
        'http://89.252.153.171/api',
        '/masaustu/kutuphane-v1.1.7-linux-x64.tar.gz',
      );
      expect(a,
          'http://89.252.153.171/masaustu/kutuphane-v1.1.7-linux-x64.tar.gz');
    });

    test('portu korur', () {
      final a = indirmeAdresi('http://127.0.0.1:8000/api', '/masaustu/a.tar.gz');
      expect(a, 'http://127.0.0.1:8000/masaustu/a.tar.gz');
    });

    test('mutlak adresi korur', () {
      final a = indirmeAdresi('http://sunucu/api', 'https://ornek/a.tar.gz');
      expect(a, 'https://ornek/a.tar.gz');
    });
  });
}
