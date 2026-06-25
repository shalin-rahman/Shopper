import 'package:dartz/dartz.dart' hide Order;
import '../../core/error/failures.dart';
import '../entities/cart.dart';

abstract class CartRepository {
  Future<Either<Failure, Cart>> getCart();

  Future<Either<Failure, Cart>> addToCart({
    required String productId,
    required int quantity,
    double? discount,
    String? notes,
  });

  Future<Either<Failure, Cart>> updateCartItem({
    required String cartItemId,
    int? quantity,
    double? discount,
    String? notes,
  });

  Future<Either<Failure, Cart>> removeFromCart(String cartItemId);

  Future<Either<Failure, Cart>> clearCart();

  Stream<Cart> watchCart();

  Future<Either<Failure, int>> getCartItemCount();
}
