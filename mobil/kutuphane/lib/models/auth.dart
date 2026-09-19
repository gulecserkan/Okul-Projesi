class AuthTokens {
  const AuthTokens({
    required this.accessToken,
    required this.refreshToken,
    this.fullName,
    this.role,
    this.tip = 'personel',
    this.uyeNo,
    this.parolaDegistirilsin = false,
  });

  final String accessToken;
  final String refreshToken;
  final String? fullName;
  final String? role;

  /// K9: hesap tipi — 'personel' (operatör/admin) veya 'uye' (öğrenci/öğretmen/editör).
  final String tip;

  /// Üye hesabında üye numarası (kendi ödünçleri için).
  final String? uyeNo;

  /// İlk girişte şifre değiştirme zorunluluğu.
  final bool parolaDegistirilsin;

  bool get isUye => tip == 'uye';

  /// K9: editör — hem ödünç alır hem kitap düzenleyebilir.
  bool get isEditor => role == 'editor';

  AuthTokens copyWith({
    String? accessToken,
    String? refreshToken,
    String? fullName,
    String? role,
    String? tip,
    String? uyeNo,
    bool? parolaDegistirilsin,
  }) {
    return AuthTokens(
      accessToken: accessToken ?? this.accessToken,
      refreshToken: refreshToken ?? this.refreshToken,
      fullName: fullName ?? this.fullName,
      role: role ?? this.role,
      tip: tip ?? this.tip,
      uyeNo: uyeNo ?? this.uyeNo,
      parolaDegistirilsin: parolaDegistirilsin ?? this.parolaDegistirilsin,
    );
  }

  factory AuthTokens.fromJson(Map<String, dynamic> json) {
    return AuthTokens(
      accessToken: (json["access"] ?? "").toString(),
      refreshToken: (json["refresh"] ?? "").toString(),
      fullName: json["full_name"]?.toString(),
      role: json["role"]?.toString(),
      tip: (json["tip"] ?? "personel").toString(),
      uyeNo: json["uye_no"]?.toString(),
      parolaDegistirilsin: json["parola_degistirilsin"] == true,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      "access": accessToken,
      "refresh": refreshToken,
      "full_name": fullName,
      "role": role,
      "tip": tip,
      "uye_no": uyeNo,
      "parola_degistirilsin": parolaDegistirilsin,
    };
  }
}
