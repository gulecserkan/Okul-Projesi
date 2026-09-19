import 'package:flutter/material.dart';

import '../api/library_api.dart';
import '../models/auth.dart';
import '../models/book.dart';
import '../theme/app_theme.dart';
import 'book_detail_screen.dart';
import 'barcode_scanner_screen.dart';
import 'dart:developer' as dev;

class BookListScreen extends StatefulWidget {
  const BookListScreen({
    super.key,
    required this.baseUrl,
    required this.tokens,
    required this.onLogout,
    required this.onChangeServer,
    required this.currentTheme,
    required this.onThemeChange,
  });

  final String baseUrl;
  final AuthTokens tokens;
  final Future<void> Function() onLogout;
  final Future<void> Function() onChangeServer;
  final AppTheme currentTheme;
  final Future<void> Function(AppTheme) onThemeChange;

  @override
  State<BookListScreen> createState() => _BookListScreenState();
}

class _BookListScreenState extends State<BookListScreen> {
  late LibraryApiClient _api;
  final TextEditingController _searchController = TextEditingController();

  List<BookSummary> _books = [];
  bool _loading = true;
  String? _error;
  List<Category> _categories = [];
  List<Author> _authors = [];
  List<String> _shelfOptions = [];
  Category? _selectedCategory;
  Author? _selectedAuthor;
  bool _onlyMissingImages = false;
  bool _missingDescription = false;
  String _shelfQuery = "";
  String? _lastDebugInfo;
  bool _forceBarcodeSearch = false;

