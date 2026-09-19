import 'package:flutter/material.dart';

/// DataTable yerine tam satır tıklama alanı sunan basit satır tablosu.
///
/// Her satır tek bir Listener+InkWell'dir; satırın herhangi bir yerine
/// tık/yeniden yükle hiçbir hücre sınırına takılmadan çalışır.
class RowTableColumn {
  final String label;
  final int flex;

  /// Sunucu tarafı sıralama anahtarı (null ise bu başlık sıralanamaz).
  final String? sortKey;

  const RowTableColumn(this.label, {this.flex = 1, this.sortKey});
}

class RowTableRow {
  final List<Widget> cells;
  final bool selected;
  final VoidCallback onSelected;

  /// Satıra tek tıklandığında çağrılır (global imleç konumu verilir).
  final void Function(Offset globalPosition)? onTap;

  /// (Opsiyonel) satırı açma; listede artık menüdeki "Detay" kullanılır.
  final VoidCallback? onOpen;

  /// Satırın konum ölçümü için GlobalKey (yüzen aksiyon çubuğu).
  final Key? rowKey;

  const RowTableRow({
    required this.cells,
    this.selected = false,
    required this.onSelected,
    this.onTap,
    this.onOpen,
    this.rowKey,
  });
}

class RowTable extends StatelessWidget {
  final List<RowTableColumn> columns;
  final List<RowTableRow> rows;
  final double? minWidth;
  final ScrollController? controller;

  /// ListView.builder yapılandırıldığında en alta eklenen satır (→ yükleme göstergesi).
  final Widget? footer;

  /// Aktif sıralama anahtarı ve yönü; `onSort` ile birlikte başlıklar tıklanır.
  final String? sortKey;
  final bool sortAscending;
  final ValueChanged<String>? onSort;

  const RowTable({
    super.key,
    required this.columns,
    required this.rows,
    this.minWidth,
    this.controller,
    this.footer,
    this.sortKey,
    this.sortAscending = true,
    this.onSort,
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
                          child: ListView.builder(
                            controller: controller,
                            itemCount: rows.length + (footer != null ? 1 : 0),
                            itemBuilder: (context, i) {
                              if (i < rows.length) return _row(context, rows[i]);
                              return footer ?? const SizedBox.shrink();
                            },
                          ),
                        ),
                      ],
                    )
                  : Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        _header(context),
                        for (final row in rows) _row(context, row),
                        ?footer,
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
              child: _headerCell(theme, col),
            ),
        ],
      ),
    );
  }

  Widget _headerCell(ThemeData theme, RowTableColumn col) {
    final style =
        theme.textTheme.labelLarge?.copyWith(fontWeight: FontWeight.bold);
    final sortable = onSort != null && col.sortKey != null;
    if (!sortable) {
      return Text(col.label, style: style);
    }
    final active = sortKey == col.sortKey;
    return InkWell(
      onTap: () => onSort!(col.sortKey!),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Flexible(
            child: Text(col.label,
                style: style, overflow: TextOverflow.ellipsis),
          ),
          const SizedBox(width: 4),
          Icon(
            active
                ? (sortAscending ? Icons.arrow_upward : Icons.arrow_downward)
                : Icons.unfold_more,
            size: 14,
            color: active
                ? theme.colorScheme.primary
                : theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.6),
          ),
        ],
      ),
    );
  }

  Widget _row(BuildContext context, RowTableRow row) {
    final theme = Theme.of(context);
    return GestureDetector(
      key: row.rowKey,
      behavior: HitTestBehavior.opaque,
      // Masaüstünde kaydırma tekerlekle yapıldığından basıldığı anda tetikle
      // (çift-tık/zaman aşımı gecikmesi olmadan anında menü).
      onTapDown: (d) {
        row.onSelected();
        row.onTap?.call(d.globalPosition);
      },
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
    );
  }
}