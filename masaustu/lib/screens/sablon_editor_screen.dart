import 'package:flutter/material.dart';

import '../config.dart';
import '../printing/label_pdf.dart';
import '../printing/print_helpers.dart';
import '../printing/printer_service.dart';
import '../printing/receipt_pdf.dart';
import '../printing/sablon.dart';
import '../theme.dart';

/// Fiş/etiket içerik editörü (K14.12).
///
/// - Sahne seçilir (ödünç, iade, şifre, borcu yoktur, ceza, etiket).
/// - Alanlar açılır/kapanır; zorunlu alanlar kilitlidir, sıra değiştirilebilir.
/// - Önizleme **yapısaldır**: basımdaki satır listesinin aynısından üretilir,
///   doğruluk için "Test bas" kullanılır.
class SablonEditorScreen extends StatefulWidget {
  const SablonEditorScreen({super.key});

  @override
  State<SablonEditorScreen> createState() => _SablonEditorScreenState();
}

class _SablonEditorScreenState extends State<SablonEditorScreen> {
  BasimSablonu _sablon = AppConfig.sablon;
  Sahne _sahne = Sahne.odunc;
  KurumBilgisi _kurum = const KurumBilgisi();
  bool _basiliyor = false;

  @override
  void initState() {
    super.initState();
    _kurumGetir();
  }

  Future<void> _kurumGetir() async {
    final kurum = await kurumGetir();
    if (!mounted) return;
    setState(() => _kurum = kurum);
  }

  void _kaydet(BasimSablonu s) {
    setState(() => _sablon = s);
    AppConfig.sablon = s;
  }

  /// Sahne için geçerli alan listesi (kullanıcı sırası + varsayılanlar).
  List<Alan> _alanlar(BasimSablonu sablon) => [
        for (final d in Sablon.durum(_sahne.kod, sablon))
          Sablon.alan(_sahne.kod, d.kod)!,
      ];

  bool _acikMi(BasimSablonu sablon, String kod) =>
      Sablon.durum(_sahne.kod, sablon).any((d) => d.kod == kod && d.acik);

  void _alanDegistir(BasimSablonu sablon, String kod, bool acik) {
    final alan = Sablon.alan(_sahne.kod, kod);
    if (alan == null || alan.zorunlu) return; // zorunlu alan kapanmaz
    final mevcut = Sablon.durum(_sahne.kod, sablon);
    final yeni = <SahneAlanDurumu>[];
    var eklendi = false;
    for (final d in mevcut) {
      if (d.kod == kod) {
        yeni.add(SahneAlanDurumu(kod, acik: acik));
        eklendi = true;
      } else {
        yeni.add(d);
      }
    }
    if (!eklendi) yeni.add(SahneAlanDurumu(kod, acik: acik));
    _kaydet(sablon.copyWith(alanlar: {...sablon.alanlar, _sahne.kod: yeni}));
  }

  /// Alan sırası değişir (`hedef` kaldırıldıktan sonraki konumdur).
  void _siraDegistir(BasimSablonu sablon, int eski, int hedef) {
    final liste = List<SahneAlanDurumu>.of(
        Sablon.durum(_sahne.kod, sablon));
    if (eski < 0 || eski >= liste.length) return;
    final oge = liste.removeAt(eski);
    liste.insert(hedef.clamp(0, liste.length), oge);
    _kaydet(sablon.copyWith(alanlar: {...sablon.alanlar, _sahne.kod: liste}));
  }

  void _varsayilanlaraDon() {
    final alanlar = {..._sablon.alanlar}..remove(_sahne.kod);
    _kaydet(_sablon.copyWith(alanlar: alanlar));
  }

  double get _kenar =>
      _sahne == Sahne.etiket ? _sablon.etiketKenarMm : _sablon.fisKenarMm;

  void _kenarDegistir(double v) {
    final y = v.clamp(BasimSablonu.kenarMinMm, BasimSablonu.kenarMaxMm);
    _kaydet(_sahne == Sahne.etiket
        ? _sablon.copyWith(etiketKenarMm: y)
        : _sablon.copyWith(fisKenarMm: y));
  }

  // ------------------------------------------------------- örnek içerik

