import 'package:dartz/dartz.dart' hide Order;
import '../../core/error/failures.dart';
import '../../domain/entities/cart.dart';
import '../../domain/repositories/cart_repository.dart';
import '../../data/sources/local/database/app_database.dart';

class CartRepositoryImpl implements CartRepository {
  final AppDatabase database;
  CartRepositoryImpl(this.database);

  @override
  Future<Either<Failure, Cart>> getCart() async => Right(Cart.empty());

  @override
  Future<Either<Failure, Cart>> addToCart({
    required String productId,
    required int quantity,
    double? discount,
    String? notes,
  }) async => Right(Cart.empty());

  @override
  Future<Either<Failure, Cart>> updateCartItem({
    required String cartItemId,
    int? quantity,
    double? discount,
    String? notes,
  }) async => Right(Cart.empty());

  @override
  Future<Either<Failure, Cart>> removeFromCart(String cartItemId) async => Right(Cart.empty());

  @override
  Future<Either<Failure, Cart>> clearCart() async => Right(Cart.empty());

  @override
  Stream<Cart> watchCart() => const Stream.empty();

  @override
  Future<Either<Failure, int>> getCartItemCount() async => const Right(0);
}
