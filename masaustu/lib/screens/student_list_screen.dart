import 'dart:async';

import 'package:flutter/material.dart';

import '../api/kutuphane_api.dart';
import '../config.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/horizontal_menu.dart';
import '../widgets/radial_menu.dart';
import '../widgets/row_table.dart';
import 'student_detail_screen.dart';
import 'student_form_dialog.dart';

class StudentListScreen extends StatefulWidget {
  const StudentListScreen({super.key});

  @override
  State<StudentListScreen> createState() => _StudentListScreenState();
}

class _StudentListScreenState extends State<StudentListScreen> {
  final _api = KutuphaneApi();
  final _searchController = TextEditingController();
  final _scrollController = ScrollController();

  List<Uye> _items = [];
  int _total = 0;
  int _loadedPage = 0;
  bool _hasMore = true;
  bool _initialLoading = true;
  bool _loadingMore = false;
  String? _error;
  int? _selectedId;
  String _query = '';
  String _sortKey = 'uye_no';
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
      final res = await _api.studentsPage(
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
        _error = 'Üye listesi alınamadı. Bağlantıyı kontrol edin.';
      });
    }
  }

  /// Liste çok kısaysa (boşluk kalıyorsa) sonraki sayfayı otomatik yükle.
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

  void _openDetail(Uye o) async {
    final result = await Navigator.of(context).push<Uye>(
      MaterialPageRoute(
        builder: (_) => StudentDetailScreen(uye: o),
      ),
    );
    if (result != null && mounted) _load(reset: true);
  }

  Future<void> _newStudent() async {
    final saved = await showDialog<Uye>(
      context: context,
      builder: (_) => const StudentFormDialog(),
    );
    if (saved != null && mounted) _load(reset: true);
  }

  Future<void> _editStudent(Uye o) async {
    final saved = await showDialog<Uye>(
      context: context,
      builder: (_) => StudentFormDialog(uye: o),
    );
    if (saved != null && mounted) _load(reset: true);
  }

  Future<void> _deleteStudent(Uye o) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Üyeyi sil'),
        content: Text(
            '${o.adSoyad} (${o.uyeNo}) silinecek. Bu işlem kalıcıdır; '
            'yalnızca ödünç geçmişi olmayan üyeler silinebilir. Onaylıyor musunuz?'),
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
    final res = await _api.deleteStudent(o.id);
    if (!mounted) return;
    if (res.ok) {
      setState(() => _selectedId = null);
      _snack('Üye silindi.');
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

  Future<void> _toggleStatus(Uye o) async {
    final targetAktif = !o.aktif;
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(targetAktif ? 'Üyeyi aktifleştir' : 'Üyeyi pasife al'),
        content: Text(targetAktif
            ? '${o.adSoyad} (${o.uyeNo}) tekrar aktif olacak. Onaylıyor musunuz?'
            : '${o.adSoyad} (${o.uyeNo}) pasife alınacak (mezun/nakil/tasdikname için). '
                'Geçmiş kayıtları korunur; yeni ödünç verilemez. Onaylıyor musunuz?'),
        actions: [
          TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Vazgeç')),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Onayla'),
          ),
        ],
      ),
    );
    if (confirm != true) return;
    final res = await _api.setStudentStatus(o.id, targetAktif);
    if (!mounted) return;
    if (res.ok) {
      final extra =
          res.warnings.isEmpty ? '' : ' Uyarı: ${res.warnings.join(' ')}';
      _snack((targetAktif ? 'Üye aktifleştirildi.' : 'Üye pasife alındı.') +
          extra);
      _load(reset: true);
    } else {
      _snack(res.error, error: true);
    }
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
                    hintText: 'No, ad, soyad veya sınıf ara...',
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
                onPressed: _newStudent,
                icon: const Icon(Icons.person_add),
                label: const Text('Yeni Üye'),
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Align(
            alignment: Alignment.centerLeft,
            child: Text('$_total üye',
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
            ? 'Kayıtlı üye bulunamadı.'
            : 'Aranan kriterde üye yok.'),
      );
    }
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
      child: RowTable(
        controller: _scrollController,
        footer: _footer(),
        minWidth: 900,
        sortKey: _sortKey,
        sortAscending: _sortAsc,
        onSort: _onSort,
        columns: const [
          RowTableColumn('Üye No', flex: 2, sortKey: 'uye_no'),
          RowTableColumn('Ad Soyad', flex: 3, sortKey: 'ad'),
          RowTableColumn('Sınıf', flex: 1, sortKey: 'sinif'),
          RowTableColumn('Telefon', flex: 3),
          RowTableColumn('Durum', flex: 1, sortKey: 'aktif'),
        ],
        rows: [
          for (final o in _items)
            RowTableRow(
              selected: _selectedId == o.id,
              onSelected: () {
                if (_selectedId != o.id) setState(() => _selectedId = o.id);
              },
              onTap: (pos) => _satirMenu(o, pos),
              cells: [
                Text(o.uyeNo,
                    style: const TextStyle(fontWeight: FontWeight.w600)),
                Text(o.adSoyad, overflow: TextOverflow.ellipsis),
                Text(o.sinif?.ad ?? '—'),
                Text(o.telefon ?? '—'),
                Text(o.aktif ? 'Aktif' : 'Pasif',
                    style: TextStyle(
                      color: o.aktif
                          ? successColor(context)
                          : Theme.of(context).colorScheme.onSurfaceVariant,
                      fontWeight: FontWeight.w500,
                    )),
              ],
            ),
        ],
      ),
    );
  }

  /// Satıra tıklanınca imlecin hemen altında yatay işlem menüsü (modal değil).
  void _satirMenu(Uye o, Offset globalPos) {
    _kapatMenu();
    final items = <RadialMenuItem>[
      const RadialMenuItem(
          icon: Icons.edit_outlined, label: 'Düzenle', value: 'duzenle'),
      const RadialMenuItem(
          icon: Icons.chevron_right, label: 'Detay', value: 'detay'),
      if (_isAdmin)
        RadialMenuItem(
          icon: o.aktif ? Icons.person_off_outlined : Icons.person_outline,
          label: o.aktif ? 'Pasife al' : 'Aktifleştir',
          value: 'durum',
        ),
      if (_isAdmin)
        const RadialMenuItem(
            icon: Icons.delete_outline, label: 'Sil', value: 'sil'),
    ];
    // Dış tıklama kapatması (Listener) ile aynı olayda çakışmaması için
    // menüyü bir mikro-görevde aç.
    scheduleMicrotask(() {
      if (!mounted) return;
      _menuEntry = buildHorizontalRowMenu(
        globalPosition: globalPos,
        items: items,
        onSelect: (value) {
          _kapatMenu();
          _menuSecildi(o, value);
        },
      );
      Overlay.of(context).insert(_menuEntry!);
    });
  }

  Future<void> _menuSecildi(Uye o, String secim) async {
    switch (secim) {
      case 'duzenle':
        await _editStudent(o);
      case 'detay':
        _openDetail(o);
      case 'durum':
        await _toggleStatus(o);
      case 'sil':
        await _deleteStudent(o);
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