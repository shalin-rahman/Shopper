import 'package:dartz/dartz.dart';
import '../../core/error/failures.dart';
import '../entities/user.dart';
import '../entities/auth_token.dart';

abstract class AuthRepository {
  Future<Either<Failure, AuthToken>> login({
    required String email,
    required String password,
  });

  Future<Either<Failure, void>> logout();

  Future<Either<Failure, User>> getCurrentUser();

  Future<Either<Failure, AuthToken>> refreshToken(String refreshToken);

  Future<Either<Failure, bool>> isLoggedIn();

  Stream<bool> get authStateChanges;
}