import 'package:flutter/material.dart';

import '../api/kutuphane_api.dart';
import '../formatters.dart';
import '../models.dart';

class BookDetailScreen extends StatefulWidget {
  final Kitap kitap;

  const BookDetailScreen({super.key, required this.kitap});

  @override
  State<BookDetailScreen> createState() => _BookDetailScreenState();
}

class _BookDetailScreenState extends State<BookDetailScreen> {
  final _api = KutuphaneApi();
  late Future<List<Nusha>> _copiesFuture;

  @override
  void initState() {
    super.initState();
    _copiesFuture = _api.copies(widget.kitap.id);
  }

  @override
  Widget build(BuildContext context) {
    final k = widget.kitap;
    return Scaffold(
      appBar: AppBar(title: Text(k.baslik)),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          _header(k),
          const SizedBox(height: 16),
          Text('Nüshalar',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
          Text('${k.nushaSayisi} adet',
              style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 8),
          FutureBuilder<List<Nusha>>(
            future: _copiesFuture,
            builder: (context, snap) {
              if (snap.connectionState != ConnectionState.done) {
                return const Padding(
                  padding: EdgeInsets.all(24),
                  child: Center(child: CircularProgressIndicator()),
                );
              }
              if (snap.hasError) {
                return const Text('Nüsha listesi alınamadı.',
                    style: TextStyle(color: Colors.red));
              }
              final copies = snap.data ?? const [];
              if (copies.isEmpty) {
                return const Card(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Center(child: Text('Bu kitabın kayıtlı nüshası yok.')),
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
                    DataColumn(label: Text('Barkod')),
                    DataColumn(label: Text('Durum')),
                    DataColumn(label: Text('Raf Kodu')),
                  ],
                  rows: [
                    for (final n in copies)
                      DataRow(
                        cells: [
                          DataCell(Text(n.barkod,
                              style: const TextStyle(fontWeight: FontWeight.w500))),
                          DataCell(Text(durumLabel(n.durum),
                              style: TextStyle(
                                  color: durumColor(n.durum), fontWeight: FontWeight.w500))),
                          DataCell(Text(n.rafKodu ?? '—')),
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

  Widget _header(Kitap k) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.menu_book, size: 48, color: theme.colorScheme.primary),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(k.baslik,
                          style: theme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold)),
                      const SizedBox(height: 4),
                      Text(k.yazar?.adSoyad ?? '', style: theme.textTheme.bodyMedium),
                      Text(k.kategori?.ad ?? '', style: theme.textTheme.bodySmall),
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
                _info(theme, Icons.calendar_today_outlined, 'Yayın Yılı', k.yayinYili?.toString() ?? '—'),
                _info(theme, Icons.qr_code, 'ISBN', k.isbn.isEmpty ? '—' : k.isbn),
                _info(theme, Icons.inventory_2_outlined, 'Nüsha', '${k.nushaSayisi}'),
                _info(theme, Icons.shelves, 'Raf', k.rafKodlari.isEmpty ? '—' : k.rafKodlari.join(', ')),
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