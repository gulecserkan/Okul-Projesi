import 'package:flutter/material.dart';

import '../api/library_api.dart';
import 'barcode_scanner_screen.dart';

/// Ödünç / iade ekranı (personel ve editör).
///
/// Barkod veya üye no ile hızlı sorgu (`fast-query`); sonuca göre ödünç ver
/// (`checkout`) veya iade al (`oduncler/<id>/kapat/`).
class LoanScreen extends StatefulWidget {
  const LoanScreen({super.key, required this.api});

  final LibraryApiClient api;

  @override
  State<LoanScreen> createState() => _LoanScreenState();
}

class _LoanScreenState extends State<LoanScreen> {
  final _queryController = TextEditingController();
  final _secondController = TextEditingController();
  bool _busy = false;
  String? _error;
  Map<String, dynamic>? _result;

  @override
  void dispose() {
    _queryController.dispose();
    _secondController.dispose();
    super.dispose();
  }

  String _s(dynamic v) => v == null ? '' : v.toString();

  String _date(dynamic iso) {
    final s = _s(iso);
    if (s.length >= 10) return s.substring(0, 10);
    return s.isEmpty ? '—' : s;
  }

  String _durumLabel(String d) {
    switch (d) {
      case 'mevcut':
        return 'Mevcut';
      case 'oduncte':
        return 'Ödünçte';
      case 'gecikmis':
        return 'Gecikmiş';
      case 'teslim':
        return 'Teslim';
      case 'kayip':
        return 'Kayıp';
      case 'hasarli':
        return 'Hasarlı';
      case 'iptal':
        return 'İptal';
      default:
        return d.isEmpty ? '—' : d;
    }
  }

  Future<void> _scan({required bool forQuery}) async {
    final code = await Navigator.of(context).push<String>(
      MaterialPageRoute(builder: (_) => const BarcodeScannerScreen()),
    );
    if (!mounted || code == null || code.isEmpty) return;
    if (forQuery) {
      _queryController.text = code;
      await _search();
    } else {
      setState(() => _secondController.text = code);
    }
  }

  Future<void> _search() async {
    final q = _queryController.text.trim();
    if (q.isEmpty) {
      setState(() => _error = 'Barkod veya üye no girin.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
      _secondController.clear();
    });
    try {
      final data = await widget.api.fastQuery(q);
      if (!mounted) return;
      setState(() {
        _result = data;
        _busy = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e is ApiException ? e.message : e.toString();
        _busy = false;
        _result = null;
      });
    }
  }

