import 'package:drift/native.dart';
import 'package:shopper_mobile/data/sources/local/database/app_database.dart';

/// Helper method to create an in-memory test database for testing
AppDatabase createTestDatabase() {
  return AppDatabase.forTesting(NativeDatabase.memory());
}
