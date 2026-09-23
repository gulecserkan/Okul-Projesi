import 'package:flutter/material.dart';

import '../api/library_api.dart';
import '../models/auth.dart';
import '../models/book.dart';
import 'image_gallery_screen.dart';

/// K9: Üye (öğrenci/öğretmen) ekranı — salt-okunur.
/// Kitaplarda gezinti/arama + kendi ödünç geçmişi + ceza bakiyesi.
/// Düzenleme ve ödünç/iade işlemleri yoktur.
class UyeHomeScreen extends StatefulWidget {
  const UyeHomeScreen({
    super.key,
    required this.baseUrl,
    required this.tokens,
    required this.onLogout,
    required this.onChangeServer,
    this.onSessionExpired,
    this.api,
  });

  final String baseUrl;
  final AuthTokens tokens;
  final Future<void> Function() onLogout;
  final Future<void> Function() onChangeServer;
  final void Function()? onSessionExpired;

  /// Test/DI için dışarıdan verilebilir.
  final LibraryApiClient? api;

  @override
  State<UyeHomeScreen> createState() => _UyeHomeScreenState();
}

class _UyeHomeScreenState extends State<UyeHomeScreen> {
  late final LibraryApiClient _api;
  final _searchController = TextEditingController();

  List<BookSummary> _books = [];
  bool _loadingBooks = false;
  String? _booksError;

  List<Map<String, dynamic>> _loans = [];
  bool _loadingLoans = false;
  String? _loansError;

  Map<String, dynamic> _ceza = {};
  bool _loadingCeza = false;
  String? _cezaError;

  @override
  void initState() {
    super.initState();
    _api = widget.api ??
        LibraryApiClient(
          baseUrl: widget.baseUrl,
          tokens: widget.tokens,
          onUnauthorized: widget.onSessionExpired,
        );
    _loadBooks();
    _loadLoans();
    _loadCeza();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadBooks() async {
    setState(() {
      _loadingBooks = true;
      _booksError = null;
    });
    try {
      final res = await _api.fetchBooks(query: _searchController.text.trim());
      if (!mounted) return;
      setState(() {
        _books = res.books;
        _loadingBooks = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _booksError = e is ApiException ? e.message : e.toString();
        _loadingBooks = false;
      });
    }
  }

  Future<void> _loadLoans() async {
    final no = widget.tokens.uyeNo;
    if (no == null || no.isEmpty) {
      setState(() => _loadingLoans = false);
      return;
    }
    setState(() {
      _loadingLoans = true;
      _loansError = null;
    });
    try {
      final list = await _api.fetchUyeGecmis(no);
      if (!mounted) return;
      setState(() {
        _loans = list;
        _loadingLoans = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loansError = e is ApiException ? e.message : e.toString();
        _loadingLoans = false;
      });
    }
  }

  Future<void> _loadCeza() async {
    final no = widget.tokens.uyeNo;
    if (no == null || no.isEmpty) {
      setState(() => _loadingCeza = false);
      return;
    }
    setState(() {
      _loadingCeza = true;
      _cezaError = null;
    });
    try {
      final data = await _api.fetchUyeCeza(no);
      if (!mounted) return;
      setState(() {
        _ceza = data;
        _loadingCeza = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _cezaError = e is ApiException ? e.message : e.toString();
        _loadingCeza = false;
      });
    }
  }

  Future<void> _openBook(BookSummary b) async {
    try {
      final d = await _api.fetchBookDetail(b.id);
      if (!mounted) return;
      showDialog<void>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text(d.baslik),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _imageStrip(d),
                if ((d.yazar ?? '').isNotEmpty) Text('Yazar: ${d.yazar}'),
                if ((d.kategori ?? '').isNotEmpty) Text('Kategori: ${d.kategori}'),
                if (d.yayinYili != null) Text('Yayın yılı: ${d.yayinYili}'),
                if ((d.isbn ?? '').isNotEmpty) Text('ISBN: ${d.isbn}'),
                if (d.shelfCodes.isNotEmpty) Text('Raf: ${d.shelfCodes.join(', ')}'),
                if ((d.aciklama ?? '').isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Text(d.aciklama!),
                ],
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Kapat'),
            ),
          ],
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Kitap açılamadı: $e')),
      );
    }
  }

  /// Kitabın gösterilecek resimleri: dış kapak (varsa) + yüklenen resimler.
  List<BookImageSlot> _bookImages(BookDetail d) {
    final list = <BookImageSlot>[];
    if ((d.kapakUrl ?? '').isNotEmpty) {
      list.add(BookImageSlot(index: 0, url: d.kapakUrl));
    }
    list.addAll(d.resimler.where((s) => s.hasImage));
    return list;
  }

  Widget _imageStrip(BookDetail d) {
    final images = _bookImages(d);
    if (images.isEmpty) return const SizedBox.shrink();
    final scheme = Theme.of(context).colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.photo_library_outlined, size: 18, color: scheme.primary),
            const SizedBox(width: 6),
            Text(
              'Resimler',
              style: Theme.of(context)
                  .textTheme
                  .titleSmall
                  ?.copyWith(fontWeight: FontWeight.bold),
            ),
            const Spacer(),
            Text(
              '${images.length}',
              style: TextStyle(fontSize: 12, color: scheme.outline),
            ),
          ],
        ),
        const SizedBox(height: 6),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: [
              for (var i = 0; i < images.length; i++) ...[
                if (i > 0) const SizedBox(width: 8),
                _imageThumb(images[i], images, scheme),
              ],
            ],
          ),
        ),
        const SizedBox(height: 10),
      ],
    );
  }

  GestureDetector _imageThumb(
    BookImageSlot slot,
    List<BookImageSlot> images,
    ColorScheme scheme,
  ) {
    return GestureDetector(
      onTap: () {
        Navigator.of(context).push(
          MaterialPageRoute<void>(
            builder: (_) => ImageGalleryScreen(
              images: images,
              initialIndex: slot.index,
            ),
          ),
        );
      },
      child: Container(
        width: 100,
        height: 150,
        clipBehavior: Clip.antiAlias,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(8),
          color: scheme.surfaceContainerHighest,
        ),
        child: Image.network(
          slot.url!,
          fit: BoxFit.cover,
          errorBuilder: (_, _, _) => _imagePlaceholder(scheme),
        ),
      ),
    );
  }

  Widget _imagePlaceholder(ColorScheme scheme) {
    return Container(
      width: 100,
      color: scheme.surfaceContainerHighest,
      child: Center(
        child: Icon(Icons.image_not_supported_outlined, color: scheme.outline),
      ),
    );
  }

  String _loanTitle(Map<String, dynamic> r) {
    final nusha = r['kitap_nusha'];
    if (nusha is Map<String, dynamic>) {
      final kitap = nusha['kitap'];
      if (kitap is Map<String, dynamic>) {
        return (kitap['baslik'] ?? '').toString();
      }
      if (nusha['kitap_baslik'] != null) return nusha['kitap_baslik'].toString();
    }
    return (r['kitap_baslik'] ?? 'Kitap').toString();
  }

  String _shortDate(dynamic iso) {
    final s = (iso ?? '').toString();
    if (s.length >= 10) return s.substring(0, 10);
    return s.isEmpty ? '—' : s;
  }

  String _durumLabel(String d) {
    switch (d) {
      case 'oduncte':
        return 'Ödünçte';
      case 'gecikmis':
        return 'Gecikmiş';
      case 'teslim':
        return 'Teslim';
      case 'kayip':
        return 'Kayıp';
      case 'hasarli':
        return 'Hasarlı';
      case 'iptal':
        return 'İptal';
      case 'mevcut':
        return 'Mevcut';
      default:
        return d.isEmpty ? '—' : d;
    }
  }

  /// iade_tarihi'ne kalan gün / gecikme metni.
  String _daysLeft(dynamic iso) {
    final s = (iso ?? '').toString();
    final due = DateTime.tryParse(s);
    if (due == null) return '';
    final diff = due.difference(DateTime.now());
    final days = diff.inDays;
    return days < 0 ? '${-days} gün gecikti' : '$days gün kaldı';
  }

  bool _isActiveLoan(Map<String, dynamic> r) {
    final durum = (r['durum'] ?? '').toString();
    return durum == 'oduncte' || durum == 'gecikmis';
  }

  bool _isOverdue(Map<String, dynamic> r) {
    final durum = (r['durum'] ?? '').toString();
    if (durum == 'gecikmis') return true;
    final due = DateTime.tryParse((r['iade_tarihi'] ?? '').toString());
    if (due == null) return false;
    return due.isBefore(DateTime.now());
  }

  /// K9.8: üye ekranındaki küçük aksiyon — ikon + metin.
  /// AppBar başlığı: üye adı+soyadı (üye no); "Kütüphane" arka planda (alt satır)
  /// uygulama adı olarak görünür.
  Widget _buildAppBarTitle() {
    final t = widget.tokens;
    final name = (t.fullName ?? '').trim();
    final no = (t.uyeNo ?? '').trim();
    final mainLabel = name.isNotEmpty
        ? (no.isNotEmpty ? '$name ($no)' : name)
        : (no.isNotEmpty ? no : 'Kütüphane');
    final scheme = Theme.of(context).colorScheme;
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          mainLabel,
          overflow: TextOverflow.ellipsis,
          style: Theme.of(context)
              .textTheme
              .titleMedium
              ?.copyWith(fontWeight: FontWeight.w600),
        ),
        Text(
          'Kütüphane',
          style: Theme.of(context)
              .textTheme
              .labelSmall
              ?.copyWith(color: scheme.onSurfaceVariant),
        ),
      ],
    );
  }

  Widget _actionButton({
    required IconData icon,
    required String label,
    required VoidCallback onPressed,
  }) {
    final scheme = Theme.of(context).colorScheme;
    return InkWell(
      onTap: onPressed,
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 20, color: scheme.onSurfaceVariant),
            const SizedBox(height: 2),
            Text(
              label,
              style: TextStyle(
                fontSize: 10,
                color: scheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _showChangePasswordDialog() async {
    final currentCtrl = TextEditingController();
    final newCtrl = TextEditingController();
    final confirmCtrl = TextEditingController();
    String? error;
    bool loading = false;

    await showDialog(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setStateDialog) {
            return AlertDialog(
              title: const Text('Şifre değiştir'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: currentCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Mevcut şifre',
                      prefixIcon: Icon(Icons.lock_clock_outlined),
                    ),
                    obscureText: true,
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: newCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Yeni şifre',
                      prefixIcon: Icon(Icons.lock_outline),
                    ),
                    obscureText: true,
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: confirmCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Yeni şifre (tekrar)',
                      prefixIcon: Icon(Icons.lock_outline),
                    ),
                    obscureText: true,
                  ),
                  if (error != null) ...[
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        const Icon(Icons.error_outline, color: Colors.red),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            error!,
                            style: const TextStyle(color: Colors.red),
                          ),
                        ),
                      ],
                    ),
                  ],
                ],
              ),
              actions: [
                TextButton(
                  onPressed:
                      loading ? null : () => Navigator.of(context).pop(),
                  child: const Text('Vazgeç'),
                ),
                ElevatedButton(
                  onPressed: loading
                      ? null
                      : () async {
                          final current = currentCtrl.text.trim();
                          final newPass = newCtrl.text.trim();
                          final confirm = confirmCtrl.text.trim();
                          if (current.isEmpty || newPass.isEmpty || confirm.isEmpty) {
                            setStateDialog(() => error = 'Tüm alanlar zorunlu.');
                            return;
                          }
                          if (newPass != confirm) {
                            setStateDialog(() => error = 'Yeni şifreler uyuşmuyor.');
                            return;
                          }
                          setStateDialog(() {
                            loading = true;
                            error = null;
                          });
                          try {
                            await _api.changePassword(
                              currentPassword: current,
                              newPassword: newPass,
                              newPasswordConfirm: confirm,
                            );
                            if (!context.mounted) return;
                            Navigator.of(context).pop();
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text('Şifre güncellendi.')),
                            );
                          } catch (e) {
                            setStateDialog(() {
                              error = e.toString();
                              loading = false;
                            });
                          }
                        },
                  child: loading
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Kaydet'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: _buildAppBarTitle(),
          actions: [
            _actionButton(
              icon: Icons.key_outlined,
              label: 'Şifre',
              onPressed: _showChangePasswordDialog,
            ),
            _actionButton(
              icon: Icons.dns_outlined,
              label: 'Sunucu',
              onPressed: () => widget.onChangeServer(),
            ),
            _actionButton(
              icon: Icons.logout,
              label: 'Çıkış',
              onPressed: () => widget.onLogout(),
            ),
          ],
          bottom: const TabBar(
            tabs: [
              Tab(icon: Icon(Icons.menu_book_outlined), text: 'Kitaplar'),
              Tab(icon: Icon(Icons.history), text: 'Ödünçlerim'),
              Tab(icon: Icon(Icons.paid_outlined), text: 'Ceza'),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            _buildBooksTab(),
            _buildLoansTab(),
            _buildPenaltyTab(),
          ],
        ),
      ),
    );
  }

  Widget _buildBooksTab() {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(12),
          child: TextField(
            controller: _searchController,
            textInputAction: TextInputAction.search,
            onSubmitted: (_) => _loadBooks(),
            decoration: InputDecoration(
              hintText: 'Kitap ara (başlık / yazar / ISBN)...',
              prefixIcon: const Icon(Icons.search),
              suffixIcon: IconButton(
                icon: const Icon(Icons.clear),
                onPressed: () {
                  _searchController.clear();
                  _loadBooks();
                },
              ),
              border: const OutlineInputBorder(),
              isDense: true,
            ),
          ),
        ),
        if (_loadingBooks)
          const Expanded(child: Center(child: CircularProgressIndicator()))
        else if (_booksError != null)
          Expanded(child: Center(child: Text('Kitaplar yüklenemedi.\n$_booksError')))
        else if (_books.isEmpty)
          const Expanded(child: Center(child: Text('Sonuç bulunamadı.')))
        else
          Expanded(
            child: RefreshIndicator(
              onRefresh: _loadBooks,
              child: ListView.builder(
                itemCount: _books.length,
                itemBuilder: (context, i) {
                  final b = _books[i];
                  return ListTile(
                    leading: const Icon(Icons.menu_book_rounded),
                    title: Text(b.baslik),
                    subtitle: Text([
                      if ((b.yazar ?? '').isNotEmpty) b.yazar!,
                      if (b.yayinYili != null) '${b.yayinYili}',
                      if ((b.kategori ?? '').isNotEmpty) b.kategori!,
                    ].join(' · ')),
                    onTap: () => _openBook(b),
                  );
                },
              ),
            ),
          ),
      ],
    );
  }

  Widget _loanTile(Map<String, dynamic> r) {
    final durum = (r['durum'] ?? '').toString();
    final label = _durumLabel(durum);
    final overdue = _isOverdue(r);
    final scheme = Theme.of(context).colorScheme;

    final subtitleParts = [
      'Ödünç: ${_shortDate(r['odunc_tarihi'])} · '
          'İade: ${_shortDate(r['iade_tarihi'])}',
    ];
    if (_isActiveLoan(r)) {
      subtitleParts.add(_daysLeft(r['iade_tarihi']));
    }

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: ListTile(
        title: Text(_loanTitle(r)),
        subtitle: Text(subtitleParts.join('\n')),
        trailing: Chip(
          label: Text(label),
          visualDensity: VisualDensity.compact,
          backgroundColor: overdue
              ? scheme.errorContainer
              : _isActiveLoan(r)
                  ? scheme.primaryContainer
                  : scheme.surfaceContainerHighest,
          labelStyle: TextStyle(
            color: overdue ? scheme.onErrorContainer : scheme.onSurface,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );
  }

  Widget _buildLoansTab() {
    if (widget.tokens.uyeNo == null || widget.tokens.uyeNo!.isEmpty) {
      return const Center(child: Text('Ödünç bilgisi için hesabınızda numara yok.'));
    }
    if (_loadingLoans) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_loansError != null) {
      return Center(child: Text('Ödünçler yüklenemedi.\n$_loansError'));
    }
    if (_loans.isEmpty) {
      return const Center(child: Text('Kayıtlı ödünç yok.'));
    }

    final active = _loans.where(_isActiveLoan).toList();
    final past = _loans.where((r) => !_isActiveLoan(r)).toList();

    return RefreshIndicator(
      onRefresh: _loadLoans,
      child: ListView(
        children: [
          if (active.isNotEmpty) ...[
            _sectionHeader('Aktif'),
            ...active.map(_loanTile),
          ],
          if (past.isNotEmpty) ...[
            _sectionHeader('Geçmiş'),
            ...past.map(_loanTile),
          ],
        ],
      ),
    );
  }

  Widget _sectionHeader(String text) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 4),
      child: Text(
        text,
        style: Theme.of(context)
            .textTheme
            .titleSmall
            ?.copyWith(fontWeight: FontWeight.bold),
      ),
    );
  }

  Widget _buildPenaltyTab() {
    if (widget.tokens.uyeNo == null || widget.tokens.uyeNo!.isEmpty) {
      return const Center(child: Text('Ceza bilgisi için hesabınızda numara yok.'));
    }
    if (_loadingCeza) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_cezaError != null) {
      return Center(child: Text('Ceza durumu yüklenemedi.\n$_cezaError'));
    }

    final entries = (_ceza['entries'] as List?) ?? const [];
    final total = (_ceza['outstanding_total'] ?? '0.00').toString();
    final count = _ceza['outstanding_count'] is int
        ? (_ceza['outstanding_count'] as int)
        : entries.length;

    return RefreshIndicator(
      onRefresh: _loadCeza,
      child: entries.isEmpty
          ? ListView(
              children: [
                _summaryCard(total, count),
                const Padding(
                  padding: EdgeInsets.all(24),
                  child: Center(child: Text('Ödenmemiş ceza yok.')),
                ),
              ],
            )
          : ListView(
              children: [
                _summaryCard(total, count),
                ...entries.map((raw) {
                  final e = (raw as Map).cast<String, dynamic>();
                  return Card(
                    margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                    child: ListTile(
                      title: Text((e['kitap'] ?? 'Kitap').toString()),
                      subtitle: Text(
                        'Barkod: ${e['barkod']} · '
                        'İade: ${_shortDate(e['iade_tarihi'])} · '
                        'Durum: ${_durumLabel((e['durum'] ?? '').toString())}',
                      ),
                      trailing: Text(
                        '₺${e['gecikme_cezasi'] ?? '0.00'}',
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
                    ),
                  );
                }),
              ],
            ),
    );
  }

  Widget _summaryCard(String total, int count) {
    final scheme = Theme.of(context).colorScheme;
    return Card(
      margin: const EdgeInsets.all(12),
      color: scheme.secondaryContainer,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Ödenmemiş ceza toplamı',
              style: TextStyle(
                color: scheme.onSecondaryContainer,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              '₺$total',
              style: Theme.of(context)
                  .textTheme
                  .headlineSmall
                  ?.copyWith(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 2),
            Text(
              '$count kayıt',
              style: TextStyle(color: scheme.onSecondaryContainer),
            ),
          ],
        ),
      ),
    );
  }
}