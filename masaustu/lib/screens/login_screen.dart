import 'package:flutter/material.dart';

import '../api/auth_api.dart';
import '../config.dart';
import '../screens/home_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  final _serverController = TextEditingController(text: AppConfig.apiBaseUrl);

  bool _showServerSettings = false;
  bool _busy = false;
  bool _serverOk = false;
  bool _healthChecked = false;

  @override
  void initState() {
    super.initState();
    _checkHealth();
  }

  Future<void> _checkHealth() async {
    final ok = await AuthApi().healthCheck();
    if (!mounted) return;
    setState(() {
      _serverOk = ok;
      _healthChecked = true;
    });
  }

  Future<void> _onSubmit() async {
    FocusScope.of(context).unfocus();
    final username = _usernameController.text.trim();
    final password = _passwordController.text;

    if (_showServerSettings) {
      final server = _serverController.text.trim();
      if (server.isEmpty) {
        _toast('Sunucu adresi boş olamaz.');
        return;
      }
      AppConfig.apiBaseUrl = server;
    }

    if (username.isEmpty || password.isEmpty) {
      _toast('Kullanıcı adı ve şifre girin.');
      return;
    }

    setState(() => _busy = true);
    final res = await AuthApi().login(username, password);
    if (!mounted) return;
    setState(() => _busy = false);

    if (res.ok) {
      final session = AppConfig.session;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => HomeScreen(session: session!)),
      );
    } else {
      _toast(res.error);
    }
  }

  void _toast(String message) {
    ScaffoldMessenger.of(context)
      ..clearSnackBars()
      ..showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF3F6FB),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Icon(Icons.menu_book, size: 64, color: Theme.of(context).colorScheme.primary),
                const SizedBox(height: 8),
                Text(
                  'Kütüphane Yönetim Sistemi',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 4),
                _serverStatus(),
                const SizedBox(height: 24),
                Card(
                  elevation: 2,
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        TextField(
                          controller: _usernameController,
                          decoration: const InputDecoration(
                            labelText: 'Kullanıcı adı',
                            prefixIcon: Icon(Icons.person_outline),
                            border: OutlineInputBorder(),
                          ),
                          autofocus: true,
                          textInputAction: TextInputAction.next,
                        ),
                        const SizedBox(height: 16),
                        TextField(
                          controller: _passwordController,
                          obscureText: true,
                          onSubmitted: (_) => _onSubmit(),
                          decoration: const InputDecoration(
                            labelText: 'Şifre',
                            prefixIcon: Icon(Icons.lock_outline),
                            border: OutlineInputBorder(),
                          ),
                        ),
                        const SizedBox(height: 8),
                        Align(
                          alignment: Alignment.centerRight,
                          child: TextButton(
                            onPressed: () => setState(() => _showServerSettings = !_showServerSettings),
                            child: Text(_showServerSettings ? 'Sunucu ayarlarını gizle' : 'Sunucu ayarları'),
                          ),
                        ),
                        if (_showServerSettings) ...[
                          TextField(
                            controller: _serverController,
                            decoration: const InputDecoration(
                              labelText: 'Sunucu adresi',
                              hintText: 'http://127.0.0.1:8000/api',
                              prefixIcon: Icon(Icons.dns_outlined),
                              border: OutlineInputBorder(),
                            ),
                          ),
                          const SizedBox(height: 12),
                        ],
                        FilledButton(
                          onPressed: _busy ? null : _onSubmit,
                          style: FilledButton.styleFrom(
                            padding: const EdgeInsets.symmetric(vertical: 16),
                          ),
                          child: _busy
                              ? const SizedBox(
                                  height: 20,
                                  width: 20,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Text('Giriş Yap'),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _serverStatus() {
    if (!_healthChecked) {
      return const Center(
        child: SizedBox(
          height: 14,
          width: 14,
          child: CircularProgressIndicator(strokeWidth: 2),
        ),
      );
    }
    final color = _serverOk ? Colors.green.shade700 : Colors.red.shade700;
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(Icons.circle, size: 10, color: color),
        const SizedBox(width: 6),
        Text(
          _serverOk ? 'Sunucu bağlı' : 'Sunucuya ulaşılamıyor',
          style: TextStyle(color: color, fontSize: 12),
        ),
      ],
    );
  }
}