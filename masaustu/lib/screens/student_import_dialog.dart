import 'package:flutter/material.dart';

import '../api/kutuphane_api.dart';

/// K9.13: Toplu öğrenci içe aktarma önizlemesi ve onayı.
///
/// CSV metni ile açılır; `dry_run` önizlemesini gösterir. "Aktar" ile uygular
/// ve Pop ile uygulama sonucu (`dry_run=false` yanıtı) döndürür.
class StudentImportDialog extends StatefulWidget {
  const StudentImportDialog({super.key, required this.csv, this.api});

  final String csv;
  final KutuphaneApi? api;

  @override
  State<StudentImportDialog> createState() => _StudentImportDialogState();
}

class _StudentImportDialogState extends State<StudentImportDialog> {
  late final KutuphaneApi _api;
  Map<String, dynamic>? _preview;
  String? _error;
  bool _loading = true;
  bool _applying = false;
  bool _yeniden = false;

  @override
  void initState() {
    super.initState();
    _api = widget.api ?? KutuphaneApi();
    _fetchPreview();
  }

  Future<void> _fetchPreview() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    final res = await _api.ogrenciImport(
      widget.csv,
      dryRun: true,
      yenidenKullan: _yeniden,
    );
    if (!mounted) return;
    setState(() {
      _loading = false;
      if (res.data != null && !res.data!.containsKey('hata')) {
        _preview = res.data;
      } else {
        _error = res.error ??
            (res.data?['hata']?.toString() ?? 'Önizleme alınamadı.');
      }
    });
  }

  Future<void> _apply() async {
    setState(() => _applying = true);
    final res = await _api.ogrenciImport(
      widget.csv,
      dryRun: false,
      yenidenKullan: _yeniden,
    );
    if (!mounted) return;
    if (res.data != null) {
      Navigator.of(context).pop(res.data);
    } else {
      setState(() {
        _applying = false;
        _error = res.error ?? 'İçe aktarma uygulanamadı.';
      });
    }
  }

  Color _islemRenk(BuildContext context, String islem) {
    final scheme = Theme.of(context).colorScheme;
    switch (islem) {
      case 'yeni':
        return Colors.green.shade600;
      case 'yenileme':
        return scheme.primary;
      case 'cakisma':
        return Colors.orange.shade700;
      default:
        return scheme.error;
    }
  }

  IconData _islemIcon(String islem) {
    switch (islem) {
      case 'yeni':
        return Icons.person_add_alt_1;
      case 'yenileme':
        return Icons.refresh;
      case 'cakisma':
        return Icons.warning_amber_rounded;
      default:
        return Icons.error_outline;
    }
  }

  String _islemEtiket(String islem) {
    switch (islem) {
      case 'yeni':
        return 'Yeni';
      case 'yenileme':
        return 'Yenile';
      case 'cakisma':
        return 'Çakışma';
      default:
        return 'Hatalı';
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Öğrenci İçe Aktar (K9.13)'),
      content: SizedBox(
        width: 760,
        height: 560,
        child: _content(context),
      ),
      actions: [
        TextButton(
          onPressed: _applying ? null : () => Navigator.of(context).pop(),
          child: const Text('İptal'),
        ),
        FilledButton.icon(
          onPressed: (_loading || _applying || _preview == null) ? null : _apply,
          icon: _applying
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.upload_file),
          label: const Text('Aktar'),
        ),
      ],
    );
  }

  Widget _content(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_preview == null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(_error ?? 'Bilinmeyen hata',
                style: TextStyle(color: Theme.of(context).colorScheme.error)),
            const SizedBox(height: 12),
            FilledButton.tonal(
                onPressed: _fetchPreview, child: const Text('Tekrar Dene')),
          ],
        ),
      );
    }

    final ozet = (_preview!['ozet'] as Map?)?.cast<String, dynamic>() ?? {};
    final satirlar = (_preview!['satirlar'] as List?) ?? const [];
    final pasife = (_preview!['pasife_cekilecekler'] as List?) ?? const [];
    final yeniSiniflar = (_preview!['yeni_siniflar'] as List?) ?? const [];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 4,
          children: [
            _chip(context, 'Yeni: ${ozet['yeni'] ?? 0}', Colors.green.shade600),
            _chip(context, 'Yenileme: ${ozet['yenileme'] ?? 0}',
                Theme.of(context).colorScheme.primary),
            _chip(context, 'Çakışma: ${ozet['cakisma'] ?? 0}',
                Colors.orange.shade700),
            _chip(context, 'Pasife: ${ozet['pasife_cekilecek'] ?? 0}',
                Colors.brown),
            _chip(context, 'Hatalı: ${ozet['hatali'] ?? 0}',
                Theme.of(context).colorScheme.error),
          ],
        ),
        if (yeniSiniflar.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text('Otomatik oluşturulacak sınıf(lar): '
                '${yeniSiniflar.join(', ')}'),
          ),
        CheckboxListTile(
          contentPadding: EdgeInsets.zero,
          dense: true,
          controlAffinity: ListTileControlAffinity.leading,
          value: _yeniden,
          onChanged: _loading
              ? null
              : (v) {
                  setState(() => _yeniden = v ?? false);
                  _fetchPreview();
                },
          title: const Text(
              'Pasif (mezun) kayıtla çakışanları yeniden kullan ve aktifleştir'),
          subtitle: const Text(
              'Dikkat: o kaydın ödünç geçmişi/cezası yeni öğrenciye devreder.'),
        ),
        const Divider(height: 1),
        Expanded(
          child: ListView.builder(
            itemCount: satirlar.length,
            itemBuilder: (c, i) {
              final s = (satirlar[i] as Map).cast<String, dynamic>();
              final islem = (s['islem'] ?? '').toString();
              final renk = _islemRenk(context, islem);
              return ListTile(
                dense: true,
                leading: Icon(_islemIcon(islem), color: renk),
                title: Text(
                    '${s['uye_no']} — ${s['ad']} ${s['soyad']}'),
                subtitle: Text(
                    '${s['sinif']} · ${_islemEtiket(islem)}'
                    '${s['sebep'] != null ? ' — ${s['sebep']}' : ''}'),
                trailing: Text(_islemEtiket(islem),
                    style: TextStyle(color: renk, fontWeight: FontWeight.w600)),
              );
            },
          ),
        ),
        if (pasife.isNotEmpty)
          ExpansionTile(
            tilePadding: EdgeInsets.zero,
            title: Text('Pasife çekilecek öğrenciler (${pasife.length})'),
            children: [
              for (final p in pasife)
                ListTile(
                  dense: true,
                  title: Text(
                      '${(p as Map)['uye_no']} — ${p['ad']} ${p['soyad']}'),
                ),
            ],
          ),
      ],
    );
  }

  Widget _chip(BuildContext context, String label, Color color) {
    return Chip(
      label: Text(label),
      labelStyle: TextStyle(color: color, fontWeight: FontWeight.w600),
      side: BorderSide(color: color.withValues(alpha: 0.5)),
      backgroundColor: color.withValues(alpha: 0.08),
    );
  }
}
