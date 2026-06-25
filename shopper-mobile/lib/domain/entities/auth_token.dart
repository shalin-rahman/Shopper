import 'package:equatable/equatable.dart';

class AuthToken extends Equatable {
  final String accessToken;
  final String? refreshToken;
  final DateTime? expiresAt;
  final String tokenType;

  const AuthToken({
    required this.accessToken,
    this.refreshToken,
    this.expiresAt,
    this.tokenType = 'Bearer',
  });

  bool get isExpired => expiresAt?.isBefore(DateTime.now()) ?? true;

  @override
  List<Object?> get props => [accessToken, refreshToken, expiresAt];
}
