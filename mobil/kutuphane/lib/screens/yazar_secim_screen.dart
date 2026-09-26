import 'package:flutter/material.dart';

import '../models/book.dart';

/// Yazar seçim sonucu. [yazar] `null` ise "Tümü" (filtreyi kaldır).
class YazarSecim {
  const YazarSecim(this.yazar);

  final Author? yazar;
}

/// Uzun yazar listeleri için tam ekran seçim ekranı.
///
/// Yazarlar Türkçe alfabetik olarak gruplanır; her grubun sabit (yapışkan)
/// bir harf başlığı olur ve sağ kenardaki A–Z şeridiyle ilgili harfe atlanır.
class YazarSecimScreen extends StatefulWidget {
  const YazarSecimScreen({
    super.key,
    required this.yukleyici,
    this.seciliId,
  });

  /// Yazarları getirir (çağıran taraf önbelleği yönetir).
  final Future<List<Author>> Function() yukleyici;
  final int? seciliId;

  @override
  State<YazarSecimScreen> createState() => _YazarSecimScreenState();
}

class _YazarSecimScreenState extends State<YazarSecimScreen> {
  static const List<String> _harfSirasi = [
    'A', 'B', 'C', 'Ç', 'D', 'E', 'F', 'G', 'Ğ', 'H', 'I', 'İ', 'J', 'K',
    'L', 'M', 'N', 'O', 'Ö', 'P', 'R', 'S', 'Ş', 'T', 'U', 'Ü', 'V', 'Y', 'Z',
    '#',
  ];
  static const double _baslikYuksekligi = 36;
  static const double _satirYuksekligi = 48;

  final ScrollController _scrollController = ScrollController();
  final TextEditingController _aramaController = TextEditingController();

  final Map<String, double> _offsetler = {};

  bool _yukleniyor = true;
  bool _hata = false;
  List<Author> _yazarlar = [];
  String _arama = '';

  @override
  void initState() {
    super.initState();
    _yukle();
  }

  @override
  void dispose() {
    _scrollController.dispose();
    _aramaController.dispose();
    super.dispose();
  }

  Future<void> _yukle() async {
    setState(() {
      _yukleniyor = true;
      _hata = false;
    });
    try {
      final list = await widget.yukleyici();
      if (!mounted) return;
      setState(() {
        _yazarlar = list;
        _yukleniyor = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _hata = true;
        _yukleniyor = false;
      });
    }
  }

  /// Türkçe harfleri sadeleştirip küçük harfe çevirir (arama/sıralama için).
  static String _anahtar(String s) {
    final b = StringBuffer();
    for (final r in s.trim().runes) {
      final c = String.fromCharCode(r);
      switch (c) {
        case 'ç':
        case 'Ç':
          b.write('c');
          break;
        case 'ğ':
        case 'Ğ':
          b.write('g');
          break;
        case 'ı':
        case 'I':
          b.write('i');
          break;
        case 'İ':
        case 'i':
          b.write('i');
          break;
        case 'ö':
        case 'Ö':
          b.write('o');
          break;
        case 'ş':
        case 'Ş':
          b.write('s');
          break;
        case 'ü':
        case 'Ü':
          b.write('u');
          break;
        default:
          b.write(c.toLowerCase());
      }
    }
    return b.toString();
  }

  /// Türkçe büyük harf başlangıcı; harf değilse `#`.
  static String _ilkHarf(String s) {
    final t = s.trim();
    if (t.isEmpty) return '#';
    final c = t[0];
    final String buyuk;
    if (c == 'i') {
      buyuk = 'İ';
    } else if (c == 'ı') {
      buyuk = 'I';
    } else {
      buyuk = c.toUpperCase();
    }
    return _harfSirasi.contains(buyuk) ? buyuk : '#';
  }

  /// Aramaya göre süzer, harfe göre gruplar; grup içi alfabetik sıralar.
  Map<String, List<Author>> _gruplar() {
    final q = _anahtar(_arama);
    final map = <String, List<Author>>{};
    for (final a in _yazarlar) {
      if (q.isNotEmpty && !_anahtar(a.adSoyad).contains(q)) continue;
      map.putIfAbsent(_ilkHarf(a.adSoyad), () => []).add(a);
    }
    for (final list in map.values) {
      list.sort((x, y) => _anahtar(x.adSoyad).compareTo(_anahtar(y.adSoyad)));
    }
    return {
      for (final h in _harfSirasi)
        if (map.containsKey(h)) h: map[h]!,
    };
  }

  void _offsetleriHesapla(List<String> harfler, Map<String, List<Author>> gruplar) {
    _offsetler.clear();
    var acc = 0.0;
    for (final h in harfler) {
      _offsetler[h] = acc;
      acc += _baslikYuksekligi + _satirYuksekligi * gruplar[h]!.length;
    }
  }

