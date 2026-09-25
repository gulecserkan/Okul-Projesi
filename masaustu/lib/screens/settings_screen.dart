import 'dart:convert';

import 'package:file_selector/file_selector.dart';
import 'package:flutter/material.dart';

import '../api/auth_api.dart';
import '../config.dart';
import '../theme.dart';
import 'student_import_dialog.dart';

/// Ayarlar ekranı.
///
/// Yalnızca istemciye ait ayarlar (görünüm, sunucu adresi, hesap) ve admin'e
/// özel toplu öğrenci aktarımı burada. Rol/ödünç politikası, bildirim ve kurum
/// ayarları Django admin paneline taşındı (tek config yüzeyi).
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  bool get _admin => AppConfig.session?.role == 'admin';

  @override
  Widget build(BuildContext context) {
    final tabs = <Tab>[
      const Tab(text: 'Görünüm'),
      const Tab(text: 'Sunucu'),
      if (_admin) const Tab(text: 'Öğrenci Aktarımı'),
      const Tab(text: 'Hesap'),
    ];
    final views = <Widget>[
      const _GorunumTab(),
      const _SunucuTab(),
      if (_admin) const _OgrenciAktarTab(),
      const _HesapTab(),
    ];
    return DefaultTabController(
      length: tabs.length,
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 16, 24, 0),
            child: Align(
              alignment: Alignment.centerLeft,
              child: Text('Ayarlar',
                  style: Theme.of(context)
                      .textTheme
                      .titleLarge
                      ?.copyWith(fontWeight: FontWeight.bold)),
            ),
          ),
          TabBar(isScrollable: true, tabs: tabs),
          Expanded(
            child: TabBarView(children: views),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------- Görünüm

class _GorunumTab extends StatelessWidget {
  const _GorunumTab();

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        Text('Renk temasını seçin; değişiklik anında uygulanır ve kaydedilir.',
            style: Theme.of(context).textTheme.bodyMedium),
        const SizedBox(height: 12),
        Card(
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
                        ? Icon(Icons.check_circle, color: scheme.primary)
                        : null,
                    onTap: () => appThemeController.select(theme),
                  ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------- Sunucu

class _SunucuTab extends StatefulWidget {
  const _SunucuTab();

  @override
  State<_SunucuTab> createState() => _SunucuTabState();
}

class _SunucuTabState extends State<_SunucuTab> {
  late final TextEditingController _server =
      TextEditingController(text: AppConfig.apiBaseUrl);
  bool _busy = false;
  String? _mesaj;

  @override
  void dispose() {
    _server.dispose();
    super.dispose();
  }

  Future<void> _kaydet() async {
    final url = _server.text.trim();
    if (url.isEmpty) {
      setState(() => _mesaj = 'Sunucu adresi boş olamaz.');
      return;
    }
    AppConfig.apiBaseUrl = url;
    setState(() => _mesaj = 'Sunucu adresi kaydedildi.');
  }

  Future<void> _test() async {
    setState(() {
      _busy = true;
      _mesaj = null;
    });
    AppConfig.apiBaseUrl = _server.text.trim();
    final ok = await AuthApi().healthCheck();
    if (!mounted) return;
    setState(() {
      _busy = false;
      _mesaj = ok ? 'Sunucuya ulaşıldı.' : 'Sunucuya ulaşılamadı.';
    });
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        Text('Sunucu adresi (API kökü)',
            style: Theme.of(context).textTheme.bodyMedium),
        const SizedBox(height: 8),
        TextField(
          controller: _server,
          decoration: const InputDecoration(
            hintText: 'http://127.0.0.1:8000/api',
            border: OutlineInputBorder(),
            isDense: true,
          ),
        ),
        const SizedBox(height: 12),
        Row(children: [
          FilledButton.icon(
            onPressed: _busy ? null : _kaydet,
            icon: const Icon(Icons.save_outlined),
            label: const Text('Kaydet'),
          ),
          const SizedBox(width: 8),
          OutlinedButton.icon(
            onPressed: _busy ? null : _test,
            icon: const Icon(Icons.wifi_tethering),
            label: const Text('Bağlantıyı test et'),
          ),
        ]),
        if (_mesaj != null) ...[
          const SizedBox(height: 12),
          Text(_mesaj!),
        ],
      ],
    );
  }
}

// ---------------------------------------------------------------- Öğrenci Aktarımı

/// K9.13: dönem başı toplu öğrenci aktarımı — yalnız admin sekmesi.
class _OgrenciAktarTab extends StatelessWidget {
  const _OgrenciAktarTab();

  Future<void> _sec(BuildContext context) async {
    const typeGroup = XTypeGroup(label: 'CSV', extensions: ['csv', 'txt']);
    final file = await openFile(acceptedTypeGroups: const [typeGroup]);
    if (file == null) return;
    final bytes = await file.readAsBytes();
    if (!context.mounted) return;
    final csv = _decodeCsv(bytes);
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (_) => StudentImportDialog(csv: csv),
    );
    if (result == null || !context.mounted) return;
    final ozet = (result['ozet'] as Map?)?.cast<String, dynamic>() ?? {};
    showAppSnack(
      context,
      'İçe aktarma tamamlandı — yeni: ${ozet['yeni'] ?? 0}, '
      'yenileme: ${ozet['yenileme'] ?? 0}, '
      'pasife: ${ozet['pasife_cekilecek'] ?? 0}, '
      'hatalı: ${ozet['hatali'] ?? 0}.',
    );
    final arsivAday = (result['arsiv_aday'] as num?)?.toInt() ?? 0;
    if (arsivAday > 0 && context.mounted) {
      await showDialog<void>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Arşiv hatırlatması'),
          content: Text(
              '$arsivAday öğrenci 3+ yıldır pasif ve arşive uygun. '
              'Arşivleme Django admin panelinden yapılır: '
              'Üyeler → "Arşive Taşı (ön izleme)".'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Tamam'),
            ),
          ],
        ),
      );
    }
  }

  /// CSV baytlarını çözer: UTF-8; bozuksa cp1254 uyumlu.
  String _decodeCsv(List<int> bytes) {
    try {
      return utf8.decode(bytes);
    } on FormatException {
      return latin1
          .decode(bytes)
          .replaceAll('Ð', 'Ğ')
          .replaceAll('Ý', 'İ')
          .replaceAll('Þ', 'Ş')
          .replaceAll('ð', 'ğ')
          .replaceAll('ý', 'ı')
          .replaceAll('þ', 'ş');
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        Text('Dönem başı toplu öğrenci aktarımı (K9.13)',
            style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        Text(
          'e-okul CSV dosyası: ogrenci_no (veya uye_no), ad, soyad, sinif. '
          'Önce önizleme gösterilir; onaylarsanız uygulanır. Yalnız Öğrenci '
          'rolü kapsanır; öğretmen/editör etkilenmez. Bu işlem yalnızca admin '
          'tarafından yapılabilir.',
          style: Theme.of(context).textTheme.bodySmall,
        ),
        const SizedBox(height: 16),
        Align(
          alignment: Alignment.centerLeft,
          child: FilledButton.icon(
            onPressed: () => _sec(context),
            icon: const Icon(Icons.upload_file),
            label: const Text('CSV Dosyası Seç ve İçe Aktar'),
          ),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------- Hesap

/// Hesap sekmesi (salt-okunur): masaüstü hesabı yalnız User'dır (personel/admin);
/// üye (öğrenci/öğretmen/editör) kayıtları mobildedir ve masaüstünden ayrı açılır (K9.6).
class _HesapTab extends StatelessWidget {
  const _HesapTab();

  String _duz(String v) => v.trim().isEmpty ? '—' : v;

  @override
  Widget build(BuildContext context) {
    final s = AppConfig.session;
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        Card(
          child: ListTile(
            leading: const Icon(Icons.person_outline),
            title: const Text('Kullanıcı adı'),
            subtitle: Text(_duz(s?.username ?? '')),
          ),
        ),
        Card(
          child: ListTile(
            leading: const Icon(Icons.badge_outlined),
            title: const Text('Rol'),
            subtitle: Text(_duz(s?.role ?? '')),
          ),
        ),
        Card(
          child: ListTile(
            leading: const Icon(Icons.account_circle_outlined),
            title: const Text('Tam ad'),
            subtitle: Text(_duz(s?.fullName ?? '')),
          ),
        ),
        const Padding(
          padding: EdgeInsets.fromLTRB(16, 8, 16, 0),
          child: Text(
            'Masaüstü hesabınız personel/admin yönetim erişimi içindir ve üye '
            '(öğrenci/öğretmen/editör) kaydıyla bağlantılı değildir. Ödünç almak için '
            'ayrı bir üye kaydı admin (öğretmen/editör) veya personel (öğrenci) '
            'tarafından oluşturulur. Rol/ödünç kuralları, bildirim ve kurum ayarları '
            'Django admin panelinden yönetilir.',
            style: TextStyle(fontSize: 12, color: Colors.grey),
          ),
        ),
      ],
    );
  }
}
