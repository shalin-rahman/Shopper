import 'package:dartz/dartz.dart' hide Order;
import '../../../core/error/failures.dart';
import '../../../core/usecase/usecase.dart';
import '../../entities/settings.dart';
import '../../repositories/settings_repository.dart';

class UpdateSettingsUseCase implements UseCase<void, AppSettings> {
  final SettingsRepository repository;

  UpdateSettingsUseCase(this.repository);

  @override
  Future<Either<Failure, void>> call(AppSettings params) async {
    return await repository.updateSettings(params);
  }
}