  Future<void> _checkout() async {
    final type = _s(_result?['type']);
    final second = _secondController.text.trim();
    late String uyeNo;
    late String barkod;

    if (type == 'student') {
      uyeNo = _s(_result?['student']?['no']);
      barkod = second;
      if (barkod.isEmpty) {
        setState(() => _error = 'Kitap barkodunu girin.');
        return;
      }
    } else if (type == 'book_copy') {
      uyeNo = second;
      barkod = _s(_result?['copy']?['barkod']);
      if (uyeNo.isEmpty) {
        setState(() => _error = 'Üye numarasını girin.');
        return;
      }
    } else {
      return;
    }

    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await widget.api.checkout(uyeNo: uyeNo, barkod: barkod);
      if (!mounted) return;
      setState(() => _busy = false);
      _snack('Ödünç verildi.');
      await _search();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _error = e is ApiException ? e.message : e.toString();
      });
    }
  }

  Future<void> _returnLoan(Map<String, dynamic> loan) async {
    final baslik = _s(loan['kitap']).isNotEmpty
        ? _s(loan['kitap'])
        : _s(loan['kitap_nusha']?['kitap']?['baslik']);
    final action = await showDialog<_ReturnAction>(
      context: context,
      builder: (_) => _ReturnDialog(
        baslik: baslik.isEmpty ? 'Kitap' : baslik,
        penaltyPreview: _s(loan['penalty_preview']),
      ),
    );
    if (action == null) return;
    final id = loan['id'];
    if (id is! int) return;

    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await widget.api.closeLoan(
        id,
        durum: action.durum,
        teslimTarihi: DateTime.now().toUtc().toIso8601String(),
        gecikmeCezasi: action.penalty,
        odendi: action.odendi,
        kapanisNotu: action.not,
      );
      if (!mounted) return;
      setState(() => _busy = false);
      _snack('İade alındı (${_durumLabel(action.durum)}).');
      await _search();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _error = e is ApiException ? e.message : e.toString();
      });
    }
  }

  void _snack(String msg) {
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(msg)));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Ödünç / İade')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          TextField(
            controller: _queryController,
            textInputAction: TextInputAction.search,
            onSubmitted: (_) => _search(),
            decoration: InputDecoration(
              labelText: 'Barkod / üye no / ISBN / başlık',
              prefixIcon: const Icon(Icons.search),
              suffixIcon: IconButton(
                tooltip: 'Barkod tara',
                icon: const Icon(Icons.qr_code_scanner),
                onPressed: _busy ? null : () => _scan(forQuery: true),
              ),
              border: const OutlineInputBorder(),
              isDense: true,
            ),
          ),
          const SizedBox(height: 8),
          FilledButton.icon(
            onPressed: _busy ? null : _search,
            icon: const Icon(Icons.search),
            label: const Text('Sorgula'),
          ),
          if (_busy)
            const Padding(
              padding: EdgeInsets.only(top: 8),
              child: LinearProgressIndicator(),
            ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Row(
                children: [
                  Icon(Icons.error_outline, color: theme.colorScheme.error),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _error!,
                      style: TextStyle(color: theme.colorScheme.error),
                    ),
                  ),
                ],
              ),
            ),
          const SizedBox(height: 16),
          ..._buildResult(theme),
        ],
      ),
    );
  }

  List<Widget> _buildResult(ThemeData theme) {
    final result = _result;
    if (result == null) return const [];
    switch (_s(result['type'])) {
      case 'student':
        return _studentView(theme, result);
      case 'book_copy':
        return _copyView(theme, result);
      case 'book_availability':
        return _availabilityView(theme, result);
      case 'not_found':
        return [_card([const Text('Kayıt bulunamadı.')])];
      default:
        return const [];
    }
  }

  Widget _card(List<Widget> children) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: children,
        ),
      ),
    );
  }

  Widget _secondField(String label) {
    return TextField(
      controller: _secondController,
      textInputAction: TextInputAction.done,
      onSubmitted: (_) => _checkout(),
      decoration: InputDecoration(
        labelText: label,
        suffixIcon: IconButton(
          tooltip: 'Tara',
          icon: const Icon(Icons.qr_code_scanner),
          onPressed: _busy ? null : () => _scan(forQuery: false),
        ),
        border: const OutlineInputBorder(),
        isDense: true,
      ),
    );
  }

  List<Widget> _studentView(ThemeData theme, Map<String, dynamic> r) {
    final s = (r['student'] as Map?)?.cast<String, dynamic>() ?? {};
    final ps = (r['penalty_summary'] as Map?)?.cast<String, dynamic>() ?? {};
    final loans = (r['active_loans'] as List?) ?? const [];
    final count = ps['outstanding_count'];
    final hasPenalty = count is int && count > 0;

    return [
      _card([
        Text(
          '${_s(s['ad'])} ${_s(s['soyad'])}',
          style: theme.textTheme.titleMedium
              ?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 4),
        Text('No: ${_s(s['no'])}  •  Sınıf: ${_s(s['sinif'])}'),
        Text('Rol: ${_s(s['rol'])}'),
        if (s['aktif'] == false)
          Text('Pasif üye — ödünç verilemez.',
              style: TextStyle(color: theme.colorScheme.error)),
        if (hasPenalty)
          Text(
            'Ödenmemiş ceza: ₺${_s(ps['outstanding_total'])} ($count kayıt)',
            style: TextStyle(color: theme.colorScheme.error),
          ),
      ]),
      const SizedBox(height: 12),
      Text('Aktif ödünçler', style: theme.textTheme.titleSmall),
      if (loans.isEmpty)
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 6),
          child: Text('Aktif ödünç yok.'),
        )
      else
        ...loans.map(_loanTile),
      const SizedBox(height: 16),
      Text('Ödünç ver', style: theme.textTheme.titleSmall),
      const SizedBox(height: 6),
      _secondField('Kitap barkodu'),
      const SizedBox(height: 8),
      FilledButton.icon(
        onPressed: _busy ? null : _checkout,
        icon: const Icon(Icons.add),
        label: const Text('Ödünç Ver'),
      ),
    ];
  }

  Widget _loanTile(dynamic raw) {
    final loan = (raw as Map).cast<String, dynamic>();
    final title = _s(loan['kitap']).isNotEmpty
        ? _s(loan['kitap'])
        : _s(loan['kitap_nusha']?['kitap']?['baslik']);
    final barkod = _s(loan['barkod']).isNotEmpty
        ? _s(loan['barkod'])
        : _s(loan['kitap_nusha']?['barkod']);
    final overdue = loan['is_overdue'] == true;
    final penalty = _s(loan['penalty_preview']);
    final parts = <String>[
      'Barkod: $barkod',
      'İade: ${_date(loan['iade_tarihi'])}',
      if (overdue) 'Gecikmiş',
      if (penalty.isNotEmpty) 'Ceza: ₺$penalty',
    ];
    return Card(
      margin: const EdgeInsets.only(bottom: 6),
      child: ListTile(
        dense: true,
        title: Text(title.isEmpty ? 'Kitap' : title),
        subtitle: Text(parts.join(' · ')),
        trailing: FilledButton.tonal(
          onPressed: _busy ? null : () => _returnLoan(loan),
          child: const Text('İade'),
        ),
      ),
    );
  }

  List<Widget> _copyView(ThemeData theme, Map<String, dynamic> r) {
    final copy = (r['copy'] as Map?)?.cast<String, dynamic>() ?? {};
    final book = (r['book'] as Map?)?.cast<String, dynamic>() ?? {};
    final loan = (r['loan'] as Map?)?.cast<String, dynamic>();
    final durum = _s(copy['durum']);
    final available = durum == 'mevcut' && loan == null;

    return [
      _card([
        Text(
          _s(book['baslik']),
          style: theme.textTheme.titleMedium
              ?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 4),
        Text('Barkod: ${_s(copy['barkod'])}  •  Raf: ${_s(copy['raf_kodu'])}'),
        Text('Durum: ${_durumLabel(durum)}'),
        if (loan != null)
          Text(
            'Ödünçte: ${_s(loan['uye']?['ad'])} ${_s(loan['uye']?['soyad'])} '
            '(${_s(loan['uye']?['uye_no'])})',
          ),
      ]),
      const SizedBox(height: 16),
      if (available) ...[
        Text('Ödünç ver', style: theme.textTheme.titleSmall),
        const SizedBox(height: 6),
        _secondField('Üye no'),
        const SizedBox(height: 8),
        FilledButton.icon(
          onPressed: _busy ? null : _checkout,
          icon: const Icon(Icons.add),
          label: const Text('Ödünç Ver'),
        ),
      ] else if (loan != null) ...[
        FilledButton.icon(
          onPressed: _busy ? null : () => _returnLoan(loan),
          icon: const Icon(Icons.assignment_turned_in_outlined),
          label: const Text('İade Al'),
        ),
      ] else
        Text('Bu nüsha ödünç verilemez (durum: ${_durumLabel(durum)}).'),
    ];
  }

  List<Widget> _availabilityView(ThemeData theme, Map<String, dynamic> r) {
    final book = (r['book'] as Map?)?.cast<String, dynamic>();
    final summary =
        (r['copy_summary'] as Map?)?.cast<String, dynamic>() ?? {};
    final suggestions = (r['suggestions'] as List?) ?? const [];

    return [
      if (book != null)
        _card([
          Text(
            _s(book['baslik']),
            style: theme.textTheme.titleMedium
                ?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 4),
          Text(
            'Nüsha: ${_s(summary['count'])} toplam · '
            '${_s(summary['available'])} mevcut · '
            '${_s(summary['loaned'])} ödünçte',
          ),
          const SizedBox(height: 4),
          const Text('Ödünç vermek için nüsha barkodunu okutun.'),
        ])
      else
        _card([const Text('Bu ISBN ile kayıtlı kitap bulunamadı.')]),
      if (suggestions.isNotEmpty) ...[
        const SizedBox(height: 12),
        Text('Öneriler', style: theme.textTheme.titleSmall),
        ...suggestions.map((s) {
          final m = (s as Map).cast<String, dynamic>();
          return ListTile(
            dense: true,
            leading: const Icon(Icons.menu_book_outlined),
            title: Text(_s(m['baslik'])),
            subtitle: Text('ISBN: ${_s(m['isbn'])}'),
          );
        }),
      ],
    ];
  }
}

class _ReturnAction {
  const _ReturnAction({
    required this.durum,
    required this.penalty,
    required this.odendi,
    required this.not,
  });

  final String durum;
  final String? penalty;
  final bool odendi;
  final String? not;
}

class _ReturnDialog extends StatefulWidget {
  const _ReturnDialog({required this.baslik, required this.penaltyPreview});

  final String baslik;
  final String penaltyPreview;

  @override
  State<_ReturnDialog> createState() => _ReturnDialogState();
}

class _ReturnDialogState extends State<_ReturnDialog> {
  String _durum = 'teslim';
  final _penaltyController = TextEditingController();
  final _notController = TextEditingController();
  bool _odendi = false;

  bool get _isDamage => _durum == 'kayip' || _durum == 'hasarli';

  @override
  void initState() {
    super.initState();
    _penaltyController.text = widget.penaltyPreview;
  }

  @override
  void dispose() {
    _penaltyController.dispose();
    _notController.dispose();
    super.dispose();
  }

  void _confirm() {
    Navigator.of(context).pop(_ReturnAction(
      durum: _durum,
      penalty: _penaltyController.text.trim().replaceAll(',', '.'),
      odendi: _odendi,
      not: _notController.text.trim(),
    ));
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text('İade: ${widget.baslik}'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
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
              onChanged: (v) => setState(() => _durum = v ?? 'teslim'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _penaltyController,
              keyboardType:
                  const TextInputType.numberWithOptions(decimal: true),
              decoration: InputDecoration(
                labelText: _isDamage
                    ? 'Ceza (₺) — gecikme + hasar'
                    : 'Gecikme cezası (₺)',
                border: const OutlineInputBorder(),
                isDense: true,
              ),
            ),
            if (_isDamage) ...[
              const SizedBox(height: 12),
              TextField(
                controller: _notController,
                maxLines: 2,
                decoration: const InputDecoration(
                  labelText: 'Açıklama (not)',
                  hintText: 'Kayıp/hasarlı için açıklama',
                  border: OutlineInputBorder(),
                  isDense: true,
                ),
              ),
            ],
            CheckboxListTile(
              value: _odendi,
              onChanged: (v) => setState(() => _odendi = v ?? false),
              title: const Text('Ceza şimdi ödendi'),
              contentPadding: EdgeInsets.zero,
              controlAffinity: ListTileControlAffinity.leading,
              dense: true,
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Vazgeç'),
        ),
        FilledButton(onPressed: _confirm, child: const Text('İade Al')),
      ],
    );
  }
}
