import 'dart:async';

import 'package:flutter/material.dart';

import '../api/kutuphane_api.dart';
import '../models.dart';
import '../theme.dart';

/// Yeni kitap ekle / kitap düzenle formu.
/// Google Books'tan otomatik doldurma ve benzer kayıt uyarısı içerir.
/// Kaydedilen kitabı `Navigator.pop` ile döndürür.
class BookFormDialog extends StatefulWidget {
  final Kitap? kitap;

  const BookFormDialog({super.key, this.kitap});

  @override
  State<BookFormDialog> createState() => _BookFormDialogState();
}

class _BookFormDialogState extends State<BookFormDialog> {
  final _api = KutuphaneApi();
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _baslik;
  final _yilController = TextEditingController();
  final _isbnController = TextEditingController();
  final _aciklamaController = TextEditingController();
  final _kapakController = TextEditingController();
  final _googleController = TextEditingController();

  List<Yazar> _yazarlar = [];
  List<Kategori> _kategoriler = [];
  int? _yazarId;
  int? _kategoriId;

  bool _busy = false;
  bool _loading = true;
  String? _yazarOneri;
  List<Kitap> _benzerler = [];
  Timer? _debounce;
  DateTime? _sonGoogle;

  bool get _editing => widget.kitap != null;

  @override
  void initState() {
    super.initState();
    final k = widget.kitap;
    _baslik = TextEditingController(text: k?.baslik ?? '');
    _yilController.text = k?.yayinYili?.toString() ?? '';
    _isbnController.text = k?.isbn ?? '';
    _aciklamaController.text = k?.aciklama ?? '';
    _kapakController.text = k?.kapakUrl ?? '';
    _yazarId = k?.yazar?.id;
    _kategoriId = k?.kategori?.id;
    _load();
    _baslik.addListener(_onBaslikChanged);
  }

