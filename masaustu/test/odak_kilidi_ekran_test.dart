import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:masaustu/config.dart';
import 'package:masaustu/screens/home_screen.dart';
import 'package:masaustu/screens/loan_screen.dart';
import 'package:masaustu/screens/book_list_screen.dart';
import 'package:masaustu/widgets/odak_kilidi.dart';

/// R1.8 — sürekli okutma yapılan alanlar odak kilidiyle sarılır: Genel Bakış hızlı
/// işlem, Ödünç/İade arama, Kitaplar arama. (Üyeler listesi kilitlenmez.)
void main() {
  Finder alan(String ipucu) => find.byWidgetPredicate(
        (w) => w is TextField && w.decoration?.hintText == ipucu,
        description: 'TextField($ipucu)',
      );

  Future<void> odakKaybolsunVeGelsin(WidgetTester tester, Finder f) async {
    final node = tester.widget<TextField>(f).focusNode!;
    await tester.pumpAndSettle();
    expect(node.hasFocus, isTrue, reason: 'ilk kurulumda odakta olmalı');

    node.unfocus(); // kullanıcı bir karta/satıra tıkladı
    await tester.pumpAndSettle();
    expect(node.hasFocus, isTrue, reason: 'odak kaçınca geri verilmeli');
  }

  testWidgets('Genel Bakış hızlı işlem alanı odakta kalır', (tester) async {
    await tester.pumpWidget(MaterialApp(
      home: HomeScreen(
        session: const Session(
          accessToken: 't',
          refreshToken: 'r',
          username: 'kullanici',
          fullName: 'Test Kullanıcı',
          role: 'personel',
        ),
      ),
    ));
    final f = alan('Barkod veya üye no okutun...');
    expect(f, findsOneWidget);
    expect(
      find.ancestor(of: f, matching: find.byType(OdakKilitli)),
      findsOneWidget,
      reason: 'alan odak kilidiyle sarılmalı (R1.8)',
    );
    await odakKaybolsunVeGelsin(tester, f);
  });

  testWidgets('Ödünç/İade arama alanı odakta kalır', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: Scaffold(body: LoanScreen())));
    final f = alan('Barkod, üye no, ISBN veya kitap adı...');
    expect(f, findsOneWidget);
    expect(find.ancestor(of: f, matching: find.byType(OdakKilitli)), findsOneWidget);
    await odakKaybolsunVeGelsin(tester, f);
  });

  testWidgets('Kitaplar arama alanı odakta kalır', (tester) async {
    await tester.pumpWidget(
        const MaterialApp(home: Scaffold(body: BookListScreen())));
    final f = alan('Başlık, ISBN, yazar, kategori veya raf ara...');
    expect(f, findsOneWidget);
    expect(find.ancestor(of: f, matching: find.byType(OdakKilitli)), findsOneWidget);
    await odakKaybolsunVeGelsin(tester, f);
  });
}
