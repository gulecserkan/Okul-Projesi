import 'package:flutter/material.dart';

import '../api/kutuphane_api.dart';
import '../models.dart';
import '../widgets/row_table.dart';
import 'book_detail_screen.dart';

class BookListScreen extends StatefulWidget {
  const BookListScreen({super.key});

  @override
  State<BookListScreen> createState() => _BookListScreenState();
}

class _BookListScreenState extends State<BookListScreen> {
  final _api = KutuphaneApi();
  final _searchController = TextEditingController();

  List<Kitap> _all = [];
  bool _loading = true;
  String? _error;
  int? _selectedId;

  void _openDetail(Kitap k) {
    Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => BookDetailScreen(kitap: k),
    ));
  }

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
      final books = await _api.books();
      if (!mounted) return;
      setState(() {
        _all = books
          ..sort((a, b) => a.baslik.toLowerCase().compareTo(b.baslik.toLowerCase()));
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'Kitap listesi alınamadı. Bağlantıyı kontrol edin.';
      });
    }
  }

  List<Kitap> get _filtered {
    final q = _searchController.text.trim().toLowerCase();
    if (q.isEmpty) return _all;
    return _all.where((k) {
      return k.baslik.toLowerCase().contains(q) ||
          k.isbn.toLowerCase().contains(q) ||
          (k.yazar?.adSoyad.toLowerCase().contains(q) ?? false) ||
          (k.kategori?.ad.toLowerCase().contains(q) ?? false) ||
          k.rafKodlari.any((r) => r.toLowerCase().contains(q));
    }).toList();
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
                  onChanged: (_) => setState(() {}),
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
                onPressed: _loading ? null : _load,
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Align(
            alignment: Alignment.centerLeft,
            child: Builder(builder: (context) {
              final nusha = _filtered.fold<int>(0, (s, k) => s + k.nushaSayisi);
              return Text('${_filtered.length} kitap ($nusha nüsha)',
                  style: Theme.of(context).textTheme.bodySmall);
            }),
          ),
        ),
        Expanded(child: _buildBody()),
      ],
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
            Text(_error!, style: const TextStyle(color: Colors.red)),
            const SizedBox(height: 8),
            FilledButton.tonal(onPressed: _load, child: const Text('Tekrar Dene')),
          ],
        ),
      );
    }
    if (_all.isEmpty) {
      return const Center(child: Text('Kayıtlı kitap bulunamadı.'));
    }
    final filtered = _filtered;
    if (filtered.isEmpty) {
      return const Center(child: Text('Aranan kriterde kitap yok.'));
    }
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
      child: RowTable(
        minWidth: 1050,
        columns: const [
          RowTableColumn('Kitap', flex: 4),
          RowTableColumn('Yazar', flex: 3),
          RowTableColumn('Kategori', flex: 2),
          RowTableColumn('Yıl', flex: 1),
          RowTableColumn('Nüsha', flex: 1),
          RowTableColumn('Raf', flex: 2),
          RowTableColumn('', flex: 0),
        ],
        rows: [
          for (final k in filtered)
            RowTableRow(
              selected: _selectedId == k.id,
              onSelected: () {
                if (_selectedId != k.id) setState(() => _selectedId = k.id);
              },
              onOpen: () => _openDetail(k),
              cells: [
                Text(k.baslik,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w500)),
                Text(k.yazar?.adSoyad ?? '—', overflow: TextOverflow.ellipsis),
                Text(k.kategori?.ad ?? '—'),
                Text(k.yayinYili?.toString() ?? '—'),
                Text('${k.nushaSayisi}'),
                Text(k.rafKodlari.join(', '), overflow: TextOverflow.ellipsis),
                IconButton(
                  tooltip: 'Detaylar',
                  visualDensity: VisualDensity.compact,
                  icon: const Icon(Icons.chevron_right),
                  onPressed: () => _openDetail(k),
                ),
              ],
            ),
        ],
      ),
    );
  }
}