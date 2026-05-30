import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:equatable/equatable.dart';
import '../../../domain/entities/product.dart';
import '../../../domain/usecases/products/get_products_usecase.dart';
import '../../../domain/usecases/products/search_products_usecase.dart';
import '../../../domain/usecases/products/adjust_stock_usecase.dart';
import '../../../domain/usecases/products/sync_adjustments_usecase.dart';
import '../../../../core/usecases/usecase.dart';
import '../../../core/error/failures.dart';

// Events
abstract class ProductsEvent extends Equatable {
  const ProductsEvent();

  @override
  List<Object?> get props => [];
}

class ProductsLoaded extends ProductsEvent {
  final int? limit;
  final int? offset;
  final String? category;
  final String? searchQuery;

  const ProductsLoaded({
    this.limit,
    this.offset,
    this.category,
    this.searchQuery,
  });

  @override
  List<Object?> get props => [limit, offset, category, searchQuery];
}

class ProductsSearched extends ProductsEvent {
  final String query;

  const ProductsSearched(this.query);

  @override
  List<Object?> get props => [query];
}

class ProductsRefreshed extends ProductsEvent {}

class AdjustStockRequested extends ProductsEvent {
  final String sku;
  final double quantity;
  final String type;
  final String? notes;
  final String? reasonCode;

  const AdjustStockRequested({
    required this.sku,
    required this.quantity,
    required this.type,
    this.notes,
    this.reasonCode,
  });

  @override
  List<Object?> get props => [sku, quantity, type, notes, reasonCode];
}

class SyncAdjustmentsRequested extends ProductsEvent {}

// States
abstract class ProductsState extends Equatable {
  const ProductsState();

  @override
  List<Object?> get props => [];
}

class ProductsInitial extends ProductsState {}

class ProductsLoading extends ProductsState {}

class ProductsLoadSuccess extends ProductsState {
  final List<Product> products;
  final bool hasReachedMax;

  const ProductsLoadSuccess({
    required this.products,
    this.hasReachedMax = false,
  });

  @override
  List<Object?> get props => [products, hasReachedMax];
}

class ProductsError extends ProductsState {
  final String message;

  const ProductsError(this.message);

  @override
  List<Object?> get props => [message];
}

// BLoC
class ProductsBloc extends Bloc<ProductsEvent, ProductsState> {
  final GetProductsUseCase getProductsUseCase;
  final SearchProductsUseCase searchProductsUseCase;
  final AdjustStockUseCase adjustStockUseCase;
  final SyncAdjustmentsUseCase syncAdjustmentsUseCase;

  ProductsBloc({
    required this.getProductsUseCase,
    required this.searchProductsUseCase,
    required this.adjustStockUseCase,
    required this.syncAdjustmentsUseCase,
  }) : super(ProductsInitial()) {
    on<ProductsLoaded>(_onProductsLoaded);
    on<ProductsSearched>(_onProductsSearched);
    on<ProductsRefreshed>(_onProductsRefreshed);
    on<AdjustStockRequested>(_onAdjustStockRequested);
    on<SyncAdjustmentsRequested>(_onSyncAdjustmentsRequested);
  }

  Future<void> _onProductsLoaded(
    ProductsLoaded event,
    Emitter<ProductsState> emit,
  ) async {
    emit(ProductsLoading());

    final result = await getProductsUseCase(
      GetProductsParams(
        limit: event.limit,
        offset: event.offset,
        category: event.category,
        searchQuery: event.searchQuery,
      ),
    );

    result.fold(
      (failure) {
        if (failure is ValidationFailure) {
          emit(ProductsError(failure.errors.isNotEmpty ? failure.errors.first : failure.message));
        } else {
          emit(ProductsError(failure.message));
        }
      },
      (products) => emit(ProductsLoadSuccess(products: products)),
    );
  }

  Future<void> _onProductsSearched(
    ProductsSearched event,
    Emitter<ProductsState> emit,
  ) async {
    if (event.query.isEmpty) {
      emit(ProductsInitial());
      return;
    }

    emit(ProductsLoading());

    final result = await searchProductsUseCase(
      SearchProductsParams(query: event.query),
    );

    result.fold(
      (failure) {
        if (failure is ValidationFailure) {
          emit(ProductsError(failure.errors.isNotEmpty ? failure.errors.first : failure.message));
        } else {
          emit(ProductsError(failure.message));
        }
      },
      (products) => emit(ProductsLoadSuccess(products: products)),
    );
  }

  Future<void> _onProductsRefreshed(
    ProductsRefreshed event,
    Emitter<ProductsState> emit,
  ) async {
    emit(ProductsLoading());

    final result = await getProductsUseCase(
      const GetProductsParams(),
    );

    result.fold(
      (failure) {
        if (failure is ValidationFailure) {
          emit(ProductsError(failure.errors.isNotEmpty ? failure.errors.first : failure.message));
        } else {
          emit(ProductsError(failure.message));
        }
      },
      (products) => emit(ProductsLoadSuccess(products: products)),
    );
  }

  Future<void> _onAdjustStockRequested(
    AdjustStockRequested event,
    Emitter<ProductsState> emit,
  ) async {
    final result = await adjustStockUseCase(
      AdjustStockParams(
        sku: event.sku,
        quantity: event.quantity,
        type: event.type,
        notes: event.notes,
        reasonCode: event.reasonCode,
      ),
    );

    result.fold(
      (failure) => emit(ProductsError(failure.message)),
      (_) => add(SyncAdjustmentsRequested()),
    );
  }

  Future<void> _onSyncAdjustmentsRequested(
    SyncAdjustmentsRequested event,
    Emitter<ProductsState> emit,
  ) async {
    final result = await syncAdjustmentsUseCase(NoParams());
    
    result.fold(
      (failure) => emit(ProductsError(failure.message)),
      (_) => add(ProductsRefreshed()),
    );
  }
}