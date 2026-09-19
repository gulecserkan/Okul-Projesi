import 'package:flutter/material.dart';

/// Seçili satırın sağında yüzen küçük aksiyon çubuğu (havuz/görünüm referanslı).
///
/// `top`, çağıran tarafça (satır + kullanıcı listesi GlobalKey ölçümüyle)
/// hesap edilerek verilir; böylece çubuk satırla birlikte hareket eder.
class FloatingRowActions extends StatelessWidget {
  /// Çubuğun üst kenarının tabloya göre dikey konumu (px).
  final double top;

  final List<Widget> actions;

  const FloatingRowActions({super.key, required this.top, required this.actions});

  @override
  Widget build(BuildContext context) {
    return Positioned(
      right: 8,
      top: top,
      child: Card(
        elevation: 4,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
        color: Theme.of(context).colorScheme.secondaryContainer,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 4),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: actions,
          ),
        ),
      ),
    );
  }
}

/// Seçili satırın gerçek konumunu ölçüp çubuğu oraya hizalayan sarmalayıcı.
///
/// Yükseklik tahminine dayanmaz; satırın `GlobalKey`'i ile tablonun
/// (Stack) `GlobalKey`'i arasındaki farkı her karede ölçer. Böylece alt
/// satırlara inildikçe sapma birikmez — çubuk satırla birebir hizada kalır.
class AnchoredRowActions extends StatefulWidget {
  /// Çubuğun bağlanacağı Stack (liste gövdesi) anahtarı.
  final GlobalKey stackKey;

  /// Seçili satırın anahtarı.
  final GlobalKey rowKey;

  final List<Widget> actions;

  /// Görünür alan yüksekliği (çubuğu altta taşmaktan korur).
  final double viewportHeight;

  /// Satır tamamen ekran dışına kayarsa çağrılır (seçim iptali için).
  final VoidCallback? onOutOfView;

  /// Her kaydırma/veri değişiminde artırılarak yeniden ölçüm tetiklenir.
  final int tick;

  const AnchoredRowActions({
    super.key,
    required this.stackKey,
    required this.rowKey,
    required this.actions,
    required this.viewportHeight,
    this.onOutOfView,
    this.tick = 0,
  });

  @override
  State<AnchoredRowActions> createState() => _AnchoredRowActionsState();
}

class _AnchoredRowActionsState extends State<AnchoredRowActions> {
  static const _barHeight = 44.0;
  double _top = 0;

  @override
  void initState() {
    super.initState();
    _measure();
  }

  @override
  void didUpdateWidget(covariant AnchoredRowActions oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.rowKey != widget.rowKey || oldWidget.tick != widget.tick) {
      _measure();
    }
  }

  void _measure() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final rowCtx = widget.rowKey.currentContext;
      final stackCtx = widget.stackKey.currentContext;
      if (rowCtx == null || stackCtx == null) return;
      final rowBox = rowCtx.findRenderObject() as RenderBox?;
      final stackBox = stackCtx.findRenderObject() as RenderBox?;
      if (rowBox == null || stackBox == null) return;
      final rowTop = rowBox.localToGlobal(Offset.zero).dy;
      final stackTop = stackBox.localToGlobal(Offset.zero).dy;
      final relativeTop = rowTop - stackTop;
      final rowHeight = rowBox.size.height;
      // Satır görünür alanın tamamen dışında kaldığında seçimi iptal et.
      final outOfView =
          relativeTop + rowHeight <= 0 || relativeTop >= widget.viewportHeight;
      if (outOfView) {
        widget.onOutOfView?.call();
        return;
      }
      final alignTop = (rowHeight - _barHeight) / 2;
      final top = relativeTop + alignTop;
      final maxTop = widget.viewportHeight - _barHeight;
      setState(() => _top = top.clamp(0.0, maxTop < 0 ? 0.0 : maxTop));
    });
  }

  @override
  Widget build(BuildContext context) {
    return FloatingRowActions(top: _top, actions: widget.actions);
  }
}