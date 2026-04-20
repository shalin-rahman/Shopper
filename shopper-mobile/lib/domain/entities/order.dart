import 'package:equatable/equatable.dart';
import 'cart.dart';
import '../../core/validation/validation.dart';

enum OrderStatus {
  pending('pending'),
  confirmed('confirmed'),
  preparing('preparing'),
  ready('ready'),
  completed('completed'),
  cancelled('cancelled'),
  refunded('refunded');

  const OrderStatus(this.value);
  final String value;

  static OrderStatus fromString(String value) {
    return OrderStatus.values.firstWhere(
      (status) => status.value == value,
      orElse: () => OrderStatus.pending,
    );
  }
}

enum PaymentStatus {
  pending('pending'),
  paid('paid'),
  failed('failed'),
  refunded('refunded');

  const PaymentStatus(this.value);
  final String value;

  static PaymentStatus fromString(String value) {
    return PaymentStatus.values.firstWhere(
      (status) => status.value == value,
      orElse: () => PaymentStatus.pending,
    );
  }
}

class OrderItem extends Equatable {
  final String id;
  final String productId;
  final String productName;
  final String? nameBn;
  final int quantity;
  final double unitPrice;
  final double? discount;
  final double? taxAmount;
  final double vatRatePct;
  final double vatAmount;
  final String? notes;

  const OrderItem({
    required this.id,
    required this.productId,
    required this.productName,
    this.nameBn,
    required this.quantity,
    required this.unitPrice,
    this.discount,
    this.taxAmount,
    this.vatRatePct = 0.0,
    this.vatAmount = 0.0,
    this.notes,
  });

  double get subtotal => (unitPrice * quantity) - (discount ?? 0);

  double get totalDiscount => (discount ?? 0) * quantity;

  double get total => subtotal + (taxAmount ?? 0);

  /// Validates the order item data
  ValidationResult validate() {
    final List<ValidationResult> validations = [];

    // Required field validations
    validations.add(ValidationUtils.validateRequired(id, 'Order item ID'));
    validations.add(ValidationUtils.validateRequired(productId, 'Product ID'));
    validations.add(ValidationUtils.validateRequired(productName, 'Product name'));
    validations.add(ValidationUtils.validateRequired(quantity, 'Quantity'));
    validations.add(ValidationUtils.validateRequired(unitPrice, 'Unit price'));

    // Length validations
    validations.add(ValidationUtils.validateLengthRange(productName, 1, 200, 'Product name'));

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

    // Tax validation
    if (taxAmount != null) {
      if (taxAmount! < 0) {
        validations.add(ValidationResult.invalid(['Tax amount cannot be negative']));
      }
      if (taxAmount! > total * 0.5) {
        validations.add(ValidationResult.invalid(['Tax amount cannot exceed 50% of total']));
      }
    }

    // Notes validation
    if (notes != null) {
      validations.add(ValidationUtils.validateLengthRange(notes!, 0, 500, 'Notes'));
    }

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
  List<Object?> get props => [
        id,
        productId,
        productName,
        quantity,
        unitPrice,
        discount,
        taxAmount,
        notes,
      ];
}

class Order extends Equatable {
  final String id;
  final String orderNumber;
  final List<OrderItem> items;
  final double subtotal;
  final double? discount;
  final double? taxAmount;
  final double total;
  final OrderStatus status;
  final PaymentStatus paymentStatus;
  final String? customerName;
  final String? customerPhone;
  final String? notes;
  final bool isSynced;
  final String? serverInvoiceId;
  final DateTime createdAt;
  final DateTime updatedAt;

  const Order({
    required this.id,
    required this.orderNumber,
    required this.items,
    required this.subtotal,
    this.discount,
    this.taxAmount,
    required this.total,
    required this.status,
    required this.paymentStatus,
    this.customerName,
    this.customerPhone,
    this.notes,
    this.isSynced = false,
    this.serverInvoiceId,
    required this.createdAt,
    required this.updatedAt,
  });

  int get totalItems => items.fold(0, (sum, item) => sum + item.quantity);

  bool get isCompleted => status == OrderStatus.completed;

  bool get isPaid => paymentStatus == PaymentStatus.paid;

