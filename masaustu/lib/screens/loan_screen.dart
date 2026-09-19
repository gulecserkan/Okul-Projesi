import 'dart:async';

import 'package:flutter/material.dart';

import '../api/kutuphane_api.dart';
import '../api_client.dart';
import '../formatters.dart';
import '../models.dart';
import '../widgets/row_table.dart';

/// Ödünç / İade ekranı — barkod / öğrenci no / ISBN taramaya dayalı akış.
class LoanScreen extends StatefulWidget {
  const LoanScreen({super.key});

  @override
  State<LoanScreen> createState() => _LoanScreenState();
}

class _LoanScreenState extends State<LoanScreen> {
  final _api = KutuphaneApi();
  final _searchController = TextEditingController();

  bool _loading = false;
  bool _busy = false;
  String _lastQ = '';
  Map<String, dynamic>? _result;
  bool _failed = false;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _search(String q) async {
    q = q.trim();
    if (q.isEmpty) {
      setState(() {
        _result = null;
        _lastQ = '';
        _failed = false;
      });
      return;
    }
    setState(() {
      _loading = true;
      _failed = false;
      _lastQ = q;
    });
    try {
      final data = await _api.fastQuery(q);
      if (!mounted) return;
      setState(() {
        _result = data;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _failed = true;
      });
    }
  }

  void _snack(String message, {bool error = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(message),
      backgroundColor: error ? Colors.red.shade700 : null,
    ));
  }

  Future<void> _checkoutCopy(int copyId, String barkod) async {
    if (_busy) return;
    final no = await showDialog<String>(
      context: context,
      builder: (_) => _StudentPickerDialog(barkod: barkod),
    );
    if (no == null || no.isEmpty) return;
    setState(() => _busy = true);
    final resp = await _api.checkout(no, barkod);
    if (!mounted) return;
    setState(() => _busy = false);
    if (resp.statusCode >= 200 && resp.statusCode < 300) {
      _snack('$barkod ödünç verildi.');
      _search(_lastQ);
    } else {
      _snack(extractError(resp, fallback: 'Ödünç verilemedi.'),
          error: true);
    }
  }

  Future<void> _returnLoan(FastLoan loan) async {
    if (_busy) return;
    final action = await showDialog<Map<String, String>>(
      context: context,
      builder: (_) => _ReturnDialog(loan: loan),
    );
    if (action == null) return;
    setState(() => _busy = true);
    final loanResp = await _api.updateLoanStatus(
      loan.id,
      durum: action['durum']!,
      teslimTarihi: DateTime.now().toUtc().toIso8601String(),
      gecikmeCezasi: action['penalty'],
    );
    var ok = loanResp.statusCode >= 200 && loanResp.statusCode < 300;
    if (ok && loan.copyId != null) {
      final copyDurum = action['durum'] == 'teslim' ? 'mevcut' : action['durum']!;
      await _api.updateCopyStatus(loan.copyId!, copyDurum);
    }
    if (!mounted) return;
    setState(() => _busy = false);
    if (ok) {
      _snack('İade alındı (${durumLabel(action['durum']!)}).');
      _search(_lastQ);
    } else {
      _snack(extractError(loanResp, fallback: 'İşlem başarısız oldu.'),
          error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(24, 24, 24, 8),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _searchController,
                  autofocus: true,
                  onSubmitted: (_) => _search(_searchController.text),
                  decoration: const InputDecoration(
                    hintText: 'Barkod, öğrenci no, ISBN veya kitap adı...',
                    prefixIcon: Icon(Icons.qr_code_scanner),
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              FilledButton.icon(
                onPressed: _loading ? null : () => _search(_searchController.text),
                icon: const Icon(Icons.search),
                label: const Text('Ara'),
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Align(
            alignment: Alignment.centerLeft,
            child: Text(
              _hintLine(),
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
        ),
        Expanded(child: _buildBody(context)),
      ],
    );
  }

  String _hintLine() {
    if (_loading) return 'Aranıyor...';
    if (_failed) return 'Sunucuya ulaşılamadı.';
    if (_result == null) {
      return _lastQ.isEmpty ? 'Tarayıcı okutun veya numara yazıp Enter verin.'
          : 'Sonuç bulunamadı.';
    }
    final type = _result!['type'];
    switch (type) {
      case 'book_copy':
        return 'Nüsha bulundu.';
      case 'book_availability':
        return 'Kitap bulundu — nüshalarını aşağıda görün.';
      case 'student':
        return 'Öğrenci bulundu — aktif ödünçleri aşağıda.';
      case 'not_found':
        return 'Eşleşen kayıt yok.';
      default:
        return '';
    }
  }

  Widget _buildBody(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_failed) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Arama yapılamadı.', style: TextStyle(color: Colors.red)),
            const SizedBox(height: 8),
            FilledButton.tonal(
              onPressed: () => _search(_lastQ),
              child: const Text('Tekrar Dene'),
            ),
          ],
        ),
      );
    }
    final result = _result;
    if (result == null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.qr_code_scanner,
                size: 64, color: Theme.of(context).colorScheme.outline),
            const SizedBox(height: 12),
            const Text('Yukarıdaki kutuya barkod veya öğrenci numarası okutun.'),
          ],
        ),
      );
    }
    switch (result['type']) {
      case 'book_copy':
        return _BookCopyResult(
          api: _api,
          data: result,
          busy: _busy,
          onCheckout: _checkoutCopy,
          onReturn: _returnLoan,
        );
      case 'book_availability':
        return _BookAvailabilityResult(
          data: result,
          busy: _busy,
          onCheckout: _checkoutCopy,
          onReturn: _returnLoan,
          onSuggestion: (t) => _search(t),
        );
      case 'student':
        return _StudentResult(
          data: result,
          busy: _busy,
          onReturn: _returnLoan,
        );
      default:
        return Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.search_off,
                  size: 56, color: Theme.of(context).colorScheme.outline),
              const SizedBox(height: 12),
              const Text('Sonuç bulunamadı. Barkodu veya numarayı kontrol edin.'),
            ],
          ),
        );
    }
  }
}

