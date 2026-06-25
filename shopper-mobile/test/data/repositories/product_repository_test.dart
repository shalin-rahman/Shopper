import 'package:dartz/dartz.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:shopper_mobile/core/error/failures.dart';
import 'package:shopper_mobile/data/repositories/product_repository_impl.dart';
import 'package:shopper_mobile/data/sources/local/database/app_database.dart';
import 'package:drift/drift.dart';

import '../../helpers/test_database.dart';
import '../../helpers/demo_data.dart';
import '../../helpers/mocks.dart';

void main() {
  late AppDatabase database;
  late MockApiClient mockApiClient;
  late ProductRepositoryImpl repository;

  setUpAll(() {
    // Register fallback values for mocktail
    registerFallbackValue(null);
  });

  setUp(() {
    database = createTestDatabase();
    mockApiClient = MockApiClient();
    repository = ProductRepositoryImpl(
      apiClient: mockApiClient,
      database: database,
    );

    // Stub API to return a failure → repo will fallback to local DB
    when(() => mockApiClient.getProducts(
          limit: any(named: 'limit'),
          offset: any(named: 'offset'),
          category: any(named: 'category'),
          searchQuery: any(named: 'searchQuery'),
        )).thenAnswer(
      (_) async => const Left(ServerFailure('No network')),
    );
  });

  tearDown(() async {
    await database.close();
  });

  group('ProductRepositoryImpl - Local DB', () {
    test('insert and get all products returns both products', () async {
      // 1. Seed sample products directly into in-memory DB
      await database.insertProducts([
        ProductsCompanion(
          id: Value(DemoData.sampleProduct1.id),
          nameEn: Value(DemoData.sampleProduct1.nameEn),
          price: Value(DemoData.sampleProduct1.price),
          stockQuantity: Value(DemoData.sampleProduct1.stockQuantity),
          isActive: Value(DemoData.sampleProduct1.isActive),
          isTaxable: Value(DemoData.sampleProduct1.isTaxable),
          category: Value(DemoData.sampleProduct1.category),
          brand: Value(DemoData.sampleProduct1.brand),
          barcode: Value(DemoData.sampleProduct1.barcode),
          createdAt: Value(DemoData.sampleProduct1.createdAt),
          updatedAt: Value(DemoData.sampleProduct1.updatedAt),
        ),
        ProductsCompanion(
          id: Value(DemoData.sampleProduct2.id),
          nameEn: Value(DemoData.sampleProduct2.nameEn),
          price: Value(DemoData.sampleProduct2.price),
          stockQuantity: Value(DemoData.sampleProduct2.stockQuantity),
          isActive: Value(DemoData.sampleProduct2.isActive),
          isTaxable: Value(DemoData.sampleProduct2.isTaxable),
          category: Value(DemoData.sampleProduct2.category),
          brand: Value(DemoData.sampleProduct2.brand),
          barcode: Value(DemoData.sampleProduct2.barcode),
          createdAt: Value(DemoData.sampleProduct2.createdAt),
          updatedAt: Value(DemoData.sampleProduct2.updatedAt),
        ),
      ]);

      // 2. Fetch via repository (will fallback to local due to stubbed failure)
      final result = await repository.getProducts();

      // 3. Verify
      result.fold(
        (failure) => fail('Should not fail: $failure'),
        (products) {
          expect(products.length, 2);
          expect(products.map((p) => p.id), containsAll([
            DemoData.sampleProduct1.id,
            DemoData.sampleProduct2.id,
          ]));
        },
      );
    });

    test('searchProducts returns matching products from local DB', () async {
      // 1. Seed
      await database.insertProducts([
        ProductsCompanion(
          id: Value(DemoData.sampleProduct1.id),
          nameEn: Value(DemoData.sampleProduct1.nameEn),
          price: Value(DemoData.sampleProduct1.price),
          stockQuantity: Value(DemoData.sampleProduct1.stockQuantity),
          createdAt: Value(DemoData.sampleProduct1.createdAt),
          updatedAt: Value(DemoData.sampleProduct1.updatedAt),
        ),
        ProductsCompanion(
          id: Value(DemoData.sampleProduct2.id),
          nameEn: Value(DemoData.sampleProduct2.nameEn),
          price: Value(DemoData.sampleProduct2.price),
          stockQuantity: Value(DemoData.sampleProduct2.stockQuantity),
          createdAt: Value(DemoData.sampleProduct2.createdAt),
          updatedAt: Value(DemoData.sampleProduct2.updatedAt),
        ),
      ]);

      // 2. Search via repository.searchProducts (pure local — no API involved)
      final result = await repository.searchProducts('Laptop');

      // 3. Verify
      result.fold(
        (failure) => fail('Should not fail: $failure'),
        (products) {
          expect(products.length, 1);
          expect(products.first.nameEn, 'Sample Laptop');
        },
      );
    });

    test('searchProducts by barcode returns exact match', () async {
      await database.insertProducts([
        ProductsCompanion(
          id: Value(DemoData.sampleProduct1.id),
          nameEn: Value(DemoData.sampleProduct1.nameEn),
          price: Value(DemoData.sampleProduct1.price),
          stockQuantity: Value(DemoData.sampleProduct1.stockQuantity),
          barcode: Value(DemoData.sampleProduct1.barcode),
          createdAt: Value(DemoData.sampleProduct1.createdAt),
          updatedAt: Value(DemoData.sampleProduct1.updatedAt),
        ),
      ]);

      final result = await repository.searchProducts('1234567890');

      result.fold(
        (failure) => fail('Should not fail: $failure'),
        (products) {
          expect(products.length, 1);
          expect(products.first.barcode, '1234567890');
        },
      );
    });

    test('getLocalProducts returns all seeded products', () async {
      await database.insertProducts([
        ProductsCompanion(
          id: Value(DemoData.sampleProduct1.id),
          nameEn: Value(DemoData.sampleProduct1.nameEn),
          price: Value(DemoData.sampleProduct1.price),
          stockQuantity: Value(DemoData.sampleProduct1.stockQuantity),
          createdAt: Value(DemoData.sampleProduct1.createdAt),
          updatedAt: Value(DemoData.sampleProduct1.updatedAt),
        ),
      ]);

      final result = await repository.getLocalProducts();

      result.fold(
        (failure) => fail('Should not fail: $failure'),
        (products) => expect(products.length, 1),
      );
    });
  });
}
