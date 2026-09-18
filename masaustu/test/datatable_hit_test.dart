import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// DataTable hücresinde minWidth infinity + dolgu (liste satır hücreleri)
/// layout'i kablo/yasidersız sarar mı diye doğrular.
void main() {
  testWidgets('DataTable satır hücresi tam hücre genişliği kaplar', (tester) async {
    var taps = 0;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: DataTable(
            columns: const [DataColumn(label: Text('A')), DataColumn(label: Text('B'))],
            rows: [
              DataRow(
                cells: [
                  DataCell(Listener(
                    onPointerDown: (_) => taps++,
                    child: GestureDetector(
                      behavior: HitTestBehavior.opaque,
                      onDoubleTap: () {},
                      child: Container(
                        constraints: const BoxConstraints(minWidth: double.infinity),
                        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 4),
                        alignment: Alignment.centerLeft,
                        child: const Text('Metin'),
                      ),
                    ),
                  )),
                  const DataCell(Text('ikinci sütun')),
                ],
              ),
            ],
          ),
        ),
      ),
    );

    await tester.tap(find.text('ikinci sütun'));
    expect(taps, 0);
    await tester.tap(find.text('Metin'));
    expect(taps, 1);

    // Çift tık tanıyıcının bekleme zamanlayıcısını boşalt.
    await tester.pump(const Duration(milliseconds: 400));
  });
}