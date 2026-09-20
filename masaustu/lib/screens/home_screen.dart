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
import 'settings_screen.dart';
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
  Offset? _sonTikPos;

  // Hızlı işlem (barkod / üye no)
  final _hizliController = TextEditingController();
  final _hizliFocus = FocusNode();
  bool _hizliBusy = false;
  String? _hizliMesaj;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _kapatMenu();
    _hizliController.dispose();
    _hizliFocus.dispose();
    super.dispose();
  }

  void _kapatMenu() {
    _menuEntry?.remove();
    _menuEntry = null;
  }

  /// Odağı bir sonraki karede hızlı işlem alanına verir (diyalog kapanışı
  /// sırasında odak değiştirmemek için ertelenir).
  void _hizliOdakla() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted && _hizliFocus.canRequestFocus) _hizliFocus.requestFocus();
    });
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

  /// Hızlı işlem: barkod veya üye no. İkinci veri ayrı bir popup'ta istenir.
  /// - Barkod: ödünçteyse iade; müsaitse popup ile üye no istenir.
  /// - Üye no: popup ile kitap barkodu istenir.
  Future<void> _hizliIslem(String raw) async {
    final q = raw.trim();
    if (q.isEmpty || _hizliBusy) return;
    _hizliController.clear();

    setState(() {
      _hizliBusy = true;
      _hizliMesaj = null;
    });
    final data = await _api.fastQuery(q);
    if (!mounted) return;
    setState(() => _hizliBusy = false);
    if (data == null) {
      setState(() => _hizliMesaj = 'Eşleşme bulunamadı.');
      _hizliOdakla();
      return;
    }
    final type = data['type'];
    if (type == 'book_copy') {
      final copy = data['copy'] as Map<String, dynamic>?;
      final durum = (copy?['durum'] ?? '').toString();
      final loan = data['loan'] as Map<String, dynamic>?;
      if (loan != null && (durum == 'oduncte' || durum == 'gecikmis')) {
        await _hizliIade(loan,
            book: data['book'] as Map<String, dynamic>?, copy: copy);
      } else if (durum == 'mevcut') {
        final book = data['book'] as Map<String, dynamic>?;
        final baslik = (book?['baslik'] ?? q).toString();
        final barkod = (copy?['barkod'] ?? q).toString();
        final uyeNo = await _hizliIkinciSor(
          baslik: 'Üye No',
          aciklama:
              '"$baslik" kitabını ödünç vermek için üye numarasını okutun/girin.',
          ipucu: 'Üye No',
        );
        if (uyeNo == null || uyeNo.trim().isEmpty) {
          _hizliOdakla();
          return;
        }
        await _hizliOdunc(uyeNo.trim(), barkod);
      } else {
        setState(
            () => _hizliMesaj = 'Bu nüsha ödünç verilemez (durum: $durum).');
        _hizliOdakla();
      }
      return;
    }
    if (type == 'student') {
      final s = data['student'] as Map<String, dynamic>?;
      final no = (s?['no'] ?? s?['uye_no'] ?? q).toString();
      final adSoyad = '${s?['ad'] ?? ''} ${s?['soyad'] ?? ''}'.trim();
      final barkod = await _hizliIkinciSor(
        baslik: 'Kitap Barkodu',
        aciklama:
            '$adSoyad ($no) için ödünç verilecek kitabın barkodunu okutun/girin.',
        ipucu: 'Barkod',
      );
      if (barkod == null || barkod.trim().isEmpty) {
        _hizliOdakla();
        return;
      }
      await _hizliOdunc(no, barkod.trim());
      return;
    }
    setState(
        () => _hizliMesaj = 'Bu arama için Ödünç / İade sayfasını kullanın.');
    _hizliOdakla();
  }

  /// İkinci veriyi (üye no / barkod) ayrı bir popup input'unda, açıklamayla ister.
  Future<String?> _hizliIkinciSor({
    required String baslik,
    required String aciklama,
    required String ipucu,
  }) {
    return showDialog<String>(
      context: context,
      builder: (_) => _HizliIkinciDialog(
        baslik: baslik,
        aciklama: aciklama,
        ipucu: ipucu,
      ),
    );
  }

  Future<void> _hizliIade(Map<String, dynamic> loanJson,
      {Map<String, dynamic>? book, Map<String, dynamic>? copy}) async {
    final temel = FastLoan.fromJson(loanJson);
    final loan = FastLoan(
      id: temel.id,
      durum: temel.durum,
      oduncTarihi: temel.oduncTarihi,
      iadeTarihi: temel.iadeTarihi,
      teslimTarihi: temel.teslimTarihi,
      isOverdue: temel.isOverdue,
      overdueDays: temel.overdueDays,
      penaltyPreview: temel.penaltyPreview,
      barkod: (copy?['barkod'] ?? temel.barkod)?.toString(),
      kitapBaslik: (book?['baslik'] ?? temel.kitapBaslik)?.toString(),
      uyeNo: temel.uyeNo,
      uyeAdSoyad: temel.uyeAdSoyad,
    );

    // Ceza/gecikme varsa onay + ceza/ödeme bilgisi için iade diyaloğu açılır.
    final cezaVar = loan.isOverdue ||
        ((double.tryParse(loan.penaltyPreview ?? '') ?? 0) > 0);

    var durum = 'teslim';
    var ceza = loan.penaltyPreview;
    var odendi = false;
    String? kapanisNotu;

    if (cezaVar) {
      final action = await showDialog<Map<String, String>>(
        context: context,
        builder: (_) => ReturnDialog(loan: loan, api: _api),
      );
      if (action == null) {
        _hizliOdakla();
        return;
      }
      durum = action['durum']!;
      ceza = action['penalty'];
      odendi = action['odendi'] == 'true';
      kapanisNotu = action['not'];
    }

    setState(() => _hizliBusy = true);
    final resp = await _api.closeLoan(
      loan.id,
      durum: durum,
      teslimTarihi: DateTime.now().toUtc().toIso8601String(),
      gecikmeCezasi: ceza,
      odendi: odendi,
      kapanisNotu: kapanisNotu,
    );
    if (!mounted) return;
    setState(() {
      _hizliBusy = false;
      _hizliMesaj = null;
    });
    final ok = resp.statusCode >= 200 && resp.statusCode < 300;
    final kim = [loan.kitapBaslik, loan.uyeAdSoyad]
        .where((s) => s != null && s.isNotEmpty)
        .join(' — ');
    final cezaNotu = (ceza != null && (double.tryParse(ceza) ?? 0) > 0)
        ? ' (ceza ₺$ceza${odendi ? ', ödendi' : ''})'
        : '';
    showAppSnack(
      context,
      ok
          ? 'İade alındı${kim.isEmpty ? '' : ': $kim'}$cezaNotu.'
          : extractError(resp, fallback: 'İade yapılamadı.'),
      error: !ok,
    );
    if (ok) _load();
    _hizliOdakla();
  }

  Future<void> _hizliOdunc(String uyeNo, String barkod) async {
    setState(() => _hizliBusy = true);
    final resp = await _api.checkout(uyeNo, barkod);
    if (!mounted) return;
    setState(() {
      _hizliBusy = false;
      _hizliMesaj = null;
    });
    final ok = resp.statusCode >= 200 && resp.statusCode < 300;
    showAppSnack(
      context,
      ok
          ? '$barkod ödünç verildi.'
          : extractError(resp, fallback: 'Ödünç verilemedi.'),
      error: !ok,
    );
    if (ok) _load();
    _hizliOdakla();
  }

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
      kapanisNotu: action['not'],
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
        onPointerDown: (e) {
          _sonTikPos = e.position;
          _kapatMenu();
        },
        child: ListView(
      padding: const EdgeInsets.all(24),
      children: [
        Text('Hoş geldiniz, ${widget.session.fullName}!',
            style: theme.textTheme.headlineSmall),
        const SizedBox(height: 8),
        Text('Ödünç, iade ve üye işlemleri için soldaki menüyü kullanın.',
            style: theme.textTheme.bodyMedium),
        const SizedBox(height: 16),
        _hizliIslemKarti(theme),
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

  /// Hızlı işlem kartı: barkod/üye no ile hızlı iade-ödünç.
  Widget _hizliIslemKarti(ThemeData theme) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.qr_code_scanner, color: theme.colorScheme.primary),
                const SizedBox(width: 8),
                Text('Hızlı İşlem',
                    style: theme.textTheme.titleSmall
                        ?.copyWith(fontWeight: FontWeight.bold)),
              ],
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _hizliController,
              focusNode: _hizliFocus,
              autofocus: true,
              enabled: !_hizliBusy,
              onSubmitted: _hizliIslem,
              decoration: InputDecoration(
                hintText: 'Barkod veya üye no okutun...',
                prefixIcon: _hizliBusy
                    ? const Padding(
                        padding: EdgeInsets.all(12),
                        child: SizedBox(
                            height: 18,
                            width: 18,
                            child: CircularProgressIndicator(strokeWidth: 2)),
                      )
                    : const Icon(Icons.qr_code_scanner),
                border: const OutlineInputBorder(),
                isDense: true,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              _hizliMesaj ??
                  'Barkod ödünçteyse iade edilir (gecikme cezası varsa iade '
                      'penceresi açılır); müsaitse üye no ayrı bir pencerede sorulur. '
                      'Üye no girilirse kitap barkodu sorulur.',
              style: theme.textTheme.bodySmall?.copyWith(
                color: _hizliMesaj != null
                    ? theme.colorScheme.primary
                    : theme.colorScheme.onSurfaceVariant,
              ),
            ),
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

  /// Satıra tıklanınca imlecin altında yatay işlem menüsü (modal değil).
  void _satirMenu(OduncKaydi l, Offset globalPos) {
    if (mounted) setState(() => _selectedLoanId = l.id);
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
        context: context,
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
          showCheckboxColumn: false,
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
                onSelectChanged: (_) =>
                    _satirMenu(l, _sonTikPos ?? Offset.zero),
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
                  DataCell(Text(l.kitapBaslik)),
                  DataCell(Text([
                    if ((l.uyeAdSoyad ?? '').isNotEmpty) l.uyeAdSoyad!,
                    if ((l.uyeNo ?? '').isNotEmpty) '(${l.uyeNo})',
                  ].join(' '))),
                  DataCell(Text(formatDate(l.oduncTarihi))),
                  DataCell(Text(formatDate(l.iadeTarihi))),
                  DataCell(Text(
                    durumLabel(l.durum),
                    style: TextStyle(
                      color: durumColor(l.durum, theme.brightness),
                      fontWeight: FontWeight.w600,
                    ),
                  )),
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

/// Hızlı işlemin ikinci adımı için ayrı, açıklamalı popup input'u.
class _HizliIkinciDialog extends StatefulWidget {
  final String baslik;
  final String aciklama;
  final String ipucu;

  const _HizliIkinciDialog({
    required this.baslik,
    required this.aciklama,
    required this.ipucu,
  });

  @override
  State<_HizliIkinciDialog> createState() => _HizliIkinciDialogState();
}

class _HizliIkinciDialogState extends State<_HizliIkinciDialog> {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _tamam() => Navigator.of(context).pop(_controller.text);

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(widget.baslik),
      content: SizedBox(
        width: 380,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(widget.aciklama),
            const SizedBox(height: 12),
            TextField(
              controller: _controller,
              autofocus: true,
              decoration: InputDecoration(
                labelText: widget.ipucu,
                border: const OutlineInputBorder(),
                isDense: true,
              ),
              onSubmitted: (_) => _tamam(),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Vazgeç'),
        ),
        FilledButton(onPressed: _tamam, child: const Text('Tamam')),
      ],
    );
  }
}
