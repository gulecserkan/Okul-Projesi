import 'package:flutter/material.dart';

/// ISO tarih stringini kısa Türkçe formata çevirir: 2026-09-19 → 19.09.2026.
String formatDate(String? iso, {bool withTime = false}) {
  if (iso == null || iso.isEmpty) return '—';
  final dt = DateTime.tryParse(iso);
  if (dt == null) return iso;
  final d =
      '${dt.day.toString().padLeft(2, '0')}.${dt.month.toString().padLeft(2, '0')}.${dt.year}';
  if (!withTime) return d;
  final t = '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
  return '$d $t';
}

/// Durum kodu → Türkçe etiket.
String durumLabel(String durum) {
  switch (durum) {
    case 'mevcut':
      return 'Mevcut';
    case 'teslim':
      return 'Teslim Edildi';
    case 'oduncte':
      return 'Ödünçte';
    case 'gecikmis':
      return 'Gecikmiş';
    case 'kayip':
      return 'Kayıp';
    case 'hasarli':
      return 'Hasarlı';
    case 'iptal':
      return 'İptal';
    default:
      return durum.isEmpty ? '—' : durum;
  }
}

/// Durum kodu → renk (açık/koyu duyarlı: koyuda daha açık ton kullanılır).
Color durumColor(String durum, Brightness brightness) {
  final dark = brightness == Brightness.dark;
  switch (durum) {
    case 'mevcut':
    case 'teslim':
      return dark ? const Color(0xFF7BD88F) : Colors.green.shade700;
    case 'oduncte':
      return dark ? const Color(0xFFE8C05A) : Colors.amber.shade800;
    case 'gecikmis':
      return dark ? const Color(0xFFF2B8B5) : Colors.red.shade700;
    case 'kayip':
      return dark ? const Color(0xFFD2A77E) : Colors.brown.shade700;
    case 'hasarli':
      return dark ? const Color(0xFFF2B98C) : Colors.orange.shade800;
    case 'iptal':
      return dark ? const Color(0xFFC5C6CE) : Colors.grey.shade600;
    default:
      return dark ? const Color(0xFFC5C6CE) : Colors.grey.shade600;
  }
}