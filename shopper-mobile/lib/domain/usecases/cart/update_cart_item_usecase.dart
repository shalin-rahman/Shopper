import 'package:dartz/dartz.dart' hide Order;
import 'package:equatable/equatable.dart';
import '../../../core/error/failures.dart';
import '../../../core/usecase/usecase.dart';
import '../../entities/cart.dart';
import '../../repositories/cart_repository.dart';

class UpdateCartItemParams extends Equatable {
  final String cartItemId;
  final int? quantity;
  final double? discount;
  final String? notes;

  const UpdateCartItemParams({
    required this.cartItemId,
    this.quantity,
    this.discount,
    this.notes,
  });

  @override
  List<Object?> get props => [cartItemId, quantity, discount, notes];
}

class UpdateCartItemUseCase implements UseCase<Cart, UpdateCartItemParams> {
  final CartRepository repository;

  UpdateCartItemUseCase(this.repository);

  @override
  Future<Either<Failure, Cart>> call(UpdateCartItemParams params) async {
    return await repository.updateCartItem(
      cartItemId: params.cartItemId,
      quantity: params.quantity,
      discount: params.discount,
      notes: params.notes,
    );
  }
}
