import 'package:flutter/material.dart';

import '../api/auth_api.dart';
import '../api/kutuphane_api.dart';
import '../config.dart';
import '../theme.dart';

/// Ayarlar ekranı (K10): sekmeli. Düzenleme yalnız admin; görüntüleme personel.
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  bool get _admin => AppConfig.session?.role == 'admin';

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 7,
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
          const TabBar(
            isScrollable: true,
            tabs: [
              Tab(text: 'Görünüm'),
              Tab(text: 'Sunucu'),
              Tab(text: 'Ödünç Politikası'),
              Tab(text: 'Ceza (Rol)'),
              Tab(text: 'Bildirim'),
              Tab(text: 'Kurum'),
              Tab(text: 'Hesap'),
            ],
          ),
          Expanded(
            child: TabBarView(
              children: [
                const _GorunumTab(),
                const _SunucuTab(),
                _OdoncPolitikasiTab(admin: _admin),
                _CezaRolTab(admin: _admin),
                _BildirimTab(admin: _admin),
                _KurumTab(admin: _admin),
                const _HesapTab(),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------- ortak

Widget _adminUyari(BuildContext context) {
  return Card(
    color: layerColor(context, warningColor(context)),
    child: Padding(
      padding: const EdgeInsets.all(12),
      child: Row(children: [
        Icon(Icons.lock_outline, color: warningColor(context), size: 18),
        const SizedBox(width: 8),
        const Expanded(
          child: Text('Bu ayarları yalnızca yönetici (admin) değiştirebilir.'),
        ),
      ]),
    ),
  );
}

Widget _sayiAlan(String label, dynamic value, ValueChanged<String> onChanged,
    {bool enabled = true}) {
  return TextFormField(
    initialValue: value == null ? '' : value.toString(),
    enabled: enabled,
    keyboardType: const TextInputType.numberWithOptions(decimal: true),
    decoration: InputDecoration(labelText: label, isDense: true),
    onChanged: onChanged,
  );
}

Widget _metinAlan(String label, dynamic value, ValueChanged<String> onChanged,
    {bool enabled = true}) {
  return TextFormField(
    initialValue: value == null ? '' : value.toString(),
    enabled: enabled,
    decoration: InputDecoration(labelText: label, isDense: true),
    onChanged: onChanged,
  );
}

Widget _switchAlan(String label, bool value, ValueChanged<bool> onChanged,
    {bool enabled = true}) {
  return SwitchListTile(
    value: value,
    onChanged: enabled ? onChanged : null,
    title: Text(label),
    dense: true,
    contentPadding: EdgeInsets.zero,
  );
}

class _KaydetButonu extends StatelessWidget {
  final bool admin;
  final bool busy;
  final VoidCallback onSave;
  const _KaydetButonu(
      {required this.admin, required this.busy, required this.onSave});

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: FilledButton.icon(
        onPressed: (!admin || busy) ? null : onSave,
        icon: busy
            ? const SizedBox(
                height: 16,
                width: 16,
                child: CircularProgressIndicator(strokeWidth: 2))
            : const Icon(Icons.save_outlined),
        label: const Text('Kaydet'),
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

// ---------------------------------------------------------------- Ödünç Politikası

class _OdoncPolitikasiTab extends StatefulWidget {
  final bool admin;
  const _OdoncPolitikasiTab({required this.admin});

  @override
  State<_OdoncPolitikasiTab> createState() => _OdoncPolitikasiTabState();
}

class _OdoncPolitikasiTabState extends State<_OdoncPolitikasiTab> {
  final _api = KutuphaneApi();
  bool _loading = true;
  bool _busy = false;
  String? _error;
  Map<String, dynamic> _data = {};

  @override
  void initState() {
    super.initState();
    _yukle();
  }

  Future<void> _yukle() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    final res = await _api.loanPolicyGet();
    if (!mounted) return;
    setState(() {
      _loading = false;
      _error = res.error;
      if (res.data != null) {
        _data = Map<String, dynamic>.from(res.data!);
        _data.remove('role_limits');
      }
    });
  }

  Future<void> _kaydet() async {
    setState(() => _busy = true);
    final res = await _api.loanPolicyUpdate(_data);
    if (!mounted) return;
    setState(() => _busy = false);
    showAppSnack(context, res.ok ? 'Ödünç politikası kaydedildi.' : (res.error ?? 'Kaydedilemedi.'), error: !res.ok);
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) {
      return Center(child: Text('Ayarlar alınamadı.\n$_error'));
    }
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        if (!widget.admin) ...[_adminUyari(context), const SizedBox(height: 12)],
        Row(children: [
          Expanded(child: _sayiAlan('Varsayılan süre (gün)', _data['default_duration'], (v) => _data['default_duration'] = v, enabled: widget.admin)),
          const SizedBox(width: 12),
          Expanded(child: _sayiAlan('Varsayılan maks. kitap', _data['default_max_items'], (v) => _data['default_max_items'] = v, enabled: widget.admin)),
        ]),
        const SizedBox(height: 12),
        Row(children: [
          Expanded(child: _sayiAlan('İade toleransı (gün)', _data['delay_grace_days'], (v) => _data['delay_grace_days'] = v, enabled: widget.admin)),
          const SizedBox(width: 12),
          Expanded(child: _sayiAlan('Ceza gecikmesi (gün)', _data['penalty_delay_days'], (v) => _data['penalty_delay_days'] = v, enabled: widget.admin)),
        ]),
        const SizedBox(height: 12),
        Row(children: [
          Expanded(child: _sayiAlan('Ceza tavanı (kitap ₺)', _data['penalty_max_per_loan'], (v) => _data['penalty_max_per_loan'] = v, enabled: widget.admin)),
          const SizedBox(width: 12),
          Expanded(child: _sayiAlan('Ceza tavanı (üye ₺)', _data['penalty_max_per_student'], (v) => _data['penalty_max_per_student'] = v, enabled: widget.admin)),
        ]),
        const SizedBox(height: 12),
        _sayiAlan('Kayıp/hasarlı cezası (₺)', _data['kayip_hasar_cezasi'], (v) => _data['kayip_hasar_cezasi'] = v, enabled: widget.admin),
        const SizedBox(height: 12),
        Row(children: [
          Expanded(child: _sayiAlan('Karantina (gün)', _data['quarantine_days'], (v) => _data['quarantine_days'] = v, enabled: widget.admin)),
          const SizedBox(width: 12),
          Expanded(child: _sayiAlan('Oto. uzatma (gün)', _data['auto_extend_days'], (v) => _data['auto_extend_days'] = v, enabled: widget.admin)),
          const SizedBox(width: 12),
          Expanded(child: _sayiAlan('Oto. uzatma limiti', _data['auto_extend_limit'], (v) => _data['auto_extend_limit'] = v, enabled: widget.admin)),
        ]),
        const SizedBox(height: 8),
        _switchAlan('Hafta sonu kaydırma', _data['shift_weekend'] == true, (v) => setState(() => _data['shift_weekend'] = v), enabled: widget.admin),
        _switchAlan('Otomatik uzatma açık', _data['auto_extend_enabled'] == true, (v) => setState(() => _data['auto_extend_enabled'] = v), enabled: widget.admin),
        _switchAlan('Hasarlı için not zorunlu', _data['require_damage_note'] == true, (v) => setState(() => _data['require_damage_note'] = v), enabled: widget.admin),
        _switchAlan('Raf kodu zorunlu', _data['require_shelf_code'] == true, (v) => setState(() => _data['require_shelf_code'] = v), enabled: widget.admin),
        _switchAlan('Sessiz saatler açık', _data['quiet_hours_enabled'] == true, (v) => setState(() => _data['quiet_hours_enabled'] = v), enabled: widget.admin),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: _metinAlan('Sessiz başlangıç (SS:DD)', _data['quiet_hours_start'], (v) => _data['quiet_hours_start'] = v, enabled: widget.admin)),
          const SizedBox(width: 12),
          Expanded(child: _metinAlan('Sessiz bitiş (SS:DD)', _data['quiet_hours_end'], (v) => _data['quiet_hours_end'] = v, enabled: widget.admin)),
        ]),
        const SizedBox(height: 16),
        _KaydetButonu(admin: widget.admin, busy: _busy, onSave: _kaydet),
      ],
    );
  }
}

