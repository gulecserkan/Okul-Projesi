import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';

import 'api/library_api.dart';

/// K15: Mobil FCM push bildirim servisi.
///
/// Firebase yapılandırılmamışsa, Google Play servisleri yoksa veya izin
/// verilmezse tüm çağrılar sessizce başarısız olur; uygulama akışı (ekran içi
/// "kaldı/gecikti" satırı) bozulmaz. Sunucu tarafı seçim/gönderim
/// `jobs.dispatch_notifications` içindedir; istemci yalnız token kaydeder.
class BildirimServisi {
  BildirimServisi({FirebaseMessaging? messaging}) : _enjekte = messaging;

  final FirebaseMessaging? _enjekte;
  bool _hazir = false;
  bool _dinleyiciKuruldu = false;
  String? _token;

  FirebaseMessaging get _messaging => _enjekte ?? FirebaseMessaging.instance;

  /// Uygulama açılışında bir kez çağrılır; hata durumunda false döner.
  Future<bool> baslat() async {
    if (_hazir) return true;
    try {
      await Firebase.initializeApp();
      _hazir = true;
      return true;
    } catch (e) {
      debugPrint("Bildirim başlatılamadı: $e");
      return false;
    }
  }

  /// Android 13+ bildirim iznini ister. İzin verilmezse sessizce devam edilir.
  Future<bool> izinIste() async {
    if (!await baslat()) return false;
    try {
      final ayar = await _messaging.requestPermission();
      return ayar.authorizationStatus == AuthorizationStatus.authorized ||
          ayar.authorizationStatus == AuthorizationStatus.provisional;
    } catch (e) {
      debugPrint("Bildirim izni alınamadı: $e");
      return false;
    }
  }

  /// FCM token'ını döner (alınamazsa null).
  Future<String?> tokenAl() async {
    if (_token != null && _token!.isNotEmpty) return _token;
    if (!await baslat()) return null;
    try {
      _token = await _messaging.getToken();
      return _token;
    } catch (e) {
      debugPrint("FCM token alınamadı: $e");
      return null;
    }
  }

  /// Token'ı sunucuya kaydeder (giriş sonrası). Token yoksa sessiz geçer.
  Future<void> tokenKaydet(LibraryApiClient api) async {
    await izinIste();
    final token = await tokenAl();
    if (token == null || token.isEmpty) return;
    try {
      await api.registerBildirimToken(token);
    } catch (e) {
      debugPrint("Bildirim token kaydedilemedi: $e");
    }
  }

  /// Token'ı sunucudan siler (çıkışta).
  Future<void> tokenSil(LibraryApiClient api) async {
    final token = _token ?? await tokenAl();
    if (token == null || token.isEmpty) return;
    try {
      await api.deleteBildirimToken(token);
    } catch (e) {
      debugPrint("Bildirim token silinemedi: $e");
    }
  }

  /// Token yenilendiğinde (nadiren) sunucudaki kaydı güncellemek için dinler.
  void yenilenmeyiDinle(Future<void> Function(String token) onYeni) {
    if (_dinleyiciKuruldu || !_hazir) return;
    _dinleyiciKuruldu = true;
    _messaging.onTokenRefresh.listen((token) {
      _token = token;
      onYeni(token);
    });
  }
}
