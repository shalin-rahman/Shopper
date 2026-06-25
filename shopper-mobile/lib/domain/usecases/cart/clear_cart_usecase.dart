import 'package:dartz/dartz.dart' hide Order;
import '../../../core/error/failures.dart';
import '../../../core/usecase/usecase.dart';
import '../../entities/cart.dart';
import '../../repositories/cart_repository.dart';

class ClearCartUseCase implements UseCase<Cart, NoParams> {
  final CartRepository repository;

  ClearCartUseCase(this.repository);

  @override
  Future<Either<Failure, Cart>> call(NoParams params) async {
    return await repository.clearCart();
  }
}
