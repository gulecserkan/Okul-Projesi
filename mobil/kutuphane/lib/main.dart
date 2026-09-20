import 'package:flutter/material.dart';

import 'api/library_api.dart';
import 'models/auth.dart';
import 'screens/book_list_screen.dart';
import 'screens/uye_home_screen.dart';
import 'screens/connection_screen.dart';
import 'screens/force_password_screen.dart';
import 'screens/login_screen.dart';
import 'storage/session_storage.dart';
import 'theme/app_theme.dart';

void main() {
  runApp(const KutuphaneApp());
}

class KutuphaneApp extends StatefulWidget {
  const KutuphaneApp({super.key});

  @override
  State<KutuphaneApp> createState() => _KutuphaneAppState();
}

class _KutuphaneAppState extends State<KutuphaneApp> {
  final SessionStorage _storage = SessionStorage();
  bool _loading = true;
  String? _baseUrl;
  String? _rememberedBaseUrl;
  AuthTokens? _tokens;
  String? _handshakeError;
  String? _sessionNotice;
  final Duration _maxAuthAge = const Duration(minutes: 15);
  AppTheme _currentTheme = AppTheme.defaultLight;

  @override
  void initState() {
    super.initState();
    _bootstrap();
  }

  Future<void> _bootstrap() async {
    final storedBaseUrl = await _storage.loadBaseUrl();
    final storedTokens = await _storage.loadTokens();
    final lastAuth = await _storage.loadLastAuthAt();
    _rememberedBaseUrl = storedBaseUrl;
    final storedTheme = await _storage.loadTheme();
    if (storedTheme != null) {
      final parsed = AppTheme.values.firstWhere(
        (t) => t.name == storedTheme,
        orElse: () => AppTheme.defaultLight,
      );
      _currentTheme = parsed;
    }

    if (storedBaseUrl == null) {
      setState(() => _loading = false);
      return;
    }

    final handshake = await LibraryApiClient(
      baseUrl: storedBaseUrl,
    ).handshake();
    if (!handshake.ok) {
      setState(() {
        _loading = false;
        _handshakeError = handshake.message;
        _baseUrl = null;
        _tokens = null;
      });
      return;
    }

    AuthTokens? refreshedTokens = storedTokens;
    if (storedTokens != null) {
      final now = DateTime.now();
      final tooOld = lastAuth == null
          ? true
          : now.difference(lastAuth) > _maxAuthAge;
      if (tooOld) {
        await _storage.clearTokens();
        refreshedTokens = null;
      } else {
        try {
          final api = LibraryApiClient(
            baseUrl: storedBaseUrl,
            tokens: storedTokens,
          );
          refreshedTokens = await api.refreshToken(storedTokens.refreshToken);
          await _storage.saveTokens(refreshedTokens);
          await _storage.saveLastAuthAt(now);
        } catch (_) {
          await _storage.clearTokens();
          refreshedTokens = null;
        }
      }
    }

    setState(() {
      _baseUrl = storedBaseUrl;
      _tokens = refreshedTokens;
      _loading = false;
      _handshakeError = null;
    });
  }

  Future<void> _onServerConnected(String baseUrl) async {
    await _storage.saveBaseUrl(baseUrl);
    setState(() {
      _baseUrl = baseUrl;
      _rememberedBaseUrl = baseUrl;
      _tokens = null;
    });
  }

  Future<void> _onLogin(AuthTokens tokens) async {
    await _storage.saveTokens(tokens);
    await _storage.saveLastAuthAt(DateTime.now());
    setState(() {
      _tokens = tokens;
      _sessionNotice = null;
    });
  }

  /// K9: ilk giriş şifresi değiştirildi → zorunluluk bayrağını kaldır.
  Future<void> _onPasswordChanged() async {
    final updated = _tokens?.copyWith(parolaDegistirilsin: false);
    if (updated != null) {
      await _storage.saveTokens(updated);
    }
    setState(() {
      _tokens = updated;
    });
  }

  Future<void> _logout() async {
    await _storage.clearTokens();
    await _storage.saveLastAuthAt(DateTime.now());
    setState(() {
      _tokens = null;
      _sessionNotice = null;
    });
  }

  /// Yetkili bir istek 401 döndüğünde: oturumu kapat ve kullanıcıyı bilgilendir.
  Future<void> _onSessionExpired() async {
    if (_tokens == null) return;
    await _storage.clearTokens();
    await _storage.saveLastAuthAt(DateTime.now());
    if (!mounted) return;
    setState(() {
      _tokens = null;
      _sessionNotice = 'Oturum süresi doldu, lütfen tekrar giriş yapın.';
    });
  }

  Future<void> _resetServer() async {
    await _storage.clearTokens();
    // Sunucu adresini silme; el sıkışma ekranına son adresle dönelim.
    setState(() {
      _baseUrl = null;
      _tokens = null;
      _handshakeError = null;
      _sessionNotice = null;
    });
  }

  ThemeData _buildTheme() {
    return appThemes[_currentTheme]!.themeData;
  }

  Future<void> _changeTheme(AppTheme theme) async {
    await _storage.saveTheme(theme.name);
    setState(() {
      _currentTheme = theme;
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: "Kütüphane",
      theme: _buildTheme(),
      home: _buildHome(),
    );
  }

  Widget _buildHome() {
    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    if (_baseUrl == null) {
      return ConnectionScreen(
        initialError: _handshakeError,
        lastKnownBaseUrl: _rememberedBaseUrl,
        onConnected: _onServerConnected,
      );
    }

    if (_tokens == null) {
      return LoginScreen(
        baseUrl: _baseUrl!,
        onAuthenticated: _onLogin,
        onChangeServer: _resetServer,
        lastKnownBaseUrl: _rememberedBaseUrl,
        initialMessage: _sessionNotice,
      );
    }

    if (_tokens!.parolaDegistirilsin) {
      return ForcePasswordScreen(
        baseUrl: _baseUrl!,
        tokens: _tokens!,
        onDone: _onPasswordChanged,
        onSessionExpired: _onSessionExpired,
      );
    }

    // Editör hem düzenler hem ödünç alır → yönetim ekranı (BookListScreen).
    if (_tokens!.isUye && !_tokens!.isEditor) {
      return UyeHomeScreen(
        baseUrl: _baseUrl!,
        tokens: _tokens!,
        onLogout: _logout,
        onChangeServer: _resetServer,
        onSessionExpired: _onSessionExpired,
      );
    }

    return BookListScreen(
      baseUrl: _baseUrl!,
      tokens: _tokens!,
      onLogout: _logout,
      onChangeServer: _resetServer,
      onSessionExpired: _onSessionExpired,
      currentTheme: _currentTheme,
      onThemeChange: _changeTheme,
    );
  }
}
