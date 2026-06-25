import 'package:dartz/dartz.dart' hide Order;
import 'package:equatable/equatable.dart';
import '../../../core/error/failures.dart';
import '../../../core/usecase/usecase.dart';
import '../../../core/validation/validation.dart';
import 'package:shopper_mobile/domain/entities/auth_token.dart';
import '../../repositories/auth_repository.dart';

class LoginParams extends Equatable {
  final String email;
  final String password;

  const LoginParams({
    required this.email,
    required this.password,
  });

  /// Validates the login parameters
  ValidationResult validate() {
    final List<ValidationResult> validations = [];

    // Required field validations
    validations.add(ValidationUtils.validateRequired(email, 'Email'));
    validations.add(ValidationUtils.validateRequired(password, 'Password'));

    // Email validation
    validations.add(ValidationUtils.validateEmail(email, 'Email'));

    // Password validation
    validations.add(ValidationUtils.validateLengthRange(password, 6, 128, 'Password'));

    // Combine all validations
    ValidationResult result = ValidationResult.valid();
    for (final validation in validations) {
      result = result.merge(validation);
    }

    return result;
  }

  @override
  List<Object?> get props => [email, password];
}

class LoginUseCase implements UseCase<AuthToken, LoginParams> {
  final AuthRepository repository;

  LoginUseCase(this.repository);

  @override
  Future<Either<Failure, AuthToken>> call(LoginParams params) async {
    // Validate parameters
    final validation = params.validate();
    if (!validation.isValid) {
      return Left(ValidationFailure(validation.errors));
    }

    return await repository.login(
      email: params.email,
      password: params.password,
    );
  }
}


