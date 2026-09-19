import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:masaustu/screens/loan_screen.dart';

void main() {
  testWidgets('Ödünç/İade ekranı arama kutusu ve boş durum içerir', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: Scaffold(body: LoanScreen())));
    await tester.pumpAndSettle();

    expect(find.byType(TextField), findsOneWidget);
    expect(find.textContaining('Tarayıcı okutun'), findsOneWidget);
  });

  testWidgets('Sorgu girilince sonuçsuz durum gösterilir', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: Scaffold(body: LoanScreen())));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), 'YOK');
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pumpAndSettle();

    expect(find.textContaining('Sonuç bulunamadı'), findsOneWidget);
  });
}