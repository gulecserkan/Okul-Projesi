import 'package:flutter/material.dart';

import '../config.dart';
import 'printer_service.dart';
import '../theme.dart';

/// Rulo tipi (K14.9).
enum RuloTipi { fis, etiket }

/// Ortak yazıcı için gösterilen durum (K14.9).
enum RuloDurum { tanimsiz, fis, etiket, pasif }

String ruloTipiEtiketi(RuloTipi tip) => tip == RuloTipi.fis ? 'Fiş' : 'Etiket';

/// Fiş ve etiket aynı CUPS kuyruğuna atanmışsa o kuyruk adını döner; değilse
/// `null` (K14.9). Rulo durumu/onayı yalnız bu durumda anlamlıdır.
String? ortakKuyruk() {
  final p = AppConfig.printer;
  final f = p.fisYazici.trim();
  final e = p.etiketYazici.trim();
  if (f.isEmpty || e.isEmpty || f != e) return null;
  return f;
}

/// Bildirilen rulodan (pasif denetimsiz) durum üretir.
RuloDurum bildirileneGore(PrinterPrefs prefs) => switch (prefs.rulo) {
      'fis' => RuloDurum.fis,
      'etiket' => RuloDurum.etiket,
      _ => RuloDurum.tanimsiz,
    };

/// Ortak yazıcının güncel durumu: pasif denetimi dahil (K14.9).
Future<RuloDurum> guncelRuloDurumu() async {
  final q = ortakKuyruk();
  if (q == null) return RuloDurum.tanimsiz;
  final info = await PrinterServices.instance.findPrinter(q);
  if (info != null && !info.cikisYapabilir) return RuloDurum.pasif;
  return bildirileneGore(AppConfig.printer);
}

/// Basımdan önce rulo uygunluğunu denetler (K14.9).
///
/// - Farklı yazıcılar seçiliyse hiçbir onay göstermeden `true`.
/// - Bildirilen rulo istenenle uyuşuyor ve yazıcı hazırsa `true` (sessiz).
/// - Uyuşmazlık/tanımsız: «X rulosu taktım → yazdır» / «Vazgeç».
/// - Yazıcı pasif: «Yine de dene» / «Vazgeç».
Future<bool> ruloOnay(BuildContext context, RuloTipi istenen) async {
  final q = ortakKuyruk();
  if (q == null) return true;
  final info = await PrinterServices.instance.findPrinter(q);
  final hazir = info?.cikisYapabilir ?? false;

  if (hazir && bildirileneGore(AppConfig.printer) == _durumOf(istenen)) {
    return true;
  }
  if (!context.mounted) return false;

  if (!hazir) {
    final dene = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Yazıcı kullanılamıyor'),
        content: Text(
            'Yazıcı "$q" kapalı, devre dışı veya bulunamadı. '
            'Basım başarısız olacaktır.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Vazgeç'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Yine de dene'),
          ),
        ],
      ),
    );
    return dene ?? false;
  }

  final tamam = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: Text('Yazıcıdaki rulo: ${ruloTipiEtiketi(istenen)}?'),
      content: Text(
        'Fiş ve etiket aynı yazıcıyı kullanıyor ($q). '
        'Şu an ${ruloTipiEtiketi(istenen)} basılacak. '
        'Yazıcıda ${ruloTipiEtiketi(istenen).toLowerCase()} rulosu varsa '
        'devam etmek için onaylayın.',
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(ctx).pop(false),
          child: const Text('Vazgeç'),
        ),
        FilledButton(
          onPressed: () => Navigator.of(ctx).pop(true),
          child: Text('${ruloTipiEtiketi(istenen)} rulosu taktım → yazdır'),
        ),
      ],
    ),
  );
  if (tamam != true) return false;
  if (!context.mounted) return false;
  await ruloBildir(context, istenen);
  return true;
}

RuloDurum _durumOf(RuloTipi tip) =>
    tip == RuloTipi.fis ? RuloDurum.fis : RuloDurum.etiket;

