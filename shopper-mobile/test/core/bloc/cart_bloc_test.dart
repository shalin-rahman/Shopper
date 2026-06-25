import 'package:bloc_test/bloc_test.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:dartz/dartz.dart';
import 'package:shopper_mobile/core/bloc/cart/cart_bloc.dart';
import 'package:shopper_mobile/core/usecase/usecase.dart';
import 'package:shopper_mobile/domain/entities/cart.dart';
import 'package:shopper_mobile/domain/usecases/cart/add_to_cart_usecase.dart';
import 'package:shopper_mobile/domain/usecases/cart/get_cart_usecase.dart';
import 'package:shopper_mobile/domain/usecases/cart/update_cart_item_usecase.dart';
import 'package:shopper_mobile/domain/usecases/cart/remove_from_cart_usecase.dart';
import 'package:shopper_mobile/domain/usecases/cart/clear_cart_usecase.dart';

class MockAddToCartUseCase extends Mock implements AddToCartUseCase {}
class MockGetCartUseCase extends Mock implements GetCartUseCase {}
class MockUpdateCartItemUseCase extends Mock implements UpdateCartItemUseCase {}
class MockRemoveFromCartUseCase extends Mock implements RemoveFromCartUseCase {}
class MockClearCartUseCase extends Mock implements ClearCartUseCase {}

class FakeAddToCartParams extends Fake implements AddToCartParams {}

void main() {
  late MockAddToCartUseCase mockAddToCart;
  late MockGetCartUseCase mockGetCart;
  late MockUpdateCartItemUseCase mockUpdateCartItem;
  late MockRemoveFromCartUseCase mockRemoveFromCart;
  late MockClearCartUseCase mockClearCart;

  setUpAll(() {
    registerFallbackValue(FakeAddToCartParams());
    registerFallbackValue(NoParams());
  });

  setUp(() {
    mockAddToCart = MockAddToCartUseCase();
    mockGetCart = MockGetCartUseCase();
    mockUpdateCartItem = MockUpdateCartItemUseCase();
    mockRemoveFromCart = MockRemoveFromCartUseCase();
    mockClearCart = MockClearCartUseCase();
  });

  CartBloc buildBloc() {
    return CartBloc(
      addToCartUseCase: mockAddToCart,
      getCartUseCase: mockGetCart,
      updateCartItemUseCase: mockUpdateCartItem,
      removeFromCartUseCase: mockRemoveFromCart,
      clearCartUseCase: mockClearCart,
    );
  }

  group('CartBloc', () {
    test('initial state is CartInitial', () {
      expect(buildBloc().state, isA<CartInitial>());
    });

    final emptyCart = Cart(id: 'c1', items: const [], createdAt: DateTime.now(), updatedAt: DateTime.now());

    blocTest<CartBloc, CartState>(
      'emits [CartLoading, CartLoadSuccess] when CartLoaded is successful',
      build: () {
        when(() => mockGetCart(any())).thenAnswer(
          (_) async => Right(emptyCart),
        );
        return buildBloc();
      },
      act: (bloc) => bloc.add(CartLoaded()),
      expect: () => [
        isA<CartLoading>(),
        isA<CartLoadSuccess>().having((s) => s.cart, 'cart', emptyCart),
      ],
    );

    blocTest<CartBloc, CartState>(
      'emits [CartLoading, CartLoadSuccess] when ItemAddedToCart is successful',
      build: () {
        when(() => mockAddToCart(any())).thenAnswer(
          (_) async => Right(emptyCart),
        );
        return buildBloc();
      },
      act: (bloc) => bloc.add(const ItemAddedToCart(productId: '1', quantity: 1)),
      expect: () => [
        isA<CartLoading>(),
        isA<CartLoadSuccess>(),
      ],
    );
  });
}
