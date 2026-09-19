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

/// Türkçe-duyarlı agresif normalizasyon (K6.1): büyük/küçük harf, `ı/i`,
/// aksan ve noktalama farkları giderilir. Kopya/benzerlik karşılaştırması için.
String normalizeTr(String? s) {
  if (s == null || s.isEmpty) return '';
  const map = {
    'İ': 'i', 'I': 'i', 'ı': 'i',
    'Ş': 's', 'ş': 's', 'Ğ': 'g', 'ğ': 'g',
    'Ü': 'u', 'ü': 'u', 'Ö': 'o', 'ö': 'o',
    'Ç': 'c', 'ç': 'c', 'Â': 'a', 'â': 'a',
    'Î': 'i', 'î': 'i', 'Û': 'u', 'û': 'u',
  };
  final buf = StringBuffer();
  for (final ch in s.split('')) {
    buf.write(map[ch] ?? ch.toLowerCase());
  }
  return buf
      .toString()
      .replaceAll(RegExp(r'[^a-z0-9]+'), ' ')
      .trim()
      .replaceAll(RegExp(r'\s+'), ' ');
}

/// İki metin arasındaki benzerlik (0..1): normalize Levenshtein oranı (K6.1).
double similarityTr(String? a, String? b) {
  final x = normalizeTr(a);
  final y = normalizeTr(b);
  if (x.isEmpty && y.isEmpty) return 1;
  if (x.isEmpty || y.isEmpty) return 0;
  final maxLen = x.length > y.length ? x.length : y.length;
  return 1 - _levenshtein(x, y) / maxLen;
}

int _levenshtein(String a, String b) {
  final m = a.length, n = b.length;
  if (m == 0) return n;
  if (n == 0) return m;
  var prev = List<int>.generate(n + 1, (i) => i);
  var curr = List<int>.filled(n + 1, 0);
  for (var i = 1; i <= m; i++) {
    curr[0] = i;
    for (var j = 1; j <= n; j++) {
      final cost = a.codeUnitAt(i - 1) == b.codeUnitAt(j - 1) ? 0 : 1;
      final del = prev[j] + 1;
      final ins = curr[j - 1] + 1;
      final sub = prev[j - 1] + cost;
      curr[j] = del < ins ? (del < sub ? del : sub) : (ins < sub ? ins : sub);
    }
    final tmp = prev;
    prev = curr;
    curr = tmp;
  }
  return prev[n];
}