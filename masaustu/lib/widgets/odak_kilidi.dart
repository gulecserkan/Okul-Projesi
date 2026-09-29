import 'package:flutter/material.dart';

/// R1.8 — Barkod okutma odak kilidi.
///
/// Barkod okuyucular klavye emülasyonudur: kodu harf harf + Enter yazarlar ve
/// Flutter tuşları **odaklı widget'a** verir. Kullanıcı bir karta/satıra/butona
/// tıklayınca veya pencere odağını kaybedince alanın odağı gider ve sonraki
/// okutmalar sessizce kaybolur. Bu widget, [node] odaklı alan görünürken odağı
/// **post-frame'da geri verir** (görsel uyarı yok, sessiz).
///
/// Geri verilmez: diyalog/kilit ekranı açıkken ([ModalRoute.isCurrent] değilse —
/// üye no penceresi, iade/ceza diyaloğu, açılan detay ekranı odak kendisindendir),
/// alan `enabled: false` iken (`canRequestFocus` false), [kilitAcik] false dönerse
/// (ekran menüsü açıkken) ve alan zaten odaktayken.
///
/// Kapsam (bkz. `docs/IS_KURALLARI.md` R1.8): Genel Bakış hızlı işlem, Ödünç/İade
/// arama, Kitaplar arama. Üyeler listesi araması, Katalog ve Ayarlar **kilitlenmez**.
class OdakKilitli extends StatefulWidget {
  /// Odağın korunacağı alanın düğümü (alan `enabled: false` olunca kilit kendiliğinden durur).
  final FocusNode node;

  /// Alanın çevresi (genelde `TextField`). Kilit, alanı devre dışı bırakmaz.
  final Widget child;

  /// Kilit kapısı (isteğe bağlı). false dönerse odak geri verilmez — ör. ekran
  /// menüsü/overlay açıkken. Her odak değişiminde yeniden değerlendirilir.
  final bool Function()? kilitAcik;

  const OdakKilitli({
    super.key,
    required this.node,
    required this.child,
    this.kilitAcik,
  });

  @override
  State<OdakKilitli> createState() => _OdakKilitliState();
}

class _OdakKilitliState extends State<OdakKilitli> with WidgetsBindingObserver {
  @override
  void initState() {
    super.initState();
    FocusManager.instance.addListener(_odakDenetle);
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    FocusManager.instance.removeListener(_odakDenetle);
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  /// R1.8: uygulama arka plandan `resumed` olduğunda (okutucu kullanılmadan önce
  /// alt-tab'dan dönüldüğünde) odak alana geri verilir.
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) _odakGeriVer();
  }

  void _odakDenetle() {
    if (!mounted) return;
    if (widget.kilitAcik != null && !widget.kilitAcik!()) return;
    // Diyalog/kilit ekranı ya da üstte açılan bir route varsa odak onundur.
    final route = ModalRoute.of(context);
    if (route != null && !route.isCurrent) return;
    if (!widget.node.canRequestFocus) return;
    if (FocusManager.instance.primaryFocus == widget.node) return;
    _odakGeriVer();
  }

  void _odakGeriVer() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      if (!widget.node.canRequestFocus) return;
      if (FocusManager.instance.primaryFocus == widget.node) return;
      widget.node.requestFocus();
    });
  }

  @override
  Widget build(BuildContext context) => widget.child;
}
