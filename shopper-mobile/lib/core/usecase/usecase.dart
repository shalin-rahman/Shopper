import 'package:dartz/dartz.dart' hide Order;
import 'package:equatable/equatable.dart';
import '../error/failures.dart';

abstract class UseCase<TType, Params> {
  Future<Either<Failure, TType>> call(Params params);
}

class NoParams extends Equatable {
  @override
  List<Object?> get props => [];
}
