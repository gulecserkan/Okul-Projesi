import 'package:flutter/material.dart';

import 'radial_menu.dart' show RadialMenuItem;

/// İmlecin hemen altında beliren **yatay** (pill) menü için bir `OverlayEntry`
/// oluşturur.
///
/// **Modal değildir:** altındaki satırlar tıklamayı alabilir; böylece menü
/// açıkken başka bir satıra tıklanınca eski menü kapanır, satır seçilir ve
/// yeni menü açılır. Kapatma ve seçim yönetimi çağıran tarafa aittir.
OverlayEntry buildHorizontalRowMenu({
  required BuildContext context,
  required Offset globalPosition,
  required List<RadialMenuItem> items,
  required void Function(String value) onSelect,
}) {
  const itemW = 94.0;
  const height = 56.0;
  final totalW = itemW * items.length;
  // Konumu overlay builder içinde değil, burada hesapla (MediaQuery bağımlılığı
  // overlay entry içinde kalmasın).
  final size = MediaQuery.of(context).size;
  var left = globalPosition.dx - 12;
  if (left + totalW > size.width - 8) left = size.width - totalW - 8;
  if (left < 8) left = 8;

  var top = globalPosition.dy + 10;
  if (top + height > size.height - 8) {
    top = globalPosition.dy - height - 10;
  }
  if (top < 8) top = 8;

  return OverlayEntry(
    builder: (_) => Positioned(
      left: left,
      top: top,
      width: totalW,
      height: height,
      child: _HorizontalMenu(items: items, onSelect: onSelect),
    ),
  );
}

class _HorizontalMenu extends StatelessWidget {
  final List<RadialMenuItem> items;
  final void Function(String value) onSelect;

  const _HorizontalMenu({required this.items, required this.onSelect});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Material(
      elevation: 6,
      borderRadius: BorderRadius.circular(18),
      color: scheme.surfaceContainerHigh,
      clipBehavior: Clip.antiAlias,
      child: Row(
        children: [
          for (var i = 0; i < items.length; i++) ...[
            if (i > 0)
              VerticalDivider(
                width: 1,
                thickness: 1,
                color: scheme.outlineVariant,
              ),
            Expanded(child: _item(context, scheme, items[i])),
          ],
        ],
      ),
    );
  }

  Widget _item(BuildContext context, ColorScheme scheme, RadialMenuItem item) {
    return InkWell(
      onTap: () => onSelect(item.value),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(item.icon, size: 18, color: scheme.primary),
          const SizedBox(height: 3),
          Text(
            item.label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(fontSize: 11, color: scheme.onSurface),
          ),
        ],
      ),
    );
  }
}