  @override
  void initState() {
    super.initState();
    _api = LibraryApiClient(baseUrl: widget.baseUrl, tokens: widget.tokens);
    _loadFilters();
    _loadBooks();
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: const Text("Kütüphane (Admin)"),
        actions: [
          IconButton(
            tooltip: "Barkod tara",
            onPressed: _scanBarcode,
            icon: const Icon(Icons.qr_code_scanner),
          ),
          PopupMenuButton<String>(
            icon: const Icon(Icons.more_vert),
            onSelected: (value) {
              switch (value) {
                case "password":
                  _showChangePasswordDialog();
                  break;
                case "server":
                  widget.onChangeServer();
                  break;
                case "theme":
                  _showThemeDialog();
                  break;
                case "logout":
                  widget.onLogout();
                  break;
              }
            },
            itemBuilder: (context) => [
              const PopupMenuItem(
                value: "password",
                child: ListTile(
                  leading: Icon(Icons.key),
                  title: Text("Şifre değiştir"),
                ),
              ),
              const PopupMenuItem(
                value: "server",
                child: ListTile(
                  leading: Icon(Icons.settings_ethernet),
                  title: Text("Sunucuyu değiştir"),
                ),
              ),
              const PopupMenuItem(
                value: "theme",
                child: ListTile(
                  leading: Icon(Icons.palette_outlined),
                  title: Text("Tema seç"),
                ),
              ),
              const PopupMenuItem(
                value: "logout",
                child: ListTile(
                  leading: Icon(Icons.logout),
                  title: Text("Çıkış yap"),
                ),
              ),
            ],
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(56),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
            child: _buildSearchBar(context),
          ),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: _loadBooks,
        child: Column(
          children: [
            _buildFilterRow(scheme),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: Row(
                  children: [
                    Icon(Icons.error_outline, color: scheme.error),
                    const SizedBox(width: 6),
                    Expanded(child: Text(_error!, style: TextStyle(color: scheme.error))),
                  ],
                ),
              ),
            if (_lastDebugInfo != null && !_loading)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                child: Text(
                  _lastDebugInfo!,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(color: scheme.outline),
                ),
              ),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _books.isEmpty
                      ? const Center(child: Text("Kriterlere uyan kitap bulunamadı."))
                      : ListView.separated(
                          physics: const AlwaysScrollableScrollPhysics(),
                          itemCount: _books.length,
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                          separatorBuilder: (_, __) => const SizedBox(height: 8),
                          itemBuilder: (context, index) {
                            final book = _books[index];
                            return _BookCard(
                              book: book,
                              onTap: () => _openBook(book),
                              missingImage: book.imageCount == 0,
                              shelfCodes: book.shelfCodes,
                            );
                          },
                        ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSearchBar(BuildContext context) {
    return TextField(
      controller: _searchController,
      decoration: InputDecoration(
        hintText: "Başlık / ISBN / Barkod",
        prefixIcon: const Icon(Icons.search),
        suffixIcon: IconButton(
          tooltip: "Ara",
          icon: const Icon(Icons.check),
          onPressed: _loadBooks,
        ),
      ),
      onSubmitted: (_) => _loadBooks(),
    );
  }

  Widget _buildFilterRow(ColorScheme scheme) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        alignment: WrapAlignment.start,
        children: [
          FilterChip(
            label: Text(
              _shelfQuery.isEmpty ? "Raf kodu" : "Raf: $_shelfQuery",
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            selected: _shelfQuery.isNotEmpty,
            avatar: const Icon(Icons.inventory_2_outlined, size: 18),
            onSelected: (_) => _showShelfPicker(),
          ),
          FilterChip(
            label: Text(
              "Resim yok",
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            selected: _onlyMissingImages,
            avatar: const Icon(Icons.photo_size_select_actual_outlined, size: 18),
            onSelected: (value) {
              setState(() => _onlyMissingImages = value);
              _loadBooks();
            },
          ),
          FilterChip(
            label: const Text(
              "Açıklama yok",
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
            selected: _missingDescription,
            avatar: const Icon(Icons.notes_outlined, size: 18),
            onSelected: (value) {
              setState(() => _missingDescription = value);
              _loadBooks();
            },
          ),
          ActionChip(
            avatar: const Icon(Icons.clear_all, size: 18),
            label: const Text("Filtreleri sıfırla"),
            onPressed: () {
              setState(() {
                _selectedCategory = null;
                _selectedAuthor = null;
                _shelfQuery = "";
                _onlyMissingImages = false;
                _missingDescription = false;
                _searchController.clear();
              });
              _loadBooks();
            },
          ),
          ActionChip(
            avatar: const Icon(Icons.refresh, size: 18),
            label: const Text("Yenile"),
            onPressed: _loadBooks,
          ),
          FilterChip(
            label: Text(
              _selectedCategory == null ? "Kategori" : _selectedCategory!.ad,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            selected: _selectedCategory != null,
            avatar: const Icon(Icons.category_outlined, size: 18),
            onSelected: (_) => _showCategoryPicker(),
          ),
          FilterChip(
            label: Text(
              _selectedAuthor == null ? "Yazar" : _selectedAuthor!.adSoyad,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            selected: _selectedAuthor != null,
            avatar: const Icon(Icons.person_outline, size: 18),
            onSelected: (_) => _showAuthorPicker(),
          ),
        ],
      ),
    );
  }

  Future<void> _showCategoryPicker() async {
    final picked = await showModalBottomSheet<Category>(
      context: context,
      builder: (context) {
        return _SelectionSheet<Category>(
          title: "Kategori seç",
          items: _categories,
          itemBuilder: (c) => c.ad,
          selected: _selectedCategory,
        );
      },
    );
    if (picked != null) {
      setState(() => _selectedCategory = picked);
      _loadBooks();
    }
  }

  Future<void> _showAuthorPicker() async {
    final picked = await showModalBottomSheet<Author>(
      context: context,
      builder: (context) {
        return _SelectionSheet<Author>(
          title: "Yazar seç",
          items: _authors,
          itemBuilder: (a) => a.adSoyad,
          selected: _selectedAuthor,
        );
      },
    );
    if (picked != null) {
      setState(() => _selectedAuthor = picked);
      _loadBooks();
    }
  }

  Future<void> _showShelfPicker() async {
    if (_shelfOptions.isEmpty) {
      await _promptManualShelf();
      return;
    }

    final searchController = TextEditingController();
    String filter = "";

    final picked = await showModalBottomSheet<String>(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setStateSheet) {
            final items = _shelfOptions
                .where((code) => code.toLowerCase().contains(filter.toLowerCase()))
                .toList();
            return SafeArea(
              child: DraggableScrollableSheet(
                initialChildSize: 0.7,
                minChildSize: 0.5,
                maxChildSize: 0.9,
                expand: false,
                builder: (context, scrollController) {
                  return Column(
                    children: [
                      Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Row(
                          children: [
                            const Text("Raf kodu seç", style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                            const Spacer(),
                            TextButton(
                              onPressed: () => Navigator.of(context).pop(""),
                              child: const Text("Temizle"),
                            ),
                          ],
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        child: TextField(
                          controller: searchController,
                          decoration: const InputDecoration(
                            labelText: "Raf kodu ara",
                            prefixIcon: Icon(Icons.search),
                          ),
                          onChanged: (value) => setStateSheet(() => filter = value),
                        ),
                      ),
                      const SizedBox(height: 8),
                      Expanded(
                        child: ListView.separated(
                          controller: scrollController,
                          itemCount: items.length + 1,
                          separatorBuilder: (_, __) => const Divider(height: 1),
                          itemBuilder: (context, index) {
                            if (index == 0) {
                              return ListTile(
                                leading: const Icon(Icons.edit),
                                title: const Text("Elle gir"),
                                onTap: () => Navigator.of(context).pop("__manual__"),
                              );
                            }
                            final code = items[index - 1];
                            return ListTile(
                              title: Text(code),
                              trailing: _shelfQuery == code ? const Icon(Icons.check) : null,
                              onTap: () => Navigator.of(context).pop(code),
                            );
                          },
                        ),
                      ),
                    ],
                  );
                },
              ),
            );
          },
        );
      },
    );

    if (picked == null) return;
    if (picked == "__manual__") {
      await _promptManualShelf();
      return;
    }

    setState(() => _shelfQuery = picked);
    _loadBooks();
  }

  Future<void> _promptManualShelf() async {
    final controller = TextEditingController(text: _shelfQuery);
    final result = await showDialog<String?>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text("Raf kodu filtresi"),
          content: TextField(
            controller: controller,
            decoration: const InputDecoration(
              labelText: "Raf kodu (içerir)",
              hintText: "Örn: A1 veya A1-",
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(""),
              child: const Text("Temizle"),
            ),
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text("Vazgeç"),
            ),
            ElevatedButton(
              onPressed: () => Navigator.of(context).pop(controller.text.trim()),
              child: const Text("Uygula"),
            ),
          ],
        );
      },
    );

