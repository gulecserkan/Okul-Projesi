import 'package:flutter/material.dart';

import '../api/kutuphane_api.dart';
import '../models.dart';
import '../theme.dart';

/// Yeni üye oluşturmak / mevcut üyeyi düzenlemek için form diyaloğu.
/// Kaydedilen üyeyi `Navigator.pop` ile döndürür; iptalde null.
class StudentFormDialog extends StatefulWidget {
  final Uye? uye;
  /// K9: yalnızca admin üye rolü seçebilir; personel için alan gizlenir ve
  /// yeni üyeler varsayılan olarak "Öğrenci" rolüyle kaydedilir.
  final bool isAdmin;

  const StudentFormDialog({super.key, this.uye, required this.isAdmin});

  @override
  State<StudentFormDialog> createState() => _StudentFormDialogState();
}

class _StudentFormDialogState extends State<StudentFormDialog> {
  final _api = KutuphaneApi();
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _ad;
  late final TextEditingController _soyad;
  late final TextEditingController _no;
  late final TextEditingController _telefon;
  late final TextEditingController _eposta;
  final _sifre = TextEditingController();
  late Future<List<Sinif>> _siniflarFuture;
  late Future<List<Map<String, dynamic>>> _rollarFuture;
  int? _sinifId;
  int? _rolId;
  int? _ogrRolId;
  bool _busy = false;

  bool get _editing => widget.uye != null;

  @override
  void initState() {
    super.initState();
    final o = widget.uye;
    _ad = TextEditingController(text: o?.ad ?? '');
    _soyad = TextEditingController(text: o?.soyad ?? '');
    _no = TextEditingController(text: o?.uyeNo ?? '');
    _telefon = TextEditingController(text: o?.telefon ?? '');
    _eposta = TextEditingController(text: o?.eposta ?? '');
    _sinifId = o?.sinif?.id;
    _siniflarFuture = _loadSiniflar(o?.sinif);
    _rollarFuture = _loadRollar(o);
  }

  Future<List<Map<String, dynamic>>> _loadRollar(Uye? o) async {
    final list = await _api.roller();
    int? ogrId;
    for (final r in list) {
      if (r['ad'] == 'Öğrenci') {
        ogrId = r['id'] as int?;
        break;
      }
    }
    if (mounted) {
      // Varsayılan: düzenlemede mevcut rol korunur; yeni üyede "Öğrenci".
      int? hedef;
      if (widget.isAdmin &&
          o != null &&
          o.rolId != null &&
          list.any((r) => r['id'] == o.rolId)) {
        hedef = o.rolId;
      } else {
        hedef = ogrId ?? (list.isEmpty ? null : list.first['id'] as int?);
      }
      if (_rolId == null && hedef != null) _rolId = hedef;
      _ogrRolId = ogrId;
    }
    return list;
  }

  Future<List<Sinif>> _loadSiniflar(Sinif? current) async {
    try {
      final list = await _api.siniflar();
      if (mounted &&
          current != null &&
          _sinifId == null &&
          !list.any((s) => s.id == current.id)) {
        _sinifId = current.id;
      }
      return list;
    } catch (_) {
      return current == null ? const [] : [current];
    }
  }

