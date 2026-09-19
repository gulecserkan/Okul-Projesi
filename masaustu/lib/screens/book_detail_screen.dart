import 'package:flutter/material.dart';

import '../api/kutuphane_api.dart';
import '../config.dart';
import '../formatters.dart';
import '../models.dart';
import '../theme.dart';
import 'book_form_dialog.dart';

const _deletedBook = Kitap(id: -1, baslik: '');

class BookDetailScreen extends StatefulWidget {
  final Kitap kitap;

  const BookDetailScreen({super.key, required this.kitap});

  @override
  State<BookDetailScreen> createState() => _BookDetailScreenState();
}

class _BookDetailScreenState extends State<BookDetailScreen> {
  final _api = KutuphaneApi();
  late Future<List<Nusha>> _copiesFuture;
  late Kitap _kitap = widget.kitap;
  late int _nushaSayi = widget.kitap.nushaSayisi;

  bool get _isAdmin => AppConfig.session?.role == 'admin';

  @override
  void initState() {
    super.initState();
    _loadCopies();
  }

  void _loadCopies() {
    setState(() {
      _copiesFuture = _api.copies(_kitap.id);
    });
  }

  void _snack(String msg, {bool error = false}) {
    if (!mounted) return;
    showAppSnack(context, msg, error: error);
  }

  Future<void> _edit() async {
    final saved = await showDialog<Kitap>(
      context: context,
      builder: (_) => BookFormDialog(kitap: _kitap),
    );
    if (saved != null && mounted) {
      setState(() {
        _kitap = saved;
        _nushaSayi = saved.nushaSayisi == 0 ? _nushaSayi : saved.nushaSayisi;
      });
    }
  }

  Future<void> _delete() async {
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
    final res = await _api.deleteBook(_kitap.id);
    if (!mounted) return;
    if (res.ok) {
      Navigator.of(context).pop(_deletedBook);
    } else {
      _snack(res.error ?? 'Silme yapılamadı.', error: true);
    }
  }

