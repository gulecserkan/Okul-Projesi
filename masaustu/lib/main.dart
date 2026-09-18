import 'package:flutter/material.dart';

import 'api_client.dart';
import 'config.dart';
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';

void main() {
  runApp(const KutuphaneApp());
}

class KutuphaneApp extends StatelessWidget {
  const KutuphaneApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Kütüphane Yönetim Sistemi',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF6750A4),
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      initialRoute: '/',
      routes: {
        '/': (_) => const _BootstrapHome(),
        '/login': (_) => const LoginScreen(),
        '/home': (_) => const _RequireSession(),
      },
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
    WidgetsBinding.instance.addPostFrameCallback((_) => _restoreSession());
  }

  Future<void> _restoreSession() async {
    final session = AppConfig.session;
    if (session == null || !session.isValid) {
      if (!mounted) return;
      Navigator.of(context).pushReplacementNamed('/login');
      return;
    }
    final api = ApiClient();
    final ok = await api.tryRefresh();
    if (!mounted) return;
    Navigator.of(context).pushReplacementNamed(ok ? '/home' : '/login');
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