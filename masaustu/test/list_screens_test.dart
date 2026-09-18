import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:masaustu/screens/student_list_screen.dart';
import 'package:masaustu/screens/book_list_screen.dart';

void main() {
  testWidgets('Öğrenci ekranı arama kutusu ve boş durum içerir', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: Scaffold(body: StudentListScreen())));
    await tester.pumpAndSettle();

    expect(find.widgetWithText(TextField, ''), findsOneWidget);
    expect(find.textContaining('öğrenci'), findsWidgets);
  });

  testWidgets('Kitap ekranı arama kutusu ve boş durum içerir', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: Scaffold(body: BookListScreen())));
    await tester.pumpAndSettle();

    expect(find.byType(TextField), findsOneWidget);
    expect(find.textContaining('kitap'), findsWidgets);
  });
}