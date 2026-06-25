import 'package:dartz/dartz.dart' hide Order;
import '../../../core/error/failures.dart';
import '../../../core/usecase/usecase.dart';
import '../../entities/product.dart';
import '../../repositories/product_repository.dart';

class SearchProductsUseCase implements UseCase<List<Product>, SearchProductsParams> {
  final ProductRepository repository;

  SearchProductsUseCase(this.repository);

  @override
  Future<Either<Failure, List<Product>>> call(SearchProductsParams params) async {
    return await repository.searchProducts(params.query);
  }
}

class SearchProductsParams {
  final String query;

  const SearchProductsParams(this.query);
}
