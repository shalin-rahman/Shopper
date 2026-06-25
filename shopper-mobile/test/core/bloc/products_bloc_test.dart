import 'package:bloc_test/bloc_test.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:dartz/dartz.dart';
import 'package:shopper_mobile/core/bloc/products/products_bloc.dart';
import 'package:shopper_mobile/core/error/failures.dart';
import 'package:shopper_mobile/domain/usecases/products/get_products_usecase.dart';
import 'package:shopper_mobile/domain/usecases/products/search_products_usecase.dart';
import 'package:shopper_mobile/domain/usecases/products/adjust_stock_usecase.dart';
import 'package:shopper_mobile/domain/usecases/products/sync_adjustments_usecase.dart';

import '../../helpers/demo_data.dart';

class MockGetProductsUseCase extends Mock implements GetProductsUseCase {}
class MockSearchProductsUseCase extends Mock implements SearchProductsUseCase {}
class MockAdjustStockUseCase extends Mock implements AdjustStockUseCase {}
class MockSyncAdjustmentsUseCase extends Mock implements SyncAdjustmentsUseCase {}

void main() {
  late MockGetProductsUseCase mockGetProducts;
  late MockSearchProductsUseCase mockSearchProducts;
  late MockAdjustStockUseCase mockAdjustStock;
  late MockSyncAdjustmentsUseCase mockSyncAdjustments;

  setUpAll(() {
    registerFallbackValue(const GetProductsParams());
  });

  setUp(() {
    mockGetProducts = MockGetProductsUseCase();
    mockSearchProducts = MockSearchProductsUseCase();
    mockAdjustStock = MockAdjustStockUseCase();
    mockSyncAdjustments = MockSyncAdjustmentsUseCase();
  });

  ProductsBloc buildBloc() {
    return ProductsBloc(
      getProductsUseCase: mockGetProducts,
      searchProductsUseCase: mockSearchProducts,
      adjustStockUseCase: mockAdjustStock,
      syncAdjustmentsUseCase: mockSyncAdjustments,
    );
  }

  group('ProductsBloc', () {
    test('initial state is ProductsInitial', () {
      expect(buildBloc().state, isA<ProductsInitial>());
    });

    blocTest<ProductsBloc, ProductsState>(
      'emits [ProductsLoading, ProductsLoadSuccess] when ProductsLoaded is successful',
      build: () {
        when(() => mockGetProducts(any())).thenAnswer(
          (_) async => Right(DemoData.sampleProducts),
        );
        return buildBloc();
      },
      act: (bloc) => bloc.add(const ProductsLoaded()),
      expect: () => [
        isA<ProductsLoading>(),
        isA<ProductsLoadSuccess>().having(
          (s) => s.products,
          'products',
          DemoData.sampleProducts,
        ),
      ],
    );

    blocTest<ProductsBloc, ProductsState>(
      'emits [ProductsLoading, ProductsLoadFailure] when ProductsLoaded fails',
      build: () {
        when(() => mockGetProducts(any())).thenAnswer(
          (_) async => const Left(ServerFailure('Error')),
        );
        return buildBloc();
      },
      act: (bloc) => bloc.add(const ProductsLoaded()),
      expect: () => [
        isA<ProductsLoading>(),
        isA<ProductsError>(),
      ],
    );
  });
}
