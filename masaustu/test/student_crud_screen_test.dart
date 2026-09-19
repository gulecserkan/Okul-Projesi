import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:masaustu/screens/student_list_screen.dart';

void main() {
  testWidgets('Öğrenci listesinde Yeni Öğrenci butonu formu açıyor',
      (tester) async {
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(body: StudentListScreen()),
    ));
    await tester.pumpAndSettle();

    expect(find.text('Yeni Öğrenci'), findsOneWidget);

    await tester.tap(find.text('Yeni Öğrenci'));
    await tester.pumpAndSettle();

    expect(find.text('Ad'), findsWidgets);
    expect(find.text('Soyad'), findsWidgets);
    expect(find.text('Öğrenci No'), findsWidgets);
    expect(find.text('Kaydet'), findsOneWidget);
  });
}