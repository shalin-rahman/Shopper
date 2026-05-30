import 'package:dartz/dartz.dart';
import 'package:equatable/equatable.dart';
import '../../../../core/error/failures.dart';
import '../../../../core/usecases/usecase.dart';
import '../../repositories/product_repository.dart';

class AdjustStockUseCase implements UseCase<void, AdjustStockParams> {
  final ProductRepository repository;

  AdjustStockUseCase(this.repository);

  @override
  Future<Either<Failure, void>> call(AdjustStockParams params) async {
    return await repository.adjustStock(
      sku: params.sku,
      quantity: params.quantity,
      type: params.type,
      notes: params.notes,
      reasonCode: params.reasonCode,
    );
  }
}

class AdjustStockParams extends Equatable {
  final String sku;
  final double quantity;
  final String type;
  final String? notes;
  final String? reasonCode;

  const AdjustStockParams({
    required this.sku,
    required this.quantity,
    required this.type,
    this.notes,
    this.reasonCode,
  });

  @override
  List<Object?> get props => [sku, quantity, type, notes, reasonCode];
}
