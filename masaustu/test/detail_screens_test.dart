import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:masaustu/models.dart';
import 'package:masaustu/screens/student_detail_screen.dart';
import 'package:masaustu/screens/book_detail_screen.dart';

void main() {
  final uye = Uye(
    id: 1,
    ad: 'Arpağ',
    soyad: 'Seven',
    uyeNo: '5A01',
    sinif: const Sinif(id: 1, ad: '5-A'),
    telefon: '+90 555 111 22 33',
    eposta: 'a@b.c',
    aktif: true,
  );

  testWidgets('Üye detay ekranı başlık bilgilerini gösterir', (tester) async {
    await tester.pumpWidget(
      MaterialApp(home: StudentDetailScreen(uye: uye)),
    );
    await tester.pump();

    expect(find.text('Arpağ Seven'), findsWidgets);
    expect(find.text('5A01'), findsOneWidget);
    expect(find.text('5-A'), findsOneWidget);
    expect(find.text('Ödünç Geçmişi'), findsOneWidget);
  });

  final kitap = Kitap(
    id: 2,
    baslik: 'Masumiyet Müzesi',
    yayinYili: 1991,
    isbn: '978-1-5061-5009-3',
    yazar: const Yazar(id: 12, adSoyad: 'Halil İnalcık'),
    kategori: const Kategori(id: 1, ad: 'Roman'),
    nushaSayisi: 4,
    rafKodlari: const ['R27', 'R7'],
  );

  testWidgets('Kitap detay ekranı başlık bilgilerini gösterir', (tester) async {
    await tester.pumpWidget(
      MaterialApp(home: BookDetailScreen(kitap: kitap)),
    );
    await tester.pump();

    expect(find.text('Masumiyet Müzesi'), findsWidgets);
    expect(find.text('Halil İnalcık'), findsOneWidget);
    expect(find.text('Nüshalar'), findsOneWidget);
  });
}