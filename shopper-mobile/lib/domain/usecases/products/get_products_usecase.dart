import 'package:dartz/dartz.dart';
import 'package:equatable/equatable.dart';
import '../../../core/error/failures.dart';
import '../../../core/usecase/usecase.dart';
import '../../../core/validation/validation.dart';
import '../../entities/product.dart';
import '../../repositories/product_repository.dart';

class GetProductsParams extends Equatable {
  final int? limit;
  final int? offset;
  final String? category;
  final String? searchQuery;

  const GetProductsParams({
    this.limit,
    this.offset,
    this.category,
    this.searchQuery,
  });

  /// Validates the get products parameters
  ValidationResult validate() {
    final List<ValidationResult> validations = [];

    // Limit validation
    if (limit != null) {
      if (limit! <= 0) {
        validations.add(ValidationResult.invalid(['Limit must be greater than 0']));
      }
      if (limit! > 1000) {
        validations.add(ValidationResult.invalid(['Limit cannot exceed 1000']));
      }
    }

    // Offset validation
    if (offset != null) {
      if (offset! < 0) {
        validations.add(ValidationResult.invalid(['Offset cannot be negative']));
      }
    }

    // Category validation
    if (category != null) {
      validations.add(ValidationUtils.validateLengthRange(category!, 1, 100, 'Category'));
    }

    // Search query validation
    if (searchQuery != null) {
      validations.add(ValidationUtils.validateLengthRange(searchQuery!, 1, 200, 'Search query'));
    }

    // Combine all validations
    ValidationResult result = ValidationResult.valid();
    for (final validation in validations) {
      result = result.merge(validation);
    }

    return result;
  }

  @override
  List<Object?> get props => [limit, offset, category, searchQuery];
}

class GetProductsUseCase implements UseCase<List<Product>, GetProductsParams> {
  final ProductRepository repository;

  GetProductsUseCase(this.repository);

  @override
  Future<Either<Failure, List<Product>>> call(GetProductsParams params) async {
    // Validate parameters
    final validation = params.validate();
    if (!validation.isValid) {
      return Left(ValidationFailure(validation.errors));
    }

    return await repository.getProducts(
      limit: params.limit,
      offset: params.offset,
      category: params.category,
      searchQuery: params.searchQuery,
    );
  }
}

class SearchProductsParams extends Equatable {
  final String query;

  const SearchProductsParams({required this.query});

  /// Validates the search products parameters
  ValidationResult validate() {
    final List<ValidationResult> validations = [];

    // Required field validations
    validations.add(ValidationUtils.validateRequired(query, 'Search query'));

    // Search query validation
    validations.add(ValidationUtils.validateLengthRange(query, 1, 200, 'Search query'));

    // Combine all validations
    ValidationResult result = ValidationResult.valid();
    for (final validation in validations) {
      result = result.merge(validation);
    }

    return result;
  }

  @override
  List<Object?> get props => [query];
}

class SearchProductsUseCase implements UseCase<List<Product>, SearchProductsParams> {
  final ProductRepository repository;

  SearchProductsUseCase(this.repository);

  @override
  Future<Either<Failure, List<Product>>> call(SearchProductsParams params) async {
    // Validate parameters
    final validation = params.validate();
    if (!validation.isValid) {
      return Left(ValidationFailure(validation.errors));
    }

    return await repository.searchProducts(params.query);
  }
}