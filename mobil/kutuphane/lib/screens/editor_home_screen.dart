import 'package:flutter/material.dart';

import '../api/library_api.dart';
import '../models/auth.dart';
import '../theme/app_theme.dart';
import 'book_list_screen.dart';
import 'uye_home_screen.dart';

/// K9.12: Editör ekranı iki bölümlüdür (alt gezinme çubuğu):
///  1) "Editör" — kitap düzenleme (mevcut [BookListScreen])
///  2) "Üye"    — normal üyeye görünen üç sekmenin birebir aynısı
///                ([UyeHomeScreen]: Kitaplar / Ödünçlerim / Ceza)
///
/// Bölümler [IndexedStack] ile korunur; geçişte her bölümün durumu (kaydırma,
/// arama, yüklenen sayfalar) muhafaza edilir.
class EditorHomeScreen extends StatefulWidget {
  const EditorHomeScreen({
    super.key,
    required this.baseUrl,
    required this.tokens,
    required this.onLogout,
    required this.currentTheme,
    required this.onThemeChange,
    this.onSessionExpired,
    this.api,
  });

  final String baseUrl;
  final AuthTokens tokens;
  final Future<void> Function() onLogout;
  final AppTheme currentTheme;
  final Future<void> Function(AppTheme) onThemeChange;
  final void Function()? onSessionExpired;

  /// Test/DI için dışarıdan verilebilir; iki bölüme de geçirilir.
  final LibraryApiClient? api;

  @override
  State<EditorHomeScreen> createState() => _EditorHomeScreenState();
}

class _EditorHomeScreenState extends State<EditorHomeScreen> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _index,
        children: [
          BookListScreen(
            baseUrl: widget.baseUrl,
            tokens: widget.tokens,
            onLogout: widget.onLogout,
            currentTheme: widget.currentTheme,
            onThemeChange: widget.onThemeChange,
            onSessionExpired: widget.onSessionExpired,
            api: widget.api,
          ),
          UyeHomeScreen(
            baseUrl: widget.baseUrl,
            tokens: widget.tokens,
            onLogout: widget.onLogout,
            onSessionExpired: widget.onSessionExpired,
            api: widget.api,
          ),
        ],
      ),
      bottomNavigationBar: _buildBottomBar(context),
    );
  }

  /// İnce alt çubuk: yalnızca iki bölüm geçişi, ikon + metin YAN YANA.
  Widget _buildBottomBar(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return SafeArea(
      top: false,
      child: Container(
        height: 46,
        decoration: BoxDecoration(
          color: scheme.surface,
          border: Border(top: BorderSide(color: scheme.outlineVariant, width: 0.6)),
        ),
        child: Row(
          children: [
            _bolumButonu(context, 0, Icons.edit_note_outlined, Icons.edit_note, 'Editör'),
            _bolumButonu(context, 1, Icons.person_outline, Icons.person, 'Üye'),
          ],
        ),
      ),
    );
  }

  Widget _bolumButonu(
    BuildContext context,
    int index,
    IconData ikon,
    IconData seciliIkon,
    String etiket,
  ) {
    final scheme = Theme.of(context).colorScheme;
    final secili = _index == index;
    return Expanded(
      child: InkWell(
        onTap: () => setState(() => _index = index),
        child: Container(
          alignment: Alignment.center,
          decoration: secili
              ? BoxDecoration(
                  border: Border(
                    top: BorderSide(color: scheme.primary, width: 2.5),
                  ),
                )
              : null,
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                secili ? seciliIkon : ikon,
                size: 18,
                color: secili ? scheme.primary : scheme.onSurfaceVariant,
              ),
              const SizedBox(width: 6),
              Text(
                etiket,
                style: TextStyle(
                  fontSize: 13.5,
                  fontWeight: secili ? FontWeight.w700 : FontWeight.w500,
                  color: secili ? scheme.primary : scheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
