import 'package:dartz/dartz.dart';
import 'package:equatable/equatable.dart';
import '../../../core/error/failures.dart';
import '../../../core/usecase/usecase.dart';
import '../../../core/validation/validation.dart';
import '../../entities/cart.dart';
import '../../repositories/cart_repository.dart';

class AddToCartParams extends Equatable {
  final String productId;
  final int quantity;
  final double? discount;
  final String? notes;

  const AddToCartParams({
    required this.productId,
    required this.quantity,
    this.discount,
    this.notes,
  });

  /// Validates the add to cart parameters
  ValidationResult validate() {
    final List<ValidationResult> validations = [];

    // Required field validations
    validations.add(ValidationUtils.validateRequired(productId, 'Product ID'));
    validations.add(ValidationUtils.validateRequired(quantity, 'Quantity'));

    // Quantity validation
    if (quantity <= 0) {
      validations.add(ValidationResult.invalid(['Quantity must be greater than 0']));
    }
    if (quantity > 9999) {
      validations.add(ValidationResult.invalid(['Quantity cannot exceed 9999']));
    }

    // Discount validation
    if (discount != null) {
      if (discount! < 0) {
        validations.add(ValidationResult.invalid(['Discount cannot be negative']));
      }
      if (discount! > 999999.99) {
        validations.add(ValidationResult.invalid(['Discount cannot exceed 999,999.99']));
      }
    }

    // Notes validation
    if (notes != null) {
      validations.add(ValidationUtils.validateLengthRange(notes!, 0, 500, 'Notes'));
    }

    // Combine all validations
    ValidationResult result = ValidationResult.valid();
    for (final validation in validations) {
      result = result.merge(validation);
    }

    return result;
  }

  @override
  List<Object?> get props => [productId, quantity, discount, notes];
}

class AddToCartUseCase implements UseCase<Cart, AddToCartParams> {
  final CartRepository repository;

  AddToCartUseCase(this.repository);

  @override
  Future<Either<Failure, Cart>> call(AddToCartParams params) async {
    // Validate parameters
    final validation = params.validate();
    if (!validation.isValid) {
      return Left(ValidationFailure(validation.errors));
    }

    return await repository.addToCart(
      productId: params.productId,
      quantity: params.quantity,
      discount: params.discount,
      notes: params.notes,
    );
  }
}

class GetCartUseCase implements UseCase<Cart, NoParams> {
  final CartRepository repository;

  GetCartUseCase(this.repository);

  @override
  Future<Either<Failure, Cart>> call(NoParams params) async {
    return await repository.getCart();
  }
}

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

class ClearCartUseCase implements UseCase<Cart, NoParams> {
  final CartRepository repository;

  ClearCartUseCase(this.repository);

  @override
  Future<Either<Failure, Cart>> call(NoParams params) async {
    return await repository.clearCart();
  }
}