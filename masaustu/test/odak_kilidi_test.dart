import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:masaustu/widgets/odak_kilidi.dart';

/// R1.8 — barkod okutma odak kilidi. Okuyucu klavye emülasyonudur; tuşlar odaklı
/// widget'a gittiği için alanın odağını koruması gerekir.
void main() {
  Widget alan(FocusNode node, {bool enabled = true}) => MaterialApp(
        home: Scaffold(
          body: OdakKilitli(
            node: node,
            child: TextField(focusNode: node, autofocus: true, enabled: enabled),
          ),
        ),
      );

  testWidgets('odak bırakılınca (unfocus) alana geri verilir', (tester) async {
    final node = FocusNode();
    addTearDown(node.dispose);

    await tester.pumpWidget(alan(node));
    await tester.pumpAndSettle();
    expect(node.hasFocus, isTrue, reason: 'autofocus alanı odaklamalı');

    node.unfocus();
    await tester.pumpAndSettle();
    expect(node.hasFocus, isTrue, reason: 'odak kaybında geri verilmeli');
  });

  testWidgets('odak başka bir alana gidince geri verilir', (tester) async {
    final node = FocusNode();
    final diger = FocusNode();
    addTearDown(node.dispose);
    addTearDown(diger.dispose);

    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: Row(
          children: [
            Expanded(
              child: OdakKilitli(
                node: node,
                child: TextField(focusNode: node, autofocus: true),
              ),
            ),
            Expanded(child: TextField(focusNode: diger)),
          ],
        ),
      ),
    ));
    await tester.pumpAndSettle();
    expect(node.hasFocus, isTrue);

    diger.requestFocus();
    await tester.pumpAndSettle();
    expect(node.hasFocus, isTrue, reason: 'okutucu tuşları alana düşmeli');
  });

  testWidgets('diyalog açıkken odak geri verilmez (odak diyaloğun)', (tester) async {
    final node = FocusNode();
    final diger = FocusNode();
    addTearDown(node.dispose);
    addTearDown(diger.dispose);

    await tester.pumpWidget(alan(node));
    await tester.pumpAndSettle();
    expect(node.hasFocus, isTrue);

    final ctx = tester.element(find.byType(Scaffold));
    unawaited(showDialog<void>(
      context: ctx,
      builder: (_) => AlertDialog(
        content: TextField(focusNode: diger, autofocus: true),
      ),
    ));
    await tester.pumpAndSettle();
    expect(diger.hasFocus, isTrue, reason: 'diyalog kendi alanını odaklamalı');

    diger.unfocus();
    await tester.pumpAndSettle();
    expect(diger.hasFocus, isFalse, reason: 'arkadaki alan odayı çalmamalı');
  });

  testWidgets('kilitAcik false iken odak verilmez, açılınca geri verilir',
      (tester) async {
    final node = FocusNode();
    final diger = FocusNode();
    addTearDown(node.dispose);
    addTearDown(diger.dispose);
    var acik = false;

    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: Row(
          children: [
            Expanded(
              child: OdakKilitli(
                node: node,
                kilitAcik: () => acik,
                child: TextField(focusNode: node, autofocus: true),
              ),
            ),
            Expanded(child: TextField(focusNode: diger)),
          ],
        ),
      ),
    ));
    await tester.pumpAndSettle();

    diger.requestFocus();
    await tester.pumpAndSettle();
    expect(diger.hasFocus, isTrue, reason: 'kilit kapalıyken dokunulmamalı');

    acik = true;
    diger.unfocus();
    await tester.pumpAndSettle();
    expect(node.hasFocus, isTrue, reason: 'kilit açılınca geri verilmeli');
  });

  testWidgets('alan devre dışıyken (işlem sürüyor) odak verilmez', (tester) async {
    final node = FocusNode();
    addTearDown(node.dispose);

    // enabled=false ile kur: odaklanamaz, kilit de zorlamamalı.
    await tester.pumpWidget(alan(node, enabled: false));
    await tester.pumpAndSettle();

    expect(node.canRequestFocus, isFalse);
    expect(node.hasFocus, isFalse);
  });
}