/// Listelerin alt başlık satırı (özet istatistik tonunda).
class _SectionHeader extends StatelessWidget {
  final String title;
  final Widget? trailing;

  const _SectionHeader(this.title, {this.trailing});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Row(
      children: [
        Icon(Icons.label_outline,
            size: 18, color: theme.colorScheme.primary),
        const SizedBox(width: 6),
        Text(title, style: theme.textTheme.titleSmall),
        const Spacer(),
        ?trailing,
      ],
    );
  }
}

class _BookHeader extends StatelessWidget {
  final String baslik;
  final String? yazar;
  final String? kategori;
  final String? isbn;

  const _BookHeader({
    required this.baslik,
    this.yazar,
    this.kategori,
    this.isbn,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(Icons.menu_book, size: 40, color: theme.colorScheme.primary),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(baslik,
                  style: theme.textTheme.titleMedium
                      ?.copyWith(fontWeight: FontWeight.w600)),
              const SizedBox(height: 2),
              Text([
                if (yazar != null && yazar!.isNotEmpty) yazar!,
                if (kategori != null && kategori!.isNotEmpty) kategori!,
                if (isbn != null && isbn!.isNotEmpty) 'ISBN: $isbn',
              ].join(' • ')),
            ],
          ),
        ),
      ],
    );
  }
}

class _DurumChip extends StatelessWidget {
  final String durum;

  const _DurumChip(this.durum);

  @override
  Widget build(BuildContext context) {
    final color = durumColor(durum);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.5)),
      ),
      child: Text(durumLabel(durum),
          style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600)),
    );
  }
}

/// Tek nüsha sonucu (barkod tarandı).
class _BookCopyResult extends StatefulWidget {
  final KutuphaneApi api;
  final Map<String, dynamic> data;
  final bool busy;
  final Future<void> Function(int, String) onCheckout;
  final Future<void> Function(FastLoan) onReturn;

  const _BookCopyResult({
    required this.api,
    required this.data,
    required this.busy,
    required this.onCheckout,
    required this.onReturn,
  });

  @override
  State<_BookCopyResult> createState() => _BookCopyResultState();
}

class _BookCopyResultState extends State<_BookCopyResult> {
  bool _checking = false;

  FastLoan? _loanWithCopy() {
    final loanJson = widget.data['loan'];
    if (loanJson is! Map<String, dynamic>) return null;
    final copyId = widget.data['copy']?['id'] as int?;
    return FastLoan.fromJson(loanJson).copyWith(copyId: copyId);
  }

