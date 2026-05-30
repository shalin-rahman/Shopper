import 'package:dartz/dartz.dart';
import '../../core/error/failures.dart';
import '../entities/order.dart';
import '../entities/cart.dart';

abstract class OrderRepository {
  Future<Either<Failure, Order>> createOrder({
    required Cart cart,
    String? customerName,
    String? customerPhone,
    String? notes,
    String? paymentMethod,
    double? amountPaid,
  });

  Future<Either<Failure, List<Order>>> getOrders({
    int? limit,
    int? offset,
    OrderStatus? status,
    DateTime? startDate,
    DateTime? endDate,
  });

  Future<Either<Failure, Order>> getOrderById(String id);

  Future<Either<Failure, Order>> updateOrderStatus({
    required String orderId,
    required OrderStatus status,
  });

  Future<Either<Failure, OrderSummary>> getOrderSummary(DateTime date);

  Future<Either<Failure, void>> syncOrders();

  Future<Either<Failure, List<Order>>> getLocalOrders();

  Future<Either<Failure, void>> cacheOrders(List<Order> orders);

  Stream<List<Order>> watchLocalOrders();
}