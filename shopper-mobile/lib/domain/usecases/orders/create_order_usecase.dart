import 'package:dartz/dartz.dart' hide Order;
import 'package:equatable/equatable.dart';
import '../../../core/error/failures.dart';
import '../../../core/usecase/usecase.dart';
import '../../../core/validation/validation.dart';
import '../../entities/order.dart';
import '../../entities/cart.dart';
import '../../repositories/order_repository.dart';

class CreateOrderParams extends Equatable {
  final Cart cart;
  final String? customerName;
  final String? customerPhone;
  final String? notes;
  final String paymentMethod;
  final double amountPaid;

  const CreateOrderParams({
    required this.cart,
    this.customerName,
    this.customerPhone,
    this.notes,
    this.paymentMethod = 'cash',
    this.amountPaid = 0,
  });

  /// Validates the create order parameters
  ValidationResult validate() {
    final List<ValidationResult> validations = [];

    // Required field validations
    validations.add(ValidationUtils.validateRequired(cart.items.isEmpty ? '' : 'items', 'Cart'));

    // Cart validation
    validations.add(cart.validate());

    // Customer info validation
    if (customerName != null) {
      validations.add(ValidationUtils.validateLengthRange(customerName!, 1, 100, 'Customer name'));
    }
    if (customerPhone != null) {
      validations.add(ValidationUtils.validatePhone(customerPhone!, 'Customer phone'));
    }

    // Notes validation
    if (notes != null) {
      validations.add(ValidationUtils.validateLengthRange(notes!, 0, 1000, 'Notes'));
    }

    // Business logic validations
    if (cart.isEmpty) {
      validations.add(ValidationResult.invalid(['Cannot create order with empty cart']));
    }

    // Combine all validations
    ValidationResult result = ValidationResult.valid();
    for (final validation in validations) {
      result = result.merge(validation);
    }

    return result;
  }

  @override
  List<Object?> get props => [cart, customerName, customerPhone, notes, paymentMethod, amountPaid];
}

class CreateOrderUseCase implements UseCase<Order, CreateOrderParams> {
  final OrderRepository repository;

  CreateOrderUseCase(this.repository);

  @override
  Future<Either<Failure, Order>> call(CreateOrderParams params) async {
    // Validate parameters
    final validation = params.validate();
    if (!validation.isValid) {
      return Left(ValidationFailure(validation.errors));
    }

    return await repository.createOrder(
      cart: params.cart,
      customerName: params.customerName,
      customerPhone: params.customerPhone,
      notes: params.notes,
      paymentMethod: params.paymentMethod,
      amountPaid: params.amountPaid,
    );
  }
}