  Future<void> _checkout(String barkod) async {
    setState(() => _checking = true);
    await widget.onCheckout(widget.data['copy']?['id'] as int? ?? 0, barkod);
    if (mounted) setState(() => _checking = false);
  }

  Future<void> _return(FastLoan loan) async {
    setState(() => _checking = true);
    await widget.onReturn(loan);
    if (mounted) setState(() => _checking = false);
  }

  @override
  Widget build(BuildContext context) {
    final book = widget.data['book'] as Map<String, dynamic>? ?? const {};
    final copy = widget.data['copy'] as Map<String, dynamic>? ?? const {};
    final FastLoan? loan = _loanWithCopy();
    final history = (widget.data['history'] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(FastLoan.fromJson)
        .toList();
    final barkod = copy['barkod'] as String? ?? '';
    final canCheckout = loan == null && (copy['durum'] == 'mevcut');

    return ListView(
      padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _BookHeader(
                  baslik: book['baslik'] as String? ?? '',
                  yazar: book['yazar'] as String?,
                  kategori: book['kategori'] as String?,
                  isbn: book['isbn'] as String?,
                ),
                const SizedBox(height: 16),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Chip(
                      visualDensity: VisualDensity.compact,
                      avatar: const Icon(Icons.qr_code, size: 18),
                      label: Text(barkod),
                    ),
                    if ((copy['raf_kodu'] as String?)?.isNotEmpty ?? false)
                      Chip(
                        visualDensity: VisualDensity.compact,
                        avatar: const Icon(Icons.shelves, size: 18),
                        label: Text('Raf: ${copy['raf_kodu']}'),
                      ),
                    _DurumChip(copy['durum'] as String? ?? ''),
                  ],
                ),
                const SizedBox(height: 16),
                if (loan != null)
                  _LoanBanner(
                    loan: loan,
                    busy: widget.busy || _checking,
                    onReturn: () => _return(loan),
                  )
                else if (canCheckout)
                  FilledButton.icon(
                    onPressed: (widget.busy || _checking)
                        ? null
                        : () => _checkout(barkod),
                    icon: const Icon(Icons.outbox),
                    label: const Text('Ödünç Ver'),
                  )
                else
                  Text(
                    'Bu nüsha ödünç verilemez (durum: ${durumLabel(copy['durum'] as String? ?? '')}).',
                    style: TextStyle(color: Colors.grey.shade700),
                  ),
              ],
            ),
          ),
        ),
        if (history.isNotEmpty) ...[
          const SizedBox(height: 16),
          _SectionHeader('Son işlemler'),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  for (final h in history)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Row(
                        children: [
                          Expanded(
                            child: Text(
                              h.ogrenciAdSoyad ?? '—',
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          Text(formatDate(h.iadeTarihi)),
                          const SizedBox(width: 12),
                          _DurumChip(h.durum),
                        ],
                      ),
                    ),
                ],
              ),
            ),
          ),
        ],
      ],
    );
  }
}

/// Nüshanın sahibi + "İade Al" banner.
class _LoanBanner extends StatelessWidget {
  final FastLoan loan;
  final bool busy;
  final VoidCallback onReturn;

  const _LoanBanner({
    required this.loan,
    required this.busy,
    required this.onReturn,
  });

  @override
  Widget build(BuildContext context) {
    final overdue = loan.isOverdue;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: (overdue ? Colors.red : Colors.blueGrey).withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: (overdue ? Colors.red : Colors.blueGrey).withValues(alpha: 0.4),
        ),
      ),
      child: Row(
        children: [
          Icon(overdue ? Icons.warning_amber : Icons.person,
              color: overdue ? Colors.red.shade700 : Colors.blueGrey),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(loan.ogrenciAdSoyad ?? '—',
                    style: const TextStyle(fontWeight: FontWeight.w600)),
                Text('No: ${loan.ogrenciNo ?? '—'}  •  İade: ${formatDate(loan.iadeTarihi)}'),
                if (overdue)
                  Text(
                    'Gecikme: ${loan.overdueDays} gün'
                    '${loan.penaltyPreview != null ? '  •  Cezası: ₺${loan.penaltyPreview}' : ''}',
                    style: TextStyle(color: Colors.red.shade700, fontWeight: FontWeight.w600),
                  ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          FilledButton.tonalIcon(
            onPressed: busy ? null : onReturn,
            icon: const Icon(Icons.login),
            label: const Text('İade Al'),
          ),
        ],
      ),
    );
  }
}