/// Rulo durumunu bildirir (K14.9): durumu kaydeder; etiketse gerekiyorsa
/// ölçü kurulumunu sorar. Kağıt tipi/besleme ayarı zorlanmaz (K14.11).
Future<void> ruloBildir(
  BuildContext context,
  RuloTipi tip, {
  bool kalibrasyonGoster = false,
}) async {
  var prefs = AppConfig.printer;
  if (tip == RuloTipi.etiket && !prefs.etiketKurulumYapildi) {
    final kurulum = await _etiketKurulumDialog(context, prefs);
    if (kurulum == null) return;
    prefs = kurulum.copyWith(rulo: 'etiket', etiketKurulumYapildi: true);
  } else {
    prefs = prefs.copyWith(rulo: tip.name);
  }
  AppConfig.printer = prefs;
  if (!context.mounted) return;
  showAppSnack(context, '${ruloTipiEtiketi(tip)} rulosu bildirildi.');
  // Etiket takıldığında yazıcının gap sensörü kalibrasyonu gerekir: uygulama
  // boşluğu göndermez (K14.11), ölçüm cihazın kendi sensöründedir. Bildirim
  // ayarlardan yapıldığında adımlar gösterilir; basım öncesi onay akışında
  // (otomatik çağrı) modal açılmaz.
  if (tip == RuloTipi.etiket && kalibrasyonGoster) {
    await etiketKalibrasyonBilgisi(context);
  }
}

/// "Etiket rulosu taktım" sonrası kalibrasyon yönergesi (K14.11).
///
/// Etiket takıldığında yazıcının kendi `SIZE`/`GAP` değerlerini ölçmesi gerekir;
/// bu değerler cihaz belleğinde kalır ve güç döngüsü silmez. Fiş (sonsuz rulo)
/// taktığında kalibrasyon gerekmez: uygulama `PaperType=Continue` gönderir.
Future<void> etiketKalibrasyonBilgisi(BuildContext context) async {
  final q = ortakKuyruk() ??
      (AppConfig.printer.etiketYazici.trim().isNotEmpty
          ? AppConfig.printer.etiketYazici.trim()
          : '');
  final model = q.isEmpty
      ? ''
      : await PrinterServices.instance.makeAndModel(q);
  if (!context.mounted) return;
  await showDialog<void>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: const Text('Etiket rulosunu kalibre et'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Uygulama etiket boşluğunu (gap) yazıcıya göndermez; yazıcı gerçek '
              'etiket uzunluğunu ve aralığı kendi sensörüyle ölçer. Etiket '
              'değiştirdiyseniz ya da basım bir etiketin ortasından başlıp '
              'diğerinin ortasında bitiyorsa kalibrasyon gerekir.',
            ),
            const SizedBox(height: 12),
            if (termalEtiketYazici(model)) ...[
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Theme.of(ctx).colorScheme.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: const [
                    Text('Bu yazıcı için adımlar '
                        '(panel tuşu = FEED/İLERİ):',
                        style: TextStyle(fontWeight: FontWeight.w600)),
                    SizedBox(height: 8),
                    Text('1. Etiket rulosu takılı olsun, yazıcı kapalı.'),
                    Text.rich(TextSpan(children: [
                      TextSpan(text: '2. Tuşu basılı tutup gücü açın; LED '),
                      TextSpan(
                          text: 'mavi',
                          style: TextStyle(fontWeight: FontWeight.bold)),
                      TextSpan(
                          text: ' yanıp sönerken tuşu bırakın (fabrika ayarı).'),
                    ])),
                    Text.rich(TextSpan(children: [
                      TextSpan(
                          text: '3. Aynı şekilde tekrar yapın; LED '),
                      TextSpan(
                          text: 'kırmızı',
                          style: TextStyle(fontWeight: FontWeight.bold)),
                      TextSpan(
                          text:
                              ' yanıp sönerken tuşu bırakın (gap/black-mark '
                              'sensörü kalibrasyonu — etiket boyu ve boşluğu '
                              'ölçer).'),
                    ])),
                    Text('4. Ayarlar › Yazıcılar › «Test etiketi» ile '
                        'deneyin.'),
                  ],
                ),
              ),
              const SizedBox(height: 12),
            ] else
              const Text(
                'Genel adım: cihaz açılırken panel tuşu basılı tutularak '
                '"gap/black mark (boşluk) sensörü kalibrasyonu" yapılır; '
                'yazıcı yanıp söndükçe uygun anda tuşu bırakın. Ayrıntılı '
                'adımlar yazıcınızın kendi kılavuzundadır.',
              ),
            const SizedBox(height: 8),
            Text(
              'Not: Etiket kalibrasyonundan sonra fiş (sonsuz rulo) '
              'basacaksanız kalibrasyonu tekrarlayın; cihaz etiket ölçüsüne '
              'kilitlenir. Fişe dönüşte kalibrasyon gerekmez.',
              style: Theme.of(ctx).textTheme.bodySmall,
            ),
          ],
        ),
      ),
      actions: [
        FilledButton(
          onPressed: () => Navigator.of(ctx).pop(),
          child: const Text('Anladım'),
        ),
      ],
    ),
  );
}

