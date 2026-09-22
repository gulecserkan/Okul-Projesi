import 'package:flutter/material.dart';

import '../api/library_api.dart';
import 'barcode_scanner_screen.dart';

/// Sorgu ekranı (yalnızca personel/admin) — salt-okunur.
///
/// Barkod / üye no / ISBN / başlık ile hızlı sorgu (`fast-query`). Bilgiler
/// görüntülenir; ödünç verme ve iade işlemleri yalnızca masaüstünde yapılır.
class QueryScreen extends StatefulWidget {
  const QueryScreen({super.key, required this.api});

  final LibraryApiClient api;

  @override
  State<QueryScreen> createState() => _QueryScreenState();
}

class _QueryScreenState extends State<QueryScreen> {
  final _queryController = TextEditingController();
  bool _busy = false;
  String? _error;
  Map<String, dynamic>? _result;

  @override
  void dispose() {
    _queryController.dispose();
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

  Future<void> _scan() async {
    final code = await Navigator.of(context).push<String>(
      MaterialPageRoute(builder: (_) => const BarcodeScannerScreen()),
    );
    if (!mounted || code == null || code.isEmpty) return;
    _queryController.text = code;
    await _search();
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

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Sorgu')),
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
                onPressed: _busy ? null : _scan,
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

  Widget _infoNote(ThemeData theme) {
    return Card(
      color: theme.colorScheme.surfaceContainerHighest,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            Icon(Icons.info_outline, size: 18, color: theme.colorScheme.primary),
            const SizedBox(width: 8),
            const Expanded(
              child: Text(
                'Bu bilgiler görüntüleme amaçlıdır. Ödünç verme ve iade '
                'işlemleri masaüstü uygulamasında yapılır.',
              ),
            ),
          ],
        ),
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
          Text(
            'Pasif üye',
            style: TextStyle(color: theme.colorScheme.error),
          ),
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
      const SizedBox(height: 12),
      _infoNote(theme),
    ];
  }

  Widget _loanTile(dynamic raw) {
    final loan = (raw as Map).cast<String, dynamic>();
    final title = _s(loan['kitap']).isNotEmpty
        ? _s(loan['kitap'])
        : _s(loan['kitap_nusha']?['kitap']?['baslik']);
    final barkod = _s(loan['kitap_nusha']?['barkod']);
    final overdue = loan['is_overdue'] == true;
    final penalty = _s(loan['penalty_preview']);
    final parts = <String>[
      if (_s(loan['barkod']).isNotEmpty)
        'Barkod: ${_s(loan['barkod'])}'
      else if (barkod.isNotEmpty)
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
      ),
    );
  }

  List<Widget> _copyView(ThemeData theme, Map<String, dynamic> r) {
    final copy = (r['copy'] as Map?)?.cast<String, dynamic>() ?? {};
    final book = (r['book'] as Map?)?.cast<String, dynamic>() ?? {};
    final loan = (r['loan'] as Map?)?.cast<String, dynamic>();
    final durum = _s(copy['durum']);

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
      const SizedBox(height: 12),
      _infoNote(theme),
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
      const SizedBox(height: 12),
      _infoNote(theme),
    ];
  }
}