  @override
  void dispose() {
    _ad.dispose();
    _soyad.dispose();
    _no.dispose();
    _telefon.dispose();
    _eposta.dispose();
    _sifre.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _busy = true);
    // K9: personel yalnız üye eklerken "Öğrenci" varsayılanını gönderir;
    // düzenlemede mevcut rolü değiştirmez.
    final int? gonderilecekRolId;
    if (!_editing) {
      gonderilecekRolId = widget.isAdmin ? (_rolId ?? _ogrRolId) : _ogrRolId;
    } else {
      gonderilecekRolId = widget.isAdmin ? _rolId : null;
    }
    final res = await _api.saveStudent(
      id: widget.uye?.id,
      ad: _ad.text,
      soyad: _soyad.text,
      uyeNo: _no.text,
      sinifId: _sinifId,
      telefon: _telefon.text,
      eposta: _eposta.text,
      sifre: _sifre.text,
      rolId: gonderilecekRolId,
    );
    if (!mounted) return;
    if (res.uye != null) {
      Navigator.of(context).pop(res.uye);
    } else {
      setState(() => _busy = false);
      showAppSnack(context, res.error ?? 'Kayıt yapılamadı.', error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(_editing ? 'Üye Düzenle' : 'Yeni Üye'),
      content: SizedBox(
        width: 420,
        child: SingleChildScrollView(
          child: Form(
            key: _formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextFormField(
                  controller: _ad,
                  autofocus: !_editing,
                  decoration: const InputDecoration(
                    labelText: 'Ad',
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                  validator: (v) =>
                      (v == null || v.trim().isEmpty) ? 'Ad gerekli.' : null,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _soyad,
                  decoration: const InputDecoration(
                    labelText: 'Soyad',
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                  validator: (v) =>
                      (v == null || v.trim().isEmpty) ? 'Soyad gerekli.' : null,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _no,
                  decoration: const InputDecoration(
                    labelText: 'Üye No',
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                  validator: (v) => (v == null || v.trim().isEmpty)
                      ? 'Üye no gerekli.'
                      : null,
                ),
                const SizedBox(height: 12),
                if (widget.isAdmin)
                  FutureBuilder<List<Map<String, dynamic>>>(
                    future: _rollarFuture,
                    builder: (context, snap) {
                      final rollar = snap.data ?? const <Map<String, dynamic>>[];
                      return DropdownButtonFormField<int>(
                        initialValue: _rolId,
                        isExpanded: true,
                        decoration: const InputDecoration(
                          labelText: 'Rol',
                          border: OutlineInputBorder(),
                          isDense: true,
                        ),
                        items: [
                          for (final r in rollar)
                            DropdownMenuItem<int>(
                              value: r['id'] as int,
                              child: Text(r['ad'] as String? ?? ''),
                            ),
                        ],
                        onChanged: _busy
                            ? null
                            : (v) => setState(() => _rolId = v),
                      );
                    },
                  ),
                const SizedBox(height: 12),
                FutureBuilder<List<Sinif>>(
                  future: _siniflarFuture,
                  builder: (context, snap) {
                    if (snap.connectionState != ConnectionState.done) {
                      return const SizedBox(
                        height: 52,
                        child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
                      );
                    }
                    final siniflar = snap.data ?? const <Sinif>[];
                    return DropdownButtonFormField<int>(
                      initialValue: _sinifId,
                      isExpanded: true,
                      decoration: const InputDecoration(
                        labelText: 'Sınıf',
                        border: OutlineInputBorder(),
                        isDense: true,
                      ),
                      items: [
                        const DropdownMenuItem<int>(
                          value: null,
                          child: Text('— sınıf seç —'),
                        ),
                        for (final s in siniflar)
                          DropdownMenuItem<int>(value: s.id, child: Text(s.ad)),
                      ],
                      onChanged: _busy
                          ? null
                          : (v) => setState(() => _sinifId = v),
                    );
                  },
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _telefon,
                  decoration: const InputDecoration(
                    labelText: 'Telefon',
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _eposta,
                  decoration: const InputDecoration(
                    labelText: 'E-posta',
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                  keyboardType: TextInputType.emailAddress,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _sifre,
                  obscureText: true,
                  decoration: InputDecoration(
                    labelText: 'Giriş şifresi (üye uygulaması)',
                    helperText: _editing
                        ? 'Boş bırakılırsa mevcut şifre değişmez.'
                        : 'Boş bırakılırsa giriş hesabı oluşturulmaz.',
                    helperMaxLines: 2,
                    border: const OutlineInputBorder(),
                    isDense: true,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed:
              _busy ? null : () => Navigator.of(context).pop(),
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