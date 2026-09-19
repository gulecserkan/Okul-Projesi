import 'package:flutter/material.dart';

/// DataTable yerine tam satır tıklama alanı sunan basit satır tablosu.
///
/// Her satır tek bir Listener+InkWell'dir; satırın herhangi bir yerine
/// tık/yeniden yükle hiçbir hücre sınırına takılmadan çalışır.
class RowTableColumn {
  final String label;
  final int flex;

  const RowTableColumn(this.label, {this.flex = 1});
}

class RowTableRow {
  final List<Widget> cells;
  final bool selected;
  final VoidCallback onSelected;
  final VoidCallback onOpen;

  const RowTableRow({
    required this.cells,
    this.selected = false,
    required this.onSelected,
    required this.onOpen,
  });
}

class RowTable extends StatelessWidget {
  final List<RowTableColumn> columns;
  final List<RowTableRow> rows;
  final double? minWidth;

  const RowTable({
    super.key,
    required this.columns,
    required this.rows,
    this.minWidth,
  });

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final available = constraints.maxWidth.isFinite
            ? constraints.maxWidth
            : (minWidth ?? 960);
        final tableWidth = (minWidth ?? 960) > available
            ? (minWidth ?? 960)
            : available;
        final boundedHeight = constraints.maxHeight.isFinite;
        return SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: SizedBox(
            width: tableWidth,
            child: Card(
              clipBehavior: Clip.antiAlias,
              margin: EdgeInsets.zero,
              child: boundedHeight
                  ? Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        _header(context),
                        Expanded(
                          child: SingleChildScrollView(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                for (final row in rows) _row(context, row),
                              ],
                            ),
                          ),
                        ),
                      ],
                    )
                  : Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        _header(context),
                        for (final row in rows) _row(context, row),
                      ],
                    ),
            ),
          ),
        );
      },
    );
  }

  Widget _header(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      color: theme.colorScheme.surfaceContainerHighest,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          for (final col in columns)
            Expanded(
              flex: col.flex,
              child: Text(
                col.label,
                style: theme.textTheme.labelLarge
                    ?.copyWith(fontWeight: FontWeight.bold),
              ),
            ),
        ],
      ),
    );
  }

  Widget _row(BuildContext context, RowTableRow row) {
    final theme = Theme.of(context);
    return Listener(
      onPointerDown: (_) => row.onSelected(),
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onDoubleTap: row.onOpen,
        child: Material(
          color: row.selected ? theme.colorScheme.primaryContainer : Colors.transparent,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            decoration: const BoxDecoration(
              border: Border(
                bottom: BorderSide(color: Color(0xFFE4E4E7), width: 0.5),
              ),
            ),
            child: Row(
              children: [
                for (var i = 0; i < columns.length; i++)
                  Expanded(
                    flex: columns[i].flex,
                    child: Align(
                      alignment: Alignment.centerLeft,
                      child: row.cells[i],
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}