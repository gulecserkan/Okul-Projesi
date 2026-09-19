import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:masaustu/screens/student_list_screen.dart';

void main() {
  testWidgets('Üye listesinde Yeni Üye butonu formu açıyor',
      (tester) async {
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(body: StudentListScreen()),
    ));
    await tester.pumpAndSettle();

    expect(find.text('Yeni Üye'), findsOneWidget);

    await tester.tap(find.text('Yeni Üye'));
    await tester.pumpAndSettle();

    expect(find.text('Ad'), findsWidgets);
    expect(find.text('Soyad'), findsWidgets);
    expect(find.text('Üye No'), findsWidgets);
    expect(find.text('Kaydet'), findsOneWidget);
  });
}