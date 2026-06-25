import 'package:flutter/material.dart';
import 'package:shopper_mobile/l10n/app_localizations.dart';
import '../widgets/index.dart';
import '../core/design_system.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    
    return ShopperScreen(
      title: l10n.appTitle,
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(kSpacing16),
        child: ShopperColumn(
          spacing: kSpacing24,
          children: [
            // Hero Welcome Section
            _buildHero(context),

            // Metrics Grid
            _buildMetricsGrid(context),

            // Recent Activities or Shortcuts
            _buildShortcuts(context),
            
            // i18n & Localization Sample
            _buildLocalizationSample(context),
          ],
        ),
      ),
    );
  }

  Widget _buildHero(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(kSpacing24),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [kPrimaryColor, kPrimaryColor.withValues(alpha: 0.8)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(kBorderRadiusLarge * 2),
        boxShadow: [
          BoxShadow(
            color: kPrimaryColor.withValues(alpha: 0.3),
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Good Morning!',
            style: TextStyle(
              color: Colors.white70,
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Shopper Enterprise',
            style: kHeadline3.copyWith(color: Colors.white, fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(20),
            ),
            child: const Text(
              'PRO PLAN • ACTIVE',
              style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.w900, letterSpacing: 1),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMetricsGrid(BuildContext context) {
    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisSpacing: kSpacing16,
      mainAxisSpacing: kSpacing16,
      childAspectRatio: 1.4,
      children: [
        _buildMetricCard('Total Sales', '৳45,230', Icons.trending_up, Colors.green),
        _buildMetricCard('Invoices', '128', Icons.description_outlined, kPrimaryColor),
        _buildMetricCard('Low Stock', '12 items', Icons.inventory_2_outlined, Colors.orange),
        _buildMetricCard('VAT Status', 'Compliant', Icons.verified_user_outlined, Colors.blue),
      ],
    );
  }

  Widget _buildMetricCard(String label, String value, IconData icon, Color color) {
    return ShopperCard(
      padding: const EdgeInsets.all(kSpacing16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Icon(icon, color: color, size: 24),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: kBodySmall.copyWith(color: Colors.grey, fontWeight: FontWeight.bold)),
              Text(value, style: kHeadline6.copyWith(fontWeight: FontWeight.w900)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildShortcuts(BuildContext context) {
    return ShopperColumn(
      spacing: kSpacing12,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('QUICK ACTIONS', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w900, color: Colors.grey, letterSpacing: 1)),
        Row(
          children: [
            Expanded(
              child: _buildActionChip(context, 'New Sale', Icons.add_shopping_cart, kPrimaryColor),
            ),
            const SizedBox(width: kSpacing12),
            Expanded(
              child: _buildActionChip(context, 'Reports', Icons.bar_chart, Colors.indigo),
            ),
          ],
        ),
        const SizedBox(height: kSpacing12),
        Row(
          children: [
            Expanded(
              child: _buildActionChip(
                context, 
                'Stock Adjustment', 
                Icons.inventory_2_outlined, 
                Colors.orange,
                onTap: () => Navigator.pushNamed(context, '/inventory'),
              ),
            ),
            const Expanded(child: SizedBox.shrink()),
          ],
        ),
      ],
    );
  }

  Widget _buildActionChip(BuildContext context, String label, IconData icon, Color color, {VoidCallback? onTap}) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.05),
          borderRadius: BorderRadius.circular(kBorderRadiusLarge),
          border: Border.all(color: color.withValues(alpha: 0.15)),
        ),
        padding: const EdgeInsets.all(kSpacing16),
        child: Row(
          children: [
            Icon(icon, color: color, size: 20),
            const SizedBox(width: 12),
            Text(label, style: kBodyMedium.copyWith(fontWeight: FontWeight.bold, color: color)),
          ],
        ),
      ),
    );
  }

  Widget _buildLocalizationSample(BuildContext context) {
    return const ShopperCard(
      padding: EdgeInsets.all(kSpacing16),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          ShopperColumn(
            spacing: 4,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Native Bengali Support', style: TextStyle(fontWeight: FontWeight.bold)),
              Text('Active locale: English', style: TextStyle(fontSize: 10, color: Colors.grey)),
            ],
          ),
          Text(
            '৳ ১২,৩৪,৫৬৭',
            style: TextStyle(fontFamily: 'Bengali', fontSize: 20, fontWeight: FontWeight.bold, color: kPrimaryColor),
          ),
        ],
      ),
    );
  }
}
