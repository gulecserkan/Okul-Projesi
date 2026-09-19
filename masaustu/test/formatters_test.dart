import 'package:flutter_test/flutter_test.dart';

import 'package:masaustu/formatters.dart';

void main() {
  test('normalizeTr Türkçe harf/aksan/noktalama farklarını eşitler', () {
    expect(normalizeTr('Sabahattin Ali'), 'sabahattin ali');
    expect(normalizeTr('Sabahattin  ALİ'), 'sabahattin ali');
    expect(normalizeTr('Çocuk'), 'cocuk');
    expect(normalizeTr('İnce Memed'), 'ince memed');
    expect(normalizeTr('Alı'), normalizeTr('Ali'));
    expect(normalizeTr('  A-1 '), 'a 1');
  });

  test('similarityTr aynı/benzer/farklı metinleri ayırır', () {
    expect(similarityTr('Sabahattin Ali', 'sabahattin ali'), 1.0);
    expect(similarityTr('Orhan Pamuk', 'Orhan Pamukk') > 0.8, isTrue);
    expect(similarityTr('Orhan Pamuk', 'Yaşar Kemal') < 0.5, isTrue);
    expect(similarityTr('', ''), 1.0);
    expect(similarityTr('Ali', ''), 0.0);
  });
}
