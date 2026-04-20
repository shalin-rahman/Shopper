import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:equatable/equatable.dart';
import '../../../domain/entities/order.dart';
import '../../../domain/entities/cart.dart';
import '../../../domain/usecases/orders/create_order_usecase.dart';
import '../../../domain/usecases/orders/get_orders_usecase.dart';
import '../../../domain/usecases/orders/sync_orders_usecase.dart';
import '../../../../core/usecases/usecase.dart';
import '../../../core/error/failures.dart';

// Events
abstract class OrdersEvent extends Equatable {
  const OrdersEvent();

  @override
  List<Object?> get props => [];
}

class OrdersLoaded extends OrdersEvent {
  final int? limit;
  final int? offset;
  final OrderStatus? status;
  final DateTime? startDate;
  final DateTime? endDate;

  const OrdersLoaded({
    this.limit,
    this.offset,
    this.status,
    this.startDate,
    this.endDate,
  });

  @override
  List<Object?> get props => [limit, offset, status, startDate, endDate];
}

class OrderCreated extends OrdersEvent {
  final Cart cart;
  final String? customerName;
  final String? customerPhone;
  final String? notes;

  const OrderCreated({
    required this.cart,
    this.customerName,
    this.customerPhone,
    this.notes,
  });

  @override
  List<Object?> get props => [cart, customerName, customerPhone, notes];
}

class OrdersRefreshed extends OrdersEvent {}

class OrdersSyncRequested extends OrdersEvent {}

// States
abstract class OrdersState extends Equatable {
  const OrdersState();

  @override
  List<Object?> get props => [];
}

class OrdersInitial extends OrdersState {}

class OrdersLoading extends OrdersState {}

class OrdersLoadSuccess extends OrdersState {
  final List<Order> orders;
  final bool hasReachedMax;

  const OrdersLoadSuccess({
    required this.orders,
    this.hasReachedMax = false,
  });

  @override
  List<Object?> get props => [orders, hasReachedMax];
}

class OrdersSyncSuccess extends OrdersState {}

class OrderCreatedSuccess extends OrdersState {
  final Order order;

  const OrderCreatedSuccess(this.order);

  @override
  List<Object?> get props => [order];
}

class OrdersError extends OrdersState {
  final String message;

  const OrdersError(this.message);

  @override
  List<Object?> get props => [message];
}

// BLoC
class OrdersBloc extends Bloc<OrdersEvent, OrdersState> {
  OrdersBloc({
    required this.createOrderUseCase,
    required this.getOrdersUseCase,
    required this.syncOrdersUseCase,
  }) : super(OrdersInitial()) {
    on<OrdersLoaded>(_onOrdersLoaded);
    on<OrderCreated>(_onOrderCreated);
    on<OrdersRefreshed>(_onOrdersRefreshed);
    on<OrdersSyncRequested>(_onOrdersSyncRequested);
  }

  final CreateOrderUseCase createOrderUseCase;
  final GetOrdersUseCase getOrdersUseCase;
  final SyncOrdersUseCase syncOrdersUseCase;

  Future<void> _onOrdersLoaded(
    OrdersLoaded event,
    Emitter<OrdersState> emit,
  ) async {
    emit(OrdersLoading());

    final result = await getOrdersUseCase(
      GetOrdersParams(
        limit: event.limit,
        offset: event.offset,
        status: event.status,
        startDate: event.startDate,
        endDate: event.endDate,
      ),
    );

    result.fold(
      (failure) {
        if (failure is ValidationFailure) {
          emit(OrdersError(failure.errors.isNotEmpty ? failure.errors.first : failure.message));
        } else {
          emit(OrdersError(failure.message));
        }
      },
      (orders) => emit(OrdersLoadSuccess(orders: orders)),
    );
  }

  Future<void> _onOrderCreated(
    OrderCreated event,
    Emitter<OrdersState> emit,
  ) async {
    emit(OrdersLoading());

    final result = await createOrderUseCase(
      CreateOrderParams(
        cart: event.cart,
        customerName: event.customerName,
        customerPhone: event.customerPhone,
        notes: event.notes,
      ),
    );

    result.fold(
      (failure) {
        if (failure is ValidationFailure) {
          emit(OrdersError(failure.errors.isNotEmpty ? failure.errors.first : failure.message));
        } else {
          emit(OrdersError(failure.message));
        }
      },
      (order) => emit(OrderCreatedSuccess(order)),
    );
  }

  Future<void> _onOrdersRefreshed(
    OrdersRefreshed event,
    Emitter<OrdersState> emit,
  ) async {
    emit(OrdersLoading());

    final result = await getOrdersUseCase(
      const GetOrdersParams(),
    );

    result.fold(
      (failure) {
        if (failure is ValidationFailure) {
          emit(OrdersError(failure.errors.isNotEmpty ? failure.errors.first : failure.message));
        } else {
          emit(OrdersError(failure.message));
        }
      },
      (orders) => emit(OrdersLoadSuccess(orders: orders)),
    );
  }

  Future<void> _onOrdersSyncRequested(
    OrdersSyncRequested event,
    Emitter<OrdersState> emit,
  ) async {
    emit(OrdersLoading());

    final result = await syncOrdersUseCase(NoParams());

    result.fold(
      (failure) => emit(OrdersError(failure.message)),
      (_) {
        emit(OrdersSyncSuccess());
        add(OrdersRefreshed());
      },
    );
  }
}