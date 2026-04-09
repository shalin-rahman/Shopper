import 'package:dartz/dartz.dart';
import 'package:rxdart/rxdart.dart';
import '../../core/error/failures.dart';
import '../../domain/entities/user.dart';
import '../../domain/entities/auth_token.dart';
import '../../domain/repositories/auth_repository.dart';
import '../sources/local/preferences/app_preferences.dart';
import '../sources/remote/api_client.dart';

class AuthRepositoryImpl implements AuthRepository {
  final ApiClient apiClient;
  final AppPreferences preferences;

  final BehaviorSubject<bool> _authStateController = BehaviorSubject<bool>.seeded(false);

  AuthRepositoryImpl({
    required this.apiClient,
    required this.preferences,
  }) {
    // Initialize auth state
    _checkAuthState();
  }

  void _checkAuthState() async {
    final isLoggedIn = await preferences.isLoggedIn();
    _authStateController.add(isLoggedIn);
  }

  @override
  Future<Either<Failure, AuthToken>> login({
    required String email,
    required String password,
  }) async {
    try {
      final result = await apiClient.login(email: email, password: password);

      return result.fold(
        (failure) => Left(failure),
        (authToken) async {
          await preferences.saveAuthToken(authToken);
          _authStateController.add(true);
          return Right(authToken);
        },
      );
    } catch (e) {
      return Left(ServerFailure('Login failed: ${e.toString()}'));
    }
  }

  @override
  Future<Either<Failure, void>> logout() async {
    try {
      await preferences.clearAuthToken();
      _authStateController.add(false);
      return const Right(null);
    } catch (e) {
      return Left(CacheFailure('Logout failed: ${e.toString()}'));
    }
  }

  @override
  Future<Either<Failure, User>> getCurrentUser() async {
    try {
      final result = await apiClient.getCurrentUser();
      return result.fold(
        (failure) => Left(failure),
        (user) => Right(user),
      );
    } catch (e) {
      return Left(ServerFailure('Failed to get current user: ${e.toString()}'));
    }
  }

  @override
  Future<Either<Failure, AuthToken>> refreshToken(String refreshToken) async {
    try {
      final result = await apiClient.refreshToken(refreshToken);
      return result.fold(
        (failure) => Left(failure),
        (authToken) async {
          await preferences.saveAuthToken(authToken);
          return Right(authToken);
        },
      );
    } catch (e) {
      return Left(ServerFailure('Token refresh failed: ${e.toString()}'));
    }
  }

  @override
  Future<Either<Failure, bool>> isLoggedIn() async {
    try {
      final isLoggedIn = await preferences.isLoggedIn();
      return Right(isLoggedIn);
    } catch (e) {
      return Left(CacheFailure('Failed to check login status: ${e.toString()}'));
    }
  }

  @override
  Stream<bool> get authStateChanges => _authStateController.stream;

  void dispose() {
    _authStateController.close();
  }
}