import 'dart:convert';

import 'package:file_selector/file_selector.dart';
import 'package:flutter/material.dart';

import '../api/auth_api.dart';
import '../config.dart';
import '../printing/print_helpers.dart';
import '../printing/printer_service.dart';
import '../printing/rulo_durum.dart';
import '../theme.dart';
import 'student_import_dialog.dart';

/// A4 yazıcı seçiminde "Dosyaya yaz (PDF)" seçeneğinin gösterge değeri (K14.10).
const String _a4DosyaModu = '__a4Dosya__';

/// Ayarlar ekranı.
///
/// Yalnızca istemciye ait ayarlar (görünüm, sunucu adresi, yazıcı, hesap) ve admin'e
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
      const Tab(text: 'Yazıcılar'),
      if (_admin) const Tab(text: 'Öğrenci Aktarımı'),
      const Tab(text: 'Hesap'),
    ];
    final views = <Widget>[
      const _GorunumTab(),
      const _SunucuTab(),
      const _YazicilarTab(),
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

// ---------------------------------------------------------------- Yazıcılar
/// K14: fiş/etiket/A4 yazıcı seçimi, otomatik fiş anahtarları ve test basımı.
class _YazicilarTab extends StatefulWidget {
  const _YazicilarTab();

  @override
  State<_YazicilarTab> createState() => _YazicilarTabState();
}

class _YazicilarTabState extends State<_YazicilarTab> {
  final _service = PrinterServices.instance;

  bool _yukleniyor = true;
  String? _cupsUyarisi;
  List<PrinterInfo> _printers = const [];
  PrinterPrefs _prefs = AppConfig.printer;
  KurumBilgisi _kurum = AppConfig.kurumYedek ?? const KurumBilgisi();
  String? _testMesaj;
  bool _testYukleniyor = false;

  @override
  void initState() {
    super.initState();
    _yenile();
  }

  Future<void> _yenile() async {
    setState(() {
      _yukleniyor = true;
      _cupsUyarisi = null;
    });
    if (!await _service.cupsKurulu()) {
      setState(() {
        _yukleniyor = false;
        _cupsUyarisi = 'CUPS komutları bulunamadı. Sistem yöneticisinden '
            '"sudo apt-get install -y cups-client cups" çalıştırılmalı.';
      });
      return;
    }
    final printers = await _service.listPrinters();
    final kurum = await kurumGetir();
    if (!mounted) return;
    setState(() {
      _printers = printers;
      _kurum = kurum;
      _yukleniyor = false;
    });
  }

  void _kaydet(PrinterPrefs prefs) {
    setState(() => _prefs = prefs);
    AppConfig.printer = prefs;
  }

  Future<void> _testEt({
    required String rol,
    required String kuyruk,
    required Future<List<int>> Function(KurumBilgisi) uretici,
  }) async {
    if (kuyruk.trim().isEmpty) {
      showAppSnack(context, '$rol yazıcısı seçilmedi.', error: true);
      return;
    }
    setState(() {
      _testYukleniyor = true;
      _testMesaj = null;
    });
    final pdf = await uretici(_kurum);
    final sonuc = await _service.printPdf(kuyruk.trim(),
        pdf, title: 'test-basimi');
    if (!mounted) return;
    setState(() {
      _testYukleniyor = false;
      _testMesaj = sonuc.message;
    });
    showAppSnack(context, sonuc.message, error: !sonuc.ok);
  }

  /// K14.10: Test A4 — kuyruk hazırsa basar, "Dosyaya yaz"/boş/pasifse kaydeder.
  Future<void> _testA4() async {
    setState(() {
      _testYukleniyor = true;
      _testMesaj = null;
    });
    final sonuc = await a4Bas(
      context,
      () => TestPdf.a4(_kurum),
      dosyaOnAdi: 'kutuphane_a4_test.pdf',
      kuyruk: _prefs.a4Yazici,
    );
    if (!mounted) return;
    setState(() {
      _testYukleniyor = false;
      _testMesaj = sonuc.message;
    });
    showAppSnack(context, sonuc.message, error: !sonuc.ok);
  }

  /// K14.9/11: ortak yazıcıda rulo bildirimi (durum + ölçü kurulumu).
  Future<void> _ruloSec(RuloTipi tip) async {
    await ruloBildir(context, tip);
    if (!mounted) return;
    setState(() => _prefs = AppConfig.printer);
    await _yenile();
  }

  bool get _ortakYaziciVar => ortakKuyruk() != null;

  List<String> _kuyrukAdlari() {
    final set = <String>{};
    for (final p in _printers) {
      set.add(p.name);
    }
    for (final q in [_prefs.fisYazici, _prefs.etiketYazici, _prefs.a4Yazici]) {
      if (q.trim().isNotEmpty) set.add(q.trim());
    }
    final list = set.toList()..sort();
    return list;
  }

  PrinterInfo? _bul(String? name) {
    for (final p in _printers) {
      if (p.name == name) return p;
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (_cupsUyarisi != null) ...[
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: theme.colorScheme.errorContainer,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  Icon(Icons.warning_amber,
                      color: theme.colorScheme.onErrorContainer),
                  const SizedBox(width: 8),
                  Expanded(child: Text(_cupsUyarisi!)),
                ],
              ),
            ),
            const SizedBox(height: 16),
          ],
          if (_yukleniyor)
            const Padding(
              padding: EdgeInsets.all(24),
              child: Center(child: CircularProgressIndicator()),
            )
          else ...[
            Row(
              children: [
                Text('CUPS yazıcıları',
                    style: theme.textTheme.titleMedium),
                const Spacer(),
                TextButton.icon(
                  onPressed: _yenile,
                  icon: const Icon(Icons.refresh, size: 18),
                  label: const Text('Yenile'),
                ),
              ],
            ),
            if (_printers.isEmpty && _cupsUyarisi == null)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(
                    'Sistemde algılanan yazıcı yok. Yazıcıyı bilgisayara '
                    'bağlayıp yazıcı ayarlarından (CUPS) yazıcı ekleyin, '
                    'sonra "Yenile"ye basın. ',
                    style: theme.textTheme.bodySmall),
              ),
            const SizedBox(height: 8),
            _KuyrukSecici(
              etiket: 'Fiş yazıcısı (termal, 70 mm)',
              value: _prefs.fisYazici,
              kuyruklar: _kuyrukAdlari(),
              printer: _bul(_prefs.fisYazici),
              onChanged: (v) => _kaydet(_prefs.copyWith(fisYazici: v)),
            ),
            _KuyrukSecici(
              etiket: 'Etiket yazıcısı (57×40 mm)',
              value: _prefs.etiketYazici,
              kuyruklar: _kuyrukAdlari(),
              printer: _bul(_prefs.etiketYazici),
              onChanged: (v) => _kaydet(_prefs.copyWith(etiketYazici: v)),
            ),
            _KuyrukSecici(
              etiket: 'A4 yazıcı (raporlar)',
              value: _prefs.a4Dosya ? _a4DosyaModu : _prefs.a4Yazici,
              kuyruklar: _kuyrukAdlari(),
              printer: _prefs.a4Dosya ? null : _bul(_prefs.a4Yazici),
              ozelSecenekDeger: _a4DosyaModu,
              ozelSecenekEtiket: 'Dosyaya yaz (PDF)',
              onChanged: (v) {
                if (v == _a4DosyaModu) {
                  _kaydet(_prefs.copyWith(a4Dosya: true));
                } else {
                  _kaydet(_prefs.copyWith(a4Yazici: v, a4Dosya: false));
                }
              },
            ),
            if (_ortakYaziciVar) ...[
              const Divider(height: 32),
              _TermalRuloBolumu(prefs: _prefs, onRulo: _ruloSec, onKaydet: _kaydet),
            ],
            const Divider(height: 32),
            Text('Otomatik fiş basımı', style: theme.textTheme.titleMedium),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Ödünç verilince fiş yazdır'),
              value: _prefs.otomatikOduncFisi,
              onChanged: (v) =>
                  _kaydet(_prefs.copyWith(otomatikOduncFisi: v)),
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('İade alınınca fiş yazdır'),
              value: _prefs.otomatikIadeFisi,
              onChanged: (v) =>
                  _kaydet(_prefs.copyWith(otomatikIadeFisi: v)),
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Şifre verilince şifre fişi yazdır'),
              value: _prefs.sifreFisi,
              onChanged: (v) => _kaydet(_prefs.copyWith(sifreFisi: v)),
            ),
            const Divider(height: 32),
            Row(
              children: [
                Text('Test basımı', style: theme.textTheme.titleMedium),
                if (_testYukleniyor) ...[
                  const SizedBox(width: 12),
                  const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2)),
                ],
              ],
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [
                FilledButton.tonalIcon(
                  onPressed: _testYukleniyor
                      ? null
                      : () => _testEt(
                            rol: 'Fiş',
                            kuyruk: _prefs.fisYazici,
                            uretici: (k) => TestPdf.fis(k),
                          ),
                  icon: const Icon(Icons.receipt_long, size: 18),
                  label: const Text('Test fişi'),
                ),
                FilledButton.tonalIcon(
                  onPressed: _testYukleniyor
                      ? null
                      : () => _testEt(
                            rol: 'Etiket',
                            kuyruk: _prefs.etiketYazici,
                            uretici: (k) => TestPdf.etiket(k),
                          ),
                  icon: const Icon(Icons.sell_outlined, size: 18),
                  label: const Text('Test etiketi'),
                ),
                FilledButton.tonalIcon(
                  onPressed: _testYukleniyor ? null : _testA4,
                  icon: const Icon(Icons.print_outlined, size: 18),
                  label: const Text('Test A4'),
                ),
              ],
            ),
            if (_testMesaj != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(_testMesaj!, style: theme.textTheme.bodySmall),
              ),
            const Divider(height: 32),
            Text('Fiş/etiket başlığı (Kurum bilgileri)',
                style: theme.textTheme.titleMedium),
            const SizedBox(height: 4),
            Text(
              {
                if (_kurum.baslik.trim().isNotEmpty)
                  _kurum.baslik.trim()
                else
                  'Kurum bilgisi kayıtlı değil.',
                if (_kurum.adres.trim().isNotEmpty) '• ${_kurum.adres.trim()}',
              }.join(' '),
              style: theme.textTheme.bodySmall,
            ),
            TextButton.icon(
              onPressed: () async {
                final context = this.context;
                final kurum = await kurumGetir();
                if (!context.mounted) return;
                setState(() => _kurum = kurum);
                showAppSnack(context,
                    kurum.baslik.trim().isNotEmpty
                        ? 'Kurum bilgisi güncellendi.'
                        : 'Kurum bilgisi sunucudan alınamadı; yedek boş.',
                    error: kurum.baslik.trim().isEmpty);
              },
              icon: const Icon(Icons.cloud_sync_outlined, size: 18),
              label: const Text('Kurum bilgisini güncelle'),
            ),
          ],
        ],
      ),
    );
  }
}

