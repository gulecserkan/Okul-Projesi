class AuthTokens {
  const AuthTokens({
    required this.accessToken,
    required this.refreshToken,
    this.fullName,
    this.role,
    this.tip = 'personel',
    this.ogrenciNo,
    this.parolaDegistirilsin = false,
  });

  final String accessToken;
  final String refreshToken;
  final String? fullName;
  final String? role;

  /// K9: hesap tipi — 'personel' (personel/editör) veya 'ogrenci' (borçlu).
  final String tip;

  /// Borçlu hesabında öğrenci numarası (kendi ödünçleri için).
  final String? ogrenciNo;

  /// İlk girişte şifre değiştirme zorunluluğu.
  final bool parolaDegistirilsin;

  bool get isBorrower => tip == 'ogrenci';

  AuthTokens copyWith({
    String? accessToken,
    String? refreshToken,
    String? fullName,
    String? role,
    String? tip,
    String? ogrenciNo,
    bool? parolaDegistirilsin,
  }) {
    return AuthTokens(
      accessToken: accessToken ?? this.accessToken,
      refreshToken: refreshToken ?? this.refreshToken,
      fullName: fullName ?? this.fullName,
      role: role ?? this.role,
      tip: tip ?? this.tip,
      ogrenciNo: ogrenciNo ?? this.ogrenciNo,
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
      ogrenciNo: json["ogrenci_no"]?.toString(),
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
      "ogrenci_no": ogrenciNo,
      "parola_degistirilsin": parolaDegistirilsin,
    };
  }
}
