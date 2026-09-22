import 'package:flutter/material.dart';

import '../api/kutuphane_api.dart';
import '../config.dart';
import '../formatters.dart';
import '../models.dart';
import '../theme.dart';
import 'student_form_dialog.dart';
import 'password_dialog.dart';

const _deletedUye = Uye(id: -1, ad: '', soyad: '', uyeNo: '');

class StudentDetailScreen extends StatefulWidget {
  final Uye uye;

  const StudentDetailScreen({super.key, required this.uye});

  @override
  State<StudentDetailScreen> createState() => _StudentDetailScreenState();
}

class _StudentDetailScreenState extends State<StudentDetailScreen> {
  final _api = KutuphaneApi();
  late Future<List<OduncKaydi>> _historyFuture;
  late Future<PenaltySummary> _penaltiesFuture;
  late bool _aktif = widget.uye.aktif;

  bool get _isAdmin => AppConfig.session?.role == 'admin';

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    _historyFuture = _api.studentHistory(widget.uye.uyeNo);
    _penaltiesFuture = _api.studentPenalties(widget.uye.uyeNo);
  }

  void _snack(String msg, {bool error = false}) {
    if (!mounted) return;
    showAppSnack(context, msg, error: error);
  }

  Future<void> _toggleStatus() async {
    final o = widget.uye;
    final targetAktif = !_aktif;
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title:
            Text(targetAktif ? 'Üyeyi aktifleştir' : 'Üyeyi pasife al'),
        content: Text(targetAktif
            ? '${o.adSoyad} (${o.uyeNo}) tekrar aktif olacak. Onaylıyor musunuz?'
            : '${o.adSoyad} (${o.uyeNo}) pasife alınacak (mezun/nakil/tasdikname için). '
                'Geçmiş kayıtları korunur; yeni ödünç verilemez. Onaylıyor musunuz?'),
        actions: [
          TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Vazgeç')),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Onayla'),
          ),
        ],
      ),
    );
    if (confirm != true) return;
    final res = await _api.setStudentStatus(o.id, targetAktif);
    if (!mounted) return;
    if (res.ok) {
      setState(() => _aktif = targetAktif);
      final extra = res.warnings.isEmpty ? '' : ' Uyarı: ${res.warnings.join(' ')}';
      _snack((targetAktif ? 'Üye aktifleştirildi.' : 'Üye pasife alındı.') + extra);
    } else {
      _snack(res.error, error: true);
    }
  }

  Future<void> _delete() async {
    final o = widget.uye;
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Üyeyi sil'),
        content: Text(
            '${o.adSoyad} (${o.uyeNo}) silinecek. Bu işlem kalıcıdır; '
            'yalnızca ödünç geçmişi olmayan üyeler silinebilir. Onaylıyor musunuz?'),
        actions: [
          TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Vazgeç')),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Sil'),
          ),
        ],
      ),
    );
    if (confirm != true) return;
    final res = await _api.deleteStudent(o.id);
    if (!mounted) return;
    if (res.ok) {
      Navigator.of(context).pop(_deletedUye);
    } else {
      _snack(res.error ?? 'Silme yapılamadı.', error: true);
    }
  }

  Future<void> _edit() async {
    final saved = await showDialog<Uye>(
      context: context,
      builder: (_) => StudentFormDialog(uye: widget.uye, isAdmin: _isAdmin),
    );
    if (saved != null && mounted) {
      Navigator.of(context).pop(saved);
    }
  }

  Future<void> _givePassword() async {
    final sifre = await showDialog<String>(
      context: context,
      builder: (_) => PasswordDialog(uye: widget.uye),
    );
    if (sifre != null && mounted) {
      _snack('Şifre güncellendi: $sifre — öğrenci ilk girişte değiştirecek.');
    }
  }

  @override
  Widget build(BuildContext context) {
    final o = widget.uye;
    return Scaffold(
      appBar: AppBar(
        title: Text(o.adSoyad),
        actions: [
          IconButton(
            tooltip: 'Şifre Ver',
            icon: const Icon(Icons.key_outlined),
            onPressed: _givePassword,
          ),
          IconButton(
            tooltip: 'Düzenle',
            icon: const Icon(Icons.edit_outlined),
            onPressed: _edit,
          ),
          if (_isAdmin) ...[
            IconButton(
              tooltip: _aktif ? 'Pasife al' : 'Aktifleştir',
              icon: Icon(
                _aktif ? Icons.person_off_outlined : Icons.person_outline,
              ),
              onPressed: _toggleStatus,
            ),
            IconButton(
              tooltip: 'Sil',
              icon: const Icon(Icons.delete_outline),
              onPressed: _delete,
            ),
          ],
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          _header(o),
          const SizedBox(height: 16),
          FutureBuilder<PenaltySummary>(
            future: _penaltiesFuture,
            builder: (context, snap) {
              if (snap.hasData && snap.data!.outstandingCount > 0) {
                final p = snap.data!;
                return Card(
                  color: layerColor(context, dangerColor(context), alpha: 0.12),
                  child: ListTile(
                    leading: Icon(Icons.warning_amber_rounded,
                        color: dangerColor(context)),
                    title: Text('Ödenmemiş gecikme cezası: ${p.outstandingTotal} ₺',
                        style: TextStyle(
                            color: dangerColor(context),
                            fontWeight: FontWeight.bold)),
                    subtitle: Text('${p.outstandingCount} kayıt'),
                  ),
                );
              }
              return const SizedBox.shrink();
            },
          ),
          const SizedBox(height: 16),
          Text('Ödünç Geçmişi',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          FutureBuilder<List<OduncKaydi>>(
            future: _historyFuture,
            builder: (context, snap) {
              if (snap.connectionState != ConnectionState.done) {
                return const Padding(
                  padding: EdgeInsets.all(24),
                  child: Center(child: CircularProgressIndicator()),
                );
              }
              if (snap.hasError) {
                return Text('Sorgu alınamadı.',
                    style: TextStyle(
                        color: Theme.of(context).colorScheme.error));
              }
              final rows = snap.data ?? const [];
              if (rows.isEmpty) {
                return const Card(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Center(child: Text('Bu üyenin ödünç geçmişi yok.')),
                  ),
                );
              }
              return Card(
                clipBehavior: Clip.antiAlias,
                child: DataTable(
                  headingRowHeight: 44,
                  dataRowMinHeight: 40,
                  dataRowMaxHeight: 48,
                  columns: const [
                    DataColumn(label: Text('Kitap')),
                    DataColumn(label: Text('Barkod')),
                    DataColumn(label: Text('Alındı')),
                    DataColumn(label: Text('Beklenen')),
                    DataColumn(label: Text('Teslim')),
                    DataColumn(label: Text('Durum')),
                    DataColumn(label: Text('Cezası')),
                  ],
                  rows: [
                    for (final h in rows)
                      DataRow(
                        cells: [
                          DataCell(SizedBox(
                            width: 240,
                            child: Text(h.kitapBaslik,
                                maxLines: 1, overflow: TextOverflow.ellipsis),
                          )),
                          DataCell(Text(h.barkod)),
                          DataCell(Text(formatDate(h.oduncTarihi))),
                          DataCell(Text(formatDate(h.iadeTarihi))),
                          DataCell(Text(formatDate(h.teslimTarihi))),
                          DataCell(Text(durumLabel(h.durum),
                              style: TextStyle(
                                  color: durumColor(h.durum, Theme.of(context).brightness),
                                  fontWeight: FontWeight.w500))),
                          DataCell(Text(h.gecikmeCezasi ?? '—')),
                        ],
                      ),
                  ],
                ),
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _header(Uye o) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(
                  radius: 28,
                  child: Text(
                    '${o.ad.characters.first}${o.soyad.characters.first}',
                    style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('${o.ad} ${o.soyad}',
                          style: theme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold)),
                      const SizedBox(height: 4),
                      Wrap(
                        spacing: 8,
                        children: [
                          Chip(label: Text(o.uyeNo), visualDensity: VisualDensity.compact),
                          if (o.sinif != null)
                            Chip(label: Text(o.sinif!.ad), visualDensity: VisualDensity.compact),
                          Chip(
                            label: Text(_aktif ? 'Aktif' : 'Pasif',
                                style: TextStyle(
                                    color: _aktif
                                        ? successColor(context)
                                        : Theme.of(context).colorScheme.onSurfaceVariant)),
                            visualDensity: VisualDensity.compact,
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const Divider(height: 24),
            Wrap(
              spacing: 32,
              runSpacing: 8,
              children: [
                _info(theme, Icons.phone_outlined, 'Telefon', o.telefon ?? '—'),
                _info(theme, Icons.mail_outline, 'E-posta', o.eposta ?? '—'),
                _info(theme, Icons.calendar_today_outlined, 'Kayıt', formatDate(o.kayitTarihi)),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _info(ThemeData theme, IconData icon, String label, String value) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 16, color: theme.colorScheme.primary),
        const SizedBox(width: 6),
        Text('$label: ', style: theme.textTheme.bodySmall),
        Text(value, style: const TextStyle(fontWeight: FontWeight.w500)),
      ],
    );
  }
}