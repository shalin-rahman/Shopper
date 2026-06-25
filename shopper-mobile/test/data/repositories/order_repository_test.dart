import 'package:flutter_test/flutter_test.dart';
import 'package:shopper_mobile/data/repositories/order_repository_impl.dart';
import 'package:shopper_mobile/data/sources/local/database/app_database.dart';
import 'package:shopper_mobile/domain/entities/cart.dart' as cart_entity;
import 'package:shopper_mobile/domain/entities/order.dart' as order_entity;
import 'package:shopper_mobile/domain/entities/product.dart' as product_entity;

import '../../helpers/test_database.dart';
import '../../helpers/mocks.dart';

void main() {
  late AppDatabase database;
  late MockApiClient mockApiClient;
  late OrderRepositoryImpl repository;

  setUp(() {
    database = createTestDatabase();
    mockApiClient = MockApiClient();
    repository = OrderRepositoryImpl(database, mockApiClient);
  });

  tearDown(() async {
    await database.close();
  });

  group('OrderRepositoryImpl Local Operations', () {
    test('createOrder inserts order and items into database', () async {
      final cartItem = cart_entity.CartItem(
        id: 'ci1',
        product: product_entity.Product(
          id: 'p1',
          nameEn: 'Sample Item',
          price: 100.0,
          stockQuantity: 10,
          isActive: true,
          isTaxable: false,
          createdAt: DateTime.now(),
          updatedAt: DateTime.now(),
        ),
        quantity: 2,
        unitPrice: 100.0,
        addedAt: DateTime.now(),
      );

      final cart = cart_entity.Cart(id: 'c1', items: [cartItem], createdAt: DateTime.now(), updatedAt: DateTime.now());

      final result = await repository.createOrder(
        cart: cart,
        paymentMethod: 'Cash',
        amountPaid: 200.0,
      );

      result.fold(
        (failure) => fail('Should not fail: $failure'),
        (order) async {
          expect(order.total, 200.0);
          expect(order.status, order_entity.OrderStatus.completed);

          // Verify DB
          final dbOrders = await database.select(database.orders).get();
          expect(dbOrders.length, 1);
          expect(dbOrders.first.total, 200.0);

          final dbOrderItems = await database.select(database.orderItems).get();
          expect(dbOrderItems.length, 1);
          expect(dbOrderItems.first.productId, 'p1');
        },
      );
    });
  });
}
