import 'package:flutter/material.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import '../widgets/index.dart';
import '../screens/components_demo.dart';
import '../screens/products_screen.dart';
import '../screens/cart_screen.dart';
import '../screens/checkout_screen.dart';

class AppRouter {
  static const String home = '/';
  static const String products = '/products';
  static const String cart = '/cart';
  static const String checkout = '/checkout';
  static const String reports = '/reports';
  static const String settings = '/settings';
  static const String componentsDemo = '/components-demo';

  static Route<dynamic> generateRoute(RouteSettings settings) {
    switch (settings.name) {
      case home:
        return MaterialPageRoute(builder: (_) => const HomeScreen());
      case products:
        return MaterialPageRoute(builder: (_) => const ProductsScreen());
      case cart:
        return MaterialPageRoute(builder: (_) => const CartScreen());
      case checkout:
        return MaterialPageRoute(builder: (_) => const CheckoutScreen());
      case reports:
        return MaterialPageRoute(builder: (_) => const ReportsScreen());
      case settings:
        return MaterialPageRoute(builder: (_) => const SettingsScreen());
      case componentsDemo:
        return MaterialPageRoute(builder: (_) => const ComponentsDemoScreen());
      default:
        return MaterialPageRoute(
          builder: (_) => Scaffold(
            body: Center(
              child: Text('No route defined for ${settings.name}'),
            ),
          ),
        );
    }
  }
}

class MainNavigation extends StatefulWidget {
  const MainNavigation({super.key});

  @override
  State<MainNavigation> createState() => _MainNavigationState();
}

class _MainNavigationState extends State<MainNavigation> {
  int _selectedIndex = 0;

  static const List<Widget> _screens = [
    HomeScreen(),
    ProductsScreen(),
    CartScreen(),
    ReportsScreen(),
    SettingsScreen(),
  ];

  void _onItemTapped(int index) {
    setState(() {
      _selectedIndex = index;
    });
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      body: _screens[_selectedIndex],
      bottomNavigationBar: BottomNavigationBar(
        items: [
          BottomNavigationBarItem(
            icon: const Icon(Icons.home),
            label: l10n.appTitle,
          ),
          BottomNavigationBarItem(
            icon: const Icon(Icons.inventory),
            label: l10n.products,
          ),
          BottomNavigationBarItem(
            icon: const Icon(Icons.shopping_cart),
            label: l10n.cart,
          ),
          BottomNavigationBarItem(
            icon: const Icon(Icons.bar_chart),
            label: l10n.reports,
          ),
          BottomNavigationBarItem(
            icon: const Icon(Icons.settings),
            label: l10n.settings,
          ),
        ],
        currentIndex: _selectedIndex,
        onTap: _onItemTapped,
        type: BottomNavigationBarType.fixed,
      ),
    );
  }
}

// Placeholder screens
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ShopperScreen(
      title: AppLocalizations.of(context)?.appTitle ?? 'Shopper Mobile',
      body: ShopperColumn(
        spacing: kSpacing16,
        children: [
          Text(
            'Welcome to Shopper Mobile POS',
            style: kHeadline4,
            textAlign: TextAlign.center,
          ),
          ShopperPrimaryButton(
            text: 'View Components Demo',
            onPressed: () {
              Navigator.pushNamed(context, AppRouter.componentsDemo);
            },
          ),
          Consumer<ThemeProvider>(
            builder: (context, themeProvider, child) {
              return ShopperSecondaryButton(
                text: 'Toggle Theme (${themeProvider.currentTheme.name})',
                onPressed: () => themeProvider.toggleTheme(),
              );
            },
          ),
          ShopperGhostButton(
            text: 'Reports',
            onPressed: () {},
          ),
        ],
      ),
    );
  }
}

