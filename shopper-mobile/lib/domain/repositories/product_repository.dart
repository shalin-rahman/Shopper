import 'package:dartz/dartz.dart' hide Order;
import '../../core/error/failures.dart';
import '../entities/product.dart';

abstract class ProductRepository {
  Future<Either<Failure, List<Product>>> getProducts({
    int? limit,
    int? offset,
    String? category,
    String? searchQuery,
  });

  Future<Either<Failure, Product>> getProductById(String id);

  Future<Either<Failure, List<Product>>> searchProducts(String query);

  Future<Either<Failure, List<ProductCategory>>> getCategories();

  Future<Either<Failure, void>> syncProducts();

  Future<Either<Failure, List<Product>>> getLocalProducts();

  Future<Either<Failure, void>> cacheProducts(List<Product> products);

  Stream<List<Product>> watchLocalProducts();

  Future<Either<Failure, void>> adjustStock({
    required String sku,
    required double quantity,
    required String type,
    String? notes,
    String? reasonCode,
  });

  Future<Either<Failure, void>> syncAdjustments();
}
