import 'package:flutter/material.dart';

import 'api_client.dart';
import 'config.dart';
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'theme.dart';
import 'update_dialog.dart';
import 'update_service.dart';

void main() {
  runApp(const KutuphaneApp());
}

class KutuphaneApp extends StatelessWidget {
  const KutuphaneApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<AppTheme>(
      valueListenable: appThemeController,
      builder: (context, theme, _) => MaterialApp(
        title: 'Kütüphane Yönetim Sistemi',
        debugShowCheckedModeBanner: false,
        theme: buildAppTheme(theme),
        initialRoute: '/',
        routes: {
          '/': (_) => const _BootstrapHome(),
          '/login': (_) => const LoginScreen(),
          '/home': (_) => const _RequireSession(),
        },
      ),
    );
  }
}

/// Kayıtlı oturum varsa token'ı doğrulayıp ana ekrana geçer.
class _BootstrapHome extends StatefulWidget {
  const _BootstrapHome();

  @override
  State<_BootstrapHome> createState() => _BootstrapHomeState();
}

class _BootstrapHomeState extends State<_BootstrapHome> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _startup());
  }

  Future<void> _startup() async {
    await _guncellemeKontrolEt();
    await _restoreSession();
  }

  /// Açılışta sunucudaki masaüstü sürümünü kontrol eder (K13.4).
  Future<void> _guncellemeKontrolEt() async {
    final uzak = await sunucudanSurumOku();
    final karar = guncellemeKarari(
      kuruluKod: AppConfig.appVersionCode,
      uzak: uzak,
    );
    if (!karar.guncellemeVar || uzak == null || !mounted) return;
    await guncellemeGoster(context, uzak, karar.zorunlu);
  }

  Future<void> _restoreSession() async {
    final session = AppConfig.session;
    // K9: masaüstü yalnız personel/admin hesabına açıktır (üye hesapları mobilde).
    if (session == null || !session.isValid || !session.isPersonel) {
      if (!mounted) return;
      AppConfig.session = null;
      Navigator.of(context).pushReplacementNamed('/login');
      return;
    }
    final api = ApiClient();
    final ok = await api.tryRefresh();
    if (!mounted) return;
    final current = AppConfig.session;
    // K9: eski token'larda `role` boş kalabilir; rol yoksa yeniden giriş zorunlu.
    if (!ok || current == null || current.role.isEmpty || !current.isPersonel) {
      AppConfig.session = null;
      Navigator.of(context).pushReplacementNamed('/login');
      return;
    }
    Navigator.of(context).pushReplacementNamed('/home');
  }

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(child: CircularProgressIndicator()),
    );
  }
}

class _RequireSession extends StatelessWidget {
  const _RequireSession();

  @override
  Widget build(BuildContext context) {
    final session = AppConfig.session;
    if (session == null || !session.isValid) {
      return const LoginScreen();
    }
    return HomeScreen(session: session);
  }
}