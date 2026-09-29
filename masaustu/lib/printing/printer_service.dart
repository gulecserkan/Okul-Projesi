import 'dart:convert';
import 'dart:io';

/// Yazıcı kuyruğu bilgisi (CUPS `lpstat -p` çıktısından).
class PrinterInfo {
  final String name;
  final PrinterState state;
  final String detail;

  const PrinterInfo({
    required this.name,
    required this.state,
    this.detail = '',
  });

  bool get cikisYapabilir =>
      state == PrinterState.ready || state == PrinterState.busy;

  factory PrinterInfo.fromJson(Map<String, dynamic> json) => PrinterInfo(
        name: json['name'] as String? ?? '',
        state: PrinterState.values.firstWhere(
          (s) => s.name == json['state'],
          orElse: () => PrinterState.unknown,
        ),
        detail: json['detail'] as String? ?? '',
      );
}

enum PrinterState { ready, busy, disabled, error, missing, unknown }

/// Bir komut çalıştırmanın sonucu (test için inject edilebilir).
class ProcResult {
  final int exitCode;
  final String stdout;
  final String stderr;

  const ProcResult(this.exitCode, this.stdout, this.stderr);

  bool get ok => exitCode == 0;
}

/// Komut çalıştırıcı; testlerde sahte çıktı ile değiştirilir.
typedef ProcessRunner = Future<ProcResult> Function(
    String executable, List<String> args);

/// Yazdırma işlemi sonucu.
class PrintResult {
  final bool ok;
  final String message;

  const PrintResult(this.ok, this.message);
}

/// Uygulama genelinde kullanılan yazıcı servisi (testlerde değiştirilebilir).
class PrinterServices {
  static PrinterService instance = PrinterService();
}

/// CUPS üzerinden yazıcı yönetimi ve basım (K14).
///
/// Hiçbir yazıcı adı sabit değildir: kuyruklar `lpstat -p` ile çalışma anında
/// algılanır; basım `lp -d <kuyruk>` ile yapılır. Böylece aynı kurulu paket
/// geliştirme ve kütüphane bilgisayarında aynı şekilde çalışır.
class PrinterService {
  PrinterService({ProcessRunner? runner}) : _runner = runner ?? _defaultRunner;

  final ProcessRunner _runner;

  static Future<ProcResult> _defaultRunner(
      String executable, List<String> args) async {
    try {
      final r = await Process.run(executable, args,
          stdoutEncoding: utf8, stderrEncoding: utf8);
      return ProcResult(r.exitCode, (r.stdout as String?) ?? '',
          (r.stderr as String?) ?? '');
    } on ProcessException catch (e) {
      return ProcResult(127, '', e.message);
    }
  }

  /// CUPS komutları sistemde var mı? (`lp`/`lpstat` → `cups-client` paketi)
  Future<bool> cupsKurulu() async {
    final r = await _runner('lpstat', ['-p']);
    return r.ok;
  }

  /// Tüm CUPS kuyrukları (ad + durum) [K14.5].
  Future<List<PrinterInfo>> listPrinters() async {
    final r = await _runner('lpstat', ['-p']);
    if (!r.ok) {
      // lpstat döndü ama kuyruk yoksa çıktı boş olabilir; hata değilse boş liste.
      if (r.stderr.trim().isNotEmpty && r.stdout.trim().isEmpty) {
        return const [];
      }
    }
    final infos = <PrinterInfo>[];
    for (final raw in r.stdout.split('\n')) {
      final line = raw.trim();
      if (!line.startsWith('printer ')) continue;
      final rest = line.substring('printer '.length).trim();
      final name = rest.split(' ').first;
      final state = _parseState(rest);
      infos.add(PrinterInfo(name: name, state: state, detail: rest));
    }
    return infos;
  }

  static PrinterState _parseState(String rest) {
    if (rest.contains('disabled') || rest.contains('stopped')) {
      return PrinterState.disabled;
    }
    if (rest.contains('now printing') || rest.contains('is printing')) {
      return PrinterState.busy;
    }
    if (rest.contains('is idle')) return PrinterState.ready;
    if (rest.contains('missing') || rest.contains('does not exist')) {
      return PrinterState.missing;
    }
    return PrinterState.unknown;
  }

