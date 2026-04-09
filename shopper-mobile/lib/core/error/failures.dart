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
  const ServerFailure(String message, {String? code}) : super(message, code: code);
}

class NetworkFailure extends Failure {
  const NetworkFailure(String message, {String? code}) : super(message, code: code);
}

class CacheFailure extends Failure {
  const CacheFailure(String message, {String? code}) : super(message, code: code);
}

class AuthFailure extends Failure {
  const AuthFailure(String message, {String? code}) : super(message, code: code);
}

class ValidationFailure extends Failure {
  const ValidationFailure(List<String> errors, {String? code})
      : super(errors.isNotEmpty ? errors.first : 'Validation failed', errors: errors, code: code);
}

class BusinessLogicFailure extends Failure {
  const BusinessLogicFailure(String message, {String? code}) : super(message, code: code);
}

class UnknownFailure extends Failure {
  const UnknownFailure(String message, {String? code}) : super(message, code: code);
}