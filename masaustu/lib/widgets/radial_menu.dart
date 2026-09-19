import 'dart:math' as math;

import 'package:flutter/material.dart';

/// Radyal (yuvarlak, dilimli) satır menüsü öğesi.
class RadialMenuItem {
  final IconData icon;
  final String label;
  final String value;

  const RadialMenuItem({
    required this.icon,
    required this.label,
    required this.value,
  });
}

/// Tıklanan noktanın yanında yuvarlak, dilimli bir işlem menüsü gösterir.
///
/// Seçilen öğenin `value`'su döner; dışına/merkezine tıklanırsa null.
Future<String?> showRadialRowMenu(
  BuildContext context,
  Offset globalPosition,
  List<RadialMenuItem> items,
) {
  const radius = 78.0;
  final size = MediaQuery.of(context).size;
  final left = globalPosition.dx.clamp(radius, size.width - radius);
  final top = globalPosition.dy.clamp(radius, size.height - radius);

  return showGeneralDialog<String>(
    context: context,
    barrierDismissible: true,
    barrierLabel: 'İşlem menüsü',
    barrierColor: Colors.black.withValues(alpha: 0.06),
    transitionDuration: const Duration(milliseconds: 90),
    pageBuilder: (ctx, anim, sec) => Stack(
      children: [
        Positioned(
          left: left - radius,
          top: top - radius,
          width: radius * 2,
          height: radius * 2,
          child: _PieMenu(items: items, radius: radius),
        ),
      ],
    ),
    transitionBuilder: (ctx, anim, sec, child) => FadeTransition(
      opacity: anim,
      child: ScaleTransition(
        scale: Tween<double>(begin: 0.85, end: 1.0).animate(anim),
        child: child,
      ),
    ),
  );
}

class _PieMenu extends StatelessWidget {
  final List<RadialMenuItem> items;
  final double radius;

  const _PieMenu({required this.items, required this.radius});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final fills = <Color>[
      scheme.primaryContainer,
      scheme.secondaryContainer,
      scheme.tertiaryContainer,
    ];
    final foregrounds = <Color>[
      scheme.onPrimaryContainer,
      scheme.onSecondaryContainer,
      scheme.onTertiaryContainer,
    ];
    final size = radius * 2;
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTapUp: (d) {
        final v = d.localPosition - Offset(size / 2, size / 2);
        if (v.distance < 22) {
          Navigator.of(context).pop(); // merkez: kapat
          return;
        }
        final deg = math.atan2(v.dy, v.dx) * 180 / math.pi;
        final idx = (((deg + 150) % 360) / (360 / items.length)).floor() %
            items.length;
        Navigator.of(context).pop(items[idx].value);
      },
      child: CustomPaint(
        size: Size(size, size),
        painter: _PiePainter(
          items: items,
          fills: fills,
          foregrounds: foregrounds,
          surface: scheme.surface,
          onSurfaceVariant: scheme.onSurfaceVariant,
        ),
      ),
    );
  }
}

class _PiePainter extends CustomPainter {
  final List<RadialMenuItem> items;
  final List<Color> fills;
  final List<Color> foregrounds;
  final Color surface;
  final Color onSurfaceVariant;

  _PiePainter({
    required this.items,
    required this.fills,
    required this.foregrounds,
    required this.surface,
    required this.onSurfaceVariant,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2;
    final rect = Rect.fromCircle(center: center, radius: radius - 1);
    final n = items.length;
    final sweep = 360 / n;
    const gapDeg = 3.0;

    // Gölge
    canvas.drawCircle(
      center,
      radius - 1,
      Paint()
        ..color = Colors.black.withValues(alpha: 0.12)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 5),
    );

    for (var i = 0; i < n; i++) {
      final startDeg = -150 + i * sweep + gapDeg / 2;
      final paint = Paint()
        ..color = fills[i % fills.length]
        ..style = PaintingStyle.fill;
      canvas.drawArc(
        rect,
        startDeg * math.pi / 180,
        (sweep - gapDeg) * math.pi / 180,
        true,
        paint,
      );
    }

    // Merkez daire (kapat)
    canvas.drawCircle(center, 22, Paint()..color = surface);
    _drawIcon(
      canvas,
      center,
      Icons.close,
      16,
      onSurfaceVariant,
    );

    // İkon + etiket
    for (var i = 0; i < n; i++) {
      final midDeg = -150 + i * sweep + sweep / 2;
      final midRad = midDeg * math.pi / 180;
      final pos = center +
          Offset(math.cos(midRad), math.sin(midRad)) * (radius * 0.64);
      _drawItem(canvas, pos, items[i], foregrounds[i % foregrounds.length]);
    }
  }

  void _drawItem(Canvas canvas, Offset center, RadialMenuItem item, Color color) {
    final iconTp = TextPainter(
      text: TextSpan(
        text: String.fromCharCode(item.icon.codePoint),
        style: TextStyle(
          fontSize: 18,
          fontFamily: item.icon.fontFamily,
          package: item.icon.fontPackage,
          color: color,
        ),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    final labelTp = TextPainter(
      text: TextSpan(
        text: item.label,
        style: TextStyle(
            fontSize: 11, fontWeight: FontWeight.w600, color: color),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    final totalH = iconTp.height + 2 + labelTp.height;
    iconTp.paint(
        canvas, Offset(center.dx - iconTp.width / 2, center.dy - totalH / 2));
    labelTp.paint(
      canvas,
      Offset(center.dx - labelTp.width / 2,
          center.dy - totalH / 2 + iconTp.height + 2),
    );
  }

  void _drawIcon(
      Canvas canvas, Offset center, IconData icon, double size, Color color) {
    final tp = TextPainter(
      text: TextSpan(
        text: String.fromCharCode(icon.codePoint),
        style: TextStyle(
          fontSize: size,
          fontFamily: icon.fontFamily,
          package: icon.fontPackage,
          color: color,
        ),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    tp.paint(canvas, Offset(center.dx - tp.width / 2, center.dy - tp.height / 2));
  }

  @override
  bool shouldRepaint(covariant _PiePainter old) =>
      old.items != items ||
      old.fills != fills ||
      old.foregrounds != foregrounds ||
      old.surface != surface;
}
