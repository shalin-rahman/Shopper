import 'dart:math';
import 'package:dartz/dartz.dart';
import 'package:drift/drift.dart';
import '../../core/error/failures.dart';
import '../../domain/entities/cart.dart';
import '../../domain/entities/order.dart' as entity;
import '../../domain/repositories/order_repository.dart';
import '../sources/local/database/app_database.dart';
import '../sources/remote/api_client.dart';

class OrderRepositoryImpl implements OrderRepository {
  final AppDatabase database;
  final ApiClient remoteDataSource;

  OrderRepositoryImpl(this.database, this.remoteDataSource);

  String _generateId() {
    return '${DateTime.now().millisecondsSinceEpoch}_${Random().nextInt(999)}';
  }

  @override
  Future<Either<Failure, entity.Order>> createOrder({
    required Cart cart,
    String? customerName,
    String? customerPhone,
    String? notes,
  }) async {
    try {
      final result = await database.transaction(() async {
        final orderId = _generateId();
        final orderNumber = 'ORD-${DateTime.now().millisecondsSinceEpoch.toString().substring(7)}';
        
        final now = DateTime.now();

        // 1. Create Order entry
        final orderCompanion = OrdersCompanion.insert(
          id: orderId,
          orderNumber: orderNumber,
          subtotal: cart.subtotal,
          total: cart.total,
          discount: Value(cart.discount),
          taxAmount: Value(cart.taxAmount),
          status: entity.OrderStatus.completed.value,
          paymentStatus: entity.PaymentStatus.pending.value,
          customerName: Value(customerName),
          customerPhone: Value(customerPhone),
          notes: Value(notes),
          isSynced: const Value(false),
          createdAt: now,
          updatedAt: now,
        );
        await database.insertOrder(orderCompanion);

        // 2. Process Items and Atomic Stock Deduction
        final List<entity.OrderItem> createdItems = [];
        for (final item in cart.items) {
          final itemId = _generateId();
          
          await database.insertOrderItem(OrderItemsCompanion.insert(
            id: itemId,
            orderId: orderId,
            productId: item.productId,
            productName: item.productName,
            quantity: item.quantity,
            unitPrice: item.unitPrice,
            discount: Value(item.discount),
            taxAmount: Value(item.taxAmount),
            vatRatePct: Value(item.vatRatePct),
            vatAmount: Value(item.vatAmount),
            notes: Value(item.notes),
          ));

          // Real Transaction Core: Local Stock Deduction
          final product = await database.getProductById(item.productId);
          if (product != null) {
            await database.updateProduct(product.toCompanion(false).copyWith(
              stockQuantity: Value(product.stockQuantity - item.quantity),
              updatedAt: Value(now),
            ));
          }

          createdItems.add(entity.OrderItem(
            id: itemId,
            productId: item.productId,
            productName: item.productName,
            quantity: item.quantity,
            unitPrice: item.unitPrice,
            discount: item.discount,
            taxAmount: item.taxAmount,
            vatRatePct: item.vatRatePct,
            vatAmount: item.vatAmount,
            notes: item.notes,
          ));
        }

        // 3. Clear Local Cart
        await database.clearCart();

        return entity.Order(
          id: orderId,
          orderNumber: orderNumber,
          items: createdItems,
          subtotal: cart.subtotal,
          total: cart.total,
          discount: cart.discount,
          taxAmount: cart.taxAmount,
          status: entity.OrderStatus.completed,
          paymentStatus: entity.PaymentStatus.pending,
          customerName: customerName,
          customerPhone: customerPhone,
          notes: notes,
          createdAt: now,
          updatedAt: now,
          isSynced: false,
        );
      });
      
      return Right(result);
    } catch (e) {
      return Left(BusinessLogicFailure('Checkout failed: ${e.toString()}'));
    }
  }

