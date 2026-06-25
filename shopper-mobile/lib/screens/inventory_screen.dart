import '../core/design_system.dart';
import '../widgets/index.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../core/bloc/products/products_bloc.dart';

class InventoryScreen extends StatefulWidget {
  const InventoryScreen({super.key});

  @override
  State<InventoryScreen> createState() => _InventoryScreenState();
}

class _InventoryScreenState extends State<InventoryScreen> {
  final TextEditingController _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
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

  void _showAdjustmentDialog(BuildContext context, dynamic product) {
    double quantity = 1.0;
    String type = 'damage';
    String notes = '';
    
    final types = [
      {'value': 'damage', 'label': 'Damaged'},
      {'value': 'gift_out', 'label': 'Gift/Promotional'},
      {'value': 'expired', 'label': 'Expired'},
      {'value': 'lost', 'label': 'Lost/Theft'},
      {'value': 'correction', 'label': 'Audit Correction'},
    ];

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => Container(
          padding: EdgeInsets.only(
            bottom: MediaQuery.of(context).viewInsets.bottom,
          ),
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(kBorderRadiusLarge * 2)),
          ),
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(kSpacing24),
            child: ShopperColumn(
              spacing: kSpacing24,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('Adjust Stock', style: kHeadline6.copyWith(fontWeight: FontWeight.w900)),
                    IconButton(
                      icon: const Icon(Icons.close),
                      onPressed: () => Navigator.pop(context),
                    ),
                  ],
                ),
                Text(
                  product.displayName,
                  style: kBodyMedium.copyWith(color: kPrimaryColor, fontWeight: FontWeight.bold),
                ),
                const ShopperDivider(),
                
                // Adjustment Type
                const Text('Adjustment Reason', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w900, color: Colors.grey)),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: types.map((t) {
                    final isSelected = type == t['value'];
                    return FilterChip(
                      selected: isSelected,
                      label: Text(t['label']!, style: TextStyle(
                        fontSize: 12, 
                        color: isSelected ? Colors.white : Colors.black87,
                        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                      )),
                      selectedColor: kPrimaryColor,
                      checkmarkColor: Colors.white,
                      onSelected: (val) => setState(() => type = t['value']!),
                    );
                  }).toList(),
                ),

                // Quantity
                Row(
                  children: [
                    const Expanded(
                      child: Text('Quantity to Deduct', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w900, color: Colors.grey)),
                    ),
                    Row(
                      children: [
                        IconButton(
                          icon: const Icon(Icons.remove_circle_outline, color: Colors.red),
                          onPressed: quantity > 1 ? () => setState(() => quantity--) : null,
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                          decoration: BoxDecoration(
                            border: Border.all(color: Colors.grey.withValues(alpha: 0.3)),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text(quantity.toInt().toString(), style: kHeadline6),
                        ),
                        IconButton(
                          icon: const Icon(Icons.add_circle_outline, color: Colors.green),
                          onPressed: () => setState(() => quantity++),
                        ),
                      ],
                    ),
                  ],
                ),

                // Notes
                ShopperInputField(
                  label: 'Notes (Optional)',
                  onChanged: (val) => notes = val,
                  
                ),

                const SizedBox(height: kSpacing12),
                
                ShopperPrimaryButton(
                  text: 'Confirm Adjustment',
                  onPressed: () {
                    context.read<ProductsBloc>().add(AdjustStockRequested(
                      sku: product.sku,
                      quantity: quantity,
                      type: type,
                      notes: notes,
                      reasonCode: type.toUpperCase(),
                    ));
                    Navigator.pop(context);
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Adjustment recorded and syncing...')),
                    );
                  },
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {


    return ShopperScreen(
      title: 'Inventory Audit',
      body: ShopperColumn(
        spacing: kSpacing16,
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: kSpacing16),
            child: ShopperSearchBar(
              controller: _searchController,
              hintText: 'Search SKU or Name...',
              onChanged: _onSearchChanged,
            ),
          ),

          Expanded(
            child: BlocBuilder<ProductsBloc, ProductsState>(
              builder: (context, state) {
                if (state is ProductsLoading) {
                  return const Center(child: ShopperLoadingIndicator());
                } else if (state is ProductsLoadSuccess) {
                  if (state.products.isEmpty) {
                    return const ShopperEmptyState(
                      title: 'Inventory', icon: Icons.inventory_2_outlined, message: 'No items matching search', action: SizedBox.shrink(),
                    );
                  }

                  return ListView.separated(
                    padding: const EdgeInsets.all(kSpacing16),
                    itemCount: state.products.length,
                    separatorBuilder: (context, index) => const SizedBox(height: kSpacing12),
                    itemBuilder: (context, index) {
                      final product = state.products[index];
                      return ShopperCard(
                        padding: const EdgeInsets.all(kSpacing16),
                        child: Row(
                          children: [
                            Container(
                              width: 50,
                              height: 50,
                              decoration: BoxDecoration(
                                color: kPrimaryColor.withValues(alpha: 0.05),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: const Icon(Icons.inventory_2, color: kPrimaryColor),
                            ),
                            const SizedBox(width: 16),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(product.displayName, style: kBodyLarge.copyWith(fontWeight: FontWeight.bold)),
                                  Text('SKU: ${product.sku}', style: kBodySmall.copyWith(color: Colors.grey)),
                                  const SizedBox(height: 4),
                                  Text(
                                    'Stock: ${product.stockQuantity.toInt()}', 
                                    style: TextStyle(
                                      color: product.stockQuantity < 5 ? Colors.red : Colors.green,
                                      fontWeight: FontWeight.bold,
                                      fontSize: 12,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            ShopperSecondaryButton(
                              text: 'Adjust',
                              
                              onPressed: () => _showAdjustmentDialog(context, product),
                            ),
                          ],
                        ),
                      );
                    },
                  );
                } else if (state is ProductsError) {
                  return Center(child: ShopperErrorText(error: state.message));
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