  void _harfeAtla(String harf) {
    final off = _offsetler[harf];
    if (off == null || !_scrollController.hasClients) return;
    final max = _scrollController.position.maxScrollExtent;
    _scrollController.animateTo(
      off.clamp(0.0, max),
      duration: const Duration(milliseconds: 220),
      curve: Curves.easeOut,
    );
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final gruplar = _gruplar();
    final harfler = gruplar.keys.toList();
    _offsetleriHesapla(harfler, gruplar);
    final aramaVar = _arama.trim().isNotEmpty;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Yazar seç'),
        actions: [
          if (widget.seciliId != null)
            TextButton(
              onPressed: () =>
                  Navigator.of(context).pop(const YazarSecim(null)),
              child: const Text('Tümü'),
            ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(58),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 10),
            child: TextField(
              controller: _aramaController,
              onChanged: (v) => setState(() => _arama = v),
              textInputAction: TextInputAction.search,
              decoration: InputDecoration(
                hintText: 'Yazar ara...',
                prefixIcon: const Icon(Icons.search),
                isDense: true,
                filled: true,
                fillColor: scheme.surfaceContainerHighest,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: BorderSide.none,
                ),
              ),
            ),
          ),
        ),
      ),
      body: _govde(scheme, gruplar, harfler, aramaVar),
    );
  }

  Widget _govde(
    ColorScheme scheme,
    Map<String, List<Author>> gruplar,
    List<String> harfler,
    bool aramaVar,
  ) {
    if (_yukleniyor) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_hata) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Yazarlar yüklenemedi.'),
            const SizedBox(height: 12),
            FilledButton(onPressed: _yukle, child: const Text('Tekrar dene')),
          ],
        ),
      );
    }
    if (gruplar.isEmpty) {
      return Center(
        child: Text(aramaVar ? 'Eşleşen yazar yok.' : 'Yazar bulunamadı.'),
      );
    }

    return Stack(
      children: [
        CustomScrollView(
          controller: _scrollController,
          slivers: [
            for (final h in harfler) ...[
              SliverPersistentHeader(
                pinned: true,
                delegate: _HarfBasligi(h, scheme),
              ),
              SliverList(
                delegate: SliverChildBuilderDelegate(
                  (context, i) {
                    final a = gruplar[h]![i];
                    final secili = a.id == widget.seciliId;
                    return SizedBox(
                      height: _satirYuksekligi,
                      child: ListTile(
                        dense: true,
                        title: Text(a.adSoyad),
                        selected: secili,
                        trailing: secili
                            ? Icon(Icons.check, color: scheme.primary)
                            : null,
                        onTap: () =>
                            Navigator.of(context).pop(YazarSecim(a)),
                      ),
                    );
                  },
                  childCount: gruplar[h]!.length,
                ),
              ),
            ],
          ],
        ),
        if (!aramaVar && harfler.length > 1)
          Positioned(
            top: 0,
            bottom: 0,
            right: 0,
            child: _HarfSerit(harfler: harfler, onSec: _harfeAtla),
          ),
      ],
    );
  }
}

/// Yapışkan harf başlığı.
class _HarfBasligi extends SliverPersistentHeaderDelegate {
  _HarfBasligi(this.harf, this.scheme);

  final String harf;
  final ColorScheme scheme;

  @override
  double get minExtent => _YazarSecimScreenState._baslikYuksekligi;

  @override
  double get maxExtent => _YazarSecimScreenState._baslikYuksekligi;

  @override
  Widget build(BuildContext context, double shrinkOffset, bool overlapsContent) {
    return Container(
      height: _YazarSecimScreenState._baslikYuksekligi,
      alignment: Alignment.centerLeft,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      color: scheme.surfaceContainerHighest,
      child: Text(
        harf,
        style: TextStyle(
          fontWeight: FontWeight.w700,
          color: scheme.primary,
        ),
      ),
    );
  }

  @override
  bool shouldRebuild(_HarfBasligi oldDelegate) => oldDelegate.harf != harf;
}

/// Sağ kenardaki A–Z şeridi; dokun/kaydır ile ilgili harfe atlar.
class _HarfSerit extends StatelessWidget {
  const _HarfSerit({required this.harfler, required this.onSec});

  final List<String> harfler;
  final void Function(String) onSec;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return LayoutBuilder(
      builder: (context, constraints) {
        void dokun(double dy) {
          if (harfler.isEmpty || constraints.maxHeight <= 0) return;
          var idx = (dy / constraints.maxHeight * harfler.length).floor();
          if (idx < 0) idx = 0;
          if (idx >= harfler.length) idx = harfler.length - 1;
          onSec(harfler[idx]);
        }

        return GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTapDown: (d) => dokun(d.localPosition.dy),
          onVerticalDragUpdate: (d) => dokun(d.localPosition.dy),
          child: Container(
            width: 26,
            color: scheme.surface.withValues(alpha: 0.72),
            child: Column(
              children: [
                for (final h in harfler)
                  Expanded(
                    child: Center(
                      child: Text(
                        h,
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: scheme.primary,
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
        );
      },
    );
  }
}
