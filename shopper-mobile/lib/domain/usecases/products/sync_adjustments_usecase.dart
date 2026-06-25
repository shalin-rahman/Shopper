import 'package:dartz/dartz.dart' hide Order;
import '../../../../core/error/failures.dart';
import '../../../../core/usecase/usecase.dart';
import '../../repositories/product_repository.dart';

class SyncAdjustmentsUseCase implements UseCase<void, NoParams> {
  final ProductRepository repository;

  SyncAdjustmentsUseCase(this.repository);

  @override
  Future<Either<Failure, void>> call(NoParams params) async {
    return await repository.syncAdjustments();
  }
}
