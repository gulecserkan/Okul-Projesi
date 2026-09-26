import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models/mobil_surum.dart';

/// APK indirme adresini mutlak bir URI'ye çevirir.
/// Sunucu göreli yol (`/mobil/...`) dönerse taban adresle birleştirilir.
Uri guncellemeUri(String baseUrl, String apkUrl) {
  final parsed = Uri.parse(apkUrl);
  if (parsed.hasScheme) return parsed;
  final base = baseUrl.endsWith('/')
      ? baseUrl.substring(0, baseUrl.length - 1)
      : baseUrl;
  final path = apkUrl.startsWith('/') ? apkUrl : '/$apkUrl';
  return Uri.parse('$base$path');
}

/// APK indirmesini tarayıcıda/dış uygulamada açar.
Future<void> guncellemeyiAc(String baseUrl, String apkUrl) async {
  final uri = guncellemeUri(baseUrl, apkUrl);
  await launchUrl(uri, mode: LaunchMode.externalApplication);
}

/// Sürüm güncelleme diyaloğunu gösterir.
/// [zorunlu] true ise kapatılamaz (yalnızca "Güncelle").
Future<void> guncellemeDiyaloguGoster(
  BuildContext context, {
  required MobilSurum surum,
  required bool zorunlu,
  required String kuruluSurum,
  required String baseUrl,
}) {
  return showDialog<void>(
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
            Text('Kurulu sürüm: $kuruluSurum'),
            const SizedBox(height: 4),
            Text('Yeni sürüm: ${surum.surum}'),
            const SizedBox(height: 12),
            Text(
              zorunlu
                  ? 'Devam edebilmek için lütfen uygulamayı güncelleyin.'
                  : 'Dilerseniz şimdi güncelleyebilirsiniz.',
            ),
          ],
        ),
        actions: [
          if (!zorunlu)
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Daha sonra'),
            ),
          FilledButton(
            onPressed: () => guncellemeyiAc(baseUrl, surum.apkUrl),
            child: const Text('Güncelle'),
          ),
        ],
      ),
    ),
  );
}
