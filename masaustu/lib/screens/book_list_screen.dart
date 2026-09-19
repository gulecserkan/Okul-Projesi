import 'dart:async';

import 'package:flutter/material.dart';

import '../api/kutuphane_api.dart';
import '../config.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/horizontal_menu.dart';
import '../widgets/radial_menu.dart';
import '../widgets/row_table.dart';
import 'book_detail_screen.dart';
import 'book_form_dialog.dart';

class BookListScreen extends StatefulWidget {
  const BookListScreen({super.key});

  @override
  State<BookListScreen> createState() => _BookListScreenState();
}

class _BookListScreenState extends State<BookListScreen> {
  final _api = KutuphaneApi();
  final _searchController = TextEditingController();
  final _scrollController = ScrollController();

  List<Kitap> _items = [];
  int _total = 0;
  int _loadedPage = 0;
  bool _hasMore = true;
  bool _initialLoading = true;
  bool _loadingMore = false;
  String? _error;
  int? _selectedId;
  String _query = '';
  String _sortKey = 'baslik';
  bool _sortAsc = true;
  Timer? _debounce;
  OverlayEntry? _menuEntry;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    _load(reset: true);
  }

  @override
  void dispose() {
    _kapatMenu();
    _debounce?.cancel();
    _scrollController.dispose();
    super.dispose();
  }

  void _kapatMenu() {
    _menuEntry?.remove();
    _menuEntry = null;
  }

  void _onScroll() {
    if (!_scrollController.hasClients) return;
    if (_menuEntry != null) _kapatMenu();
    final pos = _scrollController.position;
    if (pos.pixels >= pos.maxScrollExtent - 200) _load(reset: false);
  }

  Future<void> _load({required bool reset}) async {
    if (reset) {
      setState(() {
        _initialLoading = true;
        _error = null;
      });
    } else {
      if (_loadingMore || !_hasMore) return;
      setState(() => _loadingMore = true);
    }

    final page = reset ? 1 : _loadedPage + 1;
    try {
      final res = await _api.booksPage(
        page: page,
        pageSize: 50,
        q: _query,
        ordering: '${_sortAsc ? '' : '-'}$_sortKey',
      );
      if (!mounted) return;
      setState(() {
        _loadedPage = page;
        _total = res.total;
        _hasMore = res.nextPage != null;
        if (reset) {
          _items = res.items;
        } else {
          _items.addAll(res.items);
        }
        _initialLoading = false;
        _loadingMore = false;
      });
      _continueIfFits();
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _initialLoading = false;
        _loadingMore = false;
        _error = 'Kitap listesi alınamadı. Bağlantıyı kontrol edin.';
      });
    }
  }

  void _continueIfFits() {
    if (!_hasMore) return;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !_scrollController.hasClients) return;
      final pos = _scrollController.position;
      if (pos.maxScrollExtent <= pos.viewportDimension ||
          pos.pixels >= pos.maxScrollExtent - 200) {
        _load(reset: false);
      }
    });
  }

  void _onSearchChanged(String text) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 400), () {
      if (!mounted) return;
      _query = text.trim();
      _load(reset: true);
    });
  }

  /// Başlığa tıklayınca sıralama (aynı başlık → yön değiştir).
  void _onSort(String key) {
    setState(() {
      if (_sortKey == key) {
        _sortAsc = !_sortAsc;
      } else {
        _sortKey = key;
        _sortAsc = true;
      }
    });
    _load(reset: true);
  }

  void _openDetail(Kitap k) async {
    final result = await Navigator.of(context).push<Kitap>(
      MaterialPageRoute(builder: (_) => BookDetailScreen(kitap: k)),
    );
    if (result != null && mounted) _load(reset: true);
  }

  Future<void> _newBook() async {
    final saved = await showDialog<Kitap>(
      context: context,
      builder: (_) => const BookFormDialog(),
    );
    // K8.4: yeni kayıt çiftsiz tamamlanınca nüsha ekleme için detaya geçilir.
    if (saved != null && mounted) {
      _load(reset: true);
      _openDetail(saved);
    }
  }

  Future<void> _editBook(Kitap k) async {
    final saved = await showDialog<Kitap>(
      context: context,
      builder: (_) => BookFormDialog(kitap: k),
    );
    if (saved != null && mounted) _load(reset: true);
  }

  Future<void> _deleteBook(Kitap k) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Kitabı sil'),
        content: const Text(
            'Bu kitap silinecek. Yalnızca ödünç geçmişi olmayan kitaplar '
            'silinebilir; aksi halde işlem reddedilir. Onaylıyor musunuz?'),
        actions: [
          TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Vazgeç')),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Sil'),
          ),
        ],
      ),
    );
    if (confirm != true) return;
    final res = await _api.deleteBook(k.id);
    if (!mounted) return;
    if (res.ok) {
      setState(() => _selectedId = null);
      _snack('Kitap silindi.');
      _load(reset: true);
    } else {
      _snack(res.error ?? 'Silme yapılamadı.', error: true);
    }
  }

  bool get _isAdmin => AppConfig.session?.role == 'admin';

  void _snack(String msg, {bool error = false}) {
    if (!mounted) return;
    showAppSnack(context, msg, error: error);
  }

  @override
  Widget build(BuildContext context) {
    return Listener(
      onPointerDown: (_) => _kapatMenu(),
      child: Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(24, 24, 24, 8),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _searchController,
                  autofocus: true,
                  onChanged: _onSearchChanged,
                  decoration: const InputDecoration(
                    hintText: 'Başlık, ISBN, yazar, kategori veya raf ara...',
                    prefixIcon: Icon(Icons.search),
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              IconButton.filledTonal(
                tooltip: 'Yenile',
                icon: const Icon(Icons.refresh),
                onPressed: _initialLoading ? null : () => _load(reset: true),
              ),
              const SizedBox(width: 8),
              FilledButton.icon(
                onPressed: _newBook,
                icon: const Icon(Icons.add),
                label: const Text('Yeni Kitap'),
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Align(
            alignment: Alignment.centerLeft,
            child: Text('$_total kitap',
                style: Theme.of(context).textTheme.bodySmall),
          ),
        ),
        Expanded(child: _buildBody()),
      ],
      ),
    );
  }

  Widget _buildBody() {
    if (_initialLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null && _items.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            const SizedBox(height: 8),
            FilledButton.tonal(
                onPressed: () => _load(reset: true),
                child: const Text('Tekrar Dene')),
          ],
        ),
      );
    }
    if (_items.isEmpty) {
      return Center(
        child: Text(_query.isEmpty
            ? 'Kayıtlı kitap bulunamadı.'
            : 'Aranan kriterde kitap yok.'),
      );
    }
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
      child: RowTable(
        controller: _scrollController,
        footer: _footer(),
        minWidth: 1050,
        sortKey: _sortKey,
        sortAscending: _sortAsc,
        onSort: _onSort,
        columns: const [
          RowTableColumn('Kitap', flex: 4, sortKey: 'baslik'),
          RowTableColumn('Yazar', flex: 3, sortKey: 'yazar'),
          RowTableColumn('Kategori', flex: 2, sortKey: 'kategori'),
          RowTableColumn('Yıl', flex: 1, sortKey: 'yayin_yili'),
          RowTableColumn('Nüsha', flex: 1, sortKey: 'nusha_sayisi'),
          RowTableColumn('Raf', flex: 2),
        ],
        rows: [
          for (final k in _items)
            RowTableRow(
              selected: _selectedId == k.id,
              onSelected: () {
                if (_selectedId != k.id) setState(() => _selectedId = k.id);
              },
              onTap: (pos) => _satirMenu(k, pos),
              cells: [
                Text(k.baslik,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w500)),
                Text(k.yazar?.adSoyad ?? '—',
                    overflow: TextOverflow.ellipsis),
                Text(k.kategori?.ad ?? '—'),
                Text(k.yayinYili?.toString() ?? '—'),
                Text('${k.nushaSayisi}'),
                Text(k.rafKodlari.join(', '),
                    overflow: TextOverflow.ellipsis),
              ],
            ),
        ],
      ),
    );
  }

  /// Satıra tıklanınca imlecin altında yatay işlem menüsü (modal değil).
  void _satirMenu(Kitap k, Offset globalPos) {
    _kapatMenu();
    final items = <RadialMenuItem>[
      const RadialMenuItem(
          icon: Icons.edit_outlined, label: 'Düzenle', value: 'duzenle'),
      const RadialMenuItem(
          icon: Icons.chevron_right, label: 'Detay', value: 'detay'),
      if (_isAdmin)
        const RadialMenuItem(
            icon: Icons.delete_outline, label: 'Sil', value: 'sil'),
    ];
    scheduleMicrotask(() {
      if (!mounted) return;
      _menuEntry = buildHorizontalRowMenu(
        globalPosition: globalPos,
        items: items,
        onSelect: (value) {
          _kapatMenu();
          _menuSecildi(k, value);
        },
      );
      Overlay.of(context).insert(_menuEntry!);
    });
  }

  Future<void> _menuSecildi(Kitap k, String secim) async {
    switch (secim) {
      case 'duzenle':
        await _editBook(k);
      case 'detay':
        _openDetail(k);
      case 'sil':
        await _deleteBook(k);
    }
  }

  Widget _footer() {
    if (!_loadingMore) return const SizedBox(height: 8);
    return const Padding(
      padding: EdgeInsets.all(16),
      child: Center(
        child: SizedBox(
          height: 20,
          width: 20,
          child: CircularProgressIndicator(strokeWidth: 2),
        ),
      ),
    );
  }
}