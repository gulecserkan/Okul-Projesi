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

  List<Ogrenci> _all = [];
  bool _loading = true;
  String? _error;
  int? _selectedId;

  void _openDetail(Ogrenci o) {
    Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => StudentDetailScreen(ogrenci: o),
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
      final students = await _api.students();
      if (!mounted) return;
      setState(() {
        _all = students
          ..sort((a, b) => a.ogrenciNo.compareTo(b.ogrenciNo));
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'Öğrenci listesi alınamadı. Bağlantıyı kontrol edin.';
      });
    }
  }

  List<Ogrenci> get _filtered {
    final q = _searchController.text.trim().toLowerCase();
    if (q.isEmpty) return _all;
    return _all.where((o) {
      final sinif = o.sinif?.ad.toLowerCase() ?? '';
      return o.ad.toLowerCase().contains(q) ||
          o.soyad.toLowerCase().contains(q) ||
          o.ogrenciNo.toLowerCase().contains(q) ||
          sinif.contains(q);
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
              return Text('${_filtered.length} öğrenci',
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
      return const Center(child: Text('Kayıtlı öğrenci bulunamadı.'));
    }
    final filtered = _filtered;
    if (filtered.isEmpty) {
      return const Center(child: Text('Aranan kriterde öğrenci yok.'));
    }
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
      child: RowTable(
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
          for (final o in filtered)
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
}