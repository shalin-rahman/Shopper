import 'package:dartz/dartz.dart' hide Order;
import '../../../core/error/failures.dart';
import '../../../core/usecase/usecase.dart';
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


