import 'dart:async';

import 'package:flutter/material.dart';

import '../config.dart';
import '../api/kutuphane_api.dart';
import '../api_client.dart';
import '../formatters.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/horizontal_menu.dart';
import '../widgets/radial_menu.dart';
import '../widgets/return_dialog.dart';
import 'book_detail_screen.dart';
import 'student_detail_screen.dart';
import 'book_list_screen.dart';
import 'catalog_screen.dart';
import 'loan_screen.dart';
import 'student_list_screen.dart';

class HomeScreen extends StatefulWidget {
  final Session session;

  const HomeScreen({super.key, required this.session});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _selectedIndex = 0;
  bool _menuAcik = AppConfig.menuAcik;

  bool get _isAdmin => widget.session.role == 'admin';

  void _logout() {
    AppConfig.session = null;
    Navigator.of(context).pushNamedAndRemoveUntil('/', (route) => false);
  }

  @override
  Widget build(BuildContext context) {
    final screens = <Widget>[
      _Overview(session: widget.session),
      const LoanScreen(),
      const StudentListScreen(),
      const BookListScreen(),
      if (_isAdmin) const CatalogScreen(),
      const SettingsScreen(),
    ];
    final destinations = <NavigationRailDestination>[
      const NavigationRailDestination(
        icon: Icon(Icons.dashboard_outlined),
        selectedIcon: Icon(Icons.dashboard),
        label: Text('Genel Bakış'),
      ),
      const NavigationRailDestination(
        icon: Icon(Icons.swap_horiz_outlined),
        selectedIcon: Icon(Icons.swap_horiz),
        label: Text('Ödünç / İade'),
      ),
      const NavigationRailDestination(
        icon: Icon(Icons.inventory_2_outlined),
        selectedIcon: Icon(Icons.inventory_2),
        label: Text('Üyeler'),
      ),
      const NavigationRailDestination(
        icon: Icon(Icons.book_outlined),
        selectedIcon: Icon(Icons.book),
        label: Text('Kitaplar'),
      ),
      if (_isAdmin)
        const NavigationRailDestination(
          icon: Icon(Icons.calendar_view_day_outlined),
          selectedIcon: Icon(Icons.calendar_view_day),
          label: Text('Katalog'),
        ),
      const NavigationRailDestination(
        icon: Icon(Icons.settings_outlined),
        selectedIcon: Icon(Icons.settings),
        label: Text('Ayarlar'),
      ),
    ];
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          tooltip: _menuAcik ? 'Menüyü gizle' : 'Menüyü göster',
          icon: Icon(_menuAcik ? Icons.menu_open : Icons.menu),
          onPressed: () => setState(() {
            _menuAcik = !_menuAcik;
            AppConfig.menuAcik = _menuAcik;
          }),
        ),
        title: const Text('Kütüphane Yönetim Sistemi'),
        actions: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Center(
              child: Chip(
                avatar: Icon(Icons.badge_outlined, size: 18, color: Theme.of(context).colorScheme.primary),
                label: Text(
                  '${widget.session.fullName} (${widget.session.role})',
                  style: const TextStyle(fontSize: 13),
                ),
              ),
            ),
          ),
          IconButton(
            tooltip: 'Çıkış',
            icon: const Icon(Icons.logout),
            onPressed: _logout,
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: SafeArea(
        child: Row(
          children: [
            if (_menuAcik) ...[
              SizedBox(
                width: 220,
                child: NavigationRail(
                  selectedIndex: _selectedIndex,
                  onDestinationSelected: (i) => setState(() => _selectedIndex = i),
                  labelType: NavigationRailLabelType.all,
                  destinations: destinations,
                ),
              ),
              const VerticalDivider(thickness: 1, width: 1),
            ],
            Expanded(
              child: screens[_selectedIndex.clamp(0, screens.length - 1)],
            ),
          ],
        ),
      ),
    );
  }
}

class _Overview extends StatefulWidget {
  final Session session;

  const _Overview({required this.session});

  @override
  State<_Overview> createState() => _OverviewState();
}