/// Kuyruk seçici + durum göstergesi. `ozelSecenekDeger` verilirse listenin
/// sonuna o değerle özel bir seçenek eklenir (K14.10 "Dosyaya yaz").
class _KuyrukSecici extends StatelessWidget {
  final String etiket;
  final String value;
  final List<String> kuyruklar;
  final PrinterInfo? printer;
  final ValueChanged<String> onChanged;
  final String? ozelSecenekDeger;
  final String? ozelSecenekEtiket;

  const _KuyrukSecici({
    required this.etiket,
    required this.value,
    required this.kuyruklar,
    required this.printer,
    required this.onChanged,
    this.ozelSecenekDeger,
    this.ozelSecenekEtiket,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final durum = printer;
    final ozelSecili = ozelSecenekDeger != null && value == ozelSecenekDeger;
    final durumText = ozelSecili
        ? 'Dosyaya yaz (PDF)'
        : switch (durum?.state) {
            PrinterState.ready => 'Hazır',
            PrinterState.busy => 'Yazdırıyor',
            PrinterState.disabled => 'Devre dışı',
            PrinterState.missing => 'Bulunamadı',
            PrinterState.unknown => 'Durum bilinmiyor',
            _ => 'Seçilmedi',
          };
    final renk = ozelSecili
        ? Colors.teal.shade700
        : switch (durum?.state) {
            PrinterState.ready => theme.colorScheme.primary,
            PrinterState.busy => Colors.orange.shade700,
            PrinterState.disabled || PrinterState.missing => theme.colorScheme.error,
            _ => theme.colorScheme.onSurfaceVariant,
          };
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        children: [
          Expanded(
            child: DropdownButtonFormField<String>(
              initialValue: value,
              decoration: InputDecoration(
                labelText: etiket,
                isDense: true,
                border: const OutlineInputBorder(),
              ),
              items: [
                const DropdownMenuItem(
                  value: '',
                  child: Text('— Seçilmedi —'),
                ),
                ...kuyruklar
                    .map((k) => DropdownMenuItem(value: k, child: Text(k))),
                if (ozelSecenekDeger != null && ozelSecenekEtiket != null)
                  DropdownMenuItem(
                    value: ozelSecenekDeger,
                    child: Row(
                      children: [
                        const Icon(Icons.save_alt, size: 16),
                        const SizedBox(width: 6),
                        Text(ozelSecenekEtiket!),
                      ],
                    ),
                  ),
              ],
              onChanged: (v) => onChanged(v ?? ''),
            ),
          ),
          const SizedBox(width: 12),
          Tooltip(
            message: durumText,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: renk.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(999),
                border: Border.all(color: renk.withValues(alpha: 0.5)),
              ),
              child: Text(durumText,
                  style: TextStyle(
                      color: renk,
                      fontSize: 11,
                      fontWeight: FontWeight.w600)),
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------- Öğrenci Aktarımı

/// K14.9/11: fiş ve etiket aynı yazıcıyı kullanınca "Termal rulo" bölümü.
/// Rulo durumu bildirimi + etiket ölçüleri + fiş genişliği.
class _TermalRuloBolumu extends StatefulWidget {
  final PrinterPrefs prefs;
  final void Function(RuloTipi) onRulo;
  final ValueChanged<PrinterPrefs> onKaydet;

  const _TermalRuloBolumu({
    required this.prefs,
    required this.onRulo,
    required this.onKaydet,
  });

  @override
  State<_TermalRuloBolumu> createState() => _TermalRuloBolumuState();
}

class _TermalRuloBolumuState extends State<_TermalRuloBolumu> {
  late final TextEditingController _etGenislik;
  late final TextEditingController _etYukseklik;
  late final TextEditingController _fisGenislik;

  @override
  void initState() {
    super.initState();
    _etGenislik =
        TextEditingController(text: widget.prefs.etiketGenislikMm.toStringAsFixed(0));
    _etYukseklik =
        TextEditingController(text: widget.prefs.etiketYukseklikMm.toStringAsFixed(0));
    _fisGenislik =
        TextEditingController(text: widget.prefs.fisGenislikMm.toStringAsFixed(0));
  }

  @override
  void dispose() {
    _etGenislik.dispose();
    _etYukseklik.dispose();
    _fisGenislik.dispose();
    super.dispose();
  }

  double _sayi(String s, double sabit) {
    final d = double.tryParse(s.trim().replaceAll(',', '.'));
    return (d == null || d <= 0) ? sabit : d;
  }

  void _kaydetAyar() {
    final p = widget.prefs;
    widget.onKaydet(p.copyWith(
      etiketGenislikMm: _sayi(_etGenislik.text, p.etiketGenislikMm),
      etiketYukseklikMm: _sayi(_etYukseklik.text, p.etiketYukseklikMm),
      fisGenislikMm: _sayi(_fisGenislik.text, p.fisGenislikMm),
      etiketKurulumYapildi: true,
    ));
    showAppSnack(context, 'Termal rulo ayarları kaydedildi.');
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final p = widget.prefs;
    final q = ortakKuyruk();
    final durum = bildirileneGore(p);
    final durumEtiket = switch (durum) {
      RuloDurum.fis => 'Fiş rulosu',
      RuloDurum.etiket => 'Etiket rulosu',
      RuloDurum.pasif => 'Pasif',
      RuloDurum.tanimsiz => 'Tanımlı Değil',
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text('Termal rulo (ortak yazıcı)', style: theme.textTheme.titleMedium),
            const Spacer(),
            Text('$q — $durumEtiket',
                style: TextStyle(fontSize: 12, color: theme.colorScheme.primary)),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          'Fiş ve etiket aynı yazıcıyı kullanıyor; yazıcıda takılı ruloyu bildirin. '
          'Aşağıdaki ölçüler yalnız PDF içeriğinin yerleşimi içindir; kağıt tipi ve '
          'etiket boşluğu (gap) yazıcının kendi sensör kalibrasyonundan gelir, '
          'program tarafından zorlanmaz (K14.9/14.11).',
          style: theme.textTheme.bodySmall,
        ),
        const SizedBox(height: 12),
        SegmentedButton<RuloTipi>(
          segments: const [
            ButtonSegment(
                value: RuloTipi.fis, label: Text('Fiş rulosu (sonsuz)')),
            ButtonSegment(
                value: RuloTipi.etiket, label: Text('Etiket rulosu')),
          ],
          selected: {if (durum == RuloDurum.fis) RuloTipi.fis},
          emptySelectionAllowed: true,
          onSelectionChanged: (s) {
            if (s.isEmpty) return;
            widget.onRulo(s.first);
          },
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: _etGenislik,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Etiket genişliği (mm)',
                  isDense: true,
                  border: OutlineInputBorder(),
                ),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: TextField(
                controller: _etYukseklik,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Etiket yüksekliği (mm)',
                  isDense: true,
                  border: OutlineInputBorder(),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: _fisGenislik,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Fiş genişliği (mm)',
                  isDense: true,
                  border: OutlineInputBorder(),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        _KalibrasyonBilgisi(),
        const SizedBox(height: 8),
        Align(
          alignment: Alignment.centerRight,
          child: FilledButton.tonalIcon(
            onPressed: _kaydetAyar,
            icon: const Icon(Icons.check, size: 18),
            label: const Text('Rulo ayarlarını kaydet'),
          ),
        ),
      ],
    );
  }
}

/// Etiket/sonsuz rulo beslemesi yazıcının kendi sensör kalibrasyonuyla yapılır;
/// program boşluğu/kağıt tipini zorlamaz. Marka/model yazılmaması için genel
/// metin verilir, ayrıntılı adımlar yazıcının kendi kılavuzundadır (K14.11).
class _KalibrasyonBilgisi extends StatelessWidget {
  const _KalibrasyonBilgisi();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.tune, size: 18, color: theme.colorScheme.primary),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Etiket kayması / boşluk hataları',
                    style: theme.textTheme.bodyMedium
                        ?.copyWith(fontWeight: FontWeight.w600)),
                const SizedBox(height: 4),
                Text(
                  'Termal yazıcılar etiket uzunluğunu ve etiketler arası boşluğu '
                  'kendi sensörüyle ölçer; bu yüzden uygulama boşluk/kağıt tipi '
                  'göndermez. Yeni rulo taktıysanız veya basım bir etiketin '
                  'ortasından başlıp diğerinin ortasında bitiyorsa, yazıcınızın '
                  'kılavuzundaki "gap/black mark (boşluk) sensörü kalibrasyonu" '
                  'adımını uygulayın. Çoğu modelde bu, cihaz açılırken panel '
                  'tuşu basılı tutularak yapılır; yazıcı yanıp söndükçe uygun '
                  'anda tuşu bırakın. Kalibrasyondan sonra fiş (sonsuz rulo) '
                  'basınca kalibrasyonu tekrarlamanız gerekebilir.',
                  style: theme.textTheme.bodySmall,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

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
