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
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.edit_note_outlined),
            selectedIcon: Icon(Icons.edit_note),
            label: 'Editör',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person),
            label: 'Üye',
          ),
        ],
      ),
    );
  }
}
