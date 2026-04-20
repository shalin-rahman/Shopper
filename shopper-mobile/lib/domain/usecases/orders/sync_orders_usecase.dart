import 'package:dartz/dartz.dart';
import '../../../../core/error/failures.dart';
import '../../../../core/usecases/usecase.dart';
import '../../repositories/order_repository.dart';

class SyncOrdersUseCase implements UseCase<void, NoParams> {
  final OrderRepository repository;

  SyncOrdersUseCase(this.repository);

  @override
  Future<Either<Failure, void>> call(NoParams params) async {
    return await repository.syncOrders();
  }
}