  @override
  Future<Either<Failure, entity.Order>> getOrderById(String id) async {
    try {
      final order = await database.getOrderById(id);
      if (order == null) return const Left(BusinessLogicFailure('Order not found'));
      
      final dbItems = await database.getOrderItems(id);
      final items = dbItems.map((i) => entity.OrderItem(
        id: i.id,
        productId: i.productId,
        productName: i.productName,
        quantity: i.quantity,
        unitPrice: i.unitPrice,
        discount: i.discount,
        taxAmount: i.taxAmount,
        vatRatePct: i.vatRatePct,
        vatAmount: i.vatAmount,
        notes: i.notes,
      )).toList();

      return Right(entity.Order(
        id: order.id,
        orderNumber: order.orderNumber,
        items: items,
        subtotal: order.subtotal,
        total: order.total,
        discount: order.discount,
        taxAmount: order.taxAmount,
        status: entity.OrderStatus.fromString(order.status),
        paymentStatus: entity.PaymentStatus.fromString(order.paymentStatus),
        customerName: order.customerName,
        customerPhone: order.customerPhone,
        notes: order.notes,
        isSynced: order.isSynced,
        serverInvoiceId: order.serverInvoiceId,
        createdAt: order.createdAt,
        updatedAt: order.updatedAt,
      ));
    } catch (e) {
      return Left(BusinessLogicFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<entity.Order>>> getOrders({int? limit, int? offset, entity.OrderStatus? status, DateTime? startDate, DateTime? endDate}) async {
     final dbOrders = await database.getAllOrders();
     // Simplified implementation for now
     return Right([]);
  }

  @override
  Future<Either<Failure, entity.Order>> updateOrderStatus({required String orderId, required entity.OrderStatus status}) async {
    return const Left(BusinessLogicFailure('Not implemented yet'));
  }

  @override
  Future<Either<Failure, entity.OrderSummary>> getOrderSummary(DateTime date) async {
    return const Left(BusinessLogicFailure('Not implemented yet'));
  }

  @override
  Future<Either<Failure, void>> syncOrders() async {
    try {
      // 1. Get all un-synced orders
      final unSyncedOrders = await (database.select(database.orders)
            ..where((t) => t.isSynced.equals(false)))
          .get();

      if (unSyncedOrders.isEmpty) {
        return const Right(null);
      }

      // 2. Prepare items for each order
      final List<Map<String, dynamic>> orderPayloads = [];
      
      for (final order in unSyncedOrders) {
        final items = await (database.select(database.orderItems)
              ..where((t) => t.orderId.equals(order.id)))
            .get();

        orderPayloads.add({
          'id': order.id,
          'orderNumber': order.orderNumber,
          'total': order.total,
          'subtotal': order.subtotal,
          'discount': order.discount,
          'taxAmount': order.taxAmount,
          'customerName': order.customerName,
          'customerPhone': order.customerPhone,
          'notes': order.notes,
          'items': items.map((item) => {
            'productId': item.productId,
            'productName': item.productName,
            'quantity': item.quantity,
            'unitPrice': item.unitPrice,
            'discount': item.discount,
            'taxAmount': item.taxAmount,
            'vatRatePct': item.vatRatePct,
            'vatAmount': item.vatAmount,
          }).toList(),
          'createdAt': order.createdAt.toIso8601String(),
        });
      }

      // 3. Push to server
      final result = await remoteDataSource.offlinePunchOrders(orderPayloads);

      return result.fold(
        (failure) => Left(failure),
        (response) async {
          final syncedLocalIds = List<String>.from(response['synced_local_ids'] ?? []);
          
          if (syncedLocalIds.isNotEmpty) {
            // 4. Mark success sync in local DB
            await (database.update(database.orders)
                  ..where((t) => t.id.isIn(syncedLocalIds)))
                .write(const OrdersCompanion(isSynced: Value(true)));
          }

          return const Right(null);
        },
      );
    } catch (e) {
      return Left(DatabaseFailure('Sync failed: ${e.toString()}'));
    }
  }

  @override
  Future<Either<Failure, List<entity.Order>>> getLocalOrders() async {
     final dbOrders = await database.getAllOrders();
     return const Right([]);
  }

  @override
  Future<Either<Failure, void>> cacheOrders(List<entity.Order> orders) async {
     return const Right(null);
  }

  @override
  Stream<List<entity.Order>> watchLocalOrders() {
     return const Stream.empty();
  }
}
