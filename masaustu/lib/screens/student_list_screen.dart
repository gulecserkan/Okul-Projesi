import 'package:flutter/material.dart';

import '../api/kutuphane_api.dart';
import '../models.dart';
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

  DataCell _cell(Ogrenci o, Widget child) {
    return DataCell(
      GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: () => setState(() => _selectedId = o.id),
        onDoubleTap: () => _openDetail(o),
        child: child,
      ),
    );
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
            child: Text('${_filtered.length} öğrenci',
                style: Theme.of(context).textTheme.bodySmall),
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
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
child: Card(
          clipBehavior: Clip.antiAlias,
          child: DataTable(
            headingRowHeight: 44,
            dataRowMinHeight: 40,
            dataRowMaxHeight: 48,
            columns: const [
              DataColumn(label: Text('Öğrenci No')),
              DataColumn(label: Text('Ad Soyad')),
              DataColumn(label: Text('Sınıf')),
              DataColumn(label: Text('Telefon')),
              DataColumn(label: Text('Durum')),
              DataColumn(label: Text('')),
            ],
            rows: [
              for (final o in filtered)
                DataRow(
                  color: _selectedId == o.id
                      ? WidgetStatePropertyAll(
                          Theme.of(context).colorScheme.primaryContainer)
                      : null,
                  cells: [
                    _cell(o, Text(o.ogrenciNo)),
                    _cell(o, Text(o.adSoyad)),
                    _cell(o, Text(o.sinif?.ad ?? '—')),
                    _cell(o, Text(o.telefon ?? '—')),
                    _cell(o, Text(o.aktif ? 'Aktif' : 'Pasif',
                        style: TextStyle(
                          color: o.aktif ? Colors.green.shade700 : Colors.grey,
                        ))),
                    DataCell(IconButton(
                      tooltip: 'Detaylar',
                      icon: const Icon(Icons.chevron_right),
                      onPressed: () => _openDetail(o),
                    )),
                  ],
                ),
              if (filtered.isEmpty)
                const DataRow(
                  cells: [
                    DataCell(Text('—')),
                    DataCell(Text('Aranan kriterde öğrenci yok')),
                    DataCell(Text('')),
                    DataCell(Text('')),
                    DataCell(Text('')),
                    DataCell(Text('')),
                  ],
                ),
            ],
          ),
        ),
    );
  }
}