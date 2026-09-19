import 'dart:async';

import 'package:flutter/material.dart';

import '../api/kutuphane_api.dart';
import '../config.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/floating_row_actions.dart';
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

  List<Ogrenci> _items = [];
  int _total = 0;
  int _loadedPage = 0;
  bool _hasMore = true;
  bool _initialLoading = true;
  bool _loadingMore = false;
  String? _error;
  int? _selectedId;
  String _query = '';
  Timer? _debounce;
  final Map<int, GlobalKey> _rowKeys = {};
  final _stackKey = GlobalKey();
  int _scrollTick = 0;

  GlobalKey _rowKeyOf(Ogrenci o) =>
      _rowKeys.putIfAbsent(o.id, () => GlobalObjectKey('ogrenci-${o.id}'));

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    _load(reset: true);
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (!_scrollController.hasClients) return;
    if (_selectedId != null) setState(() => _scrollTick++);
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
      final res = await _api.studentsPage(page: page, pageSize: 50, q: _query);
      if (!mounted) return;
      setState(() {
        _loadedPage = page;
        _total = res.total;
        _hasMore = res.nextPage != null;
        if (reset) {
          _items = res.items;
          _scrollTick++;
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
        _error = 'Öğrenci listesi alınamadı. Bağlantıyı kontrol edin.';
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

  void _openDetail(Ogrenci o) async {
    final result = await Navigator.of(context).push<Ogrenci>(
      MaterialPageRoute(
        builder: (_) => StudentDetailScreen(ogrenci: o),
      ),
    );
    if (result != null && mounted) _load(reset: true);
  }

  Future<void> _newStudent() async {
    final saved = await showDialog<Ogrenci>(
      context: context,
      builder: (_) => const StudentFormDialog(),
    );
    if (saved != null && mounted) _load(reset: true);
  }

  Future<void> _editStudent(Ogrenci o) async {
    final saved = await showDialog<Ogrenci>(
      context: context,
      builder: (_) => StudentFormDialog(ogrenci: o),
    );
    if (saved != null && mounted) _load(reset: true);
  }

  Future<void> _deleteStudent(Ogrenci o) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Öğrenciyi sil'),
        content: Text(
            '${o.adSoyad} (${o.ogrenciNo}) silinecek. Bu işlem kalıcıdır; '
            'yalnızca ödünç geçmişi olmayan öğrenciler silinebilir. Onaylıyor musunuz?'),
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
      _snack('Öğrenci silindi.');
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

  Future<void> _toggleStatus(Ogrenci o) async {
    final targetAktif = !o.aktif;
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(targetAktif ? 'Öğrenciyi aktifleştir' : 'Öğrenciyi pasife al'),
        content: Text(targetAktif
            ? '${o.adSoyad} (${o.ogrenciNo}) tekrar aktif olacak. Onaylıyor musunuz?'
            : '${o.adSoyad} (${o.ogrenciNo}) pasife alınacak (mezun/nakil/tasdikname için). '
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
      _snack((targetAktif ? 'Öğrenci aktifleştirildi.' : 'Öğrenci pasife alındı.') +
          extra);
      _load(reset: true);
    } else {
      _snack(res.error, error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
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
                label: const Text('Yeni Öğrenci'),
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Align(
            alignment: Alignment.centerLeft,
            child: Text('$_total öğrenci',
                style: Theme.of(context).textTheme.bodySmall),
          ),
        ),
        Expanded(child: _buildBody()),
      ],
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
            ? 'Kayıtlı öğrenci bulunamadı.'
            : 'Aranan kriterde öğrenci yok.'),
      );
    }
    final selectedIdx = _selectedId == null
        ? -1
        : _items.indexWhere((o) => o.id == _selectedId);
    final selected = selectedIdx >= 0 ? _items[selectedIdx] : null;
    return LayoutBuilder(
      builder: (context, constraints) => Stack(
        key: _stackKey,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
            child: RowTable(
              controller: _scrollController,
              footer: _footer(),
              minWidth: 900,
              columns: const [
                RowTableColumn('Öğrenci No', flex: 2),
                RowTableColumn('Ad Soyad', flex: 3),
                RowTableColumn('Sınıf', flex: 1),
                RowTableColumn('Telefon', flex: 3),
                RowTableColumn('Durum', flex: 1),
              ],
              rows: [
                for (final o in _items)
                  RowTableRow(
                    rowKey: _rowKeyOf(o),
                    selected: _selectedId == o.id,
                    onSelected: () {
                      if (_selectedId != o.id) setState(() => _selectedId = o.id);
                    },
                    onOpen: () => _openDetail(o),
                    cells: [
                      Text(o.ogrenciNo,
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
          ),
          if (selected != null)
            AnchoredRowActions(
              stackKey: _stackKey,
              rowKey: _rowKeyOf(selected),
              tick: _scrollTick,
              viewportHeight: constraints.maxHeight,
              onOutOfView: () => setState(() => _selectedId = null),
              actions: [
                IconButton(
                  tooltip: 'Düzenle',
                  visualDensity: VisualDensity.compact,
                  icon: const Icon(Icons.edit_outlined),
                  onPressed: () => _editStudent(selected),
                ),
                if (_isAdmin)
                  IconButton(
                    tooltip: selected.aktif ? 'Pasife al' : 'Aktifleştir',
                    visualDensity: VisualDensity.compact,
                    icon: Icon(selected.aktif
                        ? Icons.person_off_outlined
                        : Icons.person_outline),
                    onPressed: () => _toggleStatus(selected),
                  ),
                if (_isAdmin)
                  IconButton(
                    tooltip: 'Sil',
                    visualDensity: VisualDensity.compact,
                    icon: const Icon(Icons.delete_outline),
                    onPressed: () => _deleteStudent(selected),
                  ),
                IconButton(
                  tooltip: 'Detaylar',
                  visualDensity: VisualDensity.compact,
                  icon: const Icon(Icons.chevron_right),
                  onPressed: () => _openDetail(selected),
                ),
              ],
            ),
        ],
      ),
    );
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