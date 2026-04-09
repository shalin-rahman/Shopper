import 'package:flutter_test/flutter_test.dart';
import 'package:shopper_mobile/domain/entities/user.dart';
import 'package:shopper_mobile/domain/entities/cart.dart';
import 'package:shopper_mobile/domain/entities/product.dart';
import 'package:shopper_mobile/domain/entities/order.dart';
import 'package:shopper_mobile/domain/entities/settings.dart';
import 'package:shopper_mobile/domain/usecases/auth/login_usecase.dart';
import 'package:shopper_mobile/domain/usecases/cart/add_to_cart_usecase.dart';
import 'package:shopper_mobile/domain/usecases/orders/create_order_usecase.dart';
import 'package:shopper_mobile/domain/usecases/products/get_products_usecase.dart';
import 'package:shopper_mobile/domain/usecases/settings/update_settings_usecase.dart';
import 'package:shopper_mobile/core/validation/validation.dart';
import 'package:shopper_mobile/core/error/failures.dart';

void main() {
  group('Entity Validation Tests', () {
    test('User validation - valid user passes', () {
      final user = User(
        id: 'user123',
        email: 'test@example.com',
        name: 'John Doe',
        role: 'cashier',
        isActive: true,
        createdAt: DateTime.now().subtract(const Duration(days: 30)),
        updatedAt: DateTime.now(),
      );

      final result = user.validate();
      expect(result.isValid, true);
      expect(result.errors, isEmpty);
    });

    test('User validation - invalid email fails', () {
      final user = User(
        id: 'user123',
        email: 'invalid-email',
        name: 'John Doe',
        role: 'cashier',
        isActive: true,
        createdAt: DateTime.now().subtract(const Duration(days: 30)),
        updatedAt: DateTime.now(),
      );

      final result = user.validate();
      expect(result.isValid, false);
      expect(result.errors, contains('Email must be a valid email address'));
    });

    test('AuthToken validation - valid token passes', () {
      final token = AuthToken(
        accessToken: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c',
        refreshToken: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c',
        expiresAt: DateTime.now().add(const Duration(hours: 1)),
        tokenType: 'Bearer',
      );

      final result = token.validate();
      expect(result.isValid, true);
      expect(result.errors, isEmpty);
    });

    test('AuthToken validation - expired token fails', () {
      final token = AuthToken(
        accessToken: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c',
        refreshToken: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c',
        expiresAt: DateTime.now().subtract(const Duration(hours: 1)),
        tokenType: 'Bearer',
      );

      final result = token.validate();
      expect(result.isValid, false);
      expect(result.errors, contains('Token has already expired'));
    });

    test('Cart validation - empty cart fails', () {
      final cart = Cart(
        id: 'cart123',
        items: [],
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );

      final result = cart.validate();
      expect(result.isValid, false);
      expect(result.errors, contains('Cart must contain at least one item'));
    });

    test('Cart validation - valid cart passes', () {
      final product = Product(
        id: 'prod123',
        name: 'Test Product',
        description: 'Test Description',
        price: 10.0,
        category: ProductCategory(id: 'cat1', name: 'Test Category'),
        images: ['image1.jpg'],
        isActive: true,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );

      final cartItem = CartItem(
        id: 'item123',
        product: product,
        quantity: 2,
        unitPrice: 10.0,
        addedAt: DateTime.now(),
      );

      final cart = Cart(
        id: 'cart123',
        items: [cartItem],
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );

      final result = cart.validate();
      expect(result.isValid, true);
      expect(result.errors, isEmpty);
    });

    test('Order validation - valid order passes', () {
      final orderItem = OrderItem(
        id: 'orderItem123',
        productId: 'prod123',
        productName: 'Test Product',
        quantity: 2,
        unitPrice: 10.0,
      );

      final order = Order(
        id: 'order123',
        orderNumber: 'ORD-000001',
        items: [orderItem],
        subtotal: 20.0,
        total: 20.0,
        status: OrderStatus.pending,
        paymentStatus: PaymentStatus.pending,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );

      final result = order.validate();
      expect(result.isValid, true);
      expect(result.errors, isEmpty);
    });

    test('Settings validation - valid settings pass', () {
      final settings = AppSettings(
        themeMode: ThemeMode.light,
        language: Language.english,
        enableBiometric: false,
        enableNotifications: true,
        enableSound: true,
        enableVibration: true,
        autoSync: true,
        syncIntervalMinutes: 15,
        enableAutoBackup: true,
        backupIntervalDays: 7,
        currencySymbol: '৳',
        decimalPlaces: 2,
      );

      final result = settings.validate();
      expect(result.isValid, true);
      expect(result.errors, isEmpty);
    });
  });

  group('Use Case Validation Tests', () {
    test('LoginParams validation - valid params pass', () {
      final params = LoginParams(
        email: 'test@example.com',
        password: 'password123',
      );

      final result = params.validate();
      expect(result.isValid, true);
      expect(result.errors, isEmpty);
    });

    test('LoginParams validation - invalid email fails', () {
      final params = LoginParams(
        email: 'invalid-email',
        password: 'password123',
      );

      final result = params.validate();
      expect(result.isValid, false);
      expect(result.errors, contains('Email must be a valid email address'));
    });

    test('AddToCartParams validation - valid params pass', () {
      final params = AddToCartParams(
        productId: 'prod123',
        quantity: 2,
        discount: 1.0,
        notes: 'Test notes',
      );

      final result = params.validate();
      expect(result.isValid, true);
      expect(result.errors, isEmpty);
    });

    test('AddToCartParams validation - invalid quantity fails', () {
      final params = AddToCartParams(
        productId: 'prod123',
        quantity: 0,
      );

      final result = params.validate();
      expect(result.isValid, false);
      expect(result.errors, contains('Quantity must be greater than 0'));
    });

    test('GetProductsParams validation - valid params pass', () {
      final params = GetProductsParams(
        limit: 50,
        offset: 0,
        category: 'electronics',
        searchQuery: 'laptop',
      );

      final result = params.validate();
      expect(result.isValid, true);
      expect(result.errors, isEmpty);
    });

    test('GetProductsParams validation - invalid limit fails', () {
      final params = GetProductsParams(
        limit: 2000, // Exceeds max
      );

      final result = params.validate();
      expect(result.isValid, false);
      expect(result.errors, contains('Limit cannot exceed 1000'));
    });
  });

  group('ValidationFailure Tests', () {
    test('ValidationFailure handles multiple errors', () {
      final failure = ValidationFailure(['Error 1', 'Error 2', 'Error 3']);
      expect(failure.message, 'Error 1');
      expect(failure.errors, ['Error 1', 'Error 2', 'Error 3']);
    });

    test('ValidationFailure with single error', () {
      final failure = ValidationFailure(['Single error']);
      expect(failure.message, 'Single error');
      expect(failure.errors, ['Single error']);
    });
  });

  group('ValidationUtils Comprehensive Tests', () {
    test('validateRequired works correctly', () {
      expect(ValidationUtils.validateRequired('test', 'field').isValid, true);
      expect(ValidationUtils.validateRequired('', 'field').isValid, false);
      expect(ValidationUtils.validateRequired(null, 'field').isValid, false);
      expect(ValidationUtils.validateRequired([], 'field').isValid, false);
    });

    test('validateEmail comprehensive tests', () {
      expect(ValidationUtils.validateEmail('test@example.com', 'email').isValid, true);
      expect(ValidationUtils.validateEmail('user.name+tag@example.co.uk', 'email').isValid, true);
      expect(ValidationUtils.validateEmail('invalid-email', 'email').isValid, false);
      expect(ValidationUtils.validateEmail('@example.com', 'email').isValid, false);
      expect(ValidationUtils.validateEmail('test@', 'email').isValid, false);
    });

    test('validatePhone comprehensive tests', () {
      expect(ValidationUtils.validatePhone('+1234567890', 'phone').isValid, true);
      expect(ValidationUtils.validatePhone('123-456-7890', 'phone').isValid, true);
      expect(ValidationUtils.validatePhone('(123) 456-7890', 'phone').isValid, true);
      expect(ValidationUtils.validatePhone('invalid-phone', 'phone').isValid, false);
      expect(ValidationUtils.validatePhone('123', 'phone').isValid, false);
    });

    test('validateLengthRange comprehensive tests', () {
      expect(ValidationUtils.validateLengthRange('test', 1, 10, 'field').isValid, true);
      expect(ValidationUtils.validateLengthRange('a', 1, 10, 'field').isValid, true);
      expect(ValidationUtils.validateLengthRange('this is a very long string', 1, 10, 'field').isValid, false);
      expect(ValidationUtils.validateLengthRange('', 1, 10, 'field').isValid, false);
    });

    test('validatePrice comprehensive tests', () {
      expect(ValidationUtils.validatePrice(10.0, 'price').isValid, true);
      expect(ValidationUtils.validatePrice(0.01, 'price').isValid, true);
      expect(ValidationUtils.validatePrice(999999.99, 'price').isValid, true);
      expect(ValidationUtils.validatePrice(0, 'price').isValid, false);
      expect(ValidationUtils.validatePrice(-1, 'price').isValid, false);
      expect(ValidationUtils.validatePrice(1000000, 'price').isValid, false);
    });

    test('validatePercentage comprehensive tests', () {
      expect(ValidationUtils.validatePercentage(0, 'percentage').isValid, true);
      expect(ValidationUtils.validatePercentage(50, 'percentage').isValid, true);
      expect(ValidationUtils.validatePercentage(100, 'percentage').isValid, true);
      expect(ValidationUtils.validatePercentage(-1, 'percentage').isValid, false);
      expect(ValidationUtils.validatePercentage(101, 'percentage').isValid, false);
    });

    test('validateDateNotInFuture comprehensive tests', () {
      expect(ValidationUtils.validateDateNotInFuture(DateTime.now().subtract(const Duration(days: 1)), 'date').isValid, true);
      expect(ValidationUtils.validateDateNotInFuture(DateTime.now(), 'date').isValid, true);
      expect(ValidationUtils.validateDateNotInFuture(DateTime.now().add(const Duration(days: 1)), 'date').isValid, false);
    });

    test('validateDateNotTooOld comprehensive tests', () {
      expect(ValidationUtils.validateDateNotTooOld(DateTime.now().subtract(const Duration(days: 365)), 2, 'date').isValid, true);
      expect(ValidationUtils.validateDateNotTooOld(DateTime.now().subtract(const Duration(days: 800)), 2, 'date').isValid, false);
    });

    test('validateBarcode comprehensive tests', () {
      expect(ValidationUtils.validateBarcode('123456789012', 'barcode').isValid, true);
      expect(ValidationUtils.validateBarcode('12345678', 'barcode').isValid, true);
      expect(ValidationUtils.validateBarcode('123456789012345678', 'barcode').isValid, true);
      expect(ValidationUtils.validateBarcode('1234567', 'barcode').isValid, false);
      expect(ValidationUtils.validateBarcode('1234567890123456789', 'barcode').isValid, false);
      expect(ValidationUtils.validateBarcode('invalid-barcode', 'barcode').isValid, false);
    });
  });
}