import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:equatable/equatable.dart';
import '../../../domain/entities/cart.dart';
import '../../../domain/usecases/cart/add_to_cart_usecase.dart';
import '../../../domain/usecases/cart/get_cart_usecase.dart';
import '../../../domain/usecases/cart/update_cart_item_usecase.dart';
import '../../../domain/usecases/cart/remove_from_cart_usecase.dart';
import '../../../domain/usecases/cart/clear_cart_usecase.dart';
import '../../../core/error/failures.dart';

// Events
abstract class CartEvent extends Equatable {
  const CartEvent();

  @override
  List<Object?> get props => [];
}

class CartLoaded extends CartEvent {}

class ItemAddedToCart extends CartEvent {
  final String productId;
  final int quantity;
  final double? discount;
  final String? notes;

  const ItemAddedToCart({
    required this.productId,
    required this.quantity,
    this.discount,
    this.notes,
  });

  @override
  List<Object?> get props => [productId, quantity, discount, notes];
}

class CartItemUpdated extends CartEvent {
  final String cartItemId;
  final int? quantity;
  final double? discount;
  final String? notes;

  const CartItemUpdated({
    required this.cartItemId,
    this.quantity,
    this.discount,
    this.notes,
  });

  @override
  List<Object?> get props => [cartItemId, quantity, discount, notes];
}

class ItemRemovedFromCart extends CartEvent {
  final String cartItemId;

  const ItemRemovedFromCart(this.cartItemId);

  @override
  List<Object?> get props => [cartItemId];
}

class CartCleared extends CartEvent {}

// States
abstract class CartState extends Equatable {
  const CartState();

  @override
  List<Object?> get props => [];
}

class CartInitial extends CartState {}

class CartLoading extends CartState {}

class CartLoadSuccess extends CartState {
  final Cart cart;

  const CartLoadSuccess(this.cart);

  @override
  List<Object?> get props => [cart];
}

class CartError extends CartState {
  final String message;

  const CartError(this.message);

  @override
  List<Object?> get props => [message];
}

// BLoC
class CartBloc extends Bloc<CartEvent, CartState> {
  final AddToCartUseCase addToCartUseCase;
  final GetCartUseCase getCartUseCase;
  final UpdateCartItemUseCase updateCartItemUseCase;
  final RemoveFromCartUseCase removeFromCartUseCase;
  final ClearCartUseCase clearCartUseCase;

  CartBloc({
    required this.addToCartUseCase,
    required this.getCartUseCase,
    required this.updateCartItemUseCase,
    required this.removeFromCartUseCase,
    required this.clearCartUseCase,
  }) : super(CartInitial()) {
    on<CartLoaded>(_onCartLoaded);
    on<ItemAddedToCart>(_onItemAddedToCart);
    on<CartItemUpdated>(_onCartItemUpdated);
    on<ItemRemovedFromCart>(_onItemRemovedFromCart);
    on<CartCleared>(_onCartCleared);
  }

  Future<void> _onCartLoaded(
    CartLoaded event,
    Emitter<CartState> emit,
  ) async {
    emit(CartLoading());

    final result = await getCartUseCase(NoParams());

    result.fold(
      (failure) {
        if (failure is ValidationFailure) {
          emit(CartError(failure.errors.isNotEmpty ? failure.errors.first : failure.message));
        } else {
          emit(CartError(failure.message));
        }
      },
      (cart) => emit(CartLoadSuccess(cart)),
    );
  }

  Future<void> _onItemAddedToCart(
    ItemAddedToCart event,
    Emitter<CartState> emit,
  ) async {
    emit(CartLoading());

    final result = await addToCartUseCase(
      AddToCartParams(
        productId: event.productId,
        quantity: event.quantity,
        discount: event.discount,
        notes: event.notes,
      ),
    );

    result.fold(
      (failure) {
        if (failure is ValidationFailure) {
          emit(CartError(failure.errors.isNotEmpty ? failure.errors.first : failure.message));
        } else {
          emit(CartError(failure.message));
        }
      },
      (cart) => emit(CartLoadSuccess(cart)),
    );
  }

  Future<void> _onCartItemUpdated(
    CartItemUpdated event,
    Emitter<CartState> emit,
  ) async {
    emit(CartLoading());

    final result = await updateCartItemUseCase(
      UpdateCartItemParams(
        cartItemId: event.cartItemId,
        quantity: event.quantity,
        discount: event.discount,
        notes: event.notes,
      ),
    );

    result.fold(
      (failure) => emit(CartError(failure.message)),
      (cart) => emit(CartLoadSuccess(cart)),
    );
  }

  Future<void> _onItemRemovedFromCart(
    ItemRemovedFromCart event,
    Emitter<CartState> emit,
  ) async {
    emit(CartLoading());

    final result = await removeFromCartUseCase(
      RemoveFromCartParams(cartItemId: event.cartItemId),
    );

    result.fold(
      (failure) => emit(CartError(failure.message)),
      (cart) => emit(CartLoadSuccess(cart)),
    );
  }

  Future<void> _onCartCleared(
    CartCleared event,
    Emitter<CartState> emit,
  ) async {
    emit(CartLoading());

    final result = await clearCartUseCase(NoParams());

    result.fold(
      (failure) => emit(CartError(failure.message)),
      (cart) => emit(CartLoadSuccess(cart)),
    );
  }
}