  /// Validates the order data
  ValidationResult validate() {
    final List<ValidationResult> validations = [];

    // Required field validations
    validations.add(ValidationUtils.validateRequired(id, 'Order ID'));
    validations.add(ValidationUtils.validateRequired(orderNumber, 'Order number'));
    validations.add(ValidationUtils.validateRequired(items, 'Items'));
    validations.add(ValidationUtils.validateRequired(subtotal, 'Subtotal'));
    validations.add(ValidationUtils.validateRequired(total, 'Total'));
    validations.add(ValidationUtils.validateRequired(status, 'Status'));
    validations.add(ValidationUtils.validateRequired(paymentStatus, 'Payment status'));
    validations.add(ValidationUtils.validateRequired(createdAt, 'Created at'));
    validations.add(ValidationUtils.validateRequired(updatedAt, 'Updated at'));

    // Order number validation
    final orderNumberRegex = RegExp(r'^ORD-\d{6}$');
    if (!orderNumberRegex.hasMatch(orderNumber)) {
      validations.add(ValidationResult.invalid(['Order number must be in format ORD-XXXXXX']));
    }

    // Items validation
    if (items.isEmpty) {
      validations.add(ValidationResult.invalid(['Order must contain at least one item']));
    }

    // Validate each order item
    for (int i = 0; i < items.length; i++) {
      final itemValidation = items[i].validate();
      if (!itemValidation.isValid) {
        validations.add(ValidationResult.invalid(
          itemValidation.errors.map((error) => 'Item ${i + 1}: $error').toList()
        ));
      }
    }

    // Price validations
    if (subtotal < 0) {
      validations.add(ValidationResult.invalid(['Subtotal cannot be negative']));
    }
    if (total < 0) {
      validations.add(ValidationResult.invalid(['Total cannot be negative']));
    }
    if (total > 999999.99) {
      validations.add(ValidationResult.invalid(['Order total cannot exceed 999,999.99']));
    }

    // Discount validation
    if (discount != null) {
      if (discount! < 0) {
        validations.add(ValidationResult.invalid(['Discount cannot be negative']));
      }
      if (discount! > subtotal) {
        validations.add(ValidationResult.invalid(['Discount cannot exceed subtotal']));
      }
    }

    // Tax validation
    if (taxAmount != null) {
      if (taxAmount! < 0) {
        validations.add(ValidationResult.invalid(['Tax amount cannot be negative']));
      }
      if (taxAmount! > total * 0.5) {
        validations.add(ValidationResult.invalid(['Tax amount cannot exceed 50% of total']));
      }
    }

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

    // Date validations
    validations.add(ValidationUtils.validateDateNotInFuture(createdAt, 'Created date'));
    validations.add(ValidationUtils.validateDateNotInFuture(updatedAt, 'Updated date'));
    validations.add(ValidationUtils.validateDateNotTooOld(createdAt, 365, 'Created date'));
    validations.add(ValidationUtils.validateDateNotTooOld(updatedAt, 365, 'Updated date'));

    // Business logic validations
    if (totalItems > 999) {
      validations.add(ValidationResult.invalid(['Order cannot contain more than 999 total items']));
    }

    // Check for duplicate products
    final productIds = items.map((item) => item.productId).toSet();
    if (productIds.length != items.length) {
      validations.add(ValidationResult.invalid(['Order cannot contain duplicate products']));
    }

    // Status transition validations
    if (paymentStatus == PaymentStatus.paid && status == OrderStatus.cancelled) {
      validations.add(ValidationResult.invalid(['Cannot cancel a paid order']));
    }

    // Combine all validations
    ValidationResult result = ValidationResult.valid();
    for (final validation in validations) {
      result = result.merge(validation);
    }

    return result;
  }

  @override
  List<Object?> get props => [
        id,
        orderNumber,
        items,
        subtotal,
        discount,
        taxAmount,
        total,
        status,
        paymentStatus,
        customerName,
        customerPhone,
        notes,
        createdAt,
        updatedAt,
      ];
}

class OrderSummary extends Equatable {
  final int totalOrders;
  final double totalRevenue;
  final int pendingOrders;
  final int completedOrders;
  final DateTime date;

  const OrderSummary({
    required this.totalOrders,
    required this.totalRevenue,
    required this.pendingOrders,
    required this.completedOrders,
    required this.date,
  });

  /// Validates the order summary data
  ValidationResult validate() {
    final List<ValidationResult> validations = [];

    // Required field validations
    validations.add(ValidationUtils.validateRequired(totalOrders, 'Total orders'));
    validations.add(ValidationUtils.validateRequired(totalRevenue, 'Total revenue'));
    validations.add(ValidationUtils.validateRequired(pendingOrders, 'Pending orders'));
    validations.add(ValidationUtils.validateRequired(completedOrders, 'Completed orders'));
    validations.add(ValidationUtils.validateRequired(date, 'Date'));

    // Count validations
    if (totalOrders < 0) {
      validations.add(ValidationResult.invalid(['Total orders cannot be negative']));
    }
    if (pendingOrders < 0) {
      validations.add(ValidationResult.invalid(['Pending orders cannot be negative']));
    }
    if (completedOrders < 0) {
      validations.add(ValidationResult.invalid(['Completed orders cannot be negative']));
    }

    // Revenue validation
    if (totalRevenue < 0) {
      validations.add(ValidationResult.invalid(['Total revenue cannot be negative']));
    }
    if (totalRevenue > 999999999.99) {
      validations.add(ValidationResult.invalid(['Total revenue cannot exceed 999,999,999.99']));
    }

    // Date validation
    validations.add(ValidationUtils.validateDateNotInFuture(date, 'Summary date'));

    // Business logic validations
    if (pendingOrders + completedOrders > totalOrders) {
      validations.add(ValidationResult.invalid(['Pending + completed orders cannot exceed total orders']));
    }

    // Combine all validations
    ValidationResult result = ValidationResult.valid();
    for (final validation in validations) {
      result = result.merge(validation);
    }

    return result;
  }

  @override
  List<Object?> get props => [totalOrders, totalRevenue, pendingOrders, completedOrders, date];
}