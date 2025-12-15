class AuthTokens {
  const AuthTokens({
    required this.accessToken,
    required this.refreshToken,
    this.fullName,
    this.role,
  });

  final String accessToken;
  final String refreshToken;
  final String? fullName;
  final String? role;

  AuthTokens copyWith({
    String? accessToken,
    String? refreshToken,
    String? fullName,
    String? role,
  }) {
    return AuthTokens(
      accessToken: accessToken ?? this.accessToken,
      refreshToken: refreshToken ?? this.refreshToken,
      fullName: fullName ?? this.fullName,
      role: role ?? this.role,
    );
  }

  factory AuthTokens.fromJson(Map<String, dynamic> json) {
    return AuthTokens(
      accessToken: (json["access"] ?? "").toString(),
      refreshToken: (json["refresh"] ?? "").toString(),
      fullName: json["full_name"]?.toString(),
      role: json["role"]?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      "access": accessToken,
      "refresh": refreshToken,
      "full_name": fullName,
      "role": role,
    };
  }
}
