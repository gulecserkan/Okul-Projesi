import 'package:flutter/material.dart';

import '../api/kutuphane_api.dart';
import '../formatters.dart';
import '../models.dart';
import '../theme.dart';

/// İade işlemi diyaloğu: teslim / kayıp / hasarlı seçimi, ceza ve ödeme.
///
/// `Map<String, String>` döner: `{durum, penalty, odendi}` (iptalde null).
class ReturnDialog extends StatefulWidget {
  final FastLoan loan;
  final KutuphaneApi api;

  const ReturnDialog({super.key, required this.loan, required this.api});

  @override
  State<ReturnDialog> createState() => _ReturnDialogState();
}

class _ReturnDialogState extends State<ReturnDialog> {
  late String _durum = 'teslim';
  final _penaltyController = TextEditingController();
  bool _odendi = false;
  String? _suggestionNote;

  bool get _isDamageClose => _durum == 'kayip' || _durum == 'hasarli';

  @override
  void initState() {
    super.initState();
    _penaltyController.text = widget.loan.penaltyPreview ?? '';
    _loadSuggestion();
  }

  Future<void> _loadSuggestion() async {
    final (suggestion, _) = await widget.api.fetchLoanPolicy();
    if (!mounted || suggestion == null) return;
    setState(() {
      _suggestionNote = suggestion;
      if (_isDamageClose && _penaltyController.text.isEmpty) {
        _penaltyController.text = suggestion;
      }
    });
  }

  @override
  void dispose() {
    _penaltyController.dispose();
    super.dispose();
  }

  void _confirm() {
    Navigator.of(context).pop({
      'durum': _durum,
      'penalty': _penaltyController.text.trim().replaceAll(',', '.'),
      'odendi': _odendi ? 'true' : 'false',
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final loan = widget.loan;
    return AlertDialog(
      title: const Text('İade işlemi'),
      content: SizedBox(
        width: 420,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              '${loan.kitapBaslik ?? ''}\nBarkod: ${loan.barkod ?? '—'}',
              style: theme.textTheme.bodyMedium,
            ),
            const SizedBox(height: 8),
            Text(
              'Üye: ${loan.uyeAdSoyad ?? '—'} (${loan.uyeNo ?? '—'})\n'
              'İade: ${formatDate(loan.iadeTarihi)}',
              style: theme.textTheme.bodySmall,
            ),
            if (loan.isOverdue) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: layerColor(context, dangerColor(context), alpha: 0.07),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  'Gecikme: ${loan.overdueDays} gün'
                  '${loan.penaltyPreview != null ? ' • Günlük ceza öngörüsü: ₺${loan.penaltyPreview}' : ''}',
                  style: TextStyle(color: dangerColor(context)),
                ),
              ),
            ],
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              initialValue: _durum,
              decoration: const InputDecoration(
                labelText: 'Yeni durum',
                border: OutlineInputBorder(),
                isDense: true,
              ),
              items: const [
                DropdownMenuItem(value: 'teslim', child: Text('Teslim Alındı')),
                DropdownMenuItem(value: 'kayip', child: Text('Kayıp')),
                DropdownMenuItem(value: 'hasarli', child: Text('Hasarlı')),
              ],
              onChanged: (v) {
                if (v == null) return;
                setState(() {
                  _durum = v;
                  if (_isDamageClose &&
                      _suggestionNote != null &&
                      _penaltyController.text.isEmpty) {
                    _penaltyController.text = _suggestionNote!;
                  }
                });
              },
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _penaltyController,
              keyboardType:
                  const TextInputType.numberWithOptions(decimal: true),
              decoration: InputDecoration(
                labelText: _isDamageClose
                    ? 'Ceza (₺) — gecikme + hasar'
                    : 'Gecikme cezası (₺)',
                hintText: _isDamageClose && _suggestionNote != null
                    ? 'Önerilen: $_suggestionNote'
                    : 'Boş bırakılırsa bağlanmaz',
                border: const OutlineInputBorder(),
                isDense: true,
              ),
            ),
            if (_suggestionNote != null) ...[
              const SizedBox(height: 8),
              Text(
                'Kayıp/hasarlı için önerilen ceza: ₺$_suggestionNote '
                '(düzenlenebilir)',
                style: theme.textTheme.bodySmall
                    ?.copyWith(color: theme.colorScheme.primary),
              ),
            ],
            const SizedBox(height: 12),
            CheckboxListTile(
              value: _odendi,
              onChanged: (v) => setState(() => _odendi = v ?? false),
              title: const Text('Ceza şimdi ödendi'),
              contentPadding: EdgeInsets.zero,
              controlAffinity: ListTileControlAffinity.leading,
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('İptal'),
        ),
        FilledButton(
          onPressed: _confirm,
          child: const Text('İade Al'),
        ),
      ],
    );
  }
}