    if (result == null) return;
    setState(() => _shelfQuery = result);
    _loadBooks();
  }

  Future<void> _showThemeDialog() async {
    await showDialog<AppTheme>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text("Tema seç"),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: appThemes.entries.map((entry) {
              final theme = entry.key;
              final config = entry.value;
              return RadioListTile<AppTheme>(
                value: theme,
                groupValue: widget.currentTheme,
                onChanged: (value) {
                  if (value != null) {
                    widget.onThemeChange(value);
                    Navigator.of(context).pop();
                  }
                },
                title: Text(config.label),
                secondary: Icon(config.icon),
              );
            }).toList(),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text("Kapat"),
            ),
          ],
        );
      },
    );
  }

  Future<void> _scanBarcode() async {
    final code = await Navigator.of(context).push<String>(
      MaterialPageRoute(builder: (_) => const BarcodeScannerScreen()),
    );
    if (code == null || code.isEmpty) return;
    _searchController.text = code;
    _forceBarcodeSearch = true;
    await _loadBooks();
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
              title: const Text("Şifre değiştir"),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: currentCtrl,
                    decoration: const InputDecoration(
                      labelText: "Mevcut şifre",
                      prefixIcon: Icon(Icons.lock_clock_outlined),
                    ),
                    obscureText: true,
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: newCtrl,
                    decoration: const InputDecoration(
                      labelText: "Yeni şifre",
                      prefixIcon: Icon(Icons.lock_outline),
                    ),
                    obscureText: true,
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: confirmCtrl,
                    decoration: const InputDecoration(
                      labelText: "Yeni şifre (tekrar)",
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
                  child: const Text("Vazgeç"),
                ),
                ElevatedButton(
                  onPressed: loading
                      ? null
                      : () async {
                          final current = currentCtrl.text.trim();
                          final newPass = newCtrl.text.trim();
                          final confirm = confirmCtrl.text.trim();
                          if (current.isEmpty || newPass.isEmpty || confirm.isEmpty) {
                            setStateDialog(() => error = "Tüm alanlar zorunlu.");
                            return;
                          }
                          if (newPass != confirm) {
                            setStateDialog(() => error = "Yeni şifreler uyuşmuyor.");
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
                            if (!mounted) return;
                            Navigator.of(context).pop();
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text("Şifre güncellendi.")),
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
                      : const Text("Kaydet"),
                ),
              ],
            );
          },
        );
      },
    );
  }

  Future<void> _loadFilters() async {
    try {
      final categories = await _api.fetchCategories();
      final authors = await _api.fetchAuthors();
      final shelfCodes = await _api.fetchShelfCodes();
      if (!mounted) return;
      setState(() {
        _categories = categories;
        _authors = authors;
        _shelfOptions = shelfCodes;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = "Filtreler alınamadı: $e";
      });
    }
  }

  Future<void> _loadBooks() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final searchText = _searchController.text.trim();
      String? isbnQuery;
      String? barcodeQuery;
      String? titleQuery = searchText.isEmpty ? null : searchText;

      final isDigitsOnly = RegExp(r"^[0-9-]+$").hasMatch(searchText);
      final looksLikeCode = searchText.isNotEmpty && !searchText.contains(" ") && searchText.contains(RegExp(r"[0-9]"));

      if (_forceBarcodeSearch) {
        titleQuery = null;
        barcodeQuery = searchText;
        if (isDigitsOnly) {
          isbnQuery = searchText;
        }
      } else if (looksLikeCode) {
        // Sayı ağırlıklı giriş: başlıkla AND yapmak yerine sadece ilgili alanlarda ara
        titleQuery = null;
        isbnQuery = searchText;
        barcodeQuery = searchText;
      }

      final logParams = {
        "q": titleQuery,
        "kategori": _selectedCategory?.id,
        "yazar": _selectedAuthor?.id,
        "max_image_count": _onlyMissingImages ? 0 : null,
        "aciklama_var": _missingDescription ? 0 : null,
        "raf_query": _shelfQuery.isEmpty ? null : _shelfQuery,
        "isbn": isbnQuery,
        "barkod": barcodeQuery,
      };
      dev.log("Kitap sorgu parametreleri: $logParams");

      final response = await _api.fetchBooks(
        query: titleQuery,
        isbnQuery: isbnQuery,
        barcodeQuery: barcodeQuery,
        kategoriId: _selectedCategory?.id,
        yazarId: _selectedAuthor?.id,
        maxImageCount: _onlyMissingImages ? 0 : null,
        hasDescription: _missingDescription ? false : null,
        shelfQuery: _shelfQuery.isEmpty ? null : _shelfQuery,
      );
      final items = response.books;
      dev.log("Kitap sorgu sonucu: total=${response.totalCount}, items=${items.length}");
      if (!mounted) return;
      setState(() {
        _books = items;
        _loading = false;
        _lastDebugInfo = "Son sorgu: toplam=${response.totalCount}, listelenen=${items.length}";
        _forceBarcodeSearch = false;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      if (e.statusCode == 401) {
        await widget.onLogout();
        return;
      }
      setState(() {
        _error = e.message;
        _loading = false;
        _lastDebugInfo = "Hata: ${e.message}";
        _forceBarcodeSearch = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
        _lastDebugInfo = "Hata: $e";
        _forceBarcodeSearch = false;
      });
    }
  }

  Future<void> _openBook(BookSummary book) async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => BookDetailScreen(
          bookId: book.id,
          summary: book,
          api: _api,
        ),
      ),
    );
    await _loadBooks();
  }
}

