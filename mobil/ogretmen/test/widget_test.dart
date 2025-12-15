// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'package:flutter_test/flutter_test.dart';

import 'package:shared_preferences/shared_preferences.dart';

import 'package:ogretmen/main.dart';

void main() {
  testWidgets('Uygulama açılışı bağlantı ekranını gösterir', (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({});

    await tester.pumpWidget(const OgretmenApp());
    await tester.pumpAndSettle();

    expect(find.textContaining('Kütüphane sunucusuna bağlan'), findsOneWidget);
  });
}
