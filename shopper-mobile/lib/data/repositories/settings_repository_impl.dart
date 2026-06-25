import 'package:dartz/dartz.dart' hide Order;
import '../../core/error/failures.dart';
import '../../domain/entities/settings.dart';
import '../../domain/repositories/settings_repository.dart';

import '../../data/sources/local/preferences/app_preferences.dart';

class SettingsRepositoryImpl implements SettingsRepository {
  final AppPreferences preferences;
  SettingsRepositoryImpl(this.preferences);

  @override
  Future<Either<Failure, AppSettings>> getSettings() async {
    // Return default settings for now
    return const Right(AppSettings());
  }

  @override
  Future<Either<Failure, void>> updateSettings(AppSettings settings) async {
    // Stub: pretend update succeeds
    return const Right(null);
  }

  @override
  Future<Either<Failure, void>> resetSettings() async {
    // Stub: reset to default settings
    return const Right(null);
  }

  @override
  Stream<AppSettings> watchSettings() => const Stream.empty();
}
