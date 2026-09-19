import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:masaustu/widgets/row_table.dart';

void main() {
  testWidgets('RowTable: satıra tek tık seçer ve konumlu onTap çağırır',
      (tester) async {
    var selected = 0;
    Offset? tapPos;

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
                onTap: (pos) => tapPos = pos,
                cells: const [Text('Sol metin'), SizedBox.shrink()],
              ),
            ],
          ),
        ),
      ),
    );

    final rect = tester.getRect(find.byType(RowTable).first);
    final dy = tester.getCenter(find.text('Sol metin')).dy;

    // Satırın sağ (boş) tarafına tek tık → seçim + konumlu onTap
    await tester.tapAt(Offset(rect.right - 40, dy));
    await tester.pump();

    expect(selected, 1);
    expect(tapPos, isNotNull);
    expect(tapPos!.dy, closeTo(dy, 1));
  });
}