class _OverviewState extends State<_Overview> {
  final _api = KutuphaneApi();
  bool _loading = true;
  String? _error;
  List<OduncKaydi> _loans = const [];
  int _uyeCount = 0;
  int _nushaCount = 0;
  int? _selectedLoanId;
  OverlayEntry? _menuEntry;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _kapatMenu();
    super.dispose();
  }

  void _kapatMenu() {
    _menuEntry?.remove();
    _menuEntry = null;
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final results = await Future.wait([
        _api.aktifOduncler(),
        _api.count('uyeler/'),
        _api.count('nushalar/'),
      ]);
      if (!mounted) return;
      final loans = (results[0] as List<OduncKaydi>).toList()
        ..sort((a, b) {
          final da = DateTime.tryParse(a.iadeTarihi ?? '');
          final db = DateTime.tryParse(b.iadeTarihi ?? '');
          if (da == null && db == null) return 0;
          if (da == null) return 1;
          if (db == null) return -1;
          return da.compareTo(db); // geçmişten geleceğe
        });
      setState(() {
        _loans = loans;
        _uyeCount = results[1] as int;
        _nushaCount = results[2] as int;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  int get _gecikenSayisi => _loans.where((l) => l.durum == 'gecikmis').length;

  /// Genel Bakış'tan hızlı iade: satıra çift tıklama.
  Future<void> _iadeAl(OduncKaydi l) async {
    if (mounted) setState(() => _selectedLoanId = l.id);
    final now = DateTime.now();
    final bugun = DateTime(now.year, now.month, now.day);
    final due = DateTime.tryParse(l.iadeTarihi ?? '');
    var gecikmis = l.durum == 'gecikmis' ||
        (due != null && DateTime(due.year, due.month, due.day).isBefore(bugun));
    var overdueDays = (due != null && gecikmis)
        ? bugun.difference(DateTime(due.year, due.month, due.day)).inDays
        : 0;
    String? penaltyPreview;

    // Ceza öngörüsünü backend'den (fast-query) al — politika/tolerans/rol dahil.
    final no = l.uyeNo ?? '';
    if (no.isNotEmpty) {
      try {
        final data = await _api.fastQuery(no);
        final active = (data?['active_loans'] as List<dynamic>? ?? const [])
            .whereType<Map<String, dynamic>>();
        for (final m in active) {
          if (m['id'] == l.id) {
            penaltyPreview = m['penalty_preview'] as String?;
            if (m['overdue_days'] is int) {
              overdueDays = m['overdue_days'] as int;
            }
            if (m['is_overdue'] is bool) {
              gecikmis = m['is_overdue'] as bool;
            }
            break;
          }
        }
      } catch (_) {}
    }
    if (!mounted) return;

    final loan = FastLoan(
      id: l.id,
      durum: l.durum,
      oduncTarihi: l.oduncTarihi,
      iadeTarihi: l.iadeTarihi,
      teslimTarihi: l.teslimTarihi,
      isOverdue: gecikmis,
      overdueDays: overdueDays,
      penaltyPreview: penaltyPreview,
      barkod: l.barkod,
      kitapBaslik: l.kitapBaslik,
      uyeNo: l.uyeNo,
      uyeAdSoyad: l.uyeAdSoyad,
    );
    final action = await showDialog<Map<String, String>>(
      context: context,
      builder: (_) => ReturnDialog(loan: loan, api: _api),
    );
    if (action == null) return;
    final resp = await _api.closeLoan(
      l.id,
      durum: action['durum']!,
      teslimTarihi: DateTime.now().toUtc().toIso8601String(),
      gecikmeCezasi: action['penalty'],
      odendi: action['odendi'] == 'true',
    );
    if (!mounted) return;
    final ok = resp.statusCode >= 200 && resp.statusCode < 300;
    showAppSnack(
      context,
      ok
          ? 'İade alındı (${durumLabel(action['durum']!)}).'
          : extractError(resp, fallback: 'İşlem başarısız oldu.'),
      error: !ok,
    );
    if (ok) _load();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return NotificationListener<ScrollNotification>(
      onNotification: (n) {
        if (n is ScrollUpdateNotification) _kapatMenu();
        return false;
      },
      child: Listener(
        onPointerDown: (_) => _kapatMenu(),
        child: ListView(
      padding: const EdgeInsets.all(24),
      children: [
        Text('Hoş geldiniz, ${widget.session.fullName}!',
            style: theme.textTheme.headlineSmall),
        const SizedBox(height: 8),
        Text('Ödünç, iade ve üye işlemleri için soldaki menüyü kullanın.',
            style: theme.textTheme.bodyMedium),
        const SizedBox(height: 24),
        Wrap(
          spacing: 16,
          runSpacing: 16,
          children: [
            _StatCard(
                icon: Icons.swap_horiz,
                title: 'Aktif Ödünçler',
                value: _loading ? '…' : '${_loans.length}'),
            _StatCard(
                icon: Icons.report_gmailerrorred,
                title: 'Gecikenler',
                value: _loading ? '…' : '$_gecikenSayisi'),
            _StatCard(
                icon: Icons.group_outlined,
                title: 'Üye',
                value: _loading ? '…' : '$_uyeCount'),
            _StatCard(
                icon: Icons.inventory_2_outlined,
                title: 'Kitap Nüshası',
                value: _loading ? '…' : '$_nushaCount'),
          ],
        ),
        const SizedBox(height: 24),
        Row(
          children: [
            Text('Aktif Ödünçler',
                style: theme.textTheme.titleMedium
                    ?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(width: 8),
            IconButton(
              tooltip: 'Yenile',
              icon: const Icon(Icons.refresh, size: 20),
              onPressed: _loading ? null : _load,
            ),
            const SizedBox(width: 4),
            Text('İşlemler (İade / Kitap / Üye) için satıra tıklayın.',
                style: theme.textTheme.bodySmall),
          ],
        ),
        const SizedBox(height: 4),
        _renkLejandi(theme),
        const SizedBox(height: 8),
        _aktifOdunclerBolumu(theme),
      ],
    ),
      ),
    );
  }

  /// İade tarihine göre satır renklerinin açıklaması.
  Widget _renkLejandi(ThemeData theme) {
    final bugun = DateTime.now();
    String iso(int gun) => bugun.add(Duration(days: gun)).toIso8601String();
    final items = <(String, Color)>[
      ('Gecikmiş', iadeTone(iso(-1), theme.brightness)),
      ('Bugün', iadeTone(iso(0), theme.brightness)),
      ('≤3 gün', iadeTone(iso(3), theme.brightness)),
      ('Normal', iadeTone(iso(10), theme.brightness)),
    ];
    return Wrap(
      spacing: 16,
      runSpacing: 4,
      children: [
        for (final it in items)
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 12,
                height: 12,
                decoration: BoxDecoration(
                  color: it.$2.withValues(alpha: 0.35),
                  borderRadius: BorderRadius.circular(3),
                  border: Border.all(color: it.$2),
                ),
              ),
              const SizedBox(width: 6),
              Text(it.$1, style: theme.textTheme.bodySmall),
            ],
          ),
      ],
    );
  }

  /// Satır hücresi: basıldığı anda işlem menüsü (İade / Kitap / Üye).
  Widget _hucre(OduncKaydi l, Widget child) => GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTapDown: (d) {
          setState(() => _selectedLoanId = l.id);
          _satirMenu(l, d.globalPosition);
        },
        child: child,
      );

  /// Satıra tıklanınca imlecin altında yatay işlem menüsü (modal değil).
  void _satirMenu(OduncKaydi l, Offset globalPos) {
    _kapatMenu();
    final items = const [
      RadialMenuItem(icon: Icons.login, label: 'İade', value: 'iade'),
      RadialMenuItem(
          icon: Icons.menu_book_outlined, label: 'Kitap', value: 'kitap'),
      RadialMenuItem(icon: Icons.person_outline, label: 'Üye', value: 'uye'),
    ];
    scheduleMicrotask(() {
      if (!mounted) return;
      _menuEntry = buildHorizontalRowMenu(
        globalPosition: globalPos,
        items: items,
        onSelect: (value) {
          _kapatMenu();
          _menuSecildi(l, value);
        },
      );
      Overlay.of(context).insert(_menuEntry!);
    });
  }

  Future<void> _menuSecildi(OduncKaydi l, String secim) async {
    switch (secim) {
      case 'iade':
        await _iadeAl(l);
      case 'kitap':
        _kitapAc(l);
      case 'uye':
        _uyeAc(l);
    }
  }

  void _kitapAc(OduncKaydi l) {
    final kitap = l.kitap;
    if (kitap == null) {
      showAppSnack(context, 'Kitap bilgisi bulunamadı.', error: true);
      return;
    }
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => BookDetailScreen(kitap: kitap)),
    );
  }

  void _uyeAc(OduncKaydi l) {
    final uye = l.uye;
    if (uye == null) {
      showAppSnack(context, 'Üye bilgisi bulunamadı.', error: true);
      return;
    }
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => StudentDetailScreen(uye: uye)),
    );
  }

  Widget _aktifOdunclerBolumu(ThemeData theme) {
    if (_loading) {
      return const Padding(
        padding: EdgeInsets.all(24),
        child: Center(child: CircularProgressIndicator()),
      );
    }
    if (_error != null) {
      return Padding(
        padding: const EdgeInsets.all(16),
        child: Text('Aktif ödünçler yüklenemedi.\n$_error',
            style: TextStyle(color: dangerColor(context))),
      );
    }
    if (_loans.isEmpty) {
      return const Padding(
        padding: EdgeInsets.all(16),
        child: Text('Şu an aktif ödünç yok.'),
      );
    }
    return Card(
      clipBehavior: Clip.antiAlias,
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: DataTable(
          columns: const [
            DataColumn(label: Text('Kitap')),
            DataColumn(label: Text('Üye')),
            DataColumn(label: Text('Ödünç')),
            DataColumn(label: Text('İade')),
            DataColumn(label: Text('Durum')),
          ],
          rows: [
            for (final l in _loans)
              DataRow(
                selected: _selectedLoanId == l.id,
                color: WidgetStatePropertyAll<Color?>(
                  _selectedLoanId == l.id
                      ? Color.alphaBlend(
                          theme.colorScheme.primary.withValues(alpha: 0.24),
                          iadeTone(l.iadeTarihi, theme.brightness,
                                  durum: l.durum)
                              .withValues(alpha: 0.14),
                        )
                      : iadeTone(l.iadeTarihi, theme.brightness, durum: l.durum)
                          .withValues(alpha: 0.14),
                ),
                cells: [
                  DataCell(_hucre(l, Text(l.kitapBaslik))),
                  DataCell(_hucre(
                      l,
                      Text([
                        if ((l.uyeAdSoyad ?? '').isNotEmpty) l.uyeAdSoyad!,
                        if ((l.uyeNo ?? '').isNotEmpty) '(${l.uyeNo})',
                      ].join(' ')))),
                  DataCell(_hucre(l, Text(formatDate(l.oduncTarihi)))),
                  DataCell(_hucre(l, Text(formatDate(l.iadeTarihi)))),
                  DataCell(_hucre(
                      l,
                      Text(
                        durumLabel(l.durum),
                        style: TextStyle(
                          color: durumColor(l.durum, theme.brightness),
                          fontWeight: FontWeight.w600,
                        ),
                      ))),
                ],
              ),
          ],
        ),
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String value;

  const _StatCard({required this.icon, required this.title, required this.value});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 20, color: theme.colorScheme.primary),
            const SizedBox(width: 10),
            Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(value,
                    style: theme.textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.bold, height: 1.1)),
                Text(title, style: theme.textTheme.bodySmall),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _api = KutuphaneApi();
  bool _busy = false;

  Future<void> _kendimiUyeEkle() async {
    final ad = TextEditingController();
    final soyad = TextEditingController();
    final uyeNo = TextEditingController();
    List<Map<String, dynamic>> roller = [];
    try {
      roller = await _api.roller();
    } catch (_) {}
    if (!mounted) return;
    int? rolId = roller.isNotEmpty ? roller.first['id'] as int? : null;

    final onay = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setLocal) => AlertDialog(
          title: const Text('Kendimi üye olarak ekle'),
          content: SizedBox(
            width: 360,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                    controller: ad,
                    autofocus: true,
                    decoration: const InputDecoration(
                        labelText: 'Ad', isDense: true)),
                const SizedBox(height: 8),
                TextField(
                    controller: soyad,
                    decoration: const InputDecoration(
                        labelText: 'Soyad', isDense: true)),
                const SizedBox(height: 8),
                TextField(
                    controller: uyeNo,
                    decoration: const InputDecoration(
                        labelText: 'Numara (opsiyonel)', isDense: true)),
                const SizedBox(height: 8),
                if (roller.isNotEmpty)
                  DropdownButtonFormField<int>(
                    initialValue: rolId,
                    isExpanded: true,
                    decoration: const InputDecoration(
                        labelText: 'Rol', isDense: true),
                    items: [
                      for (final r in roller)
                        DropdownMenuItem<int>(
                          value: r['id'] as int,
                          child: Text((r['ad'] ?? '').toString()),
                        ),
                    ],
                    onChanged: (v) => setLocal(() => rolId = v),
                  ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(false),
              child: const Text('Vazgeç'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(ctx).pop(true),
              child: const Text('Ekle'),
            ),
          ],
        ),
      ),
    );
    if (onay != true) return;
    setState(() => _busy = true);
    final res = await _api.uyeBenEkle(
      ad: ad.text,
      soyad: soyad.text,
      rolId: rolId,
      uyeNo: uyeNo.text,
    );
    ad.dispose();
    soyad.dispose();
    uyeNo.dispose();
    if (!mounted) return;
    setState(() => _busy = false);
    showAppSnack(
      context,
      res.uye != null ? 'Üye kaydınız oluşturuldu.' : (res.error ?? 'Kayıt yapılamadı.'),
      error: res.uye == null,
    );
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        Text('Ayarlar', style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 4),
        Text('Renk temasını seçin; değişiklik anında uygulanır ve kaydedilir.',
            style: Theme.of(context).textTheme.bodyMedium),
        const SizedBox(height: 16),
        Card(
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: ValueListenableBuilder<AppTheme>(
              valueListenable: appThemeController,
              builder: (context, current, _) => Column(
                children: [
                  for (final theme in AppTheme.values)
                    ListTile(
                      leading: CircleAvatar(
                        backgroundColor: theme.seed,
                        child: Icon(
                          theme.isDark ? Icons.dark_mode : Icons.light_mode,
                          color: theme.seed.computeLuminance() > 0.5
                              ? Colors.black87
                              : Colors.white,
                        ),
                      ),
                      title: Text(theme.label),
                      subtitle: Text(theme.description),
                      selected: current == theme,
                      trailing: current == theme
                          ? Icon(Icons.check_circle,
                              color: scheme.primary)
                          : null,
                      onTap: () => appThemeController.select(theme),
                    ),
                ],
              ),
            ),
          ),
        ),
        const SizedBox(height: 16),
        Card(
          child: ListTile(
            leading: const Icon(Icons.person_add_alt_1),
            title: const Text('Kendimi üye olarak ekle'),
            subtitle: const Text(
                'Personel/öğretmen de ödünç alabilsin diye size bir üye kaydı oluşturur.'),
            enabled: !_busy,
            onTap: _busy ? null : _kendimiUyeEkle,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'Bilgi: Tüm temalarda buton, snackbar ve kart gibi yüzeylerdeki '
          'yazılar şema rolleriyle otomatik okunabilir kontrast alır.',
          style: Theme.of(context)
              .textTheme
              .bodySmall
              ?.copyWith(color: scheme.onSurfaceVariant),
        ),
      ],
    );
  }
}