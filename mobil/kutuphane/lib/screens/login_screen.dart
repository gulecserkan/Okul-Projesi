import 'package:flutter/material.dart';

import '../api/library_api.dart';
import '../models/auth.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({
    super.key,
    required this.baseUrl,
    required this.onAuthenticated,
    required this.onChangeServer,
    this.lastKnownBaseUrl,
    this.initialMessage,
    this.api,
  });

  final String baseUrl;
  final Future<void> Function(AuthTokens tokens) onAuthenticated;
  final Future<void> Function() onChangeServer;
  final String? lastKnownBaseUrl;

  /// Oturum süresi dolduğunda gösterilecek bilgilendirme (varsa).
  final String? initialMessage;

  /// Test/DI için dışarıdan verilebilir; verilmezse kendi istemcisini kurar.
  final LibraryApiClient? api;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _loading = false;
  String? _error;
  bool _obscurePassword = true;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      body: LayoutBuilder(
        builder: (context, constraints) {
          return Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  scheme.surface,
                  scheme.secondaryContainer.withValues(alpha: 0.2),
                ],
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
              ),
            ),
            child: SingleChildScrollView(
              padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
              child: ConstrainedBox(
                constraints: BoxConstraints(
                  maxWidth: 520,
                  minHeight: constraints.maxHeight - 32,
                ),
                child: Center(
                  child: Card(
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              CircleAvatar(
                                backgroundColor: scheme.primary.withValues(alpha: 0.12),
                                child: Icon(Icons.lock_open_outlined, color: scheme.primary),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Text(
                                  "Kütüphane Girişi",
                                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                                        fontWeight: FontWeight.w700,
                                      ),
                                ),
                              ),
                              TextButton.icon(
                                onPressed: _loading
                                    ? null
                                    : () {
                                        widget.onChangeServer();
                                      },
                                icon: const Icon(Icons.settings_ethernet),
                                label: const Text("Sunucu değiştir"),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Text(
                            "Sunucu: ${widget.baseUrl}",
                            style: Theme.of(context)
                                .textTheme
                                .labelMedium
                                ?.copyWith(color: scheme.outline),
                          ),
                          const SizedBox(height: 18),
                          if (widget.initialMessage != null) ...[
                            Container(
                              width: double.infinity,
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(
                                color: scheme.secondaryContainer.withValues(alpha: 0.5),
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: Row(
                                children: [
                                  Icon(Icons.info_outline, size: 18, color: scheme.primary),
                                  const SizedBox(width: 8),
                                  Expanded(child: Text(widget.initialMessage!)),
                                ],
                              ),
                            ),
                            const SizedBox(height: 12),
                          ],
                          TextField(
                            controller: _usernameController,
                            decoration: const InputDecoration(
                              labelText: "Kullanıcı adı",
                              prefixIcon: Icon(Icons.person_outline),
                            ),
                            textInputAction: TextInputAction.next,
                            autofocus: true,
                          ),
                          const SizedBox(height: 12),
                          TextField(
                            controller: _passwordController,
                            decoration: InputDecoration(
                              labelText: "Şifre",
                              prefixIcon: const Icon(Icons.lock_outline),
                              suffixIcon: IconButton(
                                icon: Icon(_obscurePassword ? Icons.visibility_off : Icons.visibility),
                                onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                              ),
                            ),
                            obscureText: _obscurePassword,
                            onSubmitted: (_) => _login(),
                          ),
                          const SizedBox(height: 4),
                          Align(
                            alignment: Alignment.centerLeft,
                            child: TextButton(
                              onPressed: _loading ? null : _showForgotPassword,
                              child: const Text("Şifrem yok"),
                            ),
                          ),
                          const SizedBox(height: 8),
                          if (_error != null)
                            Padding(
                              padding: const EdgeInsets.only(bottom: 8),
                              child: Row(
                                children: [
                                  Icon(Icons.error_outline, color: scheme.error),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      _error!,
                                      style: TextStyle(color: scheme.error),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton.icon(
                              onPressed: _loading ? null : _login,
                              icon: _loading
                                  ? SizedBox(
                                      width: 18,
                                      height: 18,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                        color: scheme.onPrimary,
                                      ),
                                    )
                                  : const Icon(Icons.login),
                              label: Text(_loading ? "Giriş yapılıyor..." : "Giriş yap"),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  void _showForgotPassword() {
    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text("Şifrem yok"),
        content: const Text(
          "Şifreler okul kütüphanesindeki kütüphane sorumlusu tarafından "
          "tanımlanır. Üye numaranızla şifre almak için kütüphane sorumlusuyla "
          "iletişime geçin.\n\nİlk girişinizde kendinize yeni bir şifre "
          "belirleyeceksiniz.",
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text("Tamam"),
          ),
        ],
      ),
    );
  }

  Future<void> _login() async {
    final username = _usernameController.text.trim();
    final password = _passwordController.text.trim();
    if (username.isEmpty || password.isEmpty) {
      setState(() => _error = "Kullanıcı adı ve şifre zorunlu.");
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final api = widget.api ?? LibraryApiClient(baseUrl: widget.baseUrl);
      final tokens = await api.login(username, password);
      // K9: mobil uygulama yalnız üye (öğrenci/öğretmen/editör) hesaplarına açıktır;
      // personel/admin masaüstü uygulamasını kullanır.
      if (!tokens.isUye) {
        if (!mounted) return;
        setState(() {
          _error = 'Bu hesap masaüstü (personel/admin) uygulamasına aittir; '
              'mobil uygulama öğrenci, öğretmen ve editör içindir.';
          _loading = false;
        });
        return;
      }
      if (!mounted) return;
      await widget.onAuthenticated(tokens);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e is ApiException ? e.message : e.toString();
        _loading = false;
      });
    }
  }
}
