import 'dart:async';

import 'package:flutter/material.dart';

import '../api/kutuphane_api.dart';
import '../formatters.dart';
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

  /// K6.6 (revize): kitap girişinde yeni yazar ekleme (tüm personel).
  /// K6.1: fold-normalize kopya uyarısı; benzer kayıt varsa mevcut kullanılır.
  Future<void> _yeniYazar() async {
    final controller = TextEditingController();
    final ad = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Yeni yazar ekle'),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration:
              const InputDecoration(labelText: 'Ad Soyad', isDense: true),
          onSubmitted: (v) => Navigator.of(ctx).pop(v),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Vazgeç'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(controller.text),
            child: const Text('Ekle'),
          ),
        ],
      ),
    );
    final adSoyad = (ad ?? '').trim();
    controller.dispose();
    if (adSoyad.isEmpty) return;

    // K6.1: %100 aynı (normalize) kayıt varsa ekleme; mevcut seçilir.
    final norm = normalizeTr(adSoyad);
    final ayni = _yazarlar.where((y) => normalizeTr(y.adSoyad) == norm).toList();
    if (ayni.isNotEmpty) {
      if (!mounted) return;
      setState(() => _yazarId = ayni.first.id);
      _snack('"${ayni.first.adSoyad}" zaten kayıtlı; mevcut kayıt seçildi.');
      return;
    }

    // K6.1: çok benzer kayıt(lar) varsa gösterip sor.
    final benzer = _yazarlar
        .map((y) => (y, similarityTr(y.adSoyad, adSoyad)))
        .where((e) => e.$2 >= 0.8)
        .toList()
      ..sort((a, b) => b.$2.compareTo(a.$2));
    if (benzer.isNotEmpty) {
      if (!mounted) return;
      final secim = await _benzerKayitUyari(
        baslik: 'Benzer yazar var',
        girilen: adSoyad,
        kayitlar: [for (final e in benzer.take(5)) (e.$1.adSoyad, e.$2)],
      );
      if (secim == 'mevcut') {
        setState(() => _yazarId = benzer.first.$1.id);
        return;
      }
      if (secim != 'ekle') return;
    }

    setState(() => _busy = true);
    final res =
        await _api.saveCatalogItem('yazarlar/', body: {'ad_soyad': adSoyad});
    if (!mounted) return;
    setState(() => _busy = false);
    if (res.id == null) {
      _snack(res.error ?? 'Yazar eklenemedi.');
      return;
    }
    final yeniId = res.id!;
    try {
      final liste = await _api.yazarlar();
      if (!mounted) return;
      setState(() {
        _yazarlar = liste;
        _yazarId = yeniId;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _yazarlar = [..._yazarlar, Yazar(id: yeniId, adSoyad: adSoyad)];
        _yazarId = yeniId;
      });
    }
    _snack('Yazar eklendi: $adSoyad');
  }

  /// K6.1: benzer kayıtları gösterip "mevcut / yine de ekle / vazgeç" sorar.
  Future<String?> _benzerKayitUyari({
    required String baslik,
    required String girilen,
    required List<(String, double)> kayitlar,
  }) {
    return showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(baslik),
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
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Vazgeç'),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop('ekle'),
            child: const Text('Yine de ekle'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop('mevcut'),
            child: const Text('Mevcudu kullan'),
          ),
        ],
      ),
    );
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
    final isbn = _isbnController.text.trim();
    if (q.length < 3 && isbn.isEmpty) {
      _snack('Arama için en az 3 karakter veya bir ISBN girin.');
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
    final res = await _api.bookLookup(q, isbn: isbn);
    if (!mounted) return;
    setState(() => _busy = false);
    if (res.results.isEmpty) {
      _snack(res.error ?? 'Sonuç bulunamadı.');
      return;
    }
    final secili = res.results.length == 1
        ? res.results.first
        : await _sonucSec(res.results);
    if (secili == null || !mounted) return;
    _sonucuUygula(secili);
  }

  /// K7.1: arama sonuçlarını kapak resimli liste olarak sunar; seçilen döner.
  Future<Map<String, dynamic>?> _sonucSec(
    List<Map<String, dynamic>> results,
  ) {
    return showDialog<Map<String, dynamic>>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Arama sonuçları'),
        content: SizedBox(
          width: 540,
          height: 400,
          child: ListView.separated(
            itemCount: results.length,
            separatorBuilder: (_, _) => const Divider(height: 1),
            itemBuilder: (ctx, i) {
              final r = results[i];
              final yazar = (r['yazar'] as String? ?? '').trim();
              final yil = r['yayin_yili'];
              final kaynak = (r['kaynak'] as String? ?? '').trim();
              return ListTile(
                leading: _kapakKucuk(ctx, (r['kapak_url'] as String?)?.trim()),
                title: Text((r['baslik'] as String? ?? '').trim()),
                subtitle: Text([
                  if (yazar.isNotEmpty) yazar,
                  if (yil != null) '$yil',
                  if (kaynak.isNotEmpty) kaynak,
                ].join(' · ')),
                onTap: () => Navigator.of(ctx).pop(r),
              );
            },
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Vazgeç'),
          ),
        ],
      ),
    );
  }

  Widget _kapakKucuk(BuildContext context, String? url) {
    const bos = SizedBox(
      width: 40,
      height: 56,
      child: Icon(Icons.menu_book_rounded),
    );
    if (url == null || url.isEmpty) return bos;
    return GestureDetector(
      onTap: () => _buyukOnizleme(context, url),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(4),
        child: Image.network(
          url,
          width: 40,
          height: 56,
          fit: BoxFit.cover,
          errorBuilder: (_, _, _) => bos,
        ),
      ),
    );
  }

  /// Kapak resmini büyük, yakınlaştırılabilir bir pencerede gösterir.
  void _buyukOnizleme(BuildContext context, String url) {
    showDialog<void>(
      context: context,
      builder: (ctx) => Dialog(
        insetPadding: const EdgeInsets.all(24),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 720, maxHeight: 720),
          child: Stack(
            alignment: Alignment.center,
            children: [
              InteractiveViewer(
                minScale: 0.5,
                maxScale: 4,
                child: Image.network(
                  url,
                  fit: BoxFit.contain,
                  errorBuilder: (_, _, _) => Padding(
                    padding: const EdgeInsets.all(24),
                    child: Text(
                      'Kapak görseli yüklenemedi.',
                      style: TextStyle(color: dangerColor(ctx)),
                    ),
                  ),
                ),
              ),
              Positioned(
                top: 0,
                right: 0,
                child: IconButton(
                  icon: const Icon(Icons.close),
                  tooltip: 'Kapat',
                  onPressed: () => Navigator.of(ctx).pop(),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _sonucuUygula(Map<String, dynamic> r) {
    setState(() {
      // Akıllı birleştir (K7.5): kaynak alanı boşsa kullanıcının girdiği
      // değer korunur, doluysa gelen değer yazılır. Düzenleme modunda mevcut
      // veriler boş değerle silinmez.
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

  /// K7.4: kapak adresi doluysa görseli önizlemede gösterir.
  Widget _kapakOnizleme(BuildContext context) {
    return ValueListenableBuilder<TextEditingValue>(
      valueListenable: _kapakController,
      builder: (context, value, _) {
        final url = value.text.trim();
        if (url.isEmpty) return const SizedBox.shrink();
        return Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Align(
            alignment: Alignment.centerLeft,
            child: Tooltip(
              message: 'Büyük önizleme için tıkla',
              child: GestureDetector(
                onTap: () => _buyukOnizleme(context, url),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: Image.network(
                    url,
                    height: 160,
                    fit: BoxFit.contain,
                    errorBuilder: (_, _, _) => Text(
                      'Kapak görseli yüklenemedi.',
                      style:
                          TextStyle(color: dangerColor(context), fontSize: 12),
                    ),
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
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
                  Row(children: [
                    Expanded(
                      child: DropdownButtonFormField<int>(
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
                    ),
                    const SizedBox(width: 8),
                    IconButton.filledTonal(
                      tooltip: 'Yeni yazar ekle',
                      onPressed: _busy ? null : _yeniYazar,
                      icon: const Icon(Icons.person_add_alt_1),
                    ),
                  ]),
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
                _kapakOnizleme(context),
                const Divider(height: 24),
                Row(children: [
                  Expanded(
                    child: TextField(
                      controller: _googleController,
                      decoration: const InputDecoration(
                        hintText: 'Kitap ara (başlık / yazar / ISBN)...',
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