// ---------------------------------------------------------------- Ceza (Rol)

class _CezaRolTab extends StatefulWidget {
  final bool admin;
  const _CezaRolTab({required this.admin});

  @override
  State<_CezaRolTab> createState() => _CezaRolTabState();
}

class _CezaRolTabState extends State<_CezaRolTab> {
  final _api = KutuphaneApi();
  bool _loading = true;
  bool _busy = false;
  String? _error;
  List<Map<String, dynamic>> _roller = [];
  // roleId -> alanlar
  final Map<int, Map<String, dynamic>> _degerler = {};

  static const _alanlar = [
    'duration',
    'max_items',
    'delay_grace_days',
    'penalty_delay_days',
    'shift_weekend',
    'daily_penalty_rate',
    'penalty_max_per_loan',
    'penalty_max_per_student',
  ];

  @override
  void initState() {
    super.initState();
    _yukle();
  }

  Future<void> _yukle() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final roller = await _api.roller();
      final policyRes = await _api.roleLoanPolicies();
      if (!mounted) return;
      _roller = roller;
      _degerler.clear();
      for (final r in roller) {
        _degerler[r['id'] as int] = {for (final a in _alanlar) a: null};
      }
      for (final p in (policyRes.data ?? const [])) {
        if (p is Map<String, dynamic>) {
          final rid = p['role'] as int?;
          if (rid != null) {
            _degerler[rid] = {for (final a in _alanlar) a: p[a]};
          }
        }
      }
      setState(() => _loading = false);
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'Rol ayarları alınamadı.';
      });
    }
  }

  Future<void> _kaydet() async {
    setState(() => _busy = true);
    final payload = <Map<String, dynamic>>[
      for (final r in _roller)
        {'role': r['id'], ..._degerler[r['id'] as int] ?? {}},
    ];
    final res = await _api.roleLoanPoliciesUpdate(payload);
    if (!mounted) return;
    setState(() => _busy = false);
    showAppSnack(context, res.ok ? 'Rol ayarları kaydedildi.' : (res.error ?? 'Kaydedilemedi.'), error: !res.ok);
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) return Center(child: Text(_error!));
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        if (!widget.admin) ...[_adminUyari(context), const SizedBox(height: 12)],
        Text('Rol bazlı süre/limit/ceza. Boş alanlar o rol için tanımsız sayılır.',
            style: Theme.of(context).textTheme.bodySmall),
        const SizedBox(height: 8),
        for (final r in _roller)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text((r['ad'] ?? '').toString(),
                      style: const TextStyle(fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  Row(children: [
                    Expanded(child: _sayiAlan('Süre (gün)', _degerler[r['id']]?['duration'], (v) => _degerler[r['id']]!['duration'] = v, enabled: widget.admin)),
                    const SizedBox(width: 8),
                    Expanded(child: _sayiAlan('Maks. kitap', _degerler[r['id']]?['max_items'], (v) => _degerler[r['id']]!['max_items'] = v, enabled: widget.admin)),
                    const SizedBox(width: 8),
                    Expanded(child: _sayiAlan('Günlük ceza (₺)', _degerler[r['id']]?['daily_penalty_rate'], (v) => _degerler[r['id']]!['daily_penalty_rate'] = v, enabled: widget.admin)),
                  ]),
                  const SizedBox(height: 8),
                  Row(children: [
                    Expanded(child: _sayiAlan('Tolerans (gün)', _degerler[r['id']]?['delay_grace_days'], (v) => _degerler[r['id']]!['delay_grace_days'] = v, enabled: widget.admin)),
                    const SizedBox(width: 8),
                    Expanded(child: _sayiAlan('Ceza gecikmesi', _degerler[r['id']]?['penalty_delay_days'], (v) => _degerler[r['id']]!['penalty_delay_days'] = v, enabled: widget.admin)),
                    const SizedBox(width: 8),
                    Expanded(child: _sayiAlan('Tavan (kitap ₺)', _degerler[r['id']]?['penalty_max_per_loan'], (v) => _degerler[r['id']]!['penalty_max_per_loan'] = v, enabled: widget.admin)),
                  ]),
                  const SizedBox(height: 8),
                  Row(children: [
                    Expanded(child: _sayiAlan('Tavan (üye ₺)', _degerler[r['id']]?['penalty_max_per_student'], (v) => _degerler[r['id']]!['penalty_max_per_student'] = v, enabled: widget.admin)),
                    const SizedBox(width: 8),
                    Expanded(
                      child: _switchAlan('Hafta sonu kaydır', _degerler[r['id']]?['shift_weekend'] == true, (v) => setState(() => _degerler[r['id']]!['shift_weekend'] = v), enabled: widget.admin),
                    ),
                  ]),
                ],
              ),
            ),
          ),
        const SizedBox(height: 8),
        _KaydetButonu(admin: widget.admin, busy: _busy, onSave: _kaydet),
      ],
    );
  }
}

