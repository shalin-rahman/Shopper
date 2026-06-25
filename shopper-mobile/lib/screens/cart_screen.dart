import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:shopper_mobile/l10n/app_localizations.dart';
import '../core/design_system.dart';
import '../core/bloc/cart/cart_bloc.dart';
import '../navigation/app_router.dart';
import '../widgets/index.dart';

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
                title: l10n.cart,
                icon: Icons.shopping_cart_outlined,
                message: l10n.cartEmpty,
                action: ShopperPrimaryButton(
                  text: l10n.goToProducts,
                  onPressed: () => Navigator.pushNamed(context, AppRouter.products),
                ),
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
                      return Padding(
                        padding: const EdgeInsets.only(bottom: kSpacing16),
                        child: ShopperCard(
                          child: Padding(
                            padding: const EdgeInsets.all(kSpacing12),
                            child: Row(
                              children: [
                                // Thumbnail placeholder
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
                                      Text(item.product.displayName,
                                          style: kBodyLarge.copyWith(fontWeight: FontWeight.bold)),
                                      Text('${l10n.pricePrefix} ${item.unitPrice.toStringAsFixed(2)}',
                                          style: kBodySmall),
                                    ],
                                  ),
                                ),
                                ShopperQuantitySelector(
                                  quantity: item.quantity,
                                  onChanged: (val) {
                                    if (val == 0) {
                                      context.read<CartBloc>().add(ItemRemovedFromCart(item.id));
                                    } else {
                                      context.read<CartBloc>().add(CartItemUpdated(cartItemId: item.id, quantity: val));
                                    }
                                  },
                                ),
                              ],
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                ),
                // Footer Total
                ShopperCard(
                  child: Padding(
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
                            const Text('0.00', style: kBodyMedium),
                          ],
                        ),
                        const Divider(height: kSpacing32),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(l10n.total, style: kHeadline3),
                            Text(cart.total.toStringAsFixed(2),
                                style: kHeadline3.copyWith(color: kPrimaryColor)),
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
                ),
              ],
            );
          } else if (state is CartError) {
            return Center(child: ShopperErrorText(error: state.message));
          }
          return const SizedBox.shrink();
        },
      ),
    );
  }
}
