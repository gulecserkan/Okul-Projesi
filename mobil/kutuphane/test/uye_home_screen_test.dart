import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'package:kutuphane/api/library_api.dart';
import 'package:kutuphane/models/auth.dart';
import 'package:kutuphane/screens/uye_home_screen.dart';

import 'support/fake_http.dart';
import 'support/mock_api.dart';

const _tokens = AuthTokens(
  accessToken: 'acc',
  refreshToken: 'ref',
  tip: 'uye',
  uyeNo: '100',
);

Widget _screen({
  List<Map<String, dynamic>> books = const [],
  List<Map<String, dynamic>> categories = const [],
  List<Map<String, dynamic>> authors = const [],
  List<Map<String, dynamic>> loans = const [],
  Map<String, dynamic>? penalty,
  Map<String, dynamic>? bookDetail,
  void Function(http.Request request)? onRequest,
}) {
  return MaterialApp(
    home: UyeHomeScreen(
      baseUrl: 'http://test.local',
      tokens: _tokens,
      onLogout: () async {},
      api: LibraryApiClient(
        baseUrl: 'http://test.local',
        tokens: _tokens,
        httpClient: routingClient(
          books: books,
          categories: categories,
          authors: authors,
          loans: loans,
          penalty: penalty,
          bookDetail: bookDetail,
          onRequest: onRequest,
        ),
      ),
    ),
  );
}

/// Geniş test yüzeyi (kitap ızgarası kartlarının başlıkları görünür olsun diye).
Future<void> pumpScreen(
  WidgetTester tester, {
  List<Map<String, dynamic>> books = const [],
  List<Map<String, dynamic>> categories = const [],
  List<Map<String, dynamic>> authors = const [],
  List<Map<String, dynamic>> loans = const [],
  Map<String, dynamic>? penalty,
  Map<String, dynamic>? bookDetail,
  void Function(http.Request request)? onRequest,
}) async {
  tester.view.physicalSize = const Size(1200, 2400);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    _screen(
      books: books,
      categories: categories,
      authors: authors,
      loans: loans,
      penalty: penalty,
      bookDetail: bookDetail,
      onRequest: onRequest,
    ),
  );
  await tester.pumpAndSettle();
}

/// /api/kitaplar/ isteklerini toplayan yardımcı.
List<Uri> _kitapIstemleri(List<http.Request> reqs) => reqs
    .where((r) => r.url.path.endsWith('/api/kitaplar/'))
    .map((r) => r.url)
    .toList();

