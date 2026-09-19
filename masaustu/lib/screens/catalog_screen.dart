import 'package:flutter/material.dart';

import '../api/kutuphane_api.dart';
import '../formatters.dart';
import '../models.dart';
import '../theme.dart';

/// Faz C: Merkezi Katalog (yalnızca admin).
/// Yazar / Kategori / Raf kayıtları: ekle, düzenle, sil, birleştir (K6.2).
/// Çift Kitaplar: fold-normalize başlık çakışmaları (K6.1) birleştirme ile çözülür.
class CatalogScreen extends StatefulWidget {
  const CatalogScreen({super.key});

  @override
  State<CatalogScreen> createState() => _CatalogScreenState();
}

class _CatalogScreenState extends State<CatalogScreen> {
  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 4,
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 16, 24, 0),
            child: Align(
              alignment: Alignment.centerLeft,
              child: Text('Merkezi Katalog',
                  style: Theme.of(context)
                      .textTheme
                      .titleLarge
                      ?.copyWith(fontWeight: FontWeight.bold)),
            ),
          ),
          const TabBar(
            tabs: [
              Tab(text: 'Yazarlar'),
              Tab(text: 'Kategoriler'),
              Tab(text: 'Raflar'),
              Tab(text: 'Çift Kitaplar'),
            ],
          ),
          const Expanded(
            child: TabBarView(
              children: [
                _CatalogListTab<Yazar>(
                  path: 'yazarlar/',
                  labelField: 'Yazar',
                  parser: Yazar.fromJson,
                  nameOf: _yazarName,
                  renameOf: _renameYazar,
                ),
                _CatalogListTab<Kategori>(
                  path: 'kategoriler/',
                  labelField: 'Kategori',
                  parser: Kategori.fromJson,
                  nameOf: _kategoriName,
                  renameOf: _renameKategori,
                ),
                _CatalogListTab<Raf>(
                  path: 'raflar/',
                  labelField: 'Raf',
                  parser: Raf.fromJson,
                  nameOf: _rafName,
                  renameOf: _renameRaf,
                ),
                _DuplicateBooksTab(),
              ],
            ),
          ),
        ],
      ),
    );
  }

  static Map<String, dynamic> _renameYazar(String v) =>
      {'ad_soyad': v.trim()};
  static Map<String, dynamic> _renameKategori(String v) => {'ad': v.trim()};
  static Map<String, dynamic> _renameRaf(String v) => {'ad': v.trim()};

  static String _yazarName(Yazar y) => y.adSoyad;
  static String _kategoriName(Kategori k) => k.ad;
  static String _rafName(Raf r) => r.ad;
}

class _CatalogListTab<T> extends StatefulWidget {
  final String path;
  final String labelField;
  final T Function(Map<String, dynamic>) parser;
  final String Function(T) nameOf;
  final Map<String, dynamic> Function(String) renameOf;

  const _CatalogListTab({
    required this.path,
    required this.labelField,
    required this.parser,
    required this.nameOf,
    required this.renameOf,
  });

  @override
  State<_CatalogListTab<T>> createState() => _CatalogListTabState<T>();
}

class _CatalogListTabState<T> extends State<_CatalogListTab<T>> {
  final _api = KutuphaneApi();
  late Future<List<T>> _future;
  final _addController = TextEditingController();
  final _renameController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<T>> _load() async {
    try {
      final data = await _api.fetchAllPages(widget.path);
      return data
          .whereType<Map<String, dynamic>>()
          .map(widget.parser)
          .toList();
    } catch (_) {
      return [];
    }
  }

  @override
  void dispose() {
    _addController.dispose();
    _renameController.dispose();
    super.dispose();
  }

  Future<void> _add() async {
    final name = await _prompt(_addController, '${widget.labelField} Ekle',
        '${widget.labelField} adı:');
    final ad = (name ?? '').trim();
    if (ad.isEmpty) return;

    final items = await _load();
    // K6.1: %100 aynı (normalize) kayıt varsa ekleme.
    final norm = normalizeTr(ad);
    final ayni =
        items.where((e) => normalizeTr(widget.nameOf(e)) == norm).toList();
    if (ayni.isNotEmpty) {
      if (!mounted) return;
      showAppSnack(context, '"${widget.nameOf(ayni.first)}" zaten kayıtlı.',
          error: true);
      return;
    }
    // K6.1: çok benzer kayıt(lar) varsa gösterip sor.
    final benzer = items
        .map((e) => (e, similarityTr(widget.nameOf(e), ad)))
        .where((e) => e.$2 >= 0.8)
        .toList()
      ..sort((a, b) => b.$2.compareTo(a.$2));
    if (benzer.isNotEmpty) {
      if (!mounted) return;
      final ekle = await _benzerUyari(ad, [
        for (final e in benzer.take(5)) (widget.nameOf(e.$1), e.$2),
      ]);
      if (ekle != true) return;
    }

    final res =
        await _api.saveCatalogItem(widget.path, body: widget.renameOf(ad));
    _after(res.error == null, res.error,
        okMessage: '${widget.labelField} eklendi.',
        errorText: 'Ekleme yapılamadı.');
  }

