import 'package:equatable/equatable.dart';
import '../../core/validation/validation.dart';

class User extends Equatable {
  final String id;
  final String email;
  final String name;
  final String? phone;
  final String role;
  final bool isActive;
  final DateTime createdAt;
  final DateTime updatedAt;

  const User({
    required this.id,
    required this.email,
    required this.name,
    this.phone,
    required this.role,
    required this.isActive,
    required this.createdAt,
    required this.updatedAt,
  });

  /// Validates the user data
  ValidationResult validate() {
    final List<ValidationResult> validations = [];

    // Required field validations
    validations.add(ValidationUtils.validateRequired(id, 'User ID'));
    validations.add(ValidationUtils.validateRequired(email, 'Email'));
    validations.add(ValidationUtils.validateRequired(name, 'Name'));
    validations.add(ValidationUtils.validateRequired(role, 'Role'));

    // Email validation
    validations.add(ValidationUtils.validateEmail(email, 'Email'));

    // Length validations
    validations.add(ValidationUtils.validateLengthRange(name, 1, 100, 'Name'));
    validations.add(ValidationUtils.validateLengthRange(role, 1, 50, 'Role'));

    if (phone != null) {
      validations.add(ValidationUtils.validatePhone(phone!, 'Phone'));
    }

    // Date validations
    validations.add(ValidationUtils.validateDateNotInFuture(createdAt, 'Created date'));
    validations.add(ValidationUtils.validateDateNotInFuture(updatedAt, 'Updated date'));
    validations.add(ValidationUtils.validateDateNotTooOld(createdAt, 10, 'Created date'));
    validations.add(ValidationUtils.validateDateNotTooOld(updatedAt, 10, 'Updated date'));

    // Business logic validations
    final allowedRoles = ['admin', 'manager', 'cashier', 'staff'];
    if (!allowedRoles.contains(role.toLowerCase())) {
      validations.add(ValidationResult.invalid(['Role must be one of: ${allowedRoles.join(', ')}']));
    }

    // Combine all validations
    ValidationResult result = ValidationResult.valid();
    for (final validation in validations) {
      result = result.merge(validation);
    }

    return result;
  }

  @override
  List<Object?> get props => [id, email, name, phone, role, isActive, createdAt, updatedAt];
}

// Duplicate AuthToken class removed; using AuthToken from 'auth_token.dart'