void main() {
  setUpAll(() {
    HttpOverrides.global = FakeHttpOverrides();
  });

  tearDownAll(() {
    HttpOverrides.global = null;
  });

  testWidgets('app bar üye adı+soyadı (no) ve uygulama adını gösterir', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: UyeHomeScreen(
          baseUrl: 'http://test.local',
          tokens: AuthTokens(
            accessToken: 'acc',
            refreshToken: 'ref',
            tip: 'uye',
            fullName: 'Ayşe Kaya',
            uyeNo: '100',
          ),
          onLogout: () async {},
          api: LibraryApiClient(
            baseUrl: 'http://test.local',
            tokens: _tokens,
            httpClient: routingClient(),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Ayşe Kaya (100)'), findsOneWidget);
    expect(find.text('Kütüphane'), findsOneWidget);
  });

  testWidgets('kitaplar kapak ızgarasında yüklenir', (tester) async {
    await pumpScreen(tester, books: [bookJson(baslik: 'Sefiller')]);

    expect(find.text('Sefiller'), findsOneWidget);
    expect(find.text('1 kitap'), findsOneWidget);
  });

  testWidgets('sonuç yoksa boş durum gösterilir', (tester) async {
    await pumpScreen(tester);

    expect(find.text('Sonuç bulunamadı.'), findsOneWidget);
  });

  testWidgets('kategori çipi seçilince kategori filtresi gider (K9.9)', (
    tester,
  ) async {
    final reqs = <http.Request>[];
    await pumpScreen(
      tester,
      books: [bookJson(baslik: 'Sefiller', kategori: 'Roman')],
      categories: [
        {'id': 2, 'ad': 'Roman'},
      ],
      onRequest: reqs.add,
    );

    await tester.tap(find.text('Roman'));
    await tester.pumpAndSettle();

    final kitaplar = _kitapIstemleri(reqs);
    expect(kitaplar.last.queryParameters['kategori'], '2');
  });

  testWidgets('yazar seçimi yazar filtresi gönderir', (tester) async {
    final reqs = <http.Request>[];
    await pumpScreen(
      tester,
      books: [bookJson(baslik: 'Sefiller', yazar: 'Victor Hugo')],
      authors: [
        {'id': 9, 'ad_soyad': 'Victor Hugo'},
      ],
      onRequest: reqs.add,
    );

    await tester.tap(find.text('Yazar'));
    await tester.pumpAndSettle();

    await tester.tap(
      find.descendant(
        of: find.byType(BottomSheet),
        matching: find.text('Victor Hugo'),
      ),
    );
    await tester.pumpAndSettle();

    final kitaplar = _kitapIstemleri(reqs);
    expect(kitaplar.last.queryParameters['yazar'], '9');
  });

  testWidgets('görsellik ve öğretmen görüşü anahtarları parametre gönderir', (
    tester,
  ) async {
    final reqs = <http.Request>[];
    await pumpScreen(
      tester,
      books: [bookJson(baslik: 'Sefiller', imageCount: 3, aciklamaVar: true)],
      onRequest: reqs.add,
    );

    await tester.tap(find.text('Sadece görselli'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Öğretmen görüşü'));
    await tester.pumpAndSettle();

    final kitaplar = _kitapIstemleri(reqs);
    expect(kitaplar.last.queryParameters['min_image_count'], '1');
    expect(kitaplar.last.queryParameters['aciklama_var'], '1');
  });

  testWidgets('sıralama menüsü ordering parametresi gönderir', (tester) async {
    final reqs = <http.Request>[];
    await pumpScreen(
      tester,
      books: [bookJson(baslik: 'Sefiller')],
      onRequest: reqs.add,
    );

    await tester.tap(find.byIcon(Icons.sort));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Yayın yılı (yeni→eski)'));
    await tester.pumpAndSettle();

    final kitaplar = _kitapIstemleri(reqs);
    expect(kitaplar.last.queryParameters['ordering'], '-yayin_yili');
  });

  testWidgets('ızgara ↔ yatay raf geçişi çalışır', (tester) async {
    await pumpScreen(tester, books: [bookJson(baslik: 'Sefiller')]);

    expect(find.byIcon(Icons.grid_view_rounded), findsOneWidget);

    await tester.tap(find.byIcon(Icons.view_agenda_outlined));
    await tester.pumpAndSettle();

    // Raf modunda yatay, kontrollü bir ListView (kategori listesi kontrollü değil).
    final raf = find.byWidgetPredicate(
      (w) =>
          w is ListView &&
          w.scrollDirection == Axis.horizontal &&
          w.controller != null,
    );
    expect(raf, findsOneWidget);
    expect(find.text('Sefiller'), findsOneWidget);

    await tester.tap(find.byIcon(Icons.grid_view_rounded));
    await tester.pumpAndSettle();
    expect(raf, findsNothing);
  });

  testWidgets('kitaba tıklanınca inceleme sayfası açılır (K9.9)', (
    tester,
  ) async {
    await pumpScreen(
      tester,
      books: [bookJson(baslik: 'Sefiller')],
      bookDetail: {
        'id': 1,
        'baslik': 'Sefiller',
        'yazar': {'ad_soyad': 'Victor Hugo'},
        'kategori': {'ad': 'Roman'},
        'nusha_sayisi': 3,
        'aciklama': 'Öğretmen görüşü: sınıfa tavsiye edilir.',
      },
    );

    await tester.tap(find.text('Sefiller'));
    await tester.pumpAndSettle();

    expect(find.text('Öğretmen Görüşü'), findsOneWidget);
    expect(find.text('Künye'), findsOneWidget);
    expect(find.text('Victor Hugo'), findsOneWidget);
    expect(
      find.text(
        'Kütüphanede 3 nüsha mevcut. Ödünç almak için kütüphaneye uğrayabilirsin.',
      ),
      findsOneWidget,
    );
  });

  testWidgets('incelemede görsel sayfası gösterilir ve galeri açılır', (
    tester,
  ) async {
    await pumpScreen(
      tester,
      books: [bookJson(baslik: 'Kapakli Kitap')],
      bookDetail: {
        'id': 7,
        'baslik': 'Kapakli Kitap',
        'resim1': 'http://test.local/media/kitap_resimleri/1.jpg',
      },
    );

    await tester.tap(find.text('Kapakli Kitap'));
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));

    expect(find.text('Sayfa 1'), findsOneWidget);
    expect(find.byType(Image), findsOneWidget);

    await tester.tap(find.byType(Image));
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));

    expect(find.text('Resmi görüntüle'), findsOneWidget);
  });

  testWidgets('ödünçlerim sekmesi aktif ödünçleri gösterir', (tester) async {
    await pumpScreen(
      tester,
      loans: [
        {
          'durum': 'oduncte',
          'odunc_tarihi': '2026-01-01T10:00:00Z',
          'iade_tarihi': '2026-01-15T10:00:00Z',
          'kitap_nusha': {
            'kitap': {'baslik': 'Sefiller'},
          },
        },
      ],
    );

    await tester.tap(find.text('Ödünçlerim'));
    await tester.pumpAndSettle();

    expect(find.text('Sefiller'), findsOneWidget);
    expect(find.text('Ödünçte'), findsOneWidget);
    expect(find.text('Aktif'), findsOneWidget);
  });

  testWidgets('ödünçlerim sekmesi geciken ödüncü uyarır', (tester) async {
    await pumpScreen(
      tester,
      loans: [
        {
          'durum': 'oduncte',
          'odunc_tarihi': '2026-01-01T10:00:00Z',
          'iade_tarihi': '2020-01-15T10:00:00Z',
          'kitap_nusha': {
            'kitap': {'baslik': 'Sefiller'},
          },
        },
      ],
    );

    await tester.tap(find.text('Ödünçlerim'));
    await tester.pumpAndSettle();

    expect(find.textContaining('gecikti'), findsOneWidget);
  });

  testWidgets('ceza sekmesi toplam ve kayıtları gösterir', (tester) async {
    await pumpScreen(
      tester,
      penalty: {
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
      },
    );

    await tester.tap(find.text('Ceza'));
    await tester.pumpAndSettle();

    expect(find.text('₺12.50'), findsWidgets);
    expect(find.text('Sefiller'), findsOneWidget);
  });

  testWidgets('ceza yoksa bilgi gösterilir', (tester) async {
    await pumpScreen(
      tester,
      penalty: {
        'outstanding_total': '0.00',
        'outstanding_count': 0,
        'has_more': false,
        'entries': <Map<String, dynamic>>[],
      },
    );

    await tester.tap(find.text('Ceza'));
    await tester.pumpAndSettle();

    expect(find.text('Ödenmemiş ceza yok.'), findsOneWidget);
  });

  testWidgets('Şifre düğmesi diyaloğu açar ve şifre güncellenir (K9.8)', (
    tester,
  ) async {
    await pumpScreen(tester);

    await tester.tap(find.text('Şifre'));
    await tester.pumpAndSettle();

    expect(find.text('Şifre değiştir'), findsOneWidget);

    await tester.enterText(
      find.widgetWithText(TextField, 'Mevcut şifre'),
      'eskisi',
    );
    await tester.enterText(
      find.widgetWithText(TextField, 'Yeni şifre'),
      'yenisi',
    );
    await tester.enterText(
      find.widgetWithText(TextField, 'Yeni şifre (tekrar)'),
      'yenisi',
    );
    await tester.tap(find.text('Kaydet'));
    await tester.pumpAndSettle();

    expect(find.text('Şifre güncellendi.'), findsOneWidget);
  });

  testWidgets('uyuşmayan yeni şifrelerde hata gösterilir', (tester) async {
    await pumpScreen(tester);

    await tester.tap(find.text('Şifre'));
    await tester.pumpAndSettle();

    await tester.enterText(
      find.widgetWithText(TextField, 'Mevcut şifre'),
      'eskisi',
    );
    await tester.enterText(
      find.widgetWithText(TextField, 'Yeni şifre'),
      'yenisi',
    );
    await tester.enterText(
      find.widgetWithText(TextField, 'Yeni şifre (tekrar)'),
      'farkli',
    );
    await tester.tap(find.text('Kaydet'));
    await tester.pumpAndSettle();

    expect(find.text('Yeni şifreler uyuşmuyor.'), findsOneWidget);
  });
}
