import 'package:flutter/material.dart';

import '../api/library_api.dart';
import '../models/auth.dart';
import '../models/book.dart';

/// K9: Borçlu (öğrenci/öğretmen) ekranı — salt-okunur.
/// Kitaplarda gezinti/arama + kendi ödünç geçmişi. Düzenleme yoktur.
class BorrowerHomeScreen extends StatefulWidget {
  const BorrowerHomeScreen({
    super.key,
    required this.baseUrl,
    required this.tokens,
    required this.onLogout,
    required this.onChangeServer,
  });

  final String baseUrl;
  final AuthTokens tokens;
  final Future<void> Function() onLogout;
  final Future<void> Function() onChangeServer;

  @override
  State<BorrowerHomeScreen> createState() => _BorrowerHomeScreenState();
}

class _BorrowerHomeScreenState extends State<BorrowerHomeScreen> {
  late final LibraryApiClient _api;
  final _searchController = TextEditingController();

  List<BookSummary> _books = [];
  bool _loadingBooks = false;
  String? _booksError;

  List<Map<String, dynamic>> _loans = [];
  bool _loadingLoans = false;
  String? _loansError;

  @override
  void initState() {
    super.initState();
    _api = LibraryApiClient(baseUrl: widget.baseUrl, tokens: widget.tokens);
    _loadBooks();
    _loadLoans();
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
        _booksError = e.toString();
        _loadingBooks = false;
      });
    }
  }

  Future<void> _loadLoans() async {
    final no = widget.tokens.ogrenciNo;
    if (no == null || no.isEmpty) {
      setState(() => _loadingLoans = false);
      return;
    }
    setState(() {
      _loadingLoans = true;
      _loansError = null;
    });
    try {
      final list = await _api.fetchStudentHistory(no);
      if (!mounted) return;
      setState(() {
        _loans = list;
        _loadingLoans = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loansError = e.toString();
        _loadingLoans = false;
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

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Kütüphane'),
          actions: [
            IconButton(
              tooltip: 'Sunucu değiştir',
              icon: const Icon(Icons.dns_outlined),
              onPressed: () => widget.onChangeServer(),
            ),
            IconButton(
              tooltip: 'Çıkış',
              icon: const Icon(Icons.logout),
              onPressed: () => widget.onLogout(),
            ),
          ],
          bottom: const TabBar(
            tabs: [
              Tab(icon: Icon(Icons.menu_book_outlined), text: 'Kitaplar'),
              Tab(icon: Icon(Icons.history), text: 'Ödünçlerim'),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            _buildBooksTab(),
            _buildLoansTab(),
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

  Widget _buildLoansTab() {
    if (widget.tokens.ogrenciNo == null || widget.tokens.ogrenciNo!.isEmpty) {
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
    return RefreshIndicator(
      onRefresh: _loadLoans,
      child: ListView.builder(
        itemCount: _loans.length,
        itemBuilder: (context, i) {
          final r = _loans[i];
          final durum = (r['durum'] ?? '').toString();
          return Card(
            margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            child: ListTile(
              title: Text(_loanTitle(r)),
              subtitle: Text(
                'Ödünç: ${_shortDate(r['odunc_tarihi'])} · '
                'İade: ${_shortDate(r['iade_tarihi'])}',
              ),
              trailing: Chip(
                label: Text(durum.isEmpty ? '—' : durum),
                visualDensity: VisualDensity.compact,
              ),
            ),
          );
        },
      ),
    );
  }
}