// ---------------------------------------------------------------- Bildirim

class _BildirimTab extends StatefulWidget {
  final bool admin;
  const _BildirimTab({required this.admin});

  @override
  State<_BildirimTab> createState() => _BildirimTabState();
}

class _BildirimTabState extends State<_BildirimTab> {
  final _api = KutuphaneApi();
  bool _loading = true;
  bool _busy = false;
  String? _error;
  Map<String, dynamic> _data = {};

  @override
  void initState() {
    super.initState();
    _yukle();
  }

  Future<void> _yukle() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    final res = await _api.notificationSettingsGet();
    if (!mounted) return;
    setState(() {
      _loading = false;
      _error = res.error;
      if (res.data != null) _data = Map<String, dynamic>.from(res.data!);
    });
  }

  Future<void> _kaydet() async {
    setState(() => _busy = true);
    final res = await _api.notificationSettingsUpdate(_data);
    if (!mounted) return;
    setState(() => _busy = false);
    showAppSnack(context, res.ok ? 'Bildirim ayarları kaydedildi.' : (res.error ?? 'Kaydedilemedi.'), error: !res.ok);
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) return Center(child: Text('Ayarlar alınamadı.\n$_error'));
    final admin = widget.admin;
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        if (!admin) ...[_adminUyari(context), const SizedBox(height: 12)],
        Text('Hatırlatma / gecikme', style: Theme.of(context).textTheme.titleSmall),
        _switchAlan('Yazıcı uyarısı (açılışta)', _data['printer_warning_enabled'] == true, (v) => setState(() => _data['printer_warning_enabled'] = v), enabled: admin),
        _switchAlan('İade hatırlatma açık', _data['due_reminder_enabled'] == true, (v) => setState(() => _data['due_reminder_enabled'] = v), enabled: admin),
        _sayiAlan('Kaç gün önce hatırlat', _data['due_reminder_days_before'], (v) => _data['due_reminder_days_before'] = v, enabled: admin),
        const SizedBox(height: 4),
        Row(children: [
          Expanded(child: _switchAlan('E-posta', _data['due_reminder_email_enabled'] == true, (v) => setState(() => _data['due_reminder_email_enabled'] = v), enabled: admin)),
          Expanded(child: _switchAlan('SMS', _data['due_reminder_sms_enabled'] == true, (v) => setState(() => _data['due_reminder_sms_enabled'] = v), enabled: admin)),
          Expanded(child: _switchAlan('Mobil', _data['due_reminder_mobile_enabled'] == true, (v) => setState(() => _data['due_reminder_mobile_enabled'] = v), enabled: admin)),
        ]),
        const Divider(height: 24),
        _switchAlan('Gecikme bildirimi açık', _data['due_overdue_enabled'] == true, (v) => setState(() => _data['due_overdue_enabled'] = v), enabled: admin),
        _sayiAlan('Kaç gün sonra', _data['due_overdue_days_after'], (v) => _data['due_overdue_days_after'] = v, enabled: admin),
        Row(children: [
          Expanded(child: _switchAlan('E-posta', _data['overdue_email_enabled'] == true, (v) => setState(() => _data['overdue_email_enabled'] = v), enabled: admin)),
          Expanded(child: _switchAlan('SMS', _data['overdue_sms_enabled'] == true, (v) => setState(() => _data['overdue_sms_enabled'] = v), enabled: admin)),
          Expanded(child: _switchAlan('Mobil', _data['overdue_mobile_enabled'] == true, (v) => setState(() => _data['overdue_mobile_enabled'] = v), enabled: admin)),
        ]),
        const Divider(height: 24),
        Text('E-posta (SMTP)', style: Theme.of(context).textTheme.titleSmall),
        _switchAlan('E-posta açık', _data['email_enabled'] == true, (v) => setState(() => _data['email_enabled'] = v), enabled: admin),
        _metinAlan('Gönderen', _data['email_sender'], (v) => _data['email_sender'] = v, enabled: admin),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(flex: 3, child: _metinAlan('SMTP sunucu', _data['email_smtp_host'], (v) => _data['email_smtp_host'] = v, enabled: admin)),
          const SizedBox(width: 8),
          Expanded(child: _sayiAlan('Port', _data['email_smtp_port'], (v) => _data['email_smtp_port'] = v, enabled: admin)),
        ]),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: _metinAlan('Kullanıcı', _data['email_username'], (v) => _data['email_username'] = v, enabled: admin)),
          const SizedBox(width: 8),
          Expanded(child: _metinAlan('Şifre', _data['email_password'], (v) => _data['email_password'] = v, enabled: admin)),
        ]),
        _switchAlan('TLS kullan', _data['email_use_tls'] == true, (v) => setState(() => _data['email_use_tls'] = v), enabled: admin),
        const Divider(height: 24),
        Text('SMS', style: Theme.of(context).textTheme.titleSmall),
        _switchAlan('SMS açık', _data['sms_enabled'] == true, (v) => setState(() => _data['sms_enabled'] = v), enabled: admin),
        _metinAlan('Sağlayıcı', _data['sms_provider'], (v) => _data['sms_provider'] = v, enabled: admin),
        const SizedBox(height: 8),
        _metinAlan('API URL', _data['sms_api_url'], (v) => _data['sms_api_url'] = v, enabled: admin),
        const SizedBox(height: 8),
        _metinAlan('API anahtarı', _data['sms_api_key'], (v) => _data['sms_api_key'] = v, enabled: admin),
        _switchAlan('Mobil bildirim açık', _data['mobile_enabled'] == true, (v) => setState(() => _data['mobile_enabled'] = v), enabled: admin),
        const Divider(height: 24),
        Text('Şablonlar', style: Theme.of(context).textTheme.titleSmall),
        _metinAlan('Hatırlatma konusu', _data['reminder_subject'], (v) => _data['reminder_subject'] = v, enabled: admin),
        const SizedBox(height: 8),
        _metinAlan('Hatırlatma metni', _data['reminder_body'], (v) => _data['reminder_body'] = v, enabled: admin),
        const SizedBox(height: 8),
        _metinAlan('Gecikme konusu', _data['overdue_subject'], (v) => _data['overdue_subject'] = v, enabled: admin),
        const SizedBox(height: 8),
        _metinAlan('Gecikme metni', _data['overdue_body'], (v) => _data['overdue_body'] = v, enabled: admin),
        const SizedBox(height: 16),
        _KaydetButonu(admin: admin, busy: _busy, onSave: _kaydet),
      ],
    );
  }
}

