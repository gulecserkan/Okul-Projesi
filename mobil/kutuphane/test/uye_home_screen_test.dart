import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:kutuphane/api/library_api.dart';
import 'package:kutuphane/models/auth.dart';
import 'package:kutuphane/screens/uye_home_screen.dart';

import 'support/mock_api.dart';

const _tokens = AuthTokens(
  accessToken: 'acc',
  refreshToken: 'ref',
  tip: 'uye',
  uyeNo: '100',
);

Widget _screen({
  List<Map<String, dynamic>> books = const [],
  List<Map<String, dynamic>> loans = const [],
  Map<String, dynamic>? penalty,
}) {
  return MaterialApp(
    home: UyeHomeScreen(
      baseUrl: 'http://test.local',
      tokens: _tokens,
      onLogout: () async {},
      onChangeServer: () async {},
      api: LibraryApiClient(
        baseUrl: 'http://test.local',
        tokens: _tokens,
        httpClient: routingClient(books: books, loans: loans, penalty: penalty),
      ),
    ),
  );
}

void main() {
  testWidgets('kitaplar listesi yüklenir', (tester) async {
    await tester.pumpWidget(_screen(books: [bookJson(baslik: 'Sefiller')]));
    await tester.pumpAndSettle();

    expect(find.text('Sefiller'), findsOneWidget);
  });

  testWidgets('sonuç yoksa boş durum gösterilir', (tester) async {
    await tester.pumpWidget(_screen());
    await tester.pumpAndSettle();

    expect(find.text('Sonuç bulunamadı.'), findsOneWidget);
  });

  testWidgets('ödünçlerim sekmesi aktif ödünçleri gösterir', (tester) async {
    await tester.pumpWidget(_screen(loans: [
      {
        'durum': 'oduncte',
        'odunc_tarihi': '2026-01-01T10:00:00Z',
        'iade_tarihi': '2026-01-15T10:00:00Z',
        'kitap_nusha': {
          'kitap': {'baslik': 'Sefiller'},
        },
      },
    ]));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Ödünçlerim'));
    await tester.pumpAndSettle();

    expect(find.text('Sefiller'), findsOneWidget);
    expect(find.text('Ödünçte'), findsOneWidget);
    expect(find.text('Aktif'), findsOneWidget);
  });

  testWidgets('ödünçlerim sekmesi geciken ödüncü uyarır', (tester) async {
    await tester.pumpWidget(_screen(loans: [
      {
        'durum': 'oduncte',
        'odunc_tarihi': '2026-01-01T10:00:00Z',
        'iade_tarihi': '2020-01-15T10:00:00Z',
        'kitap_nusha': {
          'kitap': {'baslik': 'Sefiller'},
        },
      },
    ]));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Ödünçlerim'));
    await tester.pumpAndSettle();

    expect(find.textContaining('gecikti'), findsOneWidget);
  });

  testWidgets('ceza sekmesi toplam ve kayıtları gösterir', (tester) async {
    await tester.pumpWidget(_screen(penalty: {
      'outstanding_total': '12.50',
      'outstanding_count': 1,
      'has_more': false,
      'entries': [
        {
          'id': 3,
          'kitap': 'Sefiller',
          'barkod': 'KIT00005',
          'durum': 'teslim',
          'odunc_tarihi': '2026-01-01T10:00:00Z',
          'iade_tarihi': '2026-01-15T10:00:00Z',
          'teslim_tarihi': '2026-01-20T10:00:00Z',
          'gecikme_cezasi': '12.50',
          'gecikme_cezasi_odendi': false,
        },
      ],
    }));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Ceza'));
    await tester.pumpAndSettle();

    expect(find.text('₺12.50'), findsWidgets);
    expect(find.text('Sefiller'), findsOneWidget);
  });

  testWidgets('ceza yoksa bilgi gösterilir', (tester) async {
    await tester.pumpWidget(_screen(penalty: {
      'outstanding_total': '0.00',
      'outstanding_count': 0,
      'has_more': false,
      'entries': <Map<String, dynamic>>[],
    }));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Ceza'));
    await tester.pumpAndSettle();

    expect(find.text('Ödenmemiş ceza yok.'), findsOneWidget);
  });
}