  /// Örnek fiş satırları — üretimdeki kurucularla birebir aynı yol.
  List<ReceiptLine> _ornekFis(BasimSablonu sablon) {
    final k = _kurum.baslik.trim().isEmpty
        ? KurumBilgisi(kutuphaneAdi: 'Okul Kütüphanesi')
        : _kurum;
    final lines = switch (_sahne) {
      Sahne.odunc => ReceiptPdf.oduncFisi(
          kurum: k,
          operator: operatorAdi(),
          tarih: '27.09.2026 22:31',
          ogrenci: 'Ali Yılmaz',
          sinif: '10-A',
          kitap: 'Sefere Seven Yedi Kule',
          yazar: 'Tolga Özçelik',
          barkod: 'B-2026-000123',
          oduncTarihi: '27.09.2026',
          iadeTarihi: '11.10.2026',
        ),
      Sahne.iade => ReceiptPdf.iadeFisi(
          kurum: k,
          operator: operatorAdi(),
          tarih: '27.09.2026 22:40',
          ogrenci: 'Ali Yılmaz',
          sinif: '10-A',
          kitap: 'Sefere Seven Yedi Kule',
          yazar: 'Tolga Özçelik',
          barkod: 'B-2026-000123',
          durumEtiketi: 'Zamanında',
          cezaTutari: '',
          odemeNotu: '',
        ),
      Sahne.sifre => ReceiptPdf.sifreFisi(
          kurum: k,
          operator: operatorAdi(),
          tarih: '27.09.2026 22:45',
          ogrenci: 'Ali Yılmaz',
          kullaniciAdi: '2026-0145',
          sifre: 'A7k92p',
        ),
      Sahne.borcuYoktur => ReceiptPdf.borcuYoktur(
          kurum: k,
          operator: operatorAdi(),
          tarih: '27.09.2026 22:50',
          ogrenci: 'Ali Yılmaz',
          sinif: '10-A',
          aktifOdunc: '3',
        ),
      Sahne.ceza => ReceiptPdf.cezaOdemeFisi(
          kurum: k,
          operator: operatorAdi(),
          tarih: '27.09.2026 22:55',
          ogrenci: 'Ali Yılmaz',
          sinif: '10-A',
          tutar: '25,00',
        ),
      Sahne.etiket => const <ReceiptLine>[],
    };
    return ReceiptPdf.sablonla(lines, _sahne.kod, sablon);
  }

  List<LabelElement> _ornekEtiket(BasimSablonu sablon) {
    return LabelPdf.sablonla(
        LabelPdf.etiketElemanlari(
          kurum: _kurum.baslik.trim().isEmpty
              ? KurumBilgisi(kutuphaneAdi: 'Okul Kütüphanesi')
              : _kurum,
          baslik: 'Sefere Seven Yedi Kule',
          yazar: 'Tolga Özçelik',
          kategori: 'Genel',
          barkodMetni: 'B-2026-000123',
        ),
        sablon);
  }

  Future<void> _testBas() async {
    setState(() => _basiliyor = true);
    final PrintResult sonuc;
    if (_sahne == Sahne.etiket) {
      sonuc = await EtiketYazdir.yazdir(
        _kurum.baslik.trim().isEmpty
            ? KurumBilgisi(kutuphaneAdi: 'Okul Kütüphanesi')
            : _kurum,
        'Sefere Seven Yedi Kule',
        'Tolga Özçelik',
        'Genel',
        'B-2026-000123',
      );
    } else {
      sonuc = await FisYazdir.yazdir(_ornekFis(AppConfig.sablon),
          sahne: _sahne.kod, title: 'sablon-testi');
    }
    if (!mounted) return;
    setState(() => _basiliyor = false);
    showAppSnack(context, sonuc.message, error: !sonuc.ok);
  }

  // ------------------------------------------------------------- arayüz

