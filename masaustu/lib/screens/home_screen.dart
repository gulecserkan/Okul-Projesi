import 'package:flutter/material.dart';

import '../config.dart';
import '../api/kutuphane_api.dart';
import '../theme.dart';
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
            Expanded(
              child: screens[_selectedIndex.clamp(0, screens.length - 1)],
            ),
          ],
        ),
      ),
    );
  }
}

class _Overview extends StatelessWidget {
  final Session session;

  const _Overview({required this.session});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        Text('Hoş geldiniz, ${session.fullName}!',
            style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 8),
        Text('Ödünç, iade ve üye işlemleri için sağdaki menüyü kullanın.',
            style: Theme.of(context).textTheme.bodyMedium),
        const SizedBox(height: 24),
        Wrap(
          spacing: 16,
          runSpacing: 16,
          children: const [
            _StatCard(icon: Icons.swap_horiz, title: 'Aktif Ödünçler', value: '—'),
            _StatCard(icon: Icons.report_gmailerrorred, title: 'Gecikenler', value: '—'),
            _StatCard(icon: Icons.group_outlined, title: 'Üye', value: '—'),
            _StatCard(icon: Icons.inventory_2_outlined, title: 'Kitap Nüshası', value: '—'),
          ],
        ),
      ],
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
    return SizedBox(
      width: 220,
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, color: Theme.of(context).colorScheme.primary),
              const SizedBox(height: 8),
              Text(value,
                  style: Theme.of(context)
                      .textTheme
                      .headlineMedium
                      ?.copyWith(fontWeight: FontWeight.bold)),
              Text(title, style: Theme.of(context).textTheme.bodySmall),
            ],
          ),
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