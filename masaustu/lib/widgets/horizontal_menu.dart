import 'package:flutter/material.dart';

import 'radial_menu.dart' show RadialMenuItem;

/// Fare imlecinin hemen altında beliren **yatay** (pill) işlem menüsü.
///
/// Seçilen öğenin `value`'su döner; dışına tıklanırsa null.
Future<String?> showHorizontalRowMenu(
  BuildContext context,
  Offset globalPosition,
  List<RadialMenuItem> items,
) {
  if (items.isEmpty) return Future.value(null);
  const itemW = 94.0;
  const height = 56.0;
  final totalW = itemW * items.length;
  final size = MediaQuery.of(context).size;

  var left = globalPosition.dx - 12;
  if (left + totalW > size.width - 8) left = size.width - totalW - 8;
  if (left < 8) left = 8;

  var top = globalPosition.dy + 10;
  if (top + height > size.height - 8) top = globalPosition.dy - height - 10;
  if (top < 8) top = 8;

  return showGeneralDialog<String>(
    context: context,
    barrierDismissible: true,
    barrierLabel: 'İşlem menüsü',
    barrierColor: Colors.black.withValues(alpha: 0.05),
    transitionDuration: const Duration(milliseconds: 90),
    pageBuilder: (ctx, anim, sec) => Stack(
      children: [
        Positioned(
          left: left,
          top: top,
          width: totalW,
          height: height,
          child: _HorizontalMenu(items: items),
        ),
      ],
    ),
    transitionBuilder: (ctx, anim, sec, child) => FadeTransition(
      opacity: anim,
      child: ScaleTransition(
        alignment: Alignment.topLeft,
        scale: Tween<double>(begin: 0.9, end: 1.0).animate(anim),
        child: child,
      ),
    ),
  );
}

class _HorizontalMenu extends StatelessWidget {
  final List<RadialMenuItem> items;

  const _HorizontalMenu({required this.items});

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
      onTap: () => Navigator.of(context).pop(item.value),
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