class ReportsScreen extends StatelessWidget {
  const ReportsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ShopperScreen(
      title: AppLocalizations.of(context)?.reports ?? 'Reports',
      body: const Center(child: Text('Reports')),
    );
  }
}

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ShopperScreen(
      title: AppLocalizations.of(context)?.settings ?? 'Settings',
      body: ShopperInfiniteScroll(
        itemBuilder: (context, index) {
          switch (index) {
            case 0:
              return const ShopperThemeSwitcher();
            case 1:
              return _buildLanguageSettings(context);
            case 2:
              return _buildNotificationSettings(context);
            case 3:
              return _buildPrivacySettings(context);
            case 4:
              return _buildAboutSection(context);
            default:
              return const SizedBox.shrink();
          }
        },
        itemCount: 5,
        padding: EdgeInsets.zero,
      ),
    );
  }

  Widget _buildLanguageSettings(BuildContext context) {
    return ShopperCard(
      child: ShopperColumn(
        spacing: kSpacing16,
        children: [
          ShopperSectionHeader(
            title: 'Language',
            subtitle: 'Choose your preferred language',
          ),
          ShopperDropdown<String>(
            value: 'en',
            items: const [
              DropdownMenuItem(value: 'en', child: Text('English')),
              DropdownMenuItem(value: 'bn', child: Text('বাংলা')),
            ],
            onChanged: (value) {
              // TODO: Implement language switching
            },
          ),
        ],
      ),
    );
  }

  Widget _buildNotificationSettings(BuildContext context) {
    return ShopperCard(
      child: ShopperColumn(
        spacing: kSpacing16,
        children: [
          ShopperSectionHeader(
            title: 'Notifications',
            subtitle: 'Manage your notification preferences',
          ),
          ShopperColumn(
            spacing: kSpacing12,
            children: [
              _buildSwitchSetting(
                'Push Notifications',
                'Receive push notifications for orders and updates',
                true,
                (value) {},
              ),
              _buildSwitchSetting(
                'Email Notifications',
                'Receive email updates about your account',
                false,
                (value) {},
              ),
              _buildSwitchSetting(
                'Sound',
                'Play sound for notifications',
                true,
                (value) {},
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildPrivacySettings(BuildContext context) {
    return ShopperCard(
      child: ShopperColumn(
        spacing: kSpacing16,
        children: [
          ShopperSectionHeader(
            title: 'Privacy & Security',
            subtitle: 'Manage your privacy settings',
          ),
          ShopperColumn(
            spacing: kSpacing12,
            children: [
              _buildActionSetting(
                'Change Password',
                'Update your account password',
                Icons.lock,
                () {},
              ),
              _buildActionSetting(
                'Biometric Authentication',
                'Use fingerprint or face unlock',
                Icons.fingerprint,
                () {},
              ),
              _buildActionSetting(
                'Data & Privacy',
                'View our privacy policy',
                Icons.privacy_tip,
                () {},
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildAboutSection(BuildContext context) {
    return ShopperCard(
      child: ShopperColumn(
        spacing: kSpacing16,
        children: [
          ShopperSectionHeader(
            title: 'About',
            subtitle: 'App version and information',
          ),
          ShopperColumn(
            spacing: kSpacing12,
            children: [
              _buildInfoSetting('Version', '1.0.0'),
              _buildInfoSetting('Build', '2024.1.0'),
              _buildActionSetting(
                'Rate App',
                'Leave a review on the app store',
                Icons.star,
                () {},
              ),
              _buildActionSetting(
                'Contact Support',
                'Get help with the app',
                Icons.support,
                () {},
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSwitchSetting(String title, String subtitle, bool value, ValueChanged<bool> onChanged) {
    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: kBodyMedium.copyWith(fontWeight: FontWeight.w600),
              ),
              if (subtitle.isNotEmpty)
                Text(
                  subtitle,
                  style: kBodySmall.copyWith(color: Colors.grey),
                ),
            ],
          ),
        ),
        Switch(
          value: value,
          onChanged: onChanged,
          activeColor: kPrimaryColor,
        ),
      ],
    );
  }

  Widget _buildActionSetting(String title, String subtitle, IconData icon, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(kBorderRadiusMedium),
      child: Padding(
        padding: const EdgeInsets.all(kSpacing12),
        child: Row(
          children: [
            Icon(icon, color: kPrimaryColor),
            const SizedBox(width: kSpacing12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: kBodyMedium.copyWith(fontWeight: FontWeight.w600),
                  ),
                  if (subtitle.isNotEmpty)
                    Text(
                      subtitle,
                      style: kBodySmall.copyWith(color: Colors.grey),
                    ),
                ],
              ),
            ),
            Icon(Icons.chevron_right, color: Colors.grey),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoSetting(String label, String value) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: kBodyMedium.copyWith(color: Colors.grey),
        ),
        Text(
          value,
          style: kBodyMedium.copyWith(fontWeight: FontWeight.w600),
        ),
      ],
    );
  }
}