import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:kutuphane/api/library_api.dart';
import 'package:kutuphane/api/sunucu_adresi.dart';

/// Verilen host'lar için health yanıtı üreten sahte istemci fabrikası.
LibraryApiClient Function(String) _factory({
  required Set<String> calisanHostlar,
  Set<String> yavasHostlar = const {},
}) {
  return (base) {
    final client = MockClient((request) async {
      final host = request.url.host;
      if (yavasHostlar.contains(host)) {
        await Future<void>.delayed(const Duration(milliseconds: 200));
      }
      if (calisanHostlar.contains(host)) {
        return http.Response('{"status":"ok"}', 200,
            headers: {'content-type': 'application/json'});
      }
      throw Exception('ulaşılamaz: $host');
    });
    return LibraryApiClient(baseUrl: base, httpClient: client);
  };
}

void main() {
  const adaylar = ['https://okulkitapligi.tr', 'http://89.252.153.171'];

  test('domain ölü, IP çalışıyor → IP seçilir', () async {
    final sonuc = await enIyiSunucuAdresiYokla(
      adaylar: adaylar,
      clientFactory: _factory(calisanHostlar: {'89.252.153.171'}),
    );
    expect(sonuc, 'http://89.252.153.171');
  });

  test('domain çalışıyor → domain seçilir (öncelikli)', () async {
    final sonuc = await enIyiSunucuAdresiYokla(
      adaylar: adaylar,
      clientFactory: _factory(
        calisanHostlar: {'okulkitapligi.tr', '89.252.153.171'},
        yavasHostlar: {'89.252.153.171'},
      ),
    );
    expect(sonuc, 'https://okulkitapligi.tr');
  });

  test('hiçbiri ulaşılamazsa null', () async {
    final sonuc = await enIyiSunucuAdresiYokla(
      adaylar: adaylar,
      clientFactory: _factory(calisanHostlar: {}),
    );
    expect(sonuc, isNull);
  });

  test('aday listesi boşsa null', () async {
    expect(await enIyiSunucuAdresiYokla(adaylar: const []), isNull);
  });
}