  /// Belirli bir kuyruk kullanılabilir durumda mı? [K14.5]
  Future<PrinterInfo?> findPrinter(String queue) async {
    if (queue.trim().isEmpty) return null;
    final printers = await listPrinters();
    for (final p in printers) {
      if (p.name == queue) return p;
    }
    return PrinterInfo(
        name: queue, state: PrinterState.missing, detail: 'Kuyruk bulunamadı.');
  }

  /// `lp` ile bir PDF bastırır. `media` verilirse `-o media=...` eklenir;
  /// verilmezse PDF'in kendi sayfa boyutu okunur ve standart (A4/Letter) harici
  /// bir boyutse etiket/fiş gibi küçük sayfalarda `Custom.WxH` geçirilir.
  /// (Kağıt tipi/gap zorlanmaz: 4B-2074C gibi termal yazıcılar besleme ölçüsünü
  /// kendi sensör kalibrasyonundan yönetir — K14.11.)
  Future<PrintResult> printPdf(
    String queue,
    List<int> pdfBytes, {
    String title = 'kutuphane-basım',
    String? media,
    List<String> ekSecenekler = const [],
  }) async {
    final q = queue.trim();
    if (q.isEmpty) {
      return const PrintResult(false,
          'Yazıcı seçilmemiş. Ayarlar › Yazıcılar sekmesinden bir yazıcı seçin.');
    }
    final file = File(
        '${Directory.systemTemp.path}/kutuphane_${DateTime.now().millisecondsSinceEpoch}.pdf');
    try {
      await file.writeAsBytes(pdfBytes, flush: true);
      final args = <String>['-d', q];
      final mediaArg = media != null && media.trim().isNotEmpty
          ? media
          : _mediaArgFromPdf(pdfBytes);
      if (mediaArg != null) {
        args.addAll(['-o', 'media=$mediaArg']);
      }
      for (final sec in ekSecenekler) {
        if (sec.trim().isNotEmpty) args.addAll(['-o', sec.trim()]);
      }
      args.addAll(['-t', title, file.path]);
      final r = await _runner('lp', args);
      if (r.ok) {
        return PrintResult(true, 'Yazdırıldı: $q');
      }
      final msg = r.stderr.trim().isNotEmpty ? r.stderr.trim() : 'lp hatası ${r.exitCode}';
      return PrintResult(false, 'Yazdırılamadı ($q): $msg');
    } finally {
      try {
        if (await file.exists()) await file.delete();
      } catch (_) {}
    }
  }

  /// PDF `MediaBox`'ından `Custom.WxHpt` biçiminde media seçeneği üretir.
  /// A4/Letter benzeri standart boyutlar için `null` (kuyruk varsayılanını korur).
  static String? _mediaArgFromPdf(List<int> pdfBytes) {
    try {
      final s = latin1.decode(pdfBytes);
      final m = RegExp(
              r'/MediaBox\s*\[\s*([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s*\]')
          .firstMatch(s);
      if (m == null) return null;
      final w = double.parse(m.group(3)!);
      final h = double.parse(m.group(4)!);
      if (_standartSayfa(w, h)) return null;
      double trim(double v) =>
          (v * 100).round() / 100; // CUPS nokta sayısını kabul eder
      return 'Custom.${trim(w)}x${trim(h)}';
    } catch (_) {
      return null;
    }
  }

  static bool _standartSayfa(double w, double h) {
    bool near(double a, double b) => (a - b).abs() / a < 0.02;
    const a4W = 595.28, a4H = 841.89, usW = 612.0, usH = 792.0;
    return (near(a4W, w) && near(a4H, h)) ||
        (near(a4H, w) && near(a4W, h)) ||
        (near(usW, w) && near(usH, h)) ||
        (near(usH, w) && near(usW, h));
  }
}