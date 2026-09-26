import 'package:flutter_test/flutter_test.dart';

import 'package:masaustu/sunucu_adresi.dart';

/// Verilen host'lar için health sonucu dönen sahte kontrol.
Future<bool> Function(String) _kontrol({
  required Set<String> calisanHostlar,
  Set<String> yavasHostlar = const {},
}) {
  return (baseUrl) async {
    final host = Uri.parse(baseUrl).host;
    if (yavasHostlar.contains(host)) {
      await Future<void>.delayed(const Duration(milliseconds: 200));
    }
    return calisanHostlar.contains(host);
  };
}

void main() {
  const adaylar = [
    'https://okulkitapligi.tr/api',
    'http://89.252.153.171/api',
  ];

  test('domain ölü, IP çalışıyor → IP seçilir', () async {
    final sonuc = await enIyiSunucuAdresiYokla(
      adaylar: adaylar,
      saglikKontrol: _kontrol(calisanHostlar: {'89.252.153.171'}),
    );
    expect(sonuc, 'http://89.252.153.171/api');
  });

  test('domain çalışıyor → domain seçilir (öncelikli)', () async {
    final sonuc = await enIyiSunucuAdresiYokla(
      adaylar: adaylar,
      saglikKontrol: _kontrol(
        calisanHostlar: {'okulkitapligi.tr', '89.252.153.171'},
        yavasHostlar: {'89.252.153.171'},
      ),
    );
    expect(sonuc, 'https://okulkitapligi.tr/api');
  });

  test('hiçbiri ulaşılamazsa null', () async {
    final sonuc = await enIyiSunucuAdresiYokla(
      adaylar: adaylar,
      saglikKontrol: _kontrol(calisanHostlar: {}),
    );
    expect(sonuc, isNull);
  });

  test('aday listesi boşsa null', () async {
    expect(await enIyiSunucuAdresiYokla(adaylar: const []), isNull);
  });
}
