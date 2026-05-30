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
  final TextEditingController _amountPaidController = TextEditingController();

  String _paymentMethod = 'cash';

  @override
  void initState() {
    super.initState();
    final cartState = context.read<CartBloc>().state;
    if (cartState is CartLoadSuccess) {
      _amountPaidController.text = cartState.cart.total.toStringAsFixed(2);
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    _notesController.dispose();
    _amountPaidController.dispose();
    super.dispose();
  }

  void _onPlaceOrder() {
    final cartState = context.read<CartBloc>().state;
    if (cartState is CartLoadSuccess) {
      final double amountPaid = double.tryParse(_amountPaidController.text) ?? 0;
      
      context.read<OrdersBloc>().add(OrderCreated(
        cart: cartState.cart,
        customerName: _nameController.text.isNotEmpty ? _nameController.text : null,
        customerPhone: _phoneController.text.isNotEmpty ? _phoneController.text : null,
        notes: _notesController.text.isNotEmpty ? _notesController.text : null,
        paymentMethod: _paymentMethod,
        amountPaid: amountPaid,
      ));
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return BlocListener<OrdersBloc, OrdersState>(
      listener: (context, state) {
        if (state is OrderCreatedSuccess) {
          context.read<CartBloc>().add(CartCleared());
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(l10n.orderPlacedSuccess)),
          );
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
              _buildSummaryCard(),
              _buildCustomerInfoCard(),
              _buildPaymentCard(),
              _buildNotesCard(),
              
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
                    Text(item.lineTotal.toStringAsFixed(2), style: kBodyMedium),
                  ],
                )),
                const ShopperDivider(),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(l10n.totalAmount, style: kHeadline6),
                    Text(cart.total.toStringAsFixed(2), style: kHeadline6.copyWith(color: kPrimaryColor, fontWeight: FontWeight.black)),
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
    final l10n = AppLocalizations.of(context)!;
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

  Widget _buildPaymentCard() {
    final methods = [
      {'id': 'cash', 'label': 'Cash', 'icon': Icons.payments_outlined},
      {'id': 'mfs', 'label': 'MFS (bKash/Nagad)', 'icon': Icons.smartphone_outlined},
      {'id': 'card', 'label': 'Bank Card', 'icon': Icons.credit_card_outlined},
      {'id': 'credit', 'label': 'On Credit', 'icon': Icons.history_edu_outlined},
    ];

    return ShopperCard(
      child: ShopperColumn(
        spacing: kSpacing16,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const ShopperSectionHeader(title: 'Payment Details'),
          
          const Text('Payment Method', style: TextStyle(fontSize: 12, fontWeight: FontWeight.black, color: Colors.grey)),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: methods.map((m) {
              final isSelected = _paymentMethod == m['id'];
              return ChoiceChip(
                label: Text(m['label']! as String),
                selected: isSelected,
                avatar: Icon(m['icon']! as IconData, size: 16, color: isSelected ? Colors.white : kPrimaryColor),
                onSelected: (val) => setState(() => _paymentMethod = m['id']! as String),
                selectedColor: kPrimaryColor,
                labelStyle: TextStyle(color: isSelected ? Colors.white : Colors.black87, fontWeight: isSelected ? FontWeight.bold : FontWeight.normal),
              );
            }).toList(),
          ),

          ShopperInputField(
            label: 'Amount Collected (৳)',
            controller: _amountPaidController,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            hint: '0.00',
          ),
        ],
      ),
    );
  }

  Widget _buildNotesCard() {
    final l10n = AppLocalizations.of(context)!;
    return ShopperCard(
      child: ShopperColumn(
        spacing: kSpacing16,
        children: [
          ShopperSectionHeader(title: l10n.orderNotes),
          ShopperInputField(
            label: l10n.notes,
            controller: _notesController,
            hint: l10n.specialInstructions,
            maxLines: 2,
          ),
        ],
      ),
    );
  }
}