  @override
  Widget build(BuildContext context) {
    final alanlar = _alanlar(_sablon);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
          child: Wrap(
            spacing: 8,
            runSpacing: 4,
            children: [
              for (final s in Sahne.values)
                ChoiceChip(
                  label: Text(s.ad),
                  selected: _sahne == s,
                  onSelected: (_) => setState(() => _sahne = s),
                ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  '${_sahne.ad} — açık satırlar',
                  style: Theme.of(context).textTheme.titleSmall,
                ),
              ),
              TextButton.icon(
                onPressed: _varsayilanlaraDon,
                icon: const Icon(Icons.restart_alt, size: 18),
                label: const Text('Varsayılan'),
              ),
              FilledButton.icon(
                onPressed: _basiliyor ? null : _testBas,
                icon: _basiliyor
                    ? const SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.print_outlined, size: 18),
                label: const Text('Test bas'),
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Row(
            children: [
              const Text('Kenar boşluğu'),
              Expanded(
                child: Slider(
                  value: _kenar,
                  min: BasimSablonu.kenarMinMm,
                  max: BasimSablonu.kenarMaxMm,
                  divisions: 16,
                  label: '${_kenar.toStringAsFixed(1)} mm',
                  onChanged: _kenarDegistir,
                ),
              ),
              SizedBox(
                  width: 58,
                  child: Text('${_kenar.toStringAsFixed(1)} mm',
                      style: Theme.of(context).textTheme.bodySmall)),
            ],
          ),
        ),
        const Padding(
          padding: EdgeInsets.symmetric(horizontal: 16, vertical: 4),
          child: Text(
            'Önizleme yapısal: satır sırası ve içerik basımdakiyle aynıdır; '
            'satır kaydırma ve kenar boşluğu yalnız "Test bas" ile doğrulanır. '
            'Kilitli alanlar zorunludur ve kapatılamaz.',
            style: TextStyle(fontSize: 12),
          ),
        ),
        const Divider(height: 1),
        Expanded(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                flex: 3,
                child: ReorderableListView.builder(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  itemCount: alanlar.length,
                  onReorderItem: (e, y) => _siraDegistir(_sablon, e, y),
                  itemBuilder: (context, i) {
                    final a = alanlar[i];
                    final acik = _acikMi(_sablon, a.kod);
                    return SwitchListTile(
                      key: ValueKey(a.kod),
                      dense: true,
                      value: acik,
                      onChanged: a.zorunlu
                          ? null
                          : (v) => _alanDegistir(_sablon, a.kod, v),
                      title: Row(
                        children: [
                          if (a.zorunlu) ...[
                            Icon(Icons.lock_outline,
                                size: 14,
                                color: Theme.of(context).colorScheme.primary),
                            const SizedBox(width: 4),
                          ],
                          Flexible(
                              child: Text(a.etiket,
                                  overflow: TextOverflow.ellipsis)),
                        ],
                      ),
                      subtitle: Text(
                          acik ? a.ornek : 'kapalı — basılmaz',
                          style: TextStyle(
                              fontSize: 11,
                              color: acik
                                  ? null
                                  : Theme.of(context).disabledColor)),
                      secondary: ReorderableDragStartListener(
                        index: i,
                        child: const Icon(Icons.drag_handle, size: 18),
                      ),
                    );
                  },
                ),
              ),
              const VerticalDivider(width: 1),
              Expanded(
                flex: 2,
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: _onizleme(),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _onizleme() {
    final c = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: c.colorScheme.surfaceContainerHighest.withValues(alpha: .35),
        border: Border.all(color: c.dividerColor),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('Önizleme (${_sahne.ad})',
              style: c.textTheme.labelSmall
                  ?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 6),
          if (_sahne == Sahne.etiket)
            for (final e in _ornekEtiket(_sablon))
              if (e.tip == LabelTip.metin)
                _onizlemeSatiri(e.text, size: e.size, bold: e.bold)
              else if (e.tip == LabelTip.barkod)
                _onizlemeSatiri(e.onizlemeMetni, size: 9, mono: true)
          else
            for (final l in _ornekFis(_sablon))
              if (l.divider)
                const Divider(height: 6, thickness: 1)
              else
                _onizlemeSatiri(l.text, size: l.size, bold: l.bold),
        ],
      ),
    );
  }

  Widget _onizlemeSatiri(String text,
      {double size = 10, bool bold = false, bool mono = false}) {
    if (text.trim().isEmpty) return const SizedBox(height: 2);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 1),
      child: Text(
        text,
        style: TextStyle(
          fontSize: size.clamp(8, 13),
          fontWeight: bold ? FontWeight.bold : FontWeight.normal,
          fontFamily: mono ? 'monospace' : null,
        ),
      ),
    );
  }
}
