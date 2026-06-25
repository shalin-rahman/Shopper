import 'package:equatable/equatable.dart';

abstract class Failure extends Equatable {
  final String message;
  final List<String>? errors;
  final String? code;

  const Failure(this.message, {this.errors, this.code});

  @override
  List<Object?> get props => [message, errors, code];
}

class ServerFailure extends Failure {
  const ServerFailure(super.message, {super.code});
}

class NetworkFailure extends Failure {
  const NetworkFailure(super.message, {super.code});
}

class CacheFailure extends Failure {
  const CacheFailure(super.message, {super.code});
}

class AuthFailure extends Failure {
  const AuthFailure(super.message, {super.code});
}

class ValidationFailure extends Failure {
  ValidationFailure(List<String> errors, {String? code})
      : super(errors.isNotEmpty ? errors.first : 'Validation failed', errors: errors, code: code);
}

class BusinessLogicFailure extends Failure {
  const BusinessLogicFailure(super.message, {super.code});
}

class DatabaseFailure extends Failure {
  const DatabaseFailure(super.message, {super.code});
}

class UnknownFailure extends Failure {
  const UnknownFailure(super.message, {super.code});
}