/// Gap/black-mark sensörü olan termal etiket yazıcısı mı?
/// (LED renkleriyle adım tarif edilen 4B serisi vb.)
bool termalEtiketYazici(String model) {
  final m = model.toLowerCase();
  if (m.isEmpty) return false;
  const isaretler = [
    '4b-', '4b20', '2074', 'tazga', 'dxp-', 'hprt', 'xprinter', 'gprinter',
    'zebra', 'zq-', 'rongta', 'pos58', 'pos80', 'tspl',
  ];
  return isaretler.any(m.contains);
}

/// İlk etiket rulosu bildiriminde ölçü kurulumu (K14.11).
/// Vazgeçilirse `null`.
Future<PrinterPrefs?> _etiketKurulumDialog(
    BuildContext context, PrinterPrefs prefs) async {
  final genislik = TextEditingController(
      text: prefs.etiketGenislikMm.toStringAsFixed(0));
  final yukseklik = TextEditingController(
      text: prefs.etiketYukseklikMm.toStringAsFixed(0));
  final formKey = GlobalKey<FormState>();

  double? degerOku(TextEditingController c) => double.tryParse(c.text.trim());

  final result = await showDialog<PrinterPrefs>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: const Text('Etiket rulosu kurulumu'),
      content: SingleChildScrollView(
        child: Form(
          key: formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                  'Etiket rulosunun ölçülerini girin. Boşluk/kağıt tipi '
                  '(gap, mark) buradan ayarlanmaz: yazıcı beslemeyi kendi '
                  'sensör kalibrasyonuyla ölçer. Daha sonra Ayarlar › '
                  'Yazıcılar › Termal rulo bölümünden değiştirilebilir.'),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: genislik,
                      decoration: const InputDecoration(
                        labelText: 'Etiket genişliği (mm)',
                        isDense: true,
                        border: OutlineInputBorder(),
                      ),
                      keyboardType: TextInputType.number,
                      validator: (v) {
                        final d = double.tryParse(v ?? '');
                        return (d == null || d <= 0 || d > 120)
                            ? 'Geçersiz genişlik'
                            : null;
                      },
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextFormField(
                      controller: yukseklik,
                      decoration: const InputDecoration(
                        labelText: 'Etiket yüksekliği (mm)',
                        isDense: true,
                        border: OutlineInputBorder(),
                      ),
                      keyboardType: TextInputType.number,
                      validator: (v) {
                        final d = double.tryParse(v ?? '');
                        return (d == null || d <= 0 || d > 250)
                            ? 'Geçersiz yükseklik'
                            : null;
                      },
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(ctx).pop(),
          child: const Text('Vazgeç'),
        ),
        FilledButton(
          onPressed: () {
            if (!(formKey.currentState?.validate() ?? false)) return;
            Navigator.of(ctx).pop(prefs.copyWith(
              etiketGenislikMm: degerOku(genislik) ?? prefs.etiketGenislikMm,
              etiketYukseklikMm: degerOku(yukseklik) ?? prefs.etiketYukseklikMm,
              etiketKurulumYapildi: true,
            ));
          },
          child: const Text('Kaydet ve bildir'),
        ),
      ],
    ),
  );
  return result;
}