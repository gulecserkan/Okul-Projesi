import 'package:flutter/foundation.dart';

/// K15.6: Bildirime dokunulduğunda hedeflenecek sekme isteği.
///
/// 0 = Kitaplar, 1 = Ödünçlerim, 2 = Ceza. `null` istek yok demektir.
/// `UyeHomeScreen` bu değeri dinler, ilgili sekmeye geçer ve değeri tüketip
/// `null`'a çeker. Firebase'e bağımlı değildir; bu yüzden widget testleri
/// güvenle import edebilir.
final ValueNotifier<int?> bildirimSekmeIstegi = ValueNotifier<int?>(null);

/// "Ödünçlerim" sekmesinin indeksi (K15.6).
const int kOdunclerimSekmesi = 1;