  Future<void> _addCopy() async {
    final raflar = await _api.raflar();
    if (!mounted) return;
    final barkodController = TextEditingController();
    int? rafId;
    final saved = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Nüsha Ekle'),
        content: SizedBox(
          width: 380,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: barkodController,
                autofocus: true,
                decoration: const InputDecoration(
                  labelText: 'Barkod (boşsa otomatik)',
                  border: OutlineInputBorder(),
                  isDense: true,
                ),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<int>(
                initialValue: rafId,
                isExpanded: true,
                decoration: const InputDecoration(
                  labelText: 'Raf',
                  border: OutlineInputBorder(),
                  isDense: true,
                ),
                items: [
                  const DropdownMenuItem<int>(
                      value: null, child: Text('— raf seç —')),
                  for (final r in raflar)
                    DropdownMenuItem<int>(value: r.id, child: Text(r.ad)),
                ],
                onChanged: (v) => rafId = v,
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: const Text('Vazgeç')),
          FilledButton(
              onPressed: () => Navigator.of(dialogContext).pop(true),
              child: const Text('Ekle')),
        ],
      ),
    );
    if (saved != true) return;
    final res = await _api.addCopy(_kitap.id,
        barkod: barkodController.text.trim(), rafId: rafId);
    if (!mounted) return;
    if (res.nusha != null) {
      setState(() => _nushaSayi++);
      _loadCopies();
      _snack('Nüsha eklendi (${res.nusha!.barkod}).');
    } else {
      _snack(res.error ?? 'Nüsha eklenemedi.', error: true);
    }
  }

  Future<void> _changeRaf(Nusha n) async {
    final raflar = await _api.raflar();
    if (!mounted) return;
    int? rafId = n.raf?.id;
    final saved = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text('Raf Değiştir (${n.barkod})'),
        content: SizedBox(
          width: 340,
          child: StatefulBuilder(
            builder: (dialogContext, setLocal) => DropdownButtonFormField<int>(
              initialValue: rafId,
              isExpanded: true,
              decoration: const InputDecoration(
                labelText: 'Raf',
                border: OutlineInputBorder(),
                isDense: true,
              ),
              items: [
                const DropdownMenuItem<int>(
                    value: null, child: Text('— raf seç —')),
                for (final r in raflar)
                  DropdownMenuItem<int>(value: r.id, child: Text(r.ad)),
              ],
              onChanged: (v) => setLocal(() => rafId = v),
            ),
          ),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: const Text('Vazgeç')),
          FilledButton(
              onPressed: () => Navigator.of(dialogContext).pop(true),
              child: const Text('Kaydet')),
        ],
      ),
    );
    if (saved != true) return;
    final res = await _api.updateCopyRaf(n.id, rafId);
    if (!mounted) return;
    if (res.ok) {
      _loadCopies();
    } else {
      _snack(res.error ?? 'Raf güncellenemedi.', error: true);
    }
  }

  Future<void> _fixDurum(Nusha n) async {
    String durum = n.durum;
    const options = {'mevcut': 'Mevcut', 'kayip': 'Kayıp', 'hasarli': 'Hasarlı'};
    final saved = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text('Durum Düzelt (${n.barkod})'),
        content: StatefulBuilder(
          builder: (dialogContext, setLocal) => RadioGroup<String>(
            groupValue: durum,
            onChanged: (v) => setLocal(() => durum = v!),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                for (final entry in options.entries)
                  RadioListTile<String>(
                    title: Text(entry.value),
                    value: entry.key,
                    dense: true,
                  ),
              ],
            ),
          ),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: const Text('Vazgeç')),
          FilledButton(
              onPressed: () => Navigator.of(dialogContext).pop(true),
              child: const Text('Kaydet')),
        ],
      ),
    );
    if (saved != true) return;
    final res = await _api.fixCopyDurum(n.id, durum);
    if (!mounted) return;
    if (res.ok) {
      _loadCopies();
    } else {
      _snack(res.error ?? 'Durum güncellenemedi.', error: true);
    }
  }

  Future<void> _deleteCopy(Nusha n) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text('Nüshayı sil (${n.barkod})'),
        content: const Text(
            'Bu nüsha silinecek. Yalnızca ödünç geçmişi olmayan nüshalar '
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
    final res = await _api.deleteCopy(n.id);
    if (!mounted) return;
    if (res.ok) {
      setState(() => _nushaSayi = (_nushaSayi - 1).clamp(0, 1 << 31));
      _loadCopies();
    } else {
      _snack(res.error ?? 'Nüsha silinemedi.', error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_kitap.baslik),
        actions: [
          IconButton(
            tooltip: 'Düzenle',
            icon: const Icon(Icons.edit_outlined),
            onPressed: _edit,
          ),
          if (_isAdmin) ...[
            IconButton(
              tooltip: 'Sil',
              icon: const Icon(Icons.delete_outline),
              onPressed: _delete,
            ),
          ],
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          _header(_kitap),
          if (_kitap.aciklama.isNotEmpty) ...[
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Text(_kitap.aciklama,
                    style: Theme.of(context).textTheme.bodyMedium),
              ),
            ),
          ],
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: Text('Nüshalar',
                    style: Theme.of(context)
                        .textTheme
                        .titleMedium
                        ?.copyWith(fontWeight: FontWeight.bold)),
              ),
              Text('$_nushaSayi adet',
                  style: Theme.of(context).textTheme.bodySmall),
              const SizedBox(width: 12),
              FilledButton.tonalIcon(
                onPressed: _addCopy,
                icon: const Icon(Icons.add, size: 18),
                label: const Text('Nüsha Ekle'),
              ),
            ],
          ),
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
                return Text('Nüsha listesi alınamadı.',
                    style: TextStyle(color: Theme.of(context).colorScheme.error));
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
                    DataColumn(label: Text('Raf')),
                    DataColumn(label: Text('')),
                  ],
                  rows: [
                    for (final n in copies)
                      DataRow(
                        cells: [
                          DataCell(Text(n.barkod,
                              style: const TextStyle(fontWeight: FontWeight.w500))),
                          DataCell(Text(durumLabel(n.durum),
                              style: TextStyle(
                                  color: durumColor(n.durum, Theme.of(context).brightness),
                                  fontWeight: FontWeight.w500))),
                          DataCell(Text(n.raf?.ad ?? n.rafKodu ?? '—')),
                          DataCell(PopupMenuButton<String>(
                            tooltip: 'İşlemler',
                            onSelected: (v) {
                              switch (v) {
                                case 'raf':
                                  _changeRaf(n);
                                case 'durum':
                                  _fixDurum(n);
                                case 'sil':
                                  _deleteCopy(n);
                              }
                            },
                            itemBuilder: (_) => [
                              const PopupMenuItem(
                                  value: 'raf', child: Text('Raf Değiştir')),
                              if (_isAdmin)
                                const PopupMenuItem(
                                    value: 'durum', child: Text('Durum Düzelt')),
                              if (_isAdmin)
                                PopupMenuItem(
                                    value: 'sil',
                                    child: Text('Sil',
                                        style: TextStyle(
                                            color: Theme.of(context)
                                                .colorScheme
                                                .error))),
                            ],
                          )),
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
                SizedBox(
                  width: 72,
                  height: 104,
                  child: k.kapakUrl != null && k.kapakUrl!.isNotEmpty
                      ? ClipRRect(
                          borderRadius: BorderRadius.circular(6),
                          child: Image.network(
                            k.kapakUrl!,
                            fit: BoxFit.cover,
                            errorBuilder: (_, _, _) => _bookIcon(theme),
                          ),
                        )
                      : _bookIcon(theme),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(k.baslik,
                          style: theme.textTheme.headlineSmall
                              ?.copyWith(fontWeight: FontWeight.bold)),
                      const SizedBox(height: 4),
                      Text(k.yazar?.adSoyad ?? '',
                          style: theme.textTheme.bodyMedium),
                      Text(k.kategori?.ad ?? '',
                          style: theme.textTheme.bodySmall),
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
                _info(theme, Icons.calendar_today_outlined, 'Yayın Yılı',
                    k.yayinYili?.toString() ?? '—'),
                _info(theme, Icons.qr_code, 'ISBN',
                    k.isbn.isEmpty ? '—' : k.isbn),
                _info(theme, Icons.inventory_2_outlined, 'Nüsha', '$_nushaSayi'),
                _info(theme, Icons.shelves, 'Raf',
                    k.rafKodlari.isEmpty ? '—' : k.rafKodlari.join(', ')),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _bookIcon(ThemeData theme) {
    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Icon(Icons.menu_book, size: 40, color: theme.colorScheme.primary),
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