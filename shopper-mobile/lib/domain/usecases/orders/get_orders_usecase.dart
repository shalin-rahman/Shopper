import 'package:dartz/dartz.dart';
import 'package:equatable/equatable.dart';
import '../../../../core/error/failures.dart';
import '../../../../core/usecases/usecase.dart';
import '../../entities/order.dart';
import '../../repositories/order_repository.dart';

class GetOrdersUseCase implements UseCase<List<Order>, GetOrdersParams> {
  final OrderRepository repository;

  GetOrdersUseCase(this.repository);

  @override
  Future<Either<Failure, List<Order>>> call(GetOrdersParams params) async {
    return await repository.getOrders(
      limit: params.limit,
      offset: params.offset,
      status: params.status,
      startDate: params.startDate,
      endDate: params.endDate,
    );
  }
}

class GetOrdersParams extends Equatable {
  final int? limit;
  final int? offset;
  final OrderStatus? status;
  final DateTime? startDate;
  final DateTime? endDate;

  const GetOrdersParams({
    this.limit,
    this.offset,
    this.status,
    this.startDate,
    this.endDate,
  });

  @override
  List<Object?> get props => [limit, offset, status, startDate, endDate];
}