/// Kitap (ISBN / başlık) sonucu — nüsha listesiyle.
class _BookAvailabilityResult extends StatelessWidget {
  final Map<String, dynamic> data;
  final bool busy;
  final Future<void> Function(int, String) onCheckout;
  final Future<void> Function(FastLoan) onReturn;
  final void Function(String) onSuggestion;

  const _BookAvailabilityResult({
    required this.data,
    required this.busy,
    required this.onCheckout,
    required this.onReturn,
    required this.onSuggestion,
  });

  @override
  Widget build(BuildContext context) {
    final book = data['book'] as Map<String, dynamic>? ?? const {};
    final summary = data['copy_summary'] as Map<String, dynamic>? ?? const {};
    final copies = (data['copies'] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(FastCopy.fromJson)
        .toList();
    final suggestions = (data['suggestions'] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .toList();
    final count = summary['count'] as int? ?? copies.length;
    final available = summary['available'] as int? ?? 0;
    final loaned = summary['loaned'] as int? ?? 0;

    return ListView(
      padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _BookHeader(
                  baslik: book['baslik'] as String? ?? '',
                  yazar: book['yazar'] as String?,
                  kategori: book['kategori'] as String?,
                  isbn: book['isbn'] as String?,
                ),
                const SizedBox(height: 16),
                Wrap(
                  spacing: 8,
                  children: [
                    _SummaryChip(icon: Icons.inventory_2, label: '$count nüsha'),
                    _SummaryChip(
                        icon: Icons.check_circle,
                        label: '$available müsait',
                        color: Colors.green.shade700),
                    _SummaryChip(
                        icon: Icons.sync,
                        label: '$loaned ödünçte',
                        color: Colors.amber.shade800),
                  ],
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        _SectionHeader('Nüshalar'),
        const SizedBox(height: 8),
        RowTable(
          minWidth: 760,
          columns: const [
            RowTableColumn('Barkod', flex: 2),
            RowTableColumn('Raf', flex: 1),
            RowTableColumn('Durum', flex: 1),
            RowTableColumn('Öğrenci', flex: 3),
            RowTableColumn('', flex: 0),
          ],
          rows: [
            for (final c in copies)
              RowTableRow(
                selected: false,
                onSelected: () {},
                onOpen: () {},
                cells: [
                  Text(c.barkod,
                      style: const TextStyle(fontWeight: FontWeight.w600)),
                  Text(c.rafKodu ?? '—'),
                  _DurumChip(c.durum),
                  Text(c.loan?.ogrenciAdSoyad ?? '—',
                      overflow: TextOverflow.ellipsis),
                  if (c.loan != null)
                    IconButton(
                      tooltip: 'İade Al',
                      visualDensity: VisualDensity.compact,
                      icon: const Icon(Icons.login, color: Colors.blueGrey),
                      onPressed: busy ? null : () => onReturn(c.loan!),
                    )
                  else if (c.durum == 'mevcut')
                    IconButton(
                      tooltip: 'Ödünç Ver',
                      visualDensity: VisualDensity.compact,
                      icon: const Icon(Icons.outbox, color: Colors.green),
                      onPressed: busy ? null : () => onCheckout(c.id, c.barkod),
                    )
                  else
                    const SizedBox.shrink(),
                ],
              ),
          ],
        ),
        if (suggestions.isNotEmpty) ...[
          const SizedBox(height: 16),
          _SectionHeader('Benzer başlıklar'),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final s in suggestions)
                    ActionChip(
                      label: Text(s['baslik'] as String? ?? ''),
                      onPressed: () => onSuggestion(s['baslik'] as String? ?? ''),
                    ),
                ],
              ),
            ),
          ),
        ],
      ],
    );
  }
}

class _SummaryChip extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color? color;

  const _SummaryChip({required this.icon, required this.label, this.color});

  @override
  Widget build(BuildContext context) {
    return Chip(
      visualDensity: VisualDensity.compact,
      avatar: Icon(icon, size: 18, color: color),
      label: Text(label,
          style: color == null ? null : TextStyle(color: color)),
    );
  }
}

