import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:package_info_plus/package_info_plus.dart';

import 'api/library_api.dart';
import 'api/sunucu_adresi.dart';
import 'app_config.dart';
import 'models/auth.dart';
import 'models/mobil_surum.dart';
import 'screens/book_list_screen.dart';
import 'screens/uye_home_screen.dart';
import 'screens/editor_home_screen.dart';
import 'screens/connection_screen.dart';
import 'screens/force_password_screen.dart';
import 'screens/login_screen.dart';
import 'storage/session_storage.dart';
import 'theme/app_theme.dart';
import 'widgets/update_dialog.dart';

void main() {
  runApp(const KutuphaneApp());
}

class KutuphaneApp extends StatefulWidget {
  const KutuphaneApp({super.key, this.httpClient});

  /// Test/DI için dışarıdan verilebilir.
  final http.Client? httpClient;

  @override
  State<KutuphaneApp> createState() => _KutuphaneAppState();
}

class _KutuphaneAppState extends State<KutuphaneApp> with WidgetsBindingObserver {
  final SessionStorage _storage = SessionStorage();
  final GlobalKey<NavigatorState> _navigatorKey = GlobalKey<NavigatorState>();
  bool _loading = true;
  String? _baseUrl;
  String? _rememberedBaseUrl;
  AuthTokens? _tokens;
  String? _handshakeError;
  String? _sessionNotice;

  /// K9.11: "Beni hatırla" kapalıyken oturum 15 dk, açıkken 30 gün geçerli.
  final Duration _maxAuthAge = const Duration(minutes: 15);
  static const Duration _maxRememberedAge = Duration(days: 30);
  bool _rememberMe = false;
  AppTheme _currentTheme = AppTheme.defaultLight;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _bootstrap();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // K9.11: uygulama arka plana alınınca "son aktiflik" zamanını güncelle;
    // böylece kısa süre sonra geri dönen kullanıcı yeniden giriş yapmaz.
    if ((state == AppLifecycleState.paused ||
            state == AppLifecycleState.inactive) &&
        _tokens != null) {
      _storage.saveLastAuthAt(DateTime.now());
    }
  }

  Future<void> _bootstrap() async {
    final storedBaseUrl = await _storage.loadBaseUrl();
    final storedTokens = await _storage.loadTokens();
    final lastAuth = await _storage.loadLastAuthAt();
    _rememberedBaseUrl = storedBaseUrl;
    final storedRemember = await _storage.loadRememberMe();
    if (storedRemember != null) {
      _rememberMe = storedRemember;
    }
    final storedTheme = await _storage.loadTheme();
    if (storedTheme != null) {
      final parsed = AppTheme.values.firstWhere(
        (t) => t.name == storedTheme,
        orElse: () => AppTheme.defaultLight,
      );
      _currentTheme = parsed;
    }

    // Sunucu adresini çöz (K13.11): kayıtlı adres → doğrudan; yok/çöktü → adayları yokla.
    String? baseUrl = storedBaseUrl;
    var sunucuHazir = false;
    if (baseUrl != null) {
      sunucuHazir =
          (await LibraryApiClient(baseUrl: baseUrl, httpClient: widget.httpClient)
                  .handshake())
              .ok;
    }
    if (!sunucuHazir) {
      // Yalnız kayıtlı adres yoksa ya da bizim adaylarımızdan biriyse adayları yokla;
      // kullanıcının elle girdiği özel bir adrese dokunma.
      final adayMi = baseUrl == null ||
          AppConfig.effectiveServerCandidates.contains(baseUrl);
      if (adayMi) {
        final bulunan = await enIyiSunucuAdresiYokla();
        if (bulunan != null) {
          baseUrl = bulunan;
          sunucuHazir = true;
          await _storage.saveBaseUrl(bulunan);
          _rememberedBaseUrl = bulunan;
        }
      }
    }
    if (!sunucuHazir || baseUrl == null) {
      setState(() {
        _loading = false;
        _handshakeError =
            storedBaseUrl == null ? null : 'Sunucuya ulaşılamadı.';
        _baseUrl = null;
        _tokens = null;
      });
      return;
    }
    final cozulenAdres = baseUrl;

    AuthTokens? refreshedTokens = storedTokens;
    if (storedTokens != null) {
      final now = DateTime.now();
      // K9.11: "Beni hatırla" açıksa oturum uzun (30 gün), kapalıysa 12 saat.
      final ageLimit = _rememberMe ? _maxRememberedAge : _maxAuthAge;
      final tooOld = lastAuth == null
          ? true
          : now.difference(lastAuth) > ageLimit;
      if (tooOld) {
        await _storage.clearTokens();
        refreshedTokens = null;
      } else {
        try {
          final api = LibraryApiClient(
            baseUrl: cozulenAdres,
            tokens: storedTokens,
            httpClient: widget.httpClient,
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

    // K9: mobil uygulama üye hesaplarına açıktır; personel/admin hesabı varsa at.
    if (refreshedTokens != null && !refreshedTokens.isUye) {
      await _storage.clearTokens();
      refreshedTokens = null;
    }

    setState(() {
      _baseUrl = cozulenAdres;
      _tokens = refreshedTokens;
      _loading = false;
      _handshakeError = null;
    });

    // Sunucudaki sürümle karşılaştır; yeni sürüm varsa bildir (K13.4).
    await _guncellemeKontrolEt(cozulenAdres);
  }

  /// Kurulu sürümü sunucudaki sürümle karşılaştırır ve gerekirse diyalog açar.
  Future<void> _guncellemeKontrolEt(String baseUrl) async {
    final uzak = await LibraryApiClient(
      baseUrl: baseUrl,
      httpClient: widget.httpClient,
    ).mobilSurum();
    if (uzak == null || uzak.apkUrl.isEmpty) return;

    String kuruluSurum = "";
    int kuruluKod = 0;
    try {
      final info = await PackageInfo.fromPlatform();
      kuruluSurum = info.version;
      kuruluKod = int.tryParse(info.buildNumber) ?? 0;
    } catch (_) {
      return; // sürüm bilgisi okunamazsa sessizce geç
    }

    final karar = guncellemeKarari(kuruluKod: kuruluKod, uzak: uzak);
    if (!karar.guncellemeVar) return;

    // Diyalog, MaterialApp'ın ALTINDAKİ bir context ile açılmalı; kök State
    // context'i Navigator'ın üstünde kaldığından diyalog hiç görünmüyordu.
    final navContext = _navigatorKey.currentContext;
    if (navContext == null || !navContext.mounted) return;

    await guncellemeDiyaloguGoster(
      navContext,
      surum: uzak,
      zorunlu: karar.zorunlu,
      kuruluSurum: kuruluSurum,
      baseUrl: baseUrl,
    );
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

  /// K9.11: "Beni hatırla" anahtarı değiştirilince hemen pekiştir.
  Future<void> _onRememberMeChanged(bool value) async {
    await _storage.saveRememberMe(value);
    setState(() {
      _rememberMe = value;
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
      navigatorKey: _navigatorKey,
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
        initialRememberMe: _rememberMe,
        onRememberMeChanged: _onRememberMeChanged,
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

    // K9.12: Editör iki bölümlü ekran (Editör + Üye'nin aynısı).
    if (_tokens!.isEditor) {
      return EditorHomeScreen(
        baseUrl: _baseUrl!,
        tokens: _tokens!,
        onLogout: _logout,
        onSessionExpired: _onSessionExpired,
        currentTheme: _currentTheme,
        onThemeChange: _changeTheme,
      );
    }

    // Üye (editör olmayan) → salt-okunur üye ekranı.
    if (_tokens!.isUye) {
      return UyeHomeScreen(
        baseUrl: _baseUrl!,
        tokens: _tokens!,
        onLogout: _logout,
        onSessionExpired: _onSessionExpired,
      );
    }

    return BookListScreen(
      baseUrl: _baseUrl!,
      tokens: _tokens!,
      onLogout: _logout,
      onSessionExpired: _onSessionExpired,
      currentTheme: _currentTheme,
      onThemeChange: _changeTheme,
    );
  }
}