  /// K6.1: benzer kayıtları gösterip eklemeyi onaylatır.
  Future<bool?> _benzerUyari(String girilen, List<(String, double)> kayitlar) {
    return showDialog<bool>(
      context: context,
      builder: (dc) => AlertDialog(
        title: Text('Benzer ${widget.labelField.toLowerCase()} var'),
        content: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 460),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Girilen: "$girilen"'),
              const SizedBox(height: 8),
              const Text('Benzer kayıt(lar):'),
              for (final k in kayitlar)
                ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.warning_amber_rounded),
                  title: Text(k.$1),
                  subtitle: Text('Benzerlik: %${(k.$2 * 100).round()}'),
                ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dc).pop(false),
            child: const Text('Vazgeç'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dc).pop(true),
            child: const Text('Yine de ekle'),
          ),
        ],
      ),
    );
  }

  Future<void> _rename(T item) async {
    _renameController.text = widget.nameOf(item);
    final name = await _prompt(_renameController,
        '${widget.labelField} Düzenle', 'Yeni adı:');
    if (name == null || name.trim().isEmpty) return;
    final id = (item as dynamic).id as int;
    final res = await _api.saveCatalogItem(widget.path,
        id: id, body: widget.renameOf(name));
    _after(res.error == null, res.error,
        okMessage: 'Güncellendi.', errorText: 'Güncellenemedi.');
  }

  Future<void> _delete(T item) async {
    final id = (item as dynamic).id as int;
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text('${widget.labelField} sil'),
        content: Text(
            '${widget.nameOf(item)} silinecek. Kayıtlı kitap/nüsha varsa '
            'birleştirme kullanarak hedef taşıyın. Onaylıyor musunuz?'),
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
    final res = await _api.deleteCatalogItem(widget.path, id);
    _after(res.ok, res.error, okMessage: 'Silindi.', errorText: 'Silinemedi.');
  }

  Future<void> _merge(T item, List<T> all) async {
    final id = (item as dynamic).id as int;
    final others = all.where((e) => (e as dynamic).id != id).toList();
    if (others.isEmpty) return;
    int? hedefId = (others.first as dynamic).id as int;
    final saved = await showDialog<bool>(
      context: context,
      builder: (dc) => StatefulBuilder(
        builder: (dc, setLocal) => AlertDialog(
          title: Text('${widget.nameOf(item)} → hedefe birleştir'),
          content: DropdownButtonFormField<int>(
            initialValue: hedefId,
            isExpanded: true,
            decoration: const InputDecoration(
              labelText: 'Hedef',
              border: OutlineInputBorder(),
              isDense: true,
            ),
            items: [
              for (final o in others)
                DropdownMenuItem<int>(
                    value: (o as dynamic).id as int,
                    child: Text(widget.nameOf(o))),
            ],
            onChanged: (v) => setLocal(() => hedefId = v),
          ),
          actions: [
            TextButton(
                onPressed: () => Navigator.of(dc).pop(false),
                child: const Text('Vazgeç')),
            FilledButton(
                onPressed: () => Navigator.of(dc).pop(true),
                child: const Text('Birleştir')),
          ],
        ),
      ),
    );
    if (saved != true || hedefId == null) return;
    final res =
        await _api.mergeCatalogItems(widget.path, id, hedefId!);
    _after(res.ok, res.error,
        okMessage: 'Birleştirildi.', errorText: 'Birleştirilemedi.');
  }

  Future<String?> _prompt(TextEditingController controller, String title,
      String label) async {
    final saved = await showDialog<String>(
      context: context,
      builder: (dc) => AlertDialog(
        title: Text(title),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: InputDecoration(labelText: label, isDense: true),
          onSubmitted: (v) => Navigator.of(dc).pop(v),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.of(dc).pop(),
              child: const Text('Vazgeç')),
          FilledButton(
              onPressed: () => Navigator.of(dc).pop(controller.text),
              child: const Text('Kaydet')),
        ],
      ),
    );
    controller.clear();
    return saved;
  }

  void _after(bool ok, String? error,
      {required String okMessage, required String errorText}) {
    if (!mounted) return;
    if (ok) {
      setState(() => _future = _load());
      showAppSnack(context, okMessage);
    } else {
      showAppSnack(context, error ?? errorText, error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(24, 12, 24, 4),
          child: Row(
            children: [
              Expanded(
                child: Text('${widget.labelField} listesi',
                    style: theme.textTheme.bodySmall),
              ),
              FilledButton.icon(
                onPressed: _add,
                icon: const Icon(Icons.add, size: 18),
                label: Text('Yeni ${widget.labelField}'),
              ),
            ],
          ),
        ),
        Expanded(
          child: FutureBuilder<List<T>>(
            future: _future,
            builder: (context, snap) {
              if (snap.connectionState != ConnectionState.done) {
                return const Center(child: CircularProgressIndicator());
              }
              final items = snap.data ?? [];
              if (items.isEmpty) {
                return Center(
                    child: Text('${widget.labelField} kaydı yok.'));
              }
              return ListView.builder(
                padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
                itemCount: items.length,
                itemBuilder: (context, i) {
                  final item = items[i];
                  return Card(
                    margin: const EdgeInsets.symmetric(vertical: 4),
                    child: ListTile(
                      dense: true,
                      title: Text(widget.nameOf(item),
                          style: const TextStyle(fontWeight: FontWeight.w500)),
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          IconButton(
                            tooltip: 'Birleştir',
                            icon: const Icon(Icons.merge, size: 20),
                            onPressed: () => _merge(item, items),
                          ),
                          IconButton(
                            tooltip: 'Düzenle',
                            icon: const Icon(Icons.edit_outlined, size: 20),
                            onPressed: () => _rename(item),
                          ),
                          IconButton(
                            tooltip: 'Sil',
                            icon: const Icon(Icons.delete_outline, size: 20),
                            onPressed: () => _delete(item),
                          ),
                        ],
                      ),
                    ),
                  );
                },
              );
            },
          ),
        ),
      ],
    );
  }
}