/// Öğrenci sonucu — aktif ödünçler + geçmiş.
class _StudentResult extends StatelessWidget {
  final Map<String, dynamic> data;
  final bool busy;
  final Future<void> Function(FastLoan) onReturn;

  const _StudentResult({
    required this.data,
    required this.busy,
    required this.onReturn,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final st = FastStudent.fromJson(data['student'] as Map<String, dynamic>);
    final penaltyJson = data['penalty_summary'];
    final penalty = penaltyJson is Map<String, dynamic>
        ? PenaltySummary.fromJson(penaltyJson)
        : const PenaltySummary();
    final active = (data['active_loans'] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(FastLoan.fromJson)
        .toList();
    final history = (data['history'] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(FastLoan.fromJson)
        .toList();
    final role = data['policy'];

    return ListView(
      padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    CircleAvatar(
                      radius: 24,
                      child: Text(st.adSoyad.substring(0, 1).toUpperCase()),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '${st.ad} ${st.soyad}',
                            style: theme.textTheme.titleMedium
                                ?.copyWith(fontWeight: FontWeight.w600),
                          ),
                          Text(
                            [
                              'No: ${st.no}',
                              if (st.sinif != null) st.sinif!,
                              if (st.rol != null) st.rol!,
                            ].join(' • '),
                          ),
                        ],
                      ),
                    ),
                    _DurumChip(st.aktif ? 'mevcut' : 'kayip'),
                  ],
                ),
                if (role is Map<String, dynamic>)
                  Padding(
                    padding: const EdgeInsets.only(top: 12),
                    child: Text(
                      'Ödünç hakkı: ${role['max_items'] ?? '—'} kitap • '
                      '${role['duration'] ?? '—'} gün'
                      '${role['loan_blocked'] == true ? ' • Ödünç kapalı' : ''}',
                      style: theme.textTheme.bodySmall,
                    ),
                  ),
              ],
            ),
          ),
        ),
        if (penalty.outstandingCount > 0) ...[
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.red.withValues(alpha: 0.06),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.red.withValues(alpha: 0.4)),
            ),
            child: Row(
              children: [
                Icon(Icons.report_gmailerrorred, color: Colors.red.shade700),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Ödenmemiş ceza: ₺${penalty.outstandingTotal} '
                    '(${penalty.outstandingCount} kayıt)',
                    style: TextStyle(
                        color: Colors.red.shade700,
                        fontWeight: FontWeight.w600),
                  ),
                ),
              ],
            ),
          ),
        ],
        const SizedBox(height: 16),
        _SectionHeader('Aktif ödünçler', trailing: Text('${active.length}')),
        const SizedBox(height: 8),
        if (active.isEmpty)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Center(
                child: Text('Aktif ödünç yok.',
                    style: TextStyle(color: Colors.grey.shade700)),
              ),
            ),
          )
        else
          Card(
            margin: EdgeInsets.zero,
            clipBehavior: Clip.antiAlias,
            child: Column(
              children: [
                for (final loan in active)
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: const BoxDecoration(
                      border: Border(
                        bottom:
                            BorderSide(color: Color(0xFFE4E4E7), width: 0.5),
                      ),
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(loan.kitapBaslik ?? '',
                                  style: const TextStyle(fontWeight: FontWeight.w600)),
                              Text(
                                'Barkod: ${loan.barkod ?? '—'}  •  '
                                'İade: ${formatDate(loan.iadeTarihi)}',
                                style: theme.textTheme.bodySmall,
                              ),
                              if (loan.isOverdue)
                                Text(
                                  'Gecikme: ${loan.overdueDays} gün'
                                  '${loan.penaltyPreview != null ? ' • ₺${loan.penaltyPreview}' : ''}',
                                  style: TextStyle(
                                      color: Colors.red.shade700,
                                      fontWeight: FontWeight.w600,
                                      fontSize: 12),
                                ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 12),
                        FilledButton.tonalIcon(
                          onPressed: busy ? null : () => onReturn(loan),
                          icon: const Icon(Icons.login,
                              size: 18, color: Colors.blueGrey),
                          label: const Text('İade Al'),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ),
        if (history.isNotEmpty) ...[
          const SizedBox(height: 16),
          _SectionHeader('Geçmiş'),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  for (final h in history)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 3),
                      child: Row(
                        children: [
                          Expanded(
                            child: Text(h.kitapBaslik ?? '',
                                overflow: TextOverflow.ellipsis),
                          ),
                          Text(formatDate(h.teslimTarihi ?? h.iadeTarihi)),
                          const SizedBox(width: 12),
                          _DurumChip(h.durum),
                        ],
                      ),
                    ),
                ],
              ),
            ),
          ),
        ],
      ],
    );
  }
}

