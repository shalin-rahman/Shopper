import 'package:dartz/dartz.dart';
import 'package:equatable/equatable.dart';
import '../../../core/error/failures.dart';
import '../../../core/usecase/usecase.dart';
import '../../../core/validation/validation.dart';
import '../../entities/settings.dart';
import '../../repositories/settings_repository.dart';

class GetSettingsUseCase implements UseCase<AppSettings, NoParams> {
  final SettingsRepository repository;

  GetSettingsUseCase(this.repository);

  @override
  Future<Either<Failure, AppSettings>> call(NoParams params) async {
    return await repository.getSettings();
  }
}

class UpdateSettingsParams extends Equatable {
  final AppSettings settings;

  const UpdateSettingsParams({required this.settings});

  /// Validates the update settings parameters
  ValidationResult validate() {
    final List<ValidationResult> validations = [];

    // Required field validations
    validations.add(ValidationUtils.validateRequired(settings, 'Settings'));

    // Settings validation
    validations.add(settings.validate());

    // Combine all validations
    ValidationResult result = ValidationResult.valid();
    for (final validation in validations) {
      result = result.merge(validation);
    }

    return result;
  }

  @override
  List<Object?> get props => [settings];
}

class UpdateSettingsUseCase implements UseCase<void, UpdateSettingsParams> {
  final SettingsRepository repository;

  UpdateSettingsUseCase(this.repository);

  @override
  Future<Either<Failure, void>> call(UpdateSettingsParams params) async {
    // Validate parameters
    final validation = params.validate();
    if (!validation.isValid) {
      return Left(ValidationFailure(validation.errors));
    }

    return await repository.updateSettings(params.settings);
  }
}