import 'package:dartz/dartz.dart' hide Order;
import '../../core/error/failures.dart';
import '../entities/settings.dart';

abstract class SettingsRepository {
  Future<Either<Failure, AppSettings>> getSettings();

  Future<Either<Failure, void>> updateSettings(AppSettings settings);

  Future<Either<Failure, void>> resetSettings();

  Stream<AppSettings> watchSettings();
}