class _BookCard extends StatelessWidget {
  const _BookCard({
    required this.book,
    required this.onTap,
    required this.missingImage,
    this.shelfCodes = const [],
  });

  final BookSummary book;
  final VoidCallback onTap;
  final bool missingImage;
  final List<String> shelfCodes;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return InkWell(
      borderRadius: BorderRadius.circular(14),
      onTap: onTap,
      child: Ink(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: scheme.primary.withOpacity(0.08),
          borderRadius: BorderRadius.circular(14),
          boxShadow: [
            BoxShadow(
              color: scheme.primary.withOpacity(0.08),
              blurRadius: 10,
              offset: const Offset(0, 6),
            ),
          ],
          border: Border.all(color: scheme.primary.withOpacity(0.12)),
        ),
        child: Row(
          children: [
            Container(
              width: 52,
              height: 52,
              decoration: BoxDecoration(
                color: scheme.primary.withOpacity(0.12),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(
                missingImage ? Icons.photo_size_select_actual_outlined : Icons.menu_book_outlined,
                color: scheme.primary,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    book.baslik,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      if (book.yazar != null) ...[
                        Icon(Icons.person_outline, size: 16, color: scheme.outline),
                        const SizedBox(width: 4),
                        Flexible(
                          child: Text(
                            book.yazar!,
                            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: scheme.outline),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        const SizedBox(width: 8),
                      ],
                      if (book.kategori != null) ...[
                        Icon(Icons.category_outlined, size: 16, color: scheme.outline),
                        const SizedBox(width: 4),
                        Flexible(
                          child: Text(
                            book.kategori!,
                            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: scheme.outline),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 8,
                    runSpacing: 4,
                    children: [
                      Chip(
                        label: Text("Nüsha: ${book.nushaSayisi ?? "-"}"),
                        padding: EdgeInsets.zero,
                      ),
                      if (shelfCodes.isNotEmpty)
                        Chip(
                          label: Text("Raf: ${shelfCodes.take(2).join(', ')}${shelfCodes.length > 2 ? ' +' : ''}"),
                          padding: EdgeInsets.zero,
                        ),
                      if (!(missingImage && book.imageCount == 0))
                        Chip(
                          label: Text("Resim: ${book.imageCount}"),
                          padding: EdgeInsets.zero,
                        ),
                      if (book.isbn != null && book.isbn!.isNotEmpty)
                        Chip(
                          label: Text("ISBN ${book.isbn}"),
                          padding: EdgeInsets.zero,
                        ),
                      if (!book.aciklamaVar)
                        Chip(
                          label: const Text("Açıklama yok"),
                          avatar: Icon(Icons.notes_outlined, size: 16, color: scheme.error),
                          padding: EdgeInsets.zero,
                          backgroundColor: scheme.errorContainer.withOpacity(0.3),
                        ),
                      if (missingImage)
                        Chip(
                          label: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: const [
                              Icon(Icons.warning_amber_rounded, size: 16),
                              SizedBox(width: 4),
                              Text("Resim yok"),
                            ],
                          ),
                          backgroundColor: scheme.errorContainer.withOpacity(0.3),
                        ),
                    ],
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right),
          ],
        ),
      ),
    );
  }

}

class _SelectionSheet<T> extends StatelessWidget {
  const _SelectionSheet({
    required this.title,
    required this.items,
    required this.itemBuilder,
    this.selected,
  });

  final String title;
  final List<T> items;
  final String Function(T) itemBuilder;
  final T? selected;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return SafeArea(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Row(
              children: [
                Text(title, style: Theme.of(context).textTheme.titleLarge),
                const Spacer(),
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text("Kapat"),
                ),
              ],
            ),
          ),
          const Divider(height: 1),
          Flexible(
            child: ListView.separated(
              shrinkWrap: true,
              itemCount: items.length + 1,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (context, index) {
                if (index == 0) {
                  return ListTile(
                    leading: const Icon(Icons.clear),
                    title: const Text("Tümü"),
                    onTap: () => Navigator.of(context).pop<T>(null),
                  );
                }
                final item = items[index - 1];
                final label = itemBuilder(item);
                final isSelected = selected != null && selected == item;
                return ListTile(
                  title: Text(label),
                  trailing: isSelected ? Icon(Icons.check, color: scheme.primary) : null,
                  onTap: () => Navigator.of(context).pop<T>(item),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
