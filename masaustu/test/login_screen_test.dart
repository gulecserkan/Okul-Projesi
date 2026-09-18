import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:masaustu/screens/login_screen.dart';

void main() {
  testWidgets('Login ekranı alanları ve butonu içerir', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: LoginScreen()));
    await tester.pump();

    expect(
      find.widgetWithText(TextField, 'Kullanıcı adı'),
      findsOneWidget,
    );
    expect(find.widgetWithText(TextField, 'Şifre'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Giriş Yap'), findsOneWidget);
  });
}