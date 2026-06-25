import 'package:flutter/material.dart';
import 'package:shopper_mobile/l10n/app_localizations.dart';
import '../widgets/index.dart';
import '../core/design_system.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    
    return ShopperScreen(
      title: l10n.settings,
      body: ListView(
        padding: const EdgeInsets.all(kSpacing16),
        children: [
          _buildThemeSection(context),
          const SizedBox(height: kSpacing16),
          _buildLanguageSettings(context, l10n),
          const SizedBox(height: kSpacing16),
          _buildInfoSection(context),
        ],
      ),
    );
  }

  Widget _buildThemeSection(BuildContext context) {
    return const ShopperCard(
      padding: EdgeInsets.all(kSpacing16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ShopperSectionHeader(
            title: 'Appearance',
            subtitle: 'Customize your look',
          ),
          SizedBox(height: kSpacing16),
          ShopperThemeSwitcher(),
        ],
      ),
    );
  }

  Widget _buildLanguageSettings(BuildContext context, AppLocalizations l10n) {
    return ShopperCard(
      padding: const EdgeInsets.all(kSpacing16),
      child: ShopperColumn(
        spacing: kSpacing16,
        children: [
          const ShopperSectionHeader(
            title: 'Regional',
            subtitle: 'Language and currency',
          ),
          ShopperDropdown<String>(
            value: 'en',
            items: const [
              DropdownMenuItem(value: 'en', child: Text('English')),
              DropdownMenuItem(value: 'bn', child: Text('বাংলা')),
            ],
            onChanged: (value) {},
          ),
        ],
      ),
    );
  }

  Widget _buildInfoSection(BuildContext context) {
    return ShopperCard(
      padding: const EdgeInsets.all(kSpacing16),
      child: Column(
        children: [
          _buildInfoRow('Version', '2.0.0 (Hardened)'),
          const Divider(),
          _buildInfoRow('Engine', 'Flutter 3.x'),
          const Divider(),
          _buildInfoRow('Compliance', 'Mushak 6.3 Ready'),
        ],
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: Colors.grey, fontWeight: FontWeight.bold)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w900)),
        ],
      ),
    );
  }
}