class _DuplicateBooksTab extends StatefulWidget {
  const _DuplicateBooksTab();

  @override
  State<_DuplicateBooksTab> createState() => _DuplicateBooksTabState();
}

class _DuplicateBooksTabState extends State<_DuplicateBooksTab> {
  final _api = KutuphaneApi();
  late Future<List<Map<String, dynamic>>> _future;

  @override
  void initState() {
    super.initState();
    _future = _api.bookDuplicates(null);
  }

  Future<void> _mergeAll(List<dynamic> kitaplar, int hedefId) async {
    var okCount = 0;
    String? lastError;
    for (final k in kitaplar) {
      final sourceId = k['id'] as int;
      if (sourceId == hedefId) continue;
      final res = await _api.mergeBooks(sourceId, hedefId);
      if (res.ok) {
        okCount++;
      } else {
        lastError = res.error;
      }
    }
    if (!mounted) return;
    if (okCount == 0) {
      showAppSnack(context, lastError ?? 'Birleştirme yapılamadı.',
          error: true);
    } else {
      showAppSnack(context, '$okCount kayıt birleştirildi.');
    }
    setState(() => _future = _api.bookDuplicates(null));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return FutureBuilder<List<Map<String, dynamic>>>(
      future: _future,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final groups = snap.data ?? [];
        if (groups.isEmpty) {
          return Center(
              child: Text('Çift (kopya) kitap kaydı bulunmuyor.',
                  style: theme.textTheme.bodyMedium));
        }
        return ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Text(
                'Fold-normalize edilmiş başlıkta çakışan ${groups.length} grup bulundu. '
                    'Hedef kitabı seçip diğerleri o gruba birleştirilebilir. Geçmiş nüsha '
                    'bazında korunur.',
                style: theme.textTheme.bodySmall),
            const SizedBox(height: 8),
            for (final g in groups)
              Card(
                margin: const EdgeInsets.symmetric(vertical: 4),
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(g['anahtar'] as String? ?? '',
                          style: theme.textTheme.titleSmall
                              ?.copyWith(fontWeight: FontWeight.bold)),
                      const SizedBox(height: 4),
                      for (final k in g['kitaplar'] as List<dynamic>? ?? const [])
                        ListTile(
                          dense: true,
                          contentPadding: EdgeInsets.zero,
                          title: Text(k['baslik'] as String? ?? ''),
                          trailing: TextButton(
                            onPressed: () => _mergeAll(
                                (g['kitaplar'] as List<dynamic>? ?? const []),
                                k['id'] as int),
                            child: const Text('Buna birleştir'),
                          ),
                        ),
                    ],
                  ),
                ),
              ),
          ],
        );
      },
    );
  }
}