// ---------------------------------------------------------------- Kurum

class _KurumTab extends StatefulWidget {
  final bool admin;
  const _KurumTab({required this.admin});

  @override
  State<_KurumTab> createState() => _KurumTabState();
}

class _KurumTabState extends State<_KurumTab> {
  final _api = KutuphaneApi();
  bool _loading = true;
  bool _busy = false;
  String? _error;
  Map<String, dynamic> _data = {};

  @override
  void initState() {
    super.initState();
    _yukle();
  }

  Future<void> _yukle() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    final res = await _api.kurumAyarlariGet();
    if (!mounted) return;
    setState(() {
      _loading = false;
      _error = res.error;
      if (res.data != null) _data = Map<String, dynamic>.from(res.data!);
    });
  }

  Future<void> _kaydet() async {
    setState(() => _busy = true);
    final res = await _api.kurumAyarlariUpdate(_data);
    if (!mounted) return;
    setState(() => _busy = false);
    showAppSnack(context, res.ok ? 'Kurum bilgileri kaydedildi.' : (res.error ?? 'Kaydedilemedi.'), error: !res.ok);
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) return Center(child: Text('Ayarlar alınamadı.\n$_error'));
    final admin = widget.admin;
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        if (!admin) ...[_adminUyari(context), const SizedBox(height: 12)],
        Text('Bu bilgiler fiş ve etiketlerde kullanılır.',
            style: Theme.of(context).textTheme.bodySmall),
        const SizedBox(height: 12),
        _metinAlan('Kütüphane adı', _data['kutuphane_adi'], (v) => _data['kutuphane_adi'] = v, enabled: admin),
        const SizedBox(height: 12),
        _metinAlan('Okul adı', _data['okul_adi'], (v) => _data['okul_adi'] = v, enabled: admin),
        const SizedBox(height: 12),
        _metinAlan('Adres', _data['adres'], (v) => _data['adres'] = v, enabled: admin),
        const SizedBox(height: 12),
        Row(children: [
          Expanded(child: _metinAlan('Telefon', _data['telefon'], (v) => _data['telefon'] = v, enabled: admin)),
          const SizedBox(width: 12),
          Expanded(child: _metinAlan('E-posta', _data['eposta'], (v) => _data['eposta'] = v, enabled: admin)),
        ]),
        const SizedBox(height: 12),
        _metinAlan('Web sitesi', _data['website'], (v) => _data['website'] = v, enabled: admin),
        const SizedBox(height: 12),
        _metinAlan('Logo URL', _data['logo_url'], (v) => _data['logo_url'] = v, enabled: admin),
        const SizedBox(height: 16),
        _KaydetButonu(admin: admin, busy: _busy, onSave: _kaydet),
      ],
    );
  }
}

// ---------------------------------------------------------------- Hesap

class _HesapTab extends StatefulWidget {
  const _HesapTab();

  @override
  State<_HesapTab> createState() => _HesapTabState();
}

class _HesapTabState extends State<_HesapTab> {
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
                    decoration:
                        const InputDecoration(labelText: 'Ad', isDense: true)),
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
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
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
      ],
    );
  }
}
