import 'package:dartz/dartz.dart' hide Order;
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
    validations.add(ValidationUtils.validateRequired(quantity.toString(), 'Quantity'));

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



