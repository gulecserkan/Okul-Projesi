import 'package:flutter/material.dart';

import '../api/kutuphane_api.dart';
import '../config.dart';
import '../formatters.dart';
import '../models.dart';

class StudentDetailScreen extends StatefulWidget {
  final Ogrenci ogrenci;

  const StudentDetailScreen({super.key, required this.ogrenci});

  @override
  State<StudentDetailScreen> createState() => _StudentDetailScreenState();
}

class _StudentDetailScreenState extends State<StudentDetailScreen> {
  final _api = KutuphaneApi();
  late Future<List<OduncKaydi>> _historyFuture;
  late Future<PenaltySummary> _penaltiesFuture;
  late bool _aktif = widget.ogrenci.aktif;

  bool get _isAdmin => AppConfig.session?.role == 'admin';

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    _historyFuture = _api.studentHistory(widget.ogrenci.ogrenciNo);
    _penaltiesFuture = _api.studentPenalties(widget.ogrenci.ogrenciNo);
  }

  void _snack(String msg, {bool error = false}) {
    if (!mounted) return;
    final color = error
        ? Theme.of(context).colorScheme.errorContainer
        : Theme.of(context).colorScheme.secondaryContainer;
    ScaffoldMessenger.of(context)
      ..clearSnackBars()
      ..showSnackBar(SnackBar(content: Text(msg), backgroundColor: color));
  }

  Future<void> _toggleStatus() async {
    final o = widget.ogrenci;
    final targetAktif = !_aktif;
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title:
            Text(targetAktif ? 'Öğrenciyi aktifleştir' : 'Öğrenciyi pasife al'),
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
      setState(() => _aktif = targetAktif);
      final extra = res.warnings.isEmpty ? '' : ' Uyarı: ${res.warnings.join(' ')}';
      _snack((targetAktif ? 'Öğrenci aktifleştirildi.' : 'Öğrenci pasife alındı.') + extra);
    } else {
      _snack(res.error, error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final o = widget.ogrenci;
    return Scaffold(
      appBar: AppBar(
        title: Text(o.adSoyad),
        actions: [
          if (_isAdmin)
            IconButton(
              tooltip: _aktif ? 'Pasife al' : 'Aktifleştir',
              icon: Icon(
                _aktif ? Icons.person_off_outlined : Icons.person_outline,
              ),
              onPressed: _toggleStatus,
            ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          _header(o),
          const SizedBox(height: 16),
          FutureBuilder<PenaltySummary>(
            future: _penaltiesFuture,
            builder: (context, snap) {
              if (snap.hasData && snap.data!.outstandingCount > 0) {
                final p = snap.data!;
                return Card(
                  color: Colors.red.shade50,
                  child: ListTile(
                    leading: Icon(Icons.warning_amber_rounded, color: Colors.red.shade800),
                    title: Text('Ödenmemiş gecikme cezası: ${p.outstandingTotal} ₺',
                        style: TextStyle(color: Colors.red.shade800, fontWeight: FontWeight.bold)),
                    subtitle: Text('${p.outstandingCount} kayıt'),
                  ),
                );
              }
              return const SizedBox.shrink();
            },
          ),
          const SizedBox(height: 16),
          Text('Ödünç Geçmişi',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          FutureBuilder<List<OduncKaydi>>(
            future: _historyFuture,
            builder: (context, snap) {
              if (snap.connectionState != ConnectionState.done) {
                return const Padding(
                  padding: EdgeInsets.all(24),
                  child: Center(child: CircularProgressIndicator()),
                );
              }
              if (snap.hasError) {
                return const Text('Sorgu alınamadı.',
                    style: TextStyle(color: Colors.red));
              }
              final rows = snap.data ?? const [];
              if (rows.isEmpty) {
                return const Card(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Center(child: Text('Bu öğrencinin ödünç geçmişi yok.')),
                  ),
                );
              }
              return Card(
                clipBehavior: Clip.antiAlias,
                child: DataTable(
                  headingRowHeight: 44,
                  dataRowMinHeight: 40,
                  dataRowMaxHeight: 48,
                  columns: const [
                    DataColumn(label: Text('Kitap')),
                    DataColumn(label: Text('Barkod')),
                    DataColumn(label: Text('Alındı')),
                    DataColumn(label: Text('Beklenen')),
                    DataColumn(label: Text('Teslim')),
                    DataColumn(label: Text('Durum')),
                    DataColumn(label: Text('Cezası')),
                  ],
                  rows: [
                    for (final h in rows)
                      DataRow(
                        cells: [
                          DataCell(SizedBox(
                            width: 240,
                            child: Text(h.kitapBaslik,
                                maxLines: 1, overflow: TextOverflow.ellipsis),
                          )),
                          DataCell(Text(h.barkod)),
                          DataCell(Text(formatDate(h.oduncTarihi))),
                          DataCell(Text(formatDate(h.iadeTarihi))),
                          DataCell(Text(formatDate(h.teslimTarihi))),
                          DataCell(Text(durumLabel(h.durum),
                              style: TextStyle(
                                  color: durumColor(h.durum), fontWeight: FontWeight.w500))),
                          DataCell(Text(h.gecikmeCezasi ?? '—')),
                        ],
                      ),
                  ],
                ),
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _header(Ogrenci o) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(
                  radius: 28,
                  child: Text(
                    '${o.ad.characters.first}${o.soyad.characters.first}',
                    style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('${o.ad} ${o.soyad}',
                          style: theme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold)),
                      const SizedBox(height: 4),
                      Wrap(
                        spacing: 8,
                        children: [
                          Chip(label: Text(o.ogrenciNo), visualDensity: VisualDensity.compact),
                          if (o.sinif != null)
                            Chip(label: Text(o.sinif!.ad), visualDensity: VisualDensity.compact),
                          Chip(
                            label: Text(_aktif ? 'Aktif' : 'Pasif',
                                style: TextStyle(
                                    color: _aktif ? Colors.green.shade700 : Colors.grey)),
                            visualDensity: VisualDensity.compact,
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const Divider(height: 24),
            Wrap(
              spacing: 32,
              runSpacing: 8,
              children: [
                _info(theme, Icons.phone_outlined, 'Telefon', o.telefon ?? '—'),
                _info(theme, Icons.mail_outline, 'E-posta', o.eposta ?? '—'),
                _info(theme, Icons.calendar_today_outlined, 'Kayıt', formatDate(o.kayitTarihi)),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _info(ThemeData theme, IconData icon, String label, String value) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 16, color: theme.colorScheme.primary),
        const SizedBox(width: 6),
        Text('$label: ', style: theme.textTheme.bodySmall),
        Text(value, style: const TextStyle(fontWeight: FontWeight.w500)),
      ],
    );
  }
}