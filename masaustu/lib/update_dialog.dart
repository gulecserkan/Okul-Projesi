import 'dart:io';

import 'package:flutter/material.dart';

import 'config.dart';
import 'update_service.dart';

/// Masaüstü güncelleme akışını başlatır.
Future<void> guncellemeGoster(
  BuildContext context,
  MasaustuSurum bilgi,
  bool zorunlu,
) async {
  final otomatik = otomatikGuncellemeDestekli();
  final adres = indirmeAdresi(AppConfig.apiBaseUrl, bilgi.url);

  await showDialog<void>(
    context: context,
    barrierDismissible: !zorunlu,
    builder: (ctx) => PopScope(
      canPop: !zorunlu,
      child: AlertDialog(
        title: Text(zorunlu ? 'Güncelleme gerekli' : 'Yeni sürüm mevcut'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Kurulu sürüm: ${AppConfig.appVersion}'),
            const SizedBox(height: 4),
            Text('Yeni sürüm: ${bilgi.surum}'),
            const SizedBox(height: 12),
            Text(
              otomatik
                  ? (zorunlu
                      ? 'Devam edebilmek için uygulama güncellenecek ve yeniden başlatılacak.'
                      : 'Uygulama güncellenecek ve yeniden başlatılacak.')
                  : 'Bu kurulumda otomatik güncelleme kapalı. Paketi indirip kurun:\n$adres',
            ),
          ],
        ),
        actions: [
          if (!zorunlu)
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Daha sonra'),
            ),
          if (otomatik)
            FilledButton(
              onPressed: () {
                Navigator.of(ctx).pop();
                _indirVeKur(context, bilgi);
              },
              child: const Text('Güncelle'),
            )
          else
            FilledButton(
              onPressed: () => _tarayiciAc(adres),
              child: const Text('İndir'),
            ),
        ],
      ),
    ),
  );
}

Future<void> _tarayiciAc(String adres) async {
  try {
    await Process.start('xdg-open', [adres],
        mode: ProcessStartMode.detached);
  } catch (_) {}
}

Future<void> _indirVeKur(BuildContext context, MasaustuSurum bilgi) async {
  final ilerlemeNotifier = ValueNotifier<double>(0);
  showDialog<void>(
    context: context,
    barrierDismissible: false,
    builder: (_) => PopScope(
      canPop: false,
      child: AlertDialog(
        title: const Text('Güncelleniyor'),
        content: ValueListenableBuilder<double>(
          valueListenable: ilerlemeNotifier,
          builder: (_, deger, _) => Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              LinearProgressIndicator(value: deger > 0 ? deger : null),
              const SizedBox(height: 12),
              Text(deger > 0
                  ? '%${(deger * 100).clamp(0, 100).toStringAsFixed(0)} indirildi'
                  : 'İndiriliyor...'),
            ],
          ),
        ),
      ),
    ),
  );

  try {
    await guncellemeyiIndirVeBaslat(bilgi, ilerleme: (d) {
      ilerlemeNotifier.value = d;
    });
    // Başarıda süreç exit(0) ile kapanır; buraya dönülmez.
  } catch (e) {
    if (context.mounted) Navigator.of(context).pop();
    if (context.mounted) {
      await showDialog<void>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Güncellenemedi'),
          content: Text('$e'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Tamam'),
            ),
          ],
        ),
      );
    }
  }
}
