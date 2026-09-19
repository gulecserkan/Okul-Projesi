import 'package:flutter/material.dart';

import '../api/library_api.dart';
import '../models/auth.dart';

/// K9: İlk girişte şifre değiştirme zorunluluğu ekranı (üye hesapları).
class ForcePasswordScreen extends StatefulWidget {
  const ForcePasswordScreen({
    super.key,
    required this.baseUrl,
    required this.tokens,
    required this.onDone,
  });

  final String baseUrl;
  final AuthTokens tokens;
  final Future<void> Function() onDone;

  @override
  State<ForcePasswordScreen> createState() => _ForcePasswordScreenState();
}

class _ForcePasswordScreenState extends State<ForcePasswordScreen> {
  late final LibraryApiClient _api;
  final _current = TextEditingController();
  final _new = TextEditingController();
  final _confirm = TextEditingController();
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _api = LibraryApiClient(baseUrl: widget.baseUrl, tokens: widget.tokens);
  }

  @override
  void dispose() {
    _current.dispose();
    _new.dispose();
    _confirm.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final cur = _current.text.trim();
    final yeni = _new.text.trim();
    final tekrar = _confirm.text.trim();
    if (cur.isEmpty || yeni.isEmpty || tekrar.isEmpty) {
      setState(() => _error = 'Tüm alanlar zorunludur.');
      return;
    }
    if (yeni != tekrar) {
      setState(() => _error = 'Yeni şifreler uyuşmuyor.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await _api.changePassword(
        currentPassword: cur,
        newPassword: yeni,
        newPasswordConfirm: tekrar,
      );
      if (!mounted) return;
      await widget.onDone();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _error = e.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Şifre Değiştir')),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text(
                  'İlk girişte şifrenizi değiştirmeniz gerekiyor.',
                  style: TextStyle(fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _current,
                  obscureText: true,
                  decoration: const InputDecoration(
                    labelText: 'Mevcut şifre',
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _new,
                  obscureText: true,
                  decoration: const InputDecoration(
                    labelText: 'Yeni şifre',
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _confirm,
                  obscureText: true,
                  decoration: const InputDecoration(
                    labelText: 'Yeni şifre (tekrar)',
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                  onSubmitted: (_) => _busy ? null : _submit(),
                ),
                if (_error != null) ...[
                  const SizedBox(height: 12),
                  Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                ],
                const SizedBox(height: 20),
                FilledButton(
                  onPressed: _busy ? null : _submit,
                  child: _busy
                      ? const SizedBox(
                          height: 18,
                          width: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Şifreyi Değiştir'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