  Future<void> _load() async {
    try {
      final results = await Future.wait([_api.yazarlar(), _api.kategoriler()]);
      if (!mounted) return;
      setState(() {
        _yazarlar = results[0] as List<Yazar>;
        _kategoriler = results[1] as List<Kategori>;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _loading = false);
    }
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _baslik.dispose();
    _yilController.dispose();
    _isbnController.dispose();
    _aciklamaController.dispose();
    _kapakController.dispose();
    _googleController.dispose();
    super.dispose();
  }

  void _onBaslikChanged() {
    if (_editing) return;
    _debounce?.cancel();
    final q = _baslik.text.trim();
    if (q.length < 3) {
      setState(() => _benzerler = []);
      return;
    }
    _debounce = Timer(const Duration(milliseconds: 600), () async {
      final page = await _api.booksPage(page: 1, pageSize: 5, q: q);
      if (!mounted) return;
      setState(() => _benzerler = page.items);
    });
  }

  Future<void> _googleDoldur() async {
    final q = _googleController.text.trim();
    if (q.length < 3) {
      _snack('Google araması için en az 3 karakter girin.');
      return;
    }
    // K7.5: ardışık aramalar arasında en az 3 sn bekleyin (kota dostu).
    final now = DateTime.now();
    if (_sonGoogle != null && now.difference(_sonGoogle!).inSeconds < 3) {
      _snack('Aramalar arasında kısa bir süre bekleyin.');
      return;
    }
    _sonGoogle = now;
    setState(() => _busy = true);
    final res = await _api.googleBook(q);
    if (!mounted) return;
    setState(() => _busy = false);
    if (res.results.isEmpty) {
      _snack(res.error ?? 'Sonuç bulunamadı.');
      return;
    }
    final r = res.results.first;
    setState(() {
      // Akıllı birleştir (K7.5): Google alanı boşsa kullanıcının girdiği
      // değer korunur, doluysa Google değeri yazılır. Başlık hariç düzenleme
      // modunda mevcut veriler silinmez.
      final gBaslik = (r['baslik'] as String? ?? '').trim();
      final gIsbn = (r['isbn'] as String? ?? '').trim();
      final gAciklama = (r['aciklama'] as String? ?? '').trim();
      final gKapak = (r['kapak_url'] as String? ?? '').trim();
      if (gBaslik.isNotEmpty) _baslik.text = gBaslik;
      if (gIsbn.isNotEmpty) _isbnController.text = gIsbn;
      if (gAciklama.isNotEmpty) _aciklamaController.text = gAciklama;
      if (gKapak.isNotEmpty) _kapakController.text = gKapak;
      final yil = r['yayin_yili'] as int?;
      if (yil != null) _yilController.text = yil.toString();
      final onerilen = (r['yazar'] as String? ?? '').trim();
      yazarOneri = onerilen;
      if (onerilen.isNotEmpty) {
        final eslesen = _yazarlar.where((y) =>
            y.adSoyad.toLowerCase() == onerilen.toLowerCase() ||
            foldLite(y.adSoyad) == foldLite(onerilen));
        _yazarId = eslesen.isNotEmpty ? eslesen.first.id : null;
      }
    });
  }

  String foldLite(String s) => s
      .toLowerCase()
      .replaceAll(RegExp('[şŞ]'), 's')
      .replaceAll('ı', 'i')
      .replaceAll('ğ', 'g')
      .replaceAll('ü', 'u')
      .replaceAll('ö', 'o')
      .replaceAll('ç', 'c')
      .trim();

  void _snack(String msg) {
    if (!mounted) return;
    showAppSnack(context, msg);
  }

  Future<void> _save({bool force = false}) async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _busy = true);
    final res = await _api.saveBook(
      id: widget.kitap?.id,
      baslik: _baslik.text,
      yayinYili: int.tryParse(_yilController.text.trim()),
      isbn: _isbnController.text,
      aciklama: _aciklamaController.text,
      kapakUrl: _kapakController.text.isEmpty ? null : _kapakController.text,
      yazarId: _yazarId,
      kategoriId: _kategoriId,
      force: force,
    );
    if (!mounted) return;
    if (res.kitap != null) {
      Navigator.of(context).pop(res.kitap);
      return;
    }
    if (!_editing && res.benzerler.isNotEmpty) {
      setState(() => _busy = false);
      await _benzerUyari(
        benzerler: res.benzerler,
        isbnEslesme: res.isbnEslesme,
        hata: res.error ?? 'Bu kitapla eşleşen bir kayıt zaten var.',
      );
      return;
    }
    setState(() => _busy = false);
    _snack(res.error ?? 'Kayıt yapılamadı.');
  }

  Future<void> _benzerUyari({
    required List<BenzerKitapDetay> benzerler,
    required bool isbnEslesme,
    required String hata,
  }) async {
    final hedef = benzerler.first;
    final secim = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(
          isbnEslesme ? 'Aynı ISBN ile kayıtlı kitap var' : 'Benzer kitap zaten kayıtlı',
        ),
        content: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 460),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              for (final b in benzerler)
                ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.menu_book_rounded),
                  title: Text(b.baslik),
                  subtitle: Text('Nüsha sayısı: ${b.nushaSayisi}'),
                ),
              const SizedBox(height: 4),
              Text(hata,
                  style: TextStyle(color: dangerColor(context), fontSize: 12)),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop('iptal'),
            child: const Text('Vazgeç'),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop('ayrik'),
            child: const Text('Yine de ayrı kayıt oluştur'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop('nusha'),
            child: Text(isbnEslesme ? 'Mevcuda nüsha ekle' : 'Bu kitaba nüsha ekle'),
          ),
        ],
      ),
    );
    if (!mounted) return;
    switch (secim) {
      case 'nusha':
        final r = await _api.addCopy(hedef.id);
        if (!mounted) return;
        if (r.nusha != null) {
          _snack(
            'Nüsha eklendi${r.nusha!.barkod.isNotEmpty ? ' (${r.nusha!.barkod})' : ''}.',
          );
          Navigator.of(context).pop();
        } else {
          _snack(r.error ?? 'Nüsha eklenemedi.');
        }
      case 'ayrik':
        await _save(force: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(_editing ? 'Kitap Düzenle' : 'Yeni Kitap'),
      content: SizedBox(
        width: 520,
        child: SingleChildScrollView(
          child: Form(
            key: _formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (_benzerler.isNotEmpty) ...[
                  Card(
                    color: layerColor(context, warningColor(context)),
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(children: [
                            Icon(Icons.warning_amber_rounded,
                                color: warningColor(context)),
                            const SizedBox(width: 8),
                            Text('Benzer kayıt(lar) bulundu:',
                                style: TextStyle(
                                    fontWeight: FontWeight.bold,
                                    color: warningColor(context))),
                          ]),
                          for (final b in _benzerler)
                            Text('• ${b.baslik}${b.yazar != null ? ' (${b.yazar!.adSoyad})' : ''}',
                                style: const TextStyle(fontSize: 13)),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                ],
                TextFormField(
                  controller: _baslik,
                  autofocus: !_editing,
                  decoration: const InputDecoration(
                    labelText: 'Başlık',
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                  validator: (v) =>
                      (v == null || v.trim().isEmpty) ? 'Başlık gerekli.' : null,
                ),
                const SizedBox(height: 12),
                if (_loading)
                  const SizedBox(
                      height: 56,
                      child: Center(child: CircularProgressIndicator(strokeWidth: 2)))
                else ...[
                  DropdownButtonFormField<int>(
                    initialValue: _yazarId,
                    isExpanded: true,
                    decoration: const InputDecoration(
                      labelText: 'Yazar',
                      border: OutlineInputBorder(),
                      isDense: true,
                    ),
                    items: [
                      const DropdownMenuItem<int>(
                          value: null, child: Text('— yazar seç —')),
                      for (final y in _yazarlar)
                        DropdownMenuItem<int>(
                            value: y.id, child: Text(y.adSoyad)),
                    ],
                    onChanged: _busy
                        ? null
                        : (v) => setState(() => _yazarId = v),
                  ),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<int>(
                    initialValue: _kategoriId,
                    isExpanded: true,
                    decoration: const InputDecoration(
                      labelText: 'Kategori',
                      border: OutlineInputBorder(),
                      isDense: true,
                    ),
                    items: [
                      const DropdownMenuItem<int>(
                          value: null, child: Text('— kategori seç —')),
                      for (final k in _kategoriler)
                        DropdownMenuItem<int>(
                            value: k.id, child: Text(k.ad)),
                    ],
                    onChanged: _busy
                        ? null
                        : (v) => setState(() => _kategoriId = v),
                  ),
                ],
                if (_yazarOneri != null) ...[
                  const SizedBox(height: 8),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: Text('Yazar önerisi: $_yazarOneri',
                        style: TextStyle(
                            fontSize: 12,
                            color: Theme.of(context)
                                .colorScheme
                                .onSurfaceVariant)),
                  ),
                ],
                const SizedBox(height: 12),
                Row(children: [
                  Expanded(
                    flex: 3,
                    child: TextFormField(
                      controller: _yilController,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Yayın Yılı',
                        border: OutlineInputBorder(),
                        isDense: true,
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    flex: 5,
                    child: TextFormField(
                      controller: _isbnController,
                      decoration: const InputDecoration(
                        labelText: 'ISBN',
                        border: OutlineInputBorder(),
                        isDense: true,
                      ),
                    ),
                  ),
                ]),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _aciklamaController,
                  maxLines: 3,
                  minLines: 2,
                  decoration: const InputDecoration(
                    labelText: 'Açıklama',
                    border: OutlineInputBorder(),
                    isDense: true,
                    alignLabelWithHint: true,
                  ),
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _kapakController,
                  decoration: const InputDecoration(
                    labelText: 'Kapak Görsel URL (isteğe bağlı)',
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                ),
                const Divider(height: 24),
                Row(children: [
                  Expanded(
                    child: TextField(
                      controller: _googleController,
                      decoration: const InputDecoration(
                        hintText: 'Google Books araması...',
                        prefixIcon: Icon(Icons.travel_explore),
                        border: OutlineInputBorder(),
                        isDense: true,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  FilledButton.tonalIcon(
                    onPressed: _busy ? null : _googleDoldur,
                    icon: const Icon(Icons.auto_fix_high, size: 18),
                    label: const Text('Doldur'),
                  ),
                ]),
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _busy ? null : () => Navigator.of(context).pop(),
          child: const Text('Vazgeç'),
        ),
        FilledButton(
          onPressed: _busy ? null : _save,
          child: _busy
              ? const SizedBox(
                  height: 18,
                  width: 18,
                  child: CircularProgressIndicator(strokeWidth: 2))
              : const Text('Kaydet'),
        ),
      ],
    );
  }

  set yazarOneri(String? v) => _yazarOneri = v;
}