/// Ödünç verecek öğrenciyi arayıp seçtiren diyalog.
class _StudentPickerDialog extends StatefulWidget {
  final String barkod;

  const _StudentPickerDialog({required this.barkod});

  @override
  State<_StudentPickerDialog> createState() => _StudentPickerDialogState();
}

class _StudentPickerDialogState extends State<_StudentPickerDialog> {
  final _api = KutuphaneApi();
  final _controller = TextEditingController();
  List<Ogrenci> _results = [];
  bool _loading = false;
  Timer? _debounce;

  @override
  void dispose() {
    _debounce?.cancel();
    _controller.dispose();
    super.dispose();
  }

  void _onChanged(String text) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 300), () async {
      final q = text.trim();
      if (q.length < 2) {
        setState(() {
          _results = [];
          _loading = false;
        });
        return;
      }
      setState(() => _loading = true);
      final res = await _api.studentsPage(page: 1, pageSize: 20, q: q);
      if (!mounted) return;
      setState(() {
        _results = res.items;
        _loading = false;
      });
    });
  }

  void _pick(Ogrenci o) {
    Navigator.of(context).pop(o.ogrenciNo);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Dialog(
      child: SizedBox(
        width: 520,
        height: 480,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 12, 8),
              child: Row(
                children: [
                  Expanded(
                    child: Text('Ödünç verilecek öğrenci',
                        style: theme.textTheme.titleMedium),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: Text('Barkod: ${widget.barkod}',
                  style: theme.textTheme.bodySmall),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 8),
              child: TextField(
                controller: _controller,
                autofocus: true,
                onChanged: _onChanged,
                onSubmitted: (v) {
                  if (_results.length == 1) _pick(_results.first);
                },
                decoration: const InputDecoration(
                  hintText: 'No, ad veya soyad yazın...',
                  prefixIcon: Icon(Icons.search),
                  border: OutlineInputBorder(),
                  isDense: true,
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: Text(
                _results.isEmpty && _controller.text.trim().length >= 2
                    ? 'Eşleşen öğrenci yok.'
                    : 'Aramak için en az 2 karakter girin.',
                style: theme.textTheme.bodySmall,
              ),
            ),
            const SizedBox(height: 4),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : ListView.builder(
                      itemCount: _results.length,
                      itemBuilder: (context, i) {
                        final o = _results[i];
                        return ListTile(
                          leading: const Icon(Icons.person_outline),
                          title: Text(o.adSoyad),
                          subtitle: Text(
                              '${o.ogrenciNo}  •  ${o.sinif?.ad ?? '—'}'),
                          onTap: () => _pick(o),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

/// İade işlemi diyaloğu: durum + (gecikmişse) ceza.
class _ReturnDialog extends StatefulWidget {
  final FastLoan loan;

  const _ReturnDialog({required this.loan});

  @override
  State<_ReturnDialog> createState() => _ReturnDialogState();
}

class _ReturnDialogState extends State<_ReturnDialog> {
  late String _durum = 'teslim';
  final _penaltyController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _penaltyController.text = widget.loan.penaltyPreview ?? '';
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
              'Öğrenci: ${loan.ogrenciAdSoyad ?? '—'} (${loan.ogrenciNo ?? '—'})\n'
              'İade: ${formatDate(loan.iadeTarihi)}',
              style: theme.textTheme.bodySmall,
            ),
            if (loan.isOverdue) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.red.withValues(alpha: 0.07),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  'Gecikme: ${loan.overdueDays} gün'
                  '${loan.penaltyPreview != null ? ' • Günlük ceza öngörüsü: ₺${loan.penaltyPreview}' : ''}',
                  style: TextStyle(color: Colors.red.shade700),
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
                if (v != null) setState(() => _durum = v);
              },
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _penaltyController,
              keyboardType:
                  const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(
                labelText: 'Gecikme cezası (₺) — boş bırakılırsa bağlanmaz',
                border: OutlineInputBorder(),
                isDense: true,
              ),
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