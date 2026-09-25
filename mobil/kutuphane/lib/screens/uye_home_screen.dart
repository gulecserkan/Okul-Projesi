import 'package:flutter/material.dart';

import '../api/library_api.dart';
import '../models/auth.dart';
import '../models/book.dart';
import 'book_inspect_screen.dart';

/// K9: Üye (öğrenci/öğretmen) ekranı — salt-okunur.
/// Kitaplarda gezinti/arama + kendi ödünç geçmişi + ceza bakiyesi.
/// Düzenleme ve ödünç/iade işlemleri yoktur.
class UyeHomeScreen extends StatefulWidget {
  const UyeHomeScreen({
    super.key,
    required this.baseUrl,
    required this.tokens,
    required this.onLogout,
    this.onSessionExpired,
    this.api,
  });

  final String baseUrl;
  final AuthTokens tokens;
  final Future<void> Function() onLogout;
  final void Function()? onSessionExpired;

  /// Test/DI için dışarıdan verilebilir.
  final LibraryApiClient? api;

  @override
  State<UyeHomeScreen> createState() => _UyeHomeScreenState();
}

/// Sıralama seçenekleri (backend `ordering` anahtarları).
enum _SortKey { baslik, baslikDesc, yazar, yayinYiliDesc, nushaDesc }

/// Kitap gezinti görünümü.
enum _BrowseView { grid, shelf }

class _UyeHomeScreenState extends State<UyeHomeScreen> {
  late final LibraryApiClient _api;
  final _searchController = TextEditingController();
  final _gridController = ScrollController();
  final _shelfController = ScrollController();

  List<BookSummary> _books = [];
  bool _loadingBooks = false;
  String? _booksError;
  int _toplamKitaplar = 0;
  int _page = 0;
  bool _hasMore = false;
  bool _loadingMore = false;

  _BrowseView _view = _BrowseView.grid;
  List<Category> _kategoriler = [];
  int? _seciliKategoriId;
  List<Author> _yazarlar = [];
  int? _seciliYazarId;
  String? _yazarAdi;
  bool _sadeceGorselli = false;
  bool _goruslu = false;
  _SortKey _sort = _SortKey.baslik;

  List<Map<String, dynamic>> _loans = [];
  bool _loadingLoans = false;
  String? _loansError;

  Map<String, dynamic> _ceza = {};
  bool _loadingCeza = false;
  String? _cezaError;

  @override
  void initState() {
    super.initState();
    _api =
        widget.api ??
        LibraryApiClient(
          baseUrl: widget.baseUrl,
          tokens: widget.tokens,
          onUnauthorized: widget.onSessionExpired,
        );
    _gridController.addListener(_onScroll);
    _shelfController.addListener(_onScroll);
    _loadBooks();
    _loadKategoriler();
    _loadLoans();
    _loadCeza();
  }

  @override
  void dispose() {
    _searchController.dispose();
    _gridController.dispose();
    _shelfController.dispose();
    super.dispose();
  }

  bool get _filtreVar =>
      _seciliKategoriId != null ||
      _seciliYazarId != null ||
      _sadeceGorselli ||
      _goruslu ||
      _searchController.text.trim().isNotEmpty;

  Future<void> _loadKategoriler() async {
    try {
      final list = await _api.fetchCategories();
      if (!mounted) return;
      setState(() => _kategoriler = list);
    } catch (_) {
      // Kategori çipleri isteğe bağlı; yüklenemezse sessiz geç.
    }
  }

  Future<void> _loadBooks({bool reset = true}) async {
    final page = reset ? 1 : _page + 1;
    if (reset) {
      setState(() {
        _loadingBooks = true;
        _booksError = null;
      });
    } else {
      setState(() => _loadingMore = true);
    }
    try {
      final res = await _api.fetchBooks(
        query: _searchController.text.trim(),
        kategoriId: _seciliKategoriId,
        yazarId: _seciliYazarId,
        minImageCount: _sadeceGorselli ? 1 : null,
        hasDescription: _goruslu ? true : null,
        ordering: _sortKey(),
        page: page,
        pageSize: 50,
      );
      if (!mounted) return;
      setState(() {
        _books = reset ? res.books : [..._books, ...res.books];
        _toplamKitaplar = res.totalCount;
        _page = page;
        _hasMore = _books.length < res.totalCount;
        _loadingBooks = false;
        _loadingMore = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        if (reset) {
          _booksError = e is ApiException ? e.message : e.toString();
          _loadingBooks = false;
        } else {
          _loadingMore = false;
        }
      });
    }
  }

  String? _sortKey() {
    switch (_sort) {
      case _SortKey.baslik:
        return 'baslik';
      case _SortKey.baslikDesc:
        return '-baslik';
      case _SortKey.yazar:
        return 'yazar';
      case _SortKey.yayinYiliDesc:
        return '-yayin_yili';
      case _SortKey.nushaDesc:
        return '-nusha_sayisi';
    }
  }

  void _onScroll() {
    if (_loadingBooks || _loadingMore || !_hasMore) return;
    final pos = _view == _BrowseView.grid ? _gridController : _shelfController;
    if (!pos.hasClients) return;
    if (pos.position.extentAfter < 300) {
      _loadBooks(reset: false);
    }
  }

  Future<void> _resetBrowse() async {
    setState(() {
      _toplamKitaplar = 0;
      _page = 0;
      _hasMore = false;
    });
    await _loadBooks(reset: true);
  }

  void _clearFilters() {
    setState(() {
      _seciliKategoriId = null;
      _seciliYazarId = null;
      _yazarAdi = null;
      _sadeceGorselli = false;
      _goruslu = false;
      _sort = _SortKey.baslik;
      _searchController.clear();
    });
    _resetBrowse();
  }

  Future<void> _openBook(BookSummary b) async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => BookInspectScreen(api: _api, summary: b),
      ),
    );
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

  String _loanTitle(Map<String, dynamic> r) {
    final nusha = r['kitap_nusha'];
    if (nusha is Map<String, dynamic>) {
      final kitap = nusha['kitap'];
      if (kitap is Map<String, dynamic>) {
        return (kitap['baslik'] ?? '').toString();
      }
      if (nusha['kitap_baslik'] != null) {
        return nusha['kitap_baslik'].toString();
      }
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

  /// AppBar başlığı: üye adı + soyadı (üye no).
  Widget _buildAppBarTitle() {
    final t = widget.tokens;
    final name = (t.fullName ?? '').trim();
    final no = (t.uyeNo ?? '').trim();
    final mainLabel = name.isNotEmpty
        ? (no.isNotEmpty ? '$name ($no)' : name)
        : (no.isNotEmpty ? no : 'Kütüphane');
    return Text(
      mainLabel,
      overflow: TextOverflow.ellipsis,
      style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
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
              style: TextStyle(fontSize: 10, color: scheme.onSurfaceVariant),
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
                  onPressed: loading ? null : () => Navigator.of(context).pop(),
                  child: const Text('Vazgeç'),
                ),
                ElevatedButton(
                  onPressed: loading
                      ? null
                      : () async {
                          final current = currentCtrl.text.trim();
                          final newPass = newCtrl.text.trim();
                          final confirm = confirmCtrl.text.trim();
                          if (current.isEmpty ||
                              newPass.isEmpty ||
                              confirm.isEmpty) {
                            setStateDialog(
                              () => error = 'Tüm alanlar zorunlu.',
                            );
                            return;
                          }
                          if (newPass != confirm) {
                            setStateDialog(
                              () => error = 'Yeni şifreler uyuşmuyor.',
                            );
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
                              const SnackBar(
                                content: Text('Şifre güncellendi.'),
                              ),
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
          toolbarHeight: 52,
          titleSpacing: 14,
          title: _buildAppBarTitle(),
          actions: [
            _actionButton(
              icon: Icons.key_outlined,
              label: 'Şifre',
              onPressed: _showChangePasswordDialog,
            ),
            _actionButton(
              icon: Icons.logout,
              label: 'Çıkış',
              onPressed: () => widget.onLogout(),
            ),
          ],
          bottom: const TabBar(
            tabs: [
              Tab(text: 'Kitaplar'),
              Tab(text: 'Ödünçlerim'),
              Tab(text: 'Ceza'),
            ],
          ),
        ),
        body: TabBarView(
          children: [_buildBooksTab(), _buildLoansTab(), _buildPenaltyTab()],
        ),
      ),
    );
  }

  Widget _buildBooksTab() {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
          child: TextField(
            controller: _searchController,
            textInputAction: TextInputAction.search,
            onSubmitted: (_) => _resetBrowse(),
            decoration: InputDecoration(
              hintText: 'Kitap ara (başlık / yazar / ISBN)...',
              prefixIcon: const Icon(Icons.search),
              suffixIcon: IconButton(
                icon: const Icon(Icons.clear),
                onPressed: () {
                  _searchController.clear();
                  _resetBrowse();
                },
              ),
              border: const OutlineInputBorder(),
              isDense: true,
              contentPadding:
                  const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
            ),
          ),
        ),
        _buildFilterBar(),
        if (_loadingBooks && _books.isEmpty)
          const Expanded(child: Center(child: CircularProgressIndicator()))
        else if (_booksError != null)
          Expanded(
            child: Center(child: Text('Kitaplar yüklenemedi.\n$_booksError')),
          )
        else if (_books.isEmpty)
          Expanded(
            child: Center(
              child: Text(
                _filtreVar
                    ? 'Kriterlere uyan kitap bulunamadı.'
                    : 'Sonuç bulunamadı.',
              ),
            ),
          )
        else ...[
          _buildResultHeader(),
          Expanded(
            child: _view == _BrowseView.grid
                ? _buildGridList()
                : _buildShelfList(),
          ),
          if (_loadingMore) const LinearProgressIndicator(minHeight: 2),
        ],
      ],
    );
  }

  /// Kategori çipleri + filtre satırı (yazar, görsellik, görüş, sıralama, temizle).
  Widget _buildFilterBar() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
          child: SizedBox(
            height: 36,
            child: ListView(
              scrollDirection: Axis.horizontal,
              children: [
                ChoiceChip(
                  label: const Text('Tümü'),
                  selected: _seciliKategoriId == null,
                  onSelected: (_) {
                    setState(() => _seciliKategoriId = null);
                    _resetBrowse();
                  },
                  visualDensity: VisualDensity.compact,
                ),
                for (final k in _kategoriler) ...[
                  const SizedBox(width: 8),
                  ChoiceChip(
                    label: Text(k.ad),
                    selected: _seciliKategoriId == k.id,
                    onSelected: (_) {
                      setState(() => _seciliKategoriId = k.id);
                      _resetBrowse();
                    },
                    visualDensity: VisualDensity.compact,
                  ),
                ],
              ],
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 4, 12, 0),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                ActionChip(
                  avatar: const Icon(Icons.person_outline, size: 16),
                  label: Text(_yazarAdi ?? 'Yazar'),
                  onPressed: _showAuthorPicker,
                  visualDensity: VisualDensity.compact,
                ),
                const SizedBox(width: 8),
                FilterChip(
                  avatar: const Icon(Icons.image_outlined, size: 16),
                  label: const Text('Sadece görselli'),
                  selected: _sadeceGorselli,
                  onSelected: (v) {
                    setState(() => _sadeceGorselli = v);
                    _resetBrowse();
                  },
                  visualDensity: VisualDensity.compact,
                ),
                const SizedBox(width: 8),
                FilterChip(
                  avatar: const Icon(Icons.school_outlined, size: 16),
                  label: const Text('Öğretmen görüşü'),
                  selected: _goruslu,
                  onSelected: (v) {
                    setState(() => _goruslu = v);
                    _resetBrowse();
                  },
                  visualDensity: VisualDensity.compact,
                ),
                const SizedBox(width: 8),
                PopupMenuButton<_SortKey>(
                  tooltip: 'Sırala',
                  icon: const Icon(Icons.sort, size: 20),
                  initialValue: _sort,
                  onSelected: (v) {
                    setState(() => _sort = v);
                    _resetBrowse();
                  },
                  itemBuilder: (context) => const [
                    PopupMenuItem(
                      value: _SortKey.baslik,
                      child: Text('Başlık (A→Z)'),
                    ),
                    PopupMenuItem(
                      value: _SortKey.baslikDesc,
                      child: Text('Başlık (Z→A)'),
                    ),
                    PopupMenuItem(
                      value: _SortKey.yazar,
                      child: Text('Yazara göre'),
                    ),
                    PopupMenuItem(
                      value: _SortKey.yayinYiliDesc,
                      child: Text('Yayın yılı (yeni→eski)'),
                    ),
                    PopupMenuItem(
                      value: _SortKey.nushaDesc,
                      child: Text('Nüsha (çok→az)'),
                    ),
                  ],
                ),
                if (_filtreVar) ...[
                  const SizedBox(width: 4),
                  TextButton.icon(
                    onPressed: _clearFilters,
                    icon: const Icon(Icons.filter_alt_off_outlined, size: 18),
                    label: const Text('Temizle'),
                  ),
                ],
              ],
            ),
          ),
        ),
      ],
    );
  }

  Future<void> _showAuthorPicker() async {
    if (_yazarlar.isEmpty) {
      try {
        final list = await _api.fetchAuthors();
        if (!mounted) return;
        setState(() => _yazarlar = list);
      } catch (e) {
        if (!mounted) return;
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Yazarlar yüklenemedi: $e')));
        return;
      }
    }
    if (!mounted) return;
    final secilen = await showModalBottomSheet<Author>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (context) => _AuthorPickerSheet(authors: _yazarlar),
    );
    if (secilen == null || !mounted) return;
    setState(() {
      _seciliYazarId = secilen.id;
      _yazarAdi = secilen.adSoyad;
    });
    _resetBrowse();
  }

  Widget _buildResultHeader() {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 4, 12, 0),
      child: Row(
        children: [
          Text(
            '$_toplamKitaplar kitap',
            style: TextStyle(fontSize: 13, color: scheme.onSurfaceVariant),
          ),
          const Spacer(),
          IconButton(
            tooltip: 'Kapak ızgarası',
            onPressed: () => setState(() => _view = _BrowseView.grid),
            icon: Icon(
              Icons.grid_view_rounded,
              color: _view == _BrowseView.grid
                  ? scheme.primary
                  : scheme.outline,
            ),
          ),
          IconButton(
            tooltip: 'Yatay raf',
            onPressed: () => setState(() => _view = _BrowseView.shelf),
            icon: Icon(
              Icons.view_agenda_outlined,
              color: _view == _BrowseView.shelf
                  ? scheme.primary
                  : scheme.outline,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildGridList() {
    return RefreshIndicator(
      onRefresh: _resetBrowse,
      child: GridView.builder(
        controller: _gridController,
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 90),
        gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
          maxCrossAxisExtent: 220,
          childAspectRatio: 0.58,
          crossAxisSpacing: 12,
          mainAxisSpacing: 16,
        ),
        itemCount: _books.length + (_hasMore ? 1 : 0),
        itemBuilder: (context, i) {
          if (i >= _books.length) {
            return const Center(
              child: SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            );
          }
          return _GridBookCard(
            book: _books[i],
            onTap: () => _openBook(_books[i]),
          );
        },
      ),
    );
  }

  Widget _buildShelfList() {
    return ListView.builder(
      controller: _shelfController,
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 90),
      itemCount: _books.length + (_hasMore ? 1 : 0),
      itemBuilder: (context, i) {
        if (i >= _books.length) {
          return const Padding(
            padding: EdgeInsets.all(24),
            child: Center(
              child: SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            ),
          );
        }
        final b = _books[i];
        return Padding(
          padding: const EdgeInsets.only(right: 12),
          child: SizedBox(
            width: 140,
            child: _BookShelfCard(book: b, onTap: () => _openBook(b)),
          ),
        );
      },
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
      return const Center(
        child: Text('Ödünç bilgisi için hesabınızda numara yok.'),
      );
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
        style: Theme.of(
          context,
        ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold),
      ),
    );
  }

  Widget _buildPenaltyTab() {
    if (widget.tokens.uyeNo == null || widget.tokens.uyeNo!.isEmpty) {
      return const Center(
        child: Text('Ceza bilgisi için hesabınızda numara yok.'),
      );
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
                    margin: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 4,
                    ),
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
              style: Theme.of(
                context,
              ).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800),
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

/// Izgara görünümündeki kitap kartı: 3:4 kapak + başlık + yazar.
class _GridBookCard extends StatelessWidget {
  const _GridBookCard({required this.book, required this.onTap});

  final BookSummary book;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final scheme = theme.colorScheme;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AspectRatio(
            aspectRatio: 3 / 4,
            child: _BookCover(book: book),
          ),
          const SizedBox(height: 6),
          Flexible(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  book.baslik,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w700,
                    height: 1.15,
                  ),
                ),
                if ((book.yazar ?? '').isNotEmpty)
                  Text(
                    book.yazar!,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: scheme.onSurfaceVariant,
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Yatay raf görünümündeki kitap kartı.
class _BookShelfCard extends StatelessWidget {
  const _BookShelfCard({required this.book, required this.onTap});

  final BookSummary book;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final scheme = theme.colorScheme;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AspectRatio(
            aspectRatio: 3 / 4,
            child: _BookCover(book: book),
          ),
          const SizedBox(height: 4),
          Text(
            book.baslik,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: theme.textTheme.bodyMedium?.copyWith(
              fontWeight: FontWeight.w600,
              height: 1.15,
            ),
          ),
          if ((book.yazar ?? '').isNotEmpty)
            Text(
              book.yazar!,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: theme.textTheme.bodySmall?.copyWith(
                color: scheme.onSurfaceVariant,
              ),
            ),
        ],
      ),
    );
  }
}

/// Kitap kapağı: varsa görsel, yoksa degrade monogram + görsel sayısı rozeti.
class _BookCover extends StatelessWidget {
  const _BookCover({required this.book});

  final BookSummary book;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final url = book.kapakGorseli;
    return Container(
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        color: scheme.surfaceContainerHighest,
        border: Border.all(color: scheme.outlineVariant),
      ),
      child: Stack(
        fit: StackFit.expand,
        children: [
          if (url != null)
            Image.network(
              url,
              fit: BoxFit.cover,
              errorBuilder: (_, _, _) => _placeholder(scheme),
            )
          else
            _placeholder(scheme),
          if (book.imageCount > 0)
            Positioned(
              top: 6,
              right: 6,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: Colors.black.withValues(alpha: 0.6),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(
                      Icons.image_outlined,
                      size: 12,
                      color: Colors.white,
                    ),
                    const SizedBox(width: 3),
                    Text(
                      '${book.imageCount}',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _placeholder(ColorScheme scheme) {
    final trimmed = book.baslik.trim();
    final initial = trimmed.isEmpty
        ? '?'
        : trimmed.characters.first.toUpperCase();
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [scheme.primaryContainer, scheme.tertiaryContainer],
        ),
      ),
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              initial,
              style: TextStyle(
                color: scheme.onPrimaryContainer,
                fontSize: 40,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 4),
            Icon(Icons.menu_book_rounded, size: 24, color: scheme.primary),
          ],
        ),
      ),
    );
  }
}

/// Yazar filtresi için arama kutulu alt panel.
class _AuthorPickerSheet extends StatefulWidget {
  const _AuthorPickerSheet({required this.authors});

  final List<Author> authors;

  @override
  State<_AuthorPickerSheet> createState() => _AuthorPickerSheetState();
}

class _AuthorPickerSheetState extends State<_AuthorPickerSheet> {
  String _q = '';

  @override
  Widget build(BuildContext context) {
    final q = _q.toLowerCase();
    final filtered = widget.authors
        .where((a) => a.adSoyad.toLowerCase().contains(q))
        .toList();
    return Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
            child: Row(
              children: [
                Text(
                  'Yazar seç',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.close),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
            child: TextField(
              autofocus: true,
              onChanged: (v) => setState(() => _q = v),
              decoration: const InputDecoration(
                hintText: 'Yazar ara...',
                prefixIcon: Icon(Icons.search),
                border: OutlineInputBorder(),
                isDense: true,
              ),
            ),
          ),
          Flexible(
            child: ListView(
              shrinkWrap: true,
              children: [
                for (final a in filtered)
                  ListTile(
                    dense: true,
                    title: Text(a.adSoyad),
                    onTap: () => Navigator.of(context).pop(a),
                  ),
                if (filtered.isEmpty)
                  const Padding(
                    padding: EdgeInsets.all(24),
                    child: Center(child: Text('Eşleşen yazar yok')),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
