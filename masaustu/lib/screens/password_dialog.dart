import 'dart:math';

import 'package:flutter/material.dart';

import '../api/kutuphane_api.dart';
import '../models.dart';
import '../theme.dart';

/// Üyeye mobil giriş şifresi verir/sıfırlar (K9).
///
/// Şifre elle yazılabilir veya "Rastgele Üret" düğmesiyle üretilir. Backend
/// `parola_degistirilsin` bayrağını set ettiği için öğrenci ilk girişte
/// şifresini kendisi belirler.
class PasswordDialog extends StatefulWidget {
  final Uye uye;

  const PasswordDialog({super.key, required this.uye});

  @override
  State<PasswordDialog> createState() => _PasswordDialogState();
}

class _PasswordDialogState extends State<PasswordDialog> {
  static const _rastgeleChars =
      'abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789';

  final _api = KutuphaneApi();
  final _formKey = GlobalKey<FormState>();
  final _sifre = TextEditingController();
  bool _busy = false;
  bool _goster = false;

  @override
  void dispose() {
    _sifre.dispose();
    super.dispose();
  }

  String _rastgeleSifre() {
    final rnd = Random.secure();
    return String.fromCharCodes(Iterable.generate(
      8,
      (_) => _rastgeleChars.codeUnitAt(rnd.nextInt(_rastgeleChars.length)),
    ));
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _busy = true);
    final res = await _api.setPassword(widget.uye.id, _sifre.text);
    if (!mounted) return;
    if (res.ok) {
      Navigator.of(context).pop(_sifre.text.trim());
    } else {
      setState(() => _busy = false);
      showAppSnack(context, res.error ?? 'Şifre güncellenemedi.', error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final o = widget.uye;
    return AlertDialog(
      title: const Text('Üye Giriş Şifresi'),
      content: SizedBox(
        width: 420,
        child: SingleChildScrollView(
          child: Form(
            key: _formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('${o.ad} ${o.soyad}',
                    style: theme.textTheme.titleMedium
                        ?.copyWith(fontWeight: FontWeight.bold)),
                const SizedBox(height: 4),
                Wrap(
                  spacing: 8,
                  children: [
                    Chip(
                      label: Text('Kullanıcı adı: ${o.uyeNo}'),
                      visualDensity: VisualDensity.compact,
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _sifre,
                  obscureText: !_goster,
                  decoration: InputDecoration(
                    labelText: 'Şifre',
                    border: const OutlineInputBorder(),
                    isDense: true,
                    helperMaxLines: 2,
                    helperText:
                        'Öğrenci kullanıcı adıyla bu şifreyle giriş yapar; '
                        'ilk girişte kendi şifresini belirler.',
                    suffixIcon: IconButton(
                      tooltip: _goster ? 'Gizle' : 'Göster',
                      icon: Icon(
                        _goster ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                      ),
                      onPressed: _busy
                          ? null
                          : () => setState(() => _goster = !_goster),
                    ),
                  ),
                  validator: (v) {
                    final val = (v ?? '').trim();
                    if (val.isEmpty) return 'Şifre gerekli.';
                    if (val.length < 4) return 'En az 4 karakter olmalı.';
                    return null;
                  },
                ),
                const SizedBox(height: 12),
                Align(
                  alignment: Alignment.centerRight,
                  child: OutlinedButton.icon(
                    onPressed: _busy
                        ? null
                        : () => setState(() => _sifre.text = _rastgeleSifre()),
                    icon: const Icon(Icons.refresh, size: 18),
                    label: const Text('Rastgele Üret'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _busy ? null : () => Navigator.of(context).pop(),
          child: const Text('Vazgeç'),
        ),
        FilledButton(
          onPressed: _busy ? null : _save,
          child: _busy
              ? const SizedBox(
                  height: 18,
                  width: 18,
                  child: CircularProgressIndicator(strokeWidth: 2))
              : const Text('Kaydet'),
        ),
      ],
    );
  }
}