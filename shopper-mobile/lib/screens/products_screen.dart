import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:shopper_mobile/l10n/app_localizations.dart';
import '../core/bloc/products/products_bloc.dart';
import '../widgets/index.dart';
import '../core/design_system.dart';

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
                      title: l10n.noProductsFound,
                      icon: Icons.inventory_2_outlined,
                      message: l10n.noProductsFound,
                      action: ShopperPrimaryButton(
                        text: l10n.refresh,
                        onPressed: () => context.read<ProductsBloc>().add(const ProductsLoaded()),
                      ),
                    );
                  }

                  return RefreshIndicator(
                    onRefresh: () async {
                      context.read<ProductsBloc>().add(ProductsRefreshed());
                    },
                    child: Padding(
                      padding: const EdgeInsets.all(kSpacing16),
                      child: ShopperResponsiveGrid(
                        children: state.products.map((product) {
                          return ShopperProductCard(
                            name: product.displayName,
                            price: '৳${product.effectivePrice.toStringAsFixed(2)}',
                            imageUrl: product.imageUrl,
                            onTap: () {},
                          );
                        }).toList(),
                      ),
                    ),
                  );
                } else if (state is ProductsError) {
                  return Center(
                    child: ShopperColumn(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        ShopperErrorText(error: state.message),
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
