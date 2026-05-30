import 'package:dartz/dartz.dart';
import 'package:drift/drift.dart';
import '../../../core/error/failures.dart';
import '../../../domain/entities/product.dart';
import '../../../domain/repositories/product_repository.dart';
import '../sources/local/database/app_database.dart';
import '../sources/remote/api_client.dart';

class ProductRepositoryImpl implements ProductRepository {
  final ApiClient apiClient;
  final AppDatabase database;

  ProductRepositoryImpl({
    required this.apiClient,
    required this.database,
  });

  @override
  Future<Either<Failure, List<Product>>> getProducts({
    int? limit,
    int? offset,
    String? category,
    String? searchQuery,
  }) async {
    try {
      final remoteResult = await apiClient.getProducts(
        limit: limit,
        offset: offset,
        category: category,
        searchQuery: searchQuery,
      );

      return remoteResult.fold(
        (failure) async {
          // Fallback to local if remote fails
          final localProducts = await database.getAllProducts();
          return Right(localProducts.map(_mapToEntity).toList());
        },
        (products) async {
          // Cache products locally
          await cacheProducts(products);
          return Right(products);
        },
      );
    } catch (e) {
      return Left(ServerFailure('Failed to get products: ${e.toString()}'));
    }
  }

  @override
  Future<Either<Failure, Product>> getProductById(String id) async {
    try {
      final localProduct = await database.getProductById(id);
      if (localProduct != null) {
        return Right(_mapToEntity(localProduct));
      }
      return Left(CacheFailure('Product not found locally'));
    } catch (e) {
      return Left(CacheFailure('Failed to get local product: ${e.toString()}'));
    }
  }

  @override
  Future<Either<Failure, List<Product>>> searchProducts(String query) async {
    try {
      final localResults = await database.searchProducts(query);
      return Right(localResults.map(_mapToEntity).toList());
    } catch (e) {
      return Left(CacheFailure('Search failed locally: ${e.toString()}'));
    }
  }

  @override
  Future<Either<Failure, List<ProductCategory>>> getCategories() async {
    // Simplified for now
    return const Right([]);
  }

  @override
  Future<Either<Failure, void>> syncProducts() async {
    return await getProducts(limit: 1000);
  }

  @override
  Future<Either<Failure, List<Product>>> getLocalProducts() async {
    final products = await database.getAllProducts();
    return Right(products.map(_mapToEntity).toList());
  }

  @override
  Future<Either<Failure, void>> cacheProducts(List<Product> products) async {
    for (final p in products) {
      await database.insertProduct(ProductsCompanion(
        id: Value(p.id),
        nameEn: Value(p.nameEn),
        nameBn: Value(p.nameBn),
        sku: Value(p.sku),
        price: Value(p.price),
        sellPrice: Value(p.sellPrice),
        stockQuantity: Value(p.stockQuantity),
        isActive: Value(p.isActive),
        createdAt: Value(p.createdAt),
        updatedAt: Value(p.updatedAt),
      ));
    }
    return const Right(null);
  }

  @override
  Stream<List<Product>> watchLocalProducts() {
    return database.select(database.products).watch().map((rows) => 
      rows.map(_mapToEntity).toList()
    );
  }

  @override
  Future<Either<Failure, void>> adjustStock({
    required String sku,
    required double quantity,
    required String type,
    String? notes,
    String? reasonCode,
  }) async {
    try {
      final id = DateTime.now().millisecondsSinceEpoch.toString();
      await database.insertAdjustment(StockAdjustmentsCompanion(
        id: Value(id),
        sku: Value(sku),
        quantity: Value(quantity),
        type: Value(type),
        notes: Value(notes),
        reasonCode: Value(reasonCode),
        isSynced: const Value(false),
        createdAt: Value(DateTime.now()),
      ));
      return const Right(null);
    } catch (e) {
      return Left(CacheFailure('Failed to record adjustment: ${e.toString()}'));
    }
  }

  @override
  Future<Either<Failure, void>> syncAdjustments() async {
    try {
      final unsynced = await database.getUnsyncedAdjustments();
      if (unsynced.isEmpty) return const Right(null);

      for (final adj in unsynced) {
        final payload = {
          'sku': adj.sku,
          'quantity': adj.quantity,
          'type': adj.type,
          'reason_code': adj.reasonCode,
          'notes': adj.notes,
          'created_at': adj.createdAt.toIso8601String(),
        };

        final result = await apiClient.adjustStock(adjustmentData: payload);
        if (result.isRight()) {
          await database.markAdjustmentSynced(adj.id);
        }
      }
      return const Right(null);
    } catch (e) {
      return Left(ServerFailure('Sync adjustments failed: ${e.toString()}'));
    }
  }

  Product _mapToEntity(dynamic row) {
    return Product(
      id: row.id,
      nameEn: row.nameEn,
      nameBn: row.nameBn,
      sku: row.sku,
      price: row.price,
      sellPrice: row.sellPrice,
      stockQuantity: row.stockQuantity,
      isActive: row.isActive,
      createdAt: row.createdAt,
      updatedAt: row.updatedAt,
    );
  }
}
