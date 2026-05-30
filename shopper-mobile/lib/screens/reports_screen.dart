import 'package:flutter/material.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import '../widgets/index.dart';

class ReportsScreen extends StatelessWidget {
  const ReportsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    
    return ShopperScreen(
      title: l10n.reports,
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(kSpacing16),
        child: ShopperColumn(
          spacing: kSpacing20,
          children: [
            _buildReportCard(context, 'Inventory Summary', 'Detailed valuation of stock', Icons.inventory),
            _buildReportCard(context, 'Sales Register', 'Daily and monthly sales logs', Icons.receipt_long, onTap: () => Navigator.pushNamed(context, '/sales-register')),
            _buildReportCard(context, 'VAT Report', 'Mushak compliance exports', Icons.account_balance),
            _buildReportCard(context, 'Business Analytics', 'ITR & EOQ metrics', Icons.insights),
          ],
        ),
      ),
    );
  }

  Widget _buildReportCard(BuildContext context, String title, String subtitle, IconData icon, {VoidCallback? onTap}) {
    return ShopperCard(
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: kPrimaryColor.withOpacity(0.1),
          child: Icon(icon, color: kPrimaryColor),
        ),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
        subtitle: Text(subtitle),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}
