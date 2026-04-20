import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import '../core/bloc/cart/cart_bloc.dart';
import '../core/bloc/orders/orders_bloc.dart';
import '../widgets/index.dart';
import '../navigation/app_router.dart';

class CheckoutScreen extends StatefulWidget {
  const CheckoutScreen({super.key});

  @override
  State<CheckoutScreen> createState() => _CheckoutScreenState();
}

class _CheckoutScreenState extends State<CheckoutScreen> {
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _phoneController = TextEditingController();
  final TextEditingController _notesController = TextEditingController();

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  void _onPlaceOrder() {
    final cartState = context.read<CartBloc>().state;
    if (cartState is CartLoadSuccess) {
      context.read<OrdersBloc>().add(OrderCreated(
        cart: cartState.cart,
        customerName: _nameController.text.isNotEmpty ? _nameController.text : null,
        customerPhone: _phoneController.text.isNotEmpty ? _phoneController.text : null,
        notes: _notesController.text.isNotEmpty ? _notesController.text : null,
      ));
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return BlocListener<OrdersBloc, OrdersState>(
      listener: (context, state) {
        if (state is OrderCreatedSuccess) {
          // Clear cart after successful order (OrderRepositoryImpl already handles DB clear, but Bloc might need sync)
          context.read<CartBloc>().add(CartCleared());
          
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(l10n.orderPlacedSuccess)),
          );
          
          // Navigate to Home or Receipt Screen
          Navigator.pushNamedAndRemoveUntil(context, AppRouter.home, (route) => false);
        } else if (state is OrdersError) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(state.message), backgroundColor: Colors.red),
          );
        }
      },
      child: ShopperScreen(
        title: l10n.checkout,
        body: SingleChildScrollView(
          child: ShopperColumn(
            spacing: kSpacing24,
            padding: const EdgeInsets.all(kSpacing16),
            children: [
              // Order Summary Card
              _buildSummaryCard(),

              // Customer Info Card
              _buildCustomerInfoCard(),

              // Notes Card
              _buildNotesCard(),

              // Place Order Button
              BlocBuilder<OrdersBloc, OrdersState>(
                builder: (context, state) {
                  return ShopperPrimaryButton(
                    text: l10n.placeOrder,
                    isLoading: state is OrdersLoading,
                    onPressed: _onPlaceOrder,
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSummaryCard() {
    return BlocBuilder<CartBloc, CartState>(
      builder: (context, state) {
        if (state is CartLoadSuccess) {
          final cart = state.cart;
          return ShopperCard(
            child: ShopperColumn(
              spacing: kSpacing12,
              children: [
                ShopperSectionHeader(title: l10n.orderSummary),
                ...cart.items.map((item) => Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('${item.productName} x${item.quantity}', style: kBodyMedium),
                    Text((item.unitPrice * item.quantity).toStringAsFixed(2), style: kBodyMedium),
                  ],
                )),
                const Divider(),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(l10n.totalAmount, style: kHeadline6),
                    Text(cart.total.toStringAsFixed(2), style: kHeadline6.copyWith(color: kPrimaryColor)),
                  ],
                ),
              ],
            ),
          );
        }
        return const SizedBox.shrink();
      },
    );
  }

  Widget _buildCustomerInfoCard() {
    return ShopperCard(
      child: ShopperColumn(
        spacing: kSpacing16,
        children: [
          ShopperSectionHeader(title: l10n.customerInfo),
          ShopperInputField(
            label: l10n.customerName,
            controller: _nameController,
            hint: l10n.enterCustomerName,
          ),
          ShopperInputField(
            label: l10n.phoneNumber,
            controller: _phoneController,
            hint: l10n.enterPhoneNumber,
            keyboardType: TextInputType.phone,
          ),
        ],
      ),
    );
  }

  Widget _buildNotesCard() {
    return ShopperCard(
      child: ShopperColumn(
        spacing: kSpacing16,
        children: [
          ShopperSectionHeader(title: l10n.orderNotes),
          ShopperInputField(
            label: l10n.notes,
            controller: _notesController,
            hint: l10n.specialInstructions,
            maxLines: 3,
          ),
        ],
      ),
    );
  }
}
