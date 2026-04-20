import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import '../core/bloc/products/products_bloc.dart';
import '../core/bloc/cart/cart_bloc.dart';
import '../widgets/index.dart';

class ProductsScreen extends StatefulWidget {
  const ProductsScreen({super.key});

  @override
  State<ProductsScreen> createState() => _ProductsScreenState();
}

class _ProductsScreenState extends State<ProductsScreen> {
  final TextEditingController _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    // Load initial products
    context.read<ProductsBloc>().add(const ProductsLoaded());
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _onSearchChanged(String query) {
    context.read<ProductsBloc>().add(ProductsSearched(query));
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return ShopperScreen(
      title: l10n.products,
      body: ShopperColumn(
        spacing: kSpacing16,
        children: [
          // Search Bar
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: kSpacing16),
            child: ShopperSearchBar(
              controller: _searchController,
              hintText: l10n.searchProducts,
              onChanged: _onSearchChanged,
            ),
          ),

          // Product List/Grid
          Expanded(
            child: BlocBuilder<ProductsBloc, ProductsState>(
              builder: (context, state) {
                if (state is ProductsLoading) {
                  return const Center(child: ShopperLoadingIndicator());
                } else if (state is ProductsLoadSuccess) {
                  if (state.products.isEmpty) {
                    return ShopperEmptyState(
                      icon: Icons.inventory_2_outlined,
                      message: l10n.noProductsFound,
                      actionLabel: l10n.refresh,
                      onAction: () => context.read<ProductsBloc>().add(const ProductsLoaded()),
                    );
                  }

                  return RefreshIndicator(
                    onRefresh: () async {
                      context.read<ProductsBloc>().add(ProductsRefreshed());
                    },
                    child: ShopperResponsiveGrid(
                      padding: const EdgeInsets.all(kSpacing16),
                      children: state.products.map((product) {
                        return ShopperProductCard(
                          name: product.displayName,
                          price: product.effectivePrice,
                          imageUrl: product.imageUrl,
                          onTap: () {
                            // Show product details
                          },
                          // Since ShopperProductCard might not have 'onAddToCart',
                          // we can wrap it or add a button if the design allows.
                        );
                      }).toList(),
                    ),
                  );
                } else if (state is ProductsError) {
                  return Center(
                    child: ShopperColumn(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        ShopperErrorText(state.message),
                        const SizedBox(height: kSpacing16),
                        ShopperPrimaryButton(
                          text: l10n.retry,
                          onPressed: () => context.read<ProductsBloc>().add(const ProductsLoaded()),
                        ),
                      ],
                    ),
                  );
                }
                return const SizedBox.shrink();
              },
            ),
          ),
        ],
      ),
    );
  }
}
