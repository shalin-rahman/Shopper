import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../core/bloc/orders/orders_bloc.dart';
import '../widgets/index.dart';
import '../core/design_system.dart';

class DailySalesRegisterScreen extends StatefulWidget {
  const DailySalesRegisterScreen({super.key});

  @override
  State<DailySalesRegisterScreen> createState() => _DailySalesRegisterScreenState();
}

class _DailySalesRegisterScreenState extends State<DailySalesRegisterScreen> {
  @override
  void initState() {
    super.initState();
    context.read<OrdersBloc>().add(const OrdersLoaded());
  }

  @override
  Widget build(BuildContext context) {
    return ShopperScreen(
      title: 'Sales Register',
      body: BlocBuilder<OrdersBloc, OrdersState>(
        builder: (context, state) {
          if (state is OrdersLoading) {
            return const Center(child: ShopperLoadingIndicator());
          } else if (state is OrdersLoadSuccess) {
            final orders = state.orders;
            if (orders.isEmpty) {
              return const ShopperEmptyState(
                title: 'No Sales',
                icon: Icons.receipt_long_outlined,
                message: 'No sales recorded yet',
              );
            }

            return ListView.separated(
              padding: const EdgeInsets.all(kSpacing16),
              itemCount: orders.length,
              separatorBuilder: (context, index) => const SizedBox(height: kSpacing12),
              itemBuilder: (context, index) {
                final order = orders[index];
                final isSynced = order.isSynced;

                return ShopperCard(
                  padding: const EdgeInsets.all(kSpacing16),
                  child: Column(
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(order.orderNumber, style: kHeadline6.copyWith(fontSize: 16, fontWeight: FontWeight.w900)),
                              Text(
                                '${order.createdAt.hour}:${order.createdAt.minute.toString().padLeft(2, '0')} • ${order.items.length} items',
                                style: kBodySmall.copyWith(color: Colors.grey),
                              ),
                            ],
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(
                              color: isSynced ? Colors.green.withValues(alpha: 0.1) : Colors.orange.withValues(alpha: 0.1),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              isSynced ? 'SYNCED' : 'OFFLINE',
                              style: TextStyle(
                                color: isSynced ? Colors.green : Colors.orange,
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                                letterSpacing: 1,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('Total Amount', style: kBodyMedium),
                          Text('৳${order.total.toStringAsFixed(2)}', style: kHeadline6.copyWith(color: kPrimaryColor, fontWeight: FontWeight.w900)),
                        ],
                      ),
                    ],
                  ),
                );
              },
            );
          } else if (state is OrdersError) {
            return Center(child: ShopperErrorText(error: state.message));
          }
          return const SizedBox.shrink();
        },
      ),
    );
  }
}
