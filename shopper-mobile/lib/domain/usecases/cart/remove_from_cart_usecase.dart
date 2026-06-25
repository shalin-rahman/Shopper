import 'package:dartz/dartz.dart' hide Order;
import 'package:equatable/equatable.dart';
import '../../../core/error/failures.dart';
import '../../../core/usecase/usecase.dart';
import '../../entities/cart.dart';
import '../../repositories/cart_repository.dart';

class RemoveFromCartParams extends Equatable {
  final String cartItemId;

  const RemoveFromCartParams({required this.cartItemId});

  @override
  List<Object?> get props => [cartItemId];
}

class RemoveFromCartUseCase implements UseCase<Cart, RemoveFromCartParams> {
  final CartRepository repository;

  RemoveFromCartUseCase(this.repository);

  @override
  Future<Either<Failure, Cart>> call(RemoveFromCartParams params) async {
    return await repository.removeFromCart(params.cartItemId);
  }
}
