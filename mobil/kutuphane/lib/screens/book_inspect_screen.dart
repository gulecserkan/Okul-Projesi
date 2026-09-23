import 'package:flutter/material.dart';

import '../api/library_api.dart';
import '../models/book.dart';
import 'image_gallery_screen.dart';

/// K9.9: Üye için tam sayfa "Kitap İnceleme" ekranı (salt-okunur).
/// "Sanki kitap eldeymiş gibi": ön/arka kapak ve önsöz-giriş sayfalarını
/// kaydırarak çevirir; öğretmen görüşünü (aciklama) ve künyeyi okur.
class BookInspectScreen extends StatefulWidget {
  const BookInspectScreen({
    super.key,
    required this.api,
    required this.summary,
  });

  final LibraryApiClient api;
  final BookSummary summary;

  @override
  State<BookInspectScreen> createState() => _BookInspectScreenState();
}

class _BookInspectScreenState extends State<BookInspectScreen> {
  BookDetail? _detail;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final d = await widget.api.fetchBookDetail(widget.summary.id);
      if (!mounted) return;
      setState(() {
        _detail = d;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e is ApiException ? e.message : e.toString();
        _loading = false;
      });
    }
  }

  /// Gösterilecek sayfalar: dış kapak (varsa) + yüklenen resim1..5.
  List<BookImageSlot> _pages(BookDetail d) {
    final list = <BookImageSlot>[];
    if ((d.kapakUrl ?? '').isNotEmpty) {
      list.add(BookImageSlot(index: 0, url: d.kapakUrl));
    }
    list.addAll(d.resimler.where((s) => s.hasImage));
    return list;
  }

  String _pageLabel(BookImageSlot slot) {
    if (slot.index == 0) return 'Kapak';
    return 'Sayfa ${slot.index}';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.summary.baslik, overflow: TextOverflow.ellipsis),
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('Kitap açılamadı.\n$_error', textAlign: TextAlign.center),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: _load,
              icon: const Icon(Icons.refresh),
              label: const Text('Tekrar dene'),
            ),
          ],
        ),
      );
    }
    final d = _detail!;
    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _coverArea(d),
            const SizedBox(height: 16),
            _kunyaCard(d),
            const SizedBox(height: 12),
            _teacherOpinionCard(d),
          ],
        ),
      ),
    );
  }

  Widget _coverArea(BookDetail d) {
    final scheme = Theme.of(context).colorScheme;
    final pages = _pages(d);
    if (pages.isEmpty) {
      return _bookCoverPlaceholder(d.baslik, scheme, height: 300);
    }
    return StatefulBuilder(
      builder: (context, setState) {
        return Column(
          children: [
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 250, maxHeight: 350),
              child: AspectRatio(
                aspectRatio: 3 / 4,
                child: Stack(
                  children: [
                    ClipRRect(
                      borderRadius: BorderRadius.circular(12),
                      child: Container(
                        decoration: BoxDecoration(
                          color: scheme.surfaceContainerHighest,
                          border: Border.all(color: scheme.outlineVariant),
                        ),
                        child: PageView.builder(
                          itemCount: pages.length,
                          onPageChanged: (i) =>
                              setState(() => _currentPage = i),
                          itemBuilder: (context, i) {
                            final slot = pages[i];
                            return GestureDetector(
                              onTap: () {
                                Navigator.of(context).push(
                                  MaterialPageRoute<void>(
                                    builder: (_) => ImageGalleryScreen(
                                      images: pages,
                                      initialIndex: slot.index,
                                    ),
                                  ),
                                );
                              },
                              child: Image.network(
                                slot.url!,
                                fit: BoxFit.cover,
                                errorBuilder: (_, _, _) =>
                                    _bookCoverPlaceholder(d.baslik, scheme),
                              ),
                            );
                          },
                        ),
                      ),
                    ),
                    Positioned(
                      right: 0,
                      bottom: 0,
                      left: 0,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 10,
                          vertical: 6,
                        ),
                        decoration: BoxDecoration(
                          color: Colors.black.withValues(alpha: 0.55),
                          borderRadius: const BorderRadius.vertical(
                            bottom: Radius.circular(12),
                          ),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Expanded(
                              child: Text(
                                _pageLabel(pages[_currentPage]),
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.w600,
                                  fontSize: 13,
                                ),
                              ),
                            ),
                            Text(
                              '${_currentPage + 1} / ${pages.length}',
                              style: const TextStyle(
                                color: Colors.white70,
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.swipe, size: 14, color: scheme.outline),
                const SizedBox(width: 6),
                Text(
                  'Kapakları kaydırarak sayfaları çevir · dokunarak büyüt',
                  style: TextStyle(fontSize: 12, color: scheme.outline),
                ),
              ],
            ),
          ],
        );
      },
    );
  }

  int _currentPage = 0;

  Widget _bookCoverPlaceholder(
    String baslik,
    ColorScheme scheme, {
    double? height,
  }) {
    return Container(
      height: height,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [scheme.primaryContainer, scheme.tertiaryContainer],
        ),
      ),
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.menu_book_rounded, size: 48, color: scheme.primary),
              const SizedBox(height: 12),
              Text(
                baslik,
                textAlign: TextAlign.center,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: scheme.onPrimaryContainer,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _kunyaCard(BookDetail d) {
    final scheme = Theme.of(context).colorScheme;
    final rows = <(IconData, String, String)>[
      if ((d.yazar ?? '').isNotEmpty) (Icons.person_outline, 'Yazar', d.yazar!),
      if ((d.kategori ?? '').isNotEmpty)
        (Icons.label_outline, 'Kategori', d.kategori!),
      if (d.yayinYili != null)
        (Icons.calendar_today_outlined, 'Yayın yılı', '${d.yayinYili}'),
      if ((d.isbn ?? '').isNotEmpty) (Icons.qr_code_outlined, 'ISBN', d.isbn!),
      if (d.shelfCodes.isNotEmpty)
        (Icons.shelves, 'Raf', d.shelfCodes.join(', ')),
    ];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Künye',
              style: Theme.of(
                context,
              ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),
            for (final (icon, label, value) in rows)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(icon, size: 18, color: scheme.primary),
                    const SizedBox(width: 8),
                    SizedBox(
                      width: 72,
                      child: Text(
                        label,
                        style: TextStyle(
                          fontSize: 13,
                          color: scheme.onSurfaceVariant,
                        ),
                      ),
                    ),
                    Expanded(
                      child: Text(value, style: const TextStyle(fontSize: 14)),
                    ),
                  ],
                ),
              ),
            const Divider(height: 20),
            Row(
              children: [
                Icon(
                  Icons.location_on_outlined,
                  size: 18,
                  color: scheme.primary,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    d.nushaSayisi != null && d.nushaSayisi! > 0
                        ? 'Kütüphanede ${d.nushaSayisi} nüsha mevcut. Ödünç almak için kütüphaneye uğrayabilirsin.'
                        : 'Şu an kütüphanede mevcut nüsha görünmüyor.',
                    style: const TextStyle(fontSize: 13),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _teacherOpinionCard(BookDetail d) {
    final scheme = Theme.of(context).colorScheme;
    final hasOpinion = (d.aciklama ?? '').trim().isNotEmpty;
    return Card(
      color: hasOpinion ? null : scheme.surfaceContainerLow,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  hasOpinion ? Icons.school_outlined : Icons.school_outlined,
                  size: 22,
                  color: scheme.primary,
                ),
                const SizedBox(width: 8),
                Text(
                  'Öğretmen Görüşü',
                  style: Theme.of(
                    context,
                  ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              hasOpinion
                  ? d.aciklama!
                  : 'Bu kitap için öğretmen görüşü henüz eklenmemiş.',
              style: TextStyle(
                fontSize: 14,
                height: 1.5,
                color: hasOpinion ? null : scheme.onSurfaceVariant,
                fontStyle: hasOpinion ? null : FontStyle.italic,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
