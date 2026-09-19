import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:masaustu/widgets/row_table.dart';

void main() {
  testWidgets('RowTable: satırın boş alanına tek tık seçer, çift tık açar',
      (tester) async {
    var selected = 0;
    var opened = 0;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: RowTable(
            minWidth: 300,
            columns: const [
              RowTableColumn('A', flex: 1),
              RowTableColumn('B', flex: 3),
            ],
            rows: [
              RowTableRow(
                selected: false,
                onSelected: () => selected++,
                onOpen: () => opened++,
                cells: const [Text('Sol metin'), SizedBox.shrink()],
              ),
            ],
          ),
        ),
      ),
    );

    final rect = tester.getRect(find.byType(RowTable).first);
    final dy = tester.getCenter(find.text('Sol metin')).dy;

    // Satırın sağ (boş) tarafına tek tık → seleksiyon
    await tester.tapAt(Offset(rect.right - 40, dy));
    expect(selected, 1);
    expect(opened, 0);

    // Sağ tığın çift-tık zamanlayıcısını boşalt.
    await tester.pump(const Duration(milliseconds: 400));

    // Satırın sol (metin) tarafına çift tık → detay aç
    await tester.tapAt(Offset(rect.left + 40, dy));
    await tester.pump(const Duration(milliseconds: 60));
    await tester.tapAt(Offset(rect.left + 40, dy));
    await tester.pump(const Duration(milliseconds: 60));

    expect(selected, 3); // ilk tek + çift tığın iki kliği
    expect(opened, 1);

    // Çift tık tanıyıcının bekleme zamanlayıcısını boşalt.
    await tester.pump(const Duration(milliseconds: 400));
  });
}