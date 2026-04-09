import 'package:equatable/equatable.dart';
import 'product.dart';
import '../../core/validation/validation.dart';

class CartItem extends Equatable {
  final String id;
  final Product product;
  final int quantity;
  final double unitPrice;
  final double? discount;
  final String? notes;
  final DateTime addedAt;

  const CartItem({
    required this.id,
    required this.product,
    required this.quantity,
    required this.unitPrice,
    this.discount,
    this.notes,
    required this.addedAt,
  });

  double get subtotal => (unitPrice * quantity) - (discount ?? 0);

  double get totalDiscount => (discount ?? 0) * quantity;

  CartItem copyWith({
    String? id,
    Product? product,
    int? quantity,
    double? unitPrice,
    double? discount,
    String? notes,
    DateTime? addedAt,
  }) {
    return CartItem(
      id: id ?? this.id,
      product: product ?? this.product,
      quantity: quantity ?? this.quantity,
      unitPrice: unitPrice ?? this.unitPrice,
      discount: discount ?? this.discount,
      notes: notes ?? this.notes,
      addedAt: addedAt ?? this.addedAt,
    );
  }

  /// Validates the cart item data
  ValidationResult validate() {
    final List<ValidationResult> validations = [];

    // Required field validations
    validations.add(ValidationUtils.validateRequired(id, 'Cart item ID'));
    validations.add(ValidationUtils.validateRequired(product, 'Product'));
    validations.add(ValidationUtils.validateRequired(quantity, 'Quantity'));
    validations.add(ValidationUtils.validateRequired(unitPrice, 'Unit price'));
    validations.add(ValidationUtils.validateRequired(addedAt, 'Added at'));

    // Product validation
    validations.add(product.validate());

    // Quantity validation
    if (quantity <= 0) {
      validations.add(ValidationResult.invalid(['Quantity must be greater than 0']));
    }
    if (quantity > 9999) {
      validations.add(ValidationResult.invalid(['Quantity cannot exceed 9999']));
    }

    // Price validation
    if (unitPrice < 0) {
      validations.add(ValidationResult.invalid(['Unit price cannot be negative']));
    }
    if (unitPrice > 999999.99) {
      validations.add(ValidationResult.invalid(['Unit price cannot exceed 999,999.99']));
    }

    // Discount validation
    if (discount != null) {
      if (discount! < 0) {
        validations.add(ValidationResult.invalid(['Discount cannot be negative']));
      }
      if (discount! > unitPrice) {
        validations.add(ValidationResult.invalid(['Discount cannot exceed unit price']));
      }
    }

    // Notes validation
    if (notes != null) {
      validations.add(ValidationUtils.validateLengthRange(notes!, 0, 500, 'Notes'));
    }

    // Date validation
    validations.add(ValidationUtils.validateDateNotInFuture(addedAt, 'Added date'));

    // Business logic validations
    if (discount != null && discount! > 0 && quantity > 100) {
      validations.add(ValidationResult.invalid(['Bulk discounts require manager approval for quantities over 100']));
    }

    // Combine all validations
    ValidationResult result = ValidationResult.valid();
    for (final validation in validations) {
      result = result.merge(validation);
    }

    return result;
  }

  @override
  List<Object?> get props => [id, product, quantity, unitPrice, discount, notes, addedAt];
}

class Cart extends Equatable {
  final String id;
  final List<CartItem> items;
  final DateTime createdAt;
  final DateTime updatedAt;

  const Cart({
    required this.id,
    required this.items,
    required this.createdAt,
    required this.updatedAt,
  });

  double get subtotal => items.fold(0, (sum, item) => sum + item.subtotal);

  double get totalDiscount => items.fold(0, (sum, item) => sum + item.totalDiscount);

  double get total => subtotal;

  int get totalItems => items.fold(0, (sum, item) => sum + item.quantity);

  bool get isEmpty => items.isEmpty;

  Cart copyWith({
    String? id,
    List<CartItem>? items,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return Cart(
      id: id ?? this.id,
      items: items ?? this.items,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  /// Validates the cart data
  ValidationResult validate() {
    final List<ValidationResult> validations = [];

    // Required field validations
    validations.add(ValidationUtils.validateRequired(id, 'Cart ID'));
    validations.add(ValidationUtils.validateRequired(items, 'Items'));
    validations.add(ValidationUtils.validateRequired(createdAt, 'Created at'));
    validations.add(ValidationUtils.validateRequired(updatedAt, 'Updated at'));

    // Items validation
    if (items.isEmpty) {
      validations.add(ValidationResult.invalid(['Cart must contain at least one item']));
    }

    // Validate each cart item
    for (int i = 0; i < items.length; i++) {
      final itemValidation = items[i].validate();
      if (!itemValidation.isValid) {
        validations.add(ValidationResult.invalid(
          itemValidation.errors.map((error) => 'Item ${i + 1}: $error').toList()
        ));
      }
    }

    // Date validations
    validations.add(ValidationUtils.validateDateNotInFuture(createdAt, 'Created date'));
    validations.add(ValidationUtils.validateDateNotInFuture(updatedAt, 'Updated date'));
    validations.add(ValidationUtils.validateDateNotTooOld(createdAt, 30, 'Created date'));
    validations.add(ValidationUtils.validateDateNotTooOld(updatedAt, 30, 'Updated date'));

    // Business logic validations
    if (total > 999999.99) {
      validations.add(ValidationResult.invalid(['Cart total cannot exceed 999,999.99']));
    }

    if (totalItems > 999) {
      validations.add(ValidationResult.invalid(['Cart cannot contain more than 999 total items']));
    }

    // Check for duplicate products
    final productIds = items.map((item) => item.product.id).toSet();
    if (productIds.length != items.length) {
      validations.add(ValidationResult.invalid(['Cart cannot contain duplicate products']));
    }

    // Combine all validations
    ValidationResult result = ValidationResult.valid();
    for (final validation in validations) {
      result = result.merge(validation);
    }

    return result;
  }

  @override
  List<Object?> get props => [id, items, createdAt, updatedAt];
}