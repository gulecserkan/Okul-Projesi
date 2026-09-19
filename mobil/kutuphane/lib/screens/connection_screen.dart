import 'package:flutter/material.dart';

import '../api/library_api.dart';

class ConnectionScreen extends StatefulWidget {
  const ConnectionScreen({
    super.key,
    required this.onConnected,
    this.initialError,
    this.lastKnownBaseUrl,
  });

  final Future<void> Function(String baseUrl) onConnected;
  final String? initialError;
  final String? lastKnownBaseUrl;

  @override
  State<ConnectionScreen> createState() => _ConnectionScreenState();
}

class _ConnectionScreenState extends State<ConnectionScreen> {
  final TextEditingController _controller = TextEditingController();
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _error = widget.initialError;
    if (widget.lastKnownBaseUrl != null && widget.lastKnownBaseUrl!.isNotEmpty) {
      _controller.text = widget.lastKnownBaseUrl!;
    } else {
      _controller.text = "http://192.168.1.12:8000";
    }
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Scaffold(
      body: LayoutBuilder(
        builder: (context, constraints) {
          return Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  colorScheme.primary.withOpacity(0.08),
                  colorScheme.surfaceVariant.withOpacity(0.16),
                  colorScheme.surface,
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
            ),
            padding: const EdgeInsets.all(16),
            child: SingleChildScrollView(
              padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
              child: ConstrainedBox(
                constraints: BoxConstraints(
                  maxWidth: 540,
                  minHeight: constraints.maxHeight - 32,
                ),
                child: Center(
                  child: Card(
                    elevation: 10,
                    shadowColor: colorScheme.primary.withOpacity(0.2),
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
                                backgroundColor: colorScheme.primary.withOpacity(0.12),
                                child: Icon(Icons.wifi_tethering, color: colorScheme.primary),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Text(
                                  "Kütüphane sunucusuna bağlan",
                                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                                        fontWeight: FontWeight.w700,
                                      ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 16),
                          Text(
                            "Django sunucusunun adresini gir ve el sıkışma (health) kontrolünü başlat. "
                            "Adres http/https içeriyorsa aynen gir, aksi durumda http ön eki otomatik eklenir.",
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                          const SizedBox(height: 18),
                          TextField(
                            controller: _controller,
                            keyboardType: TextInputType.url,
                            textInputAction: TextInputAction.done,
                            autofocus: true,
                            decoration: const InputDecoration(
                              labelText: "Sunucu adresi",
                              prefixIcon: Icon(Icons.cloud_outlined),
                            ),
                            onSubmitted: (_) => _attemptHandshake(),
                          ),
                          const SizedBox(height: 12),
                          if (_error != null)
                            Padding(
                              padding: const EdgeInsets.only(bottom: 8),
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Icon(Icons.error_outline, color: colorScheme.error),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      _error!,
                                      style: TextStyle(color: colorScheme.error),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          Row(
                            children: [
                              Expanded(
                              child: ElevatedButton.icon(
                                onPressed: _loading ? null : _attemptHandshake,
                                icon: _loading
                                    ? SizedBox(
                                        width: 18,
                                          height: 18,
                                          child: CircularProgressIndicator(
                                            strokeWidth: 2,
                                            color: colorScheme.onPrimary,
                                          ),
                                        )
                                      : const Icon(Icons.handshake_outlined),
                                  label: Text(_loading ? "Kontrol ediliyor..." : "Bağlantıyı kontrol et"),
                                ),
                              ),
                            ],
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

  Future<void> _attemptHandshake() async {
    final rawInput = _controller.text.trim().isNotEmpty
        ? _controller.text.trim()
        : (widget.lastKnownBaseUrl ?? "");
    if (rawInput.isEmpty) {
      setState(() => _error = "Lütfen sunucu adresini girin.");
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    final api = LibraryApiClient(baseUrl: rawInput);
    final result = await api.handshake();
    if (!mounted) return;

    if (result.ok) {
      await widget.onConnected(api.baseUrl);
      if (!mounted) return;
      setState(() {
        _loading = false;
      });
      if (Navigator.of(context).canPop()) {
        Navigator.of(context).pop();
      }
    } else {
      setState(() {
        _error = result.message;
        _loading = false;
      });
    }
  }
}
