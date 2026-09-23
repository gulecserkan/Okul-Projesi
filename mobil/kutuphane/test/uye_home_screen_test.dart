import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

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
  List<Map<String, dynamic>> loans = const [],
  Map<String, dynamic>? penalty,
  Map<String, dynamic>? bookDetail,
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
        httpClient: routingClient(
          books: books,
          loans: loans,
          penalty: penalty,
          bookDetail: bookDetail,
        ),
      ),
    ),
  );
}

void main() {
  setUpAll(() {
    HttpOverrides.global = FakeHttpOverrides();
  });

  tearDownAll(() {
    HttpOverrides.global = null;
  });

  testWidgets('app bar üye adı+soyadı (no) ve uygulama adını gösterir',
      (tester) async {
    await tester.pumpWidget(MaterialApp(
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
        onChangeServer: () async {},
        api: LibraryApiClient(
          baseUrl: 'http://test.local',
          tokens: _tokens,
          httpClient: routingClient(),
        ),
      ),
    ));
    await tester.pumpAndSettle();

    expect(find.text('Ayşe Kaya (100)'), findsOneWidget);
    expect(find.text('Kütüphane'), findsOneWidget);
  });

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

  testWidgets('kitaba tıklanınca detay diyaloğu açılır', (tester) async {
    await tester.pumpWidget(_screen(
      books: [bookJson(baslik: 'Sefiller')],
      bookDetail: {
        'id': 1,
        'baslik': 'Sefiller',
        'yazar': {'ad_soyad': 'Victor Hugo'},
      },
    ));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Sefiller'));
    await tester.pumpAndSettle();

    expect(find.text('Yazar: Victor Hugo'), findsOneWidget);
  });

  testWidgets('detayda kitap resimleri gösterilir ve galeri açılır',
      (tester) async {
    await tester.pumpWidget(_screen(
      books: [bookJson(baslik: 'Kapakli Kitap')],
      bookDetail: {
        'id': 7,
        'baslik': 'Kapakli Kitap',
        'resim1': 'http://test.local/media/kitap_resimleri/1.jpg',
      },
    ));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Kapakli Kitap'));
    await tester.pumpAndSettle();

    expect(find.text('Resimler'), findsOneWidget);
    expect(find.byType(Image), findsOneWidget);

    await tester.tap(find.byType(Image));
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));

    expect(find.text('Resmi görüntüle'), findsOneWidget);
  });

  testWidgets('Şifre düğmesi diyaloğu açar ve şifre güncellenir (K9.8)',
      (tester) async {
    await tester.pumpWidget(_screen());
    await tester.pumpAndSettle();

    await tester.tap(find.text('Şifre'));
    await tester.pumpAndSettle();

    expect(find.text('Şifre değiştir'), findsOneWidget);

    await tester.enterText(
        find.widgetWithText(TextField, 'Mevcut şifre'), 'eskisi');
    await tester.enterText(
        find.widgetWithText(TextField, 'Yeni şifre'), 'yenisi');
    await tester.enterText(
        find.widgetWithText(TextField, 'Yeni şifre (tekrar)'), 'yenisi');
    await tester.tap(find.text('Kaydet'));
    await tester.pumpAndSettle();

    expect(find.text('Şifre güncellendi.'), findsOneWidget);
  });

  testWidgets('uyuşmayan yeni şifrelerde hata gösterilir', (tester) async {
    await tester.pumpWidget(_screen());
    await tester.pumpAndSettle();

    await tester.tap(find.text('Şifre'));
    await tester.pumpAndSettle();

    await tester.enterText(
        find.widgetWithText(TextField, 'Mevcut şifre'), 'eskisi');
    await tester.enterText(
        find.widgetWithText(TextField, 'Yeni şifre'), 'yenisi');
    await tester.enterText(
        find.widgetWithText(TextField, 'Yeni şifre (tekrar)'), 'farkli');
    await tester.tap(find.text('Kaydet'));
    await tester.pumpAndSettle();

    expect(find.text('Yeni şifreler uyuşmuyor.'), findsOneWidget);
  });
}
