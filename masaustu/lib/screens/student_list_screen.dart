import 'dart:async';

import 'package:flutter/material.dart';

import '../api/kutuphane_api.dart';
import '../models.dart';
import '../widgets/row_table.dart';
import 'student_detail_screen.dart';

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

  void _openDetail(Ogrenci o) {
    Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => StudentDetailScreen(ogrenci: o),
    ));
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
            Text(_error!, style: const TextStyle(color: Colors.red)),
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
    return Padding(
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
          RowTableColumn('', flex: 0),
        ],
        rows: [
          for (final o in _items)
            RowTableRow(
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
                      color: o.aktif ? Colors.green.shade700 : Colors.grey,
                      fontWeight: FontWeight.w500,
                    )),
                IconButton(
                  tooltip: 'Detaylar',
                  visualDensity: VisualDensity.compact,
                  icon: const Icon(Icons.chevron_right),
                  onPressed: () => _openDetail(o),
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