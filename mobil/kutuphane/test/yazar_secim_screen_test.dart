import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:kutuphane/models/book.dart';
import 'package:kutuphane/screens/yazar_secim_screen.dart';

void main() {
  testWidgets('alfabetik gruplar ve aramayla süzer', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: YazarSecimScreen(
          yukleyici: () async => const [
            Author(id: 1, adSoyad: 'Zeynep Ak'),
            Author(id: 2, adSoyad: 'Ali Veli'),
            Author(id: 3, adSoyad: 'Çetin Su'),
          ],
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Ali Veli'), findsOneWidget);
    expect(find.text('Zeynep Ak'), findsOneWidget);
    expect(find.text('Çetin Su'), findsOneWidget);

    await tester.enterText(find.byType(TextField), 'ali');
    await tester.pumpAndSettle();
    expect(find.text('Ali Veli'), findsOneWidget);
    expect(find.text('Zeynep Ak'), findsNothing);
    expect(find.text('Çetin Su'), findsNothing);
  });

  testWidgets('A–Z şeridi ilgili harfe atlar; başlıklar yığılmaz (K9.9)', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(360, 720);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    const harfler = 'ABCDEFGHIJKLMNOPRSTUVYZ';
    final yazarlar = <Author>[];
    var id = 0;
    for (final h in harfler.split('')) {
      for (var i = 0; i < 6; i++) {
        yazarlar.add(Author(id: ++id, adSoyad: '${h * 3} Yazar $i'));
      }
    }

    await tester.pumpWidget(
      MaterialApp(
        home: YazarSecimScreen(yukleyici: () async => yazarlar),
      ),
    );
    await tester.pumpAndSettle();

    // Şeritteki "M"ye dokun (M bölümü başlangıçta ekranda değil).
    await tester.tap(find.text('M').last);
    await tester.pumpAndSettle();

    // M bölümü ve ilk yazarı görünür olmalı.
    expect(find.text('MMM Yazar 0'), findsOneWidget);
    final rect = tester.getRect(find.text('MMM Yazar 0'));
    expect(rect.top, greaterThan(0));
    expect(rect.top, lessThan(720));

    // Geriye kalan harf başlıkları listeye yığılmamalı; "A" yalnızca şeritte kalır.
    expect(find.text('A'), findsOneWidget);
    expect(find.text('B'), findsOneWidget);
  });
}
