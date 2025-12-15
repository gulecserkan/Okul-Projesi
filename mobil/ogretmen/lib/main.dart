import 'package:flutter/material.dart';

import 'api/library_api.dart';
import 'models/auth.dart';
import 'screens/book_list_screen.dart';
import 'screens/connection_screen.dart';
import 'screens/login_screen.dart';
import 'storage/session_storage.dart';
import 'theme/app_theme.dart';

void main() {
  runApp(const OgretmenApp());
}

class OgretmenApp extends StatefulWidget {
  const OgretmenApp({super.key});

  @override
  State<OgretmenApp> createState() => _OgretmenAppState();
}

class _OgretmenAppState extends State<OgretmenApp> {
  final SessionStorage _storage = SessionStorage();
  bool _loading = true;
  String? _baseUrl;
  String? _rememberedBaseUrl;
  AuthTokens? _tokens;
  String? _handshakeError;
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
    });
  }

  Future<void> _logout() async {
    await _storage.clearTokens();
    await _storage.saveLastAuthAt(DateTime.now());
    setState(() {
      _tokens = null;
    });
  }

  Future<void> _resetServer() async {
    await _storage.clearTokens();
    // Sunucu adresini silme; el sıkışma ekranına son adresle dönelim.
    setState(() {
      _baseUrl = null;
      _tokens = null;
      _handshakeError = null;
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
      title: "Öğretmen Kütüphane",
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
      );
    }

    return BookListScreen(
      baseUrl: _baseUrl!,
      tokens: _tokens!,
      onLogout: _logout,
      onChangeServer: _resetServer,
      currentTheme: _currentTheme,
      onThemeChange: _changeTheme,
    );
  }
}
