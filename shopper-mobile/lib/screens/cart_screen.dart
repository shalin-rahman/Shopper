import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import '../core/bloc/cart/cart_bloc.dart';
import '../widgets/index.dart';
import '../navigation/app_router.dart';

class CartScreen extends StatefulWidget {
  const CartScreen({super.key});

  @override
  State<CartScreen> createState() => _CartScreenState();
}

class _CartScreenState extends State<CartScreen> {
  @override
  void initState() {
    super.initState();
    context.read<CartBloc>().add(CartLoaded());
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return ShopperScreen(
      title: l10n.cart,
      body: BlocBuilder<CartBloc, CartState>(
        builder: (context, state) {
          if (state is CartLoading) {
            return const Center(child: ShopperLoadingIndicator());
          } else if (state is CartLoadSuccess) {
            final cart = state.cart;
            if (cart.items.isEmpty) {
              return ShopperEmptyState(
                icon: Icons.shopping_cart_outlined,
                message: l10n.cartEmpty,
                actionLabel: l10n.goToProducts,
                onAction: () => Navigator.pushNamed(context, AppRouter.products),
              );
            }

            return Column(
              children: [
                Expanded(
                  child: ListView.builder(
                    padding: const EdgeInsets.all(kSpacing16),
                    itemCount: cart.items.length,
                    itemBuilder: (context, index) {
                      final item = cart.items[index];
                      return ShopperCard(
                        margin: const EdgeInsets.only(bottom: kSpacing16),
                        child: Padding(
                          padding: const EdgeInsets.all(kSpacing12),
                          child: Row(
                            children: [
                              // Small thumbnail placeholder
                              Container(
                                width: 60,
                                height: 60,
                                decoration: BoxDecoration(
                                  color: Colors.grey[200],
                                  borderRadius: BorderRadius.circular(kBorderRadiusSmall),
                                ),
                                child: const Icon(Icons.image_outlined, color: Colors.grey),
                              ),
                              const SizedBox(width: kSpacing16),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(item.productName, style: kBodyLarge.copyWith(fontWeight: FontWeight.bold)),
                                    Text('${l10n.pricePrefix} ${item.unitPrice.toStringAsFixed(2)}', style: kBodySmall),
                                  ],
                                ),
                              ),
                              ShopperQuantitySelector(
                                quantity: item.quantity,
                                onPlus: () {
                                  context.read<CartBloc>().add(CartItemUpdated(
                                    cartItemId: item.id,
                                    quantity: item.quantity + 1,
                                  ));
                                },
                                onMinus: () {
                                  if (item.quantity > 1) {
                                    context.read<CartBloc>().add(CartItemUpdated(
                                      cartItemId: item.id,
                                      quantity: item.quantity - 1,
                                    ));
                                  } else {
                                    context.read<CartBloc>().add(ItemRemovedFromCart(item.id));
                                  }
                                },
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),
                
                // Footer Total
                ShopperCard(
                  margin: EdgeInsets.zero,
                  padding: const EdgeInsets.all(kSpacing24),
                  child: Column(
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(l10n.subtotal, style: kBodyMedium),
                          Text(cart.subtotal.toStringAsFixed(2), style: kBodyMedium),
                        ],
                      ),
                      const SizedBox(height: kSpacing8),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(l10n.taxVat, style: kBodyMedium),
                          Text(cart.taxAmount.toStringAsFixed(2), style: kBodyMedium),
                        ],
                      ),
                      const Divider(height: kSpacing32),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(l10n.total, style: kHeadline6),
                          Text(cart.total.toStringAsFixed(2), style: kHeadline6.copyWith(color: kPrimaryColor)),
                        ],
                      ),
                      const SizedBox(height: kSpacing24),
                      ShopperPrimaryButton(
                        text: l10n.checkout,
                        onPressed: () => Navigator.pushNamed(context, AppRouter.checkout),
                      ),
                    ],
                  ),
                ),
              ],
            );
          } else if (state is CartError) {
            return Center(child: ShopperErrorText(state.message));
          }
          return const SizedBox.shrink();
        },
      ),
    );
  }
}
