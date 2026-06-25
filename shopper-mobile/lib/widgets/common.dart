import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/design_system.dart';
import '../core/theme_provider.dart';
import 'buttons.dart';
import 'layouts.dart';

// Reusable App Bar
class ShopperAppBar extends StatelessWidget implements PreferredSizeWidget {
  final String? title;
  final List<Widget>? actions;
  final bool showBackButton;
  final VoidCallback? onBackPressed;
  final Widget? leading;

  const ShopperAppBar({
    super.key,
    this.title,
    this.actions,
    this.showBackButton = true,
    this.onBackPressed,
    this.leading,
  });

  @override
  Widget build(BuildContext context) {
    return AppBar(
      title: title != null
          ? Text(
              title!,
              style: kHeadline6.copyWith(color: kOnPrimaryColor),
            )
          : null,
      backgroundColor: kPrimaryColor,
      foregroundColor: kOnPrimaryColor,
      elevation: 0,
      shadowColor: Colors.transparent,
      actions: actions,
      leading: leading ??
          (showBackButton && Navigator.canPop(context)
              ? IconButton(
                  icon: const Icon(Icons.arrow_back),
                  onPressed: onBackPressed ?? () => Navigator.of(context).pop(),
                )
              : null),
    );
  }

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight);
}

// Base Screen Scaffold
class ShopperScreen extends StatelessWidget {
  final String? title;
  final Widget body;
  final List<Widget>? actions;
  final Widget? floatingActionButton;
  final FloatingActionButtonLocation? floatingActionButtonLocation;
  final Widget? bottomNavigationBar;
  final bool showAppBar;
  final bool showBackButton;
  final VoidCallback? onBackPressed;
  final Widget? leading;
  final EdgeInsetsGeometry? padding;

  const ShopperScreen({
    super.key,
    this.title,
    required this.body,
    this.actions,
    this.floatingActionButton,
    this.floatingActionButtonLocation,
    this.bottomNavigationBar,
    this.showAppBar = true,
    this.showBackButton = true,
    this.onBackPressed,
    this.leading,
    this.padding = const EdgeInsets.all(kSpacing16),
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: showAppBar
          ? ShopperAppBar(
              title: title,
              actions: actions,
              showBackButton: showBackButton,
              onBackPressed: onBackPressed,
              leading: leading,
            )
          : null,
      body: Padding(
        padding: padding!,
        child: body,
      ),
      floatingActionButton: floatingActionButton,
      floatingActionButtonLocation: floatingActionButtonLocation,
      bottomNavigationBar: bottomNavigationBar,
    );
  }
}

// Form Field Label
class ShopperFieldLabel extends StatelessWidget {
  final String text;
  final bool required;

  const ShopperFieldLabel({
    super.key,
    required this.text,
    this.required = false,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: kSpacing8),
      child: RichText(
        text: TextSpan(
          text: text,
          style: kBodyMedium.copyWith(
            color: kOnSurfaceColor,
            fontWeight: FontWeight.w500,
          ),
          children: required
              ? [
                  const TextSpan(
                    text: ' *',
                    style: TextStyle(color: kErrorColor),
                  ),
                ]
              : null,
        ),
      ),
    );
  }
}

// Error Text
class ShopperErrorText extends StatelessWidget {
  final String error;

  const ShopperErrorText({
    super.key,
    required this.error,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: kSpacing4),
      child: Text(
        error,
        style: kCaption.copyWith(color: kErrorColor),
      ),
    );
  }
}

// Theme Switcher
class ShopperThemeSwitcher extends StatelessWidget {
  const ShopperThemeSwitcher({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<ThemeProvider>(
      builder: (context, themeProvider, child) {
        return ShopperCard(
          child: ShopperColumn(
            spacing: kSpacing16,
            children: [
              const ShopperSectionHeader(
                title: 'Theme',
                subtitle: 'Choose your preferred theme',
              ),
              ShopperColumn(
                spacing: kSpacing8,
                children: [
                  _buildThemeOption(
                    context,
                    themeProvider,
                    AppTheme.indigo,
                    'Light',
                    Icons.light_mode,
                  ),
                  _buildThemeOption(
                    context,
                    themeProvider,
                    AppTheme.midnight,
                    'Dark',
                    Icons.dark_mode,
                  ),
                  _buildThemeOption(
                    context,
                    themeProvider,
                    AppTheme.minimalist,
                    'System',
                    Icons.settings_suggest,
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildThemeOption(
    BuildContext context,
    ThemeProvider themeProvider,
    AppTheme theme,
    String label,
    IconData icon,
  ) {
    final isSelected = themeProvider.currentTheme == theme;

    return InkWell(
      onTap: () => themeProvider.setTheme(theme),
      borderRadius: BorderRadius.circular(kBorderRadiusMedium),
      child: Container(
        padding: const EdgeInsets.all(kSpacing12),
        decoration: BoxDecoration(
          color: isSelected
              ? Theme.of(context).colorScheme.primary.withValues(alpha: 0.1)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(kBorderRadiusMedium),
          border: Border.all(
            color: isSelected
                ? Theme.of(context).colorScheme.primary
                : Colors.grey[300]!,
            width: isSelected ? 2 : 1,
          ),
        ),
        child: Row(
          children: [
            Icon(
              icon,
              color: isSelected
                  ? Theme.of(context).colorScheme.primary
                  : Theme.of(context).colorScheme.onSurface,
            ),
            const SizedBox(width: kSpacing12),
            Expanded(
              child: Text(
                label,
                style: kBodyMedium.copyWith(
                  color: Theme.of(context).colorScheme.onSurface,
                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
                ),
              ),
            ),
            if (isSelected)
              Icon(
                Icons.check,
                color: Theme.of(context).colorScheme.primary,
              ),
          ],
        ),
      ),
    );
  }
}

// Product Card
class ShopperProductCard extends StatelessWidget {
  final String name;
  final String? description;
  final String price;
  final String? imageUrl;
  final VoidCallback? onTap;
  final bool isOutOfStock;

  const ShopperProductCard({
    super.key,
    required this.name,
    this.description,
    required this.price,
    this.imageUrl,
    this.onTap,
    this.isOutOfStock = false,
  });

  @override
  Widget build(BuildContext context) {
    return ShopperCard(
      onTap: isOutOfStock ? null : onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (imageUrl != null)
            Container(
              height: 120,
              width: double.infinity,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(kBorderRadiusMedium),
                image: DecorationImage(
                  image: NetworkImage(imageUrl!),
                  fit: BoxFit.cover,
                ),
              ),
            ),
          const SizedBox(height: kSpacing8),
          Text(
            name,
            style: kBodyLarge.copyWith(
              fontWeight: FontWeight.w600,
              color: isOutOfStock ? Colors.grey : kOnSurfaceColor,
            ),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
          if (description != null) ...[
            const SizedBox(height: kSpacing4),
            Text(
              description!,
              style: kBodySmall.copyWith(color: Colors.grey),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ],
          const SizedBox(height: kSpacing8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                price,
                style: kBodyLarge.copyWith(
                  fontWeight: FontWeight.w700,
                  color: kPrimaryColor,
                ),
              ),
              if (isOutOfStock)
                Text(
                  'Out of Stock',
                  style: kCaption.copyWith(color: kErrorColor),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

// Quantity Selector
class ShopperQuantitySelector extends StatelessWidget {
  final int quantity;
  final int minQuantity;
  final int maxQuantity;
  final ValueChanged<int> onChanged;

  const ShopperQuantitySelector({
    super.key,
    required this.quantity,
    this.minQuantity = 1,
    this.maxQuantity = 99,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        IconButton(
          onPressed: quantity > minQuantity
              ? () => onChanged(quantity - 1)
              : null,
          icon: const Icon(Icons.remove),
          style: IconButton.styleFrom(
            backgroundColor: kSurfaceColor,
            foregroundColor: quantity > minQuantity ? kPrimaryColor : Colors.grey,
          ),
        ),
        Container(
          width: 48,
          height: 48,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: kSurfaceColor,
            borderRadius: BorderRadius.circular(kBorderRadiusSmall),
          ),
          child: Text(
            quantity.toString(),
            style: kBodyLarge.copyWith(fontWeight: FontWeight.w600),
          ),
        ),
        IconButton(
          onPressed: quantity < maxQuantity
              ? () => onChanged(quantity + 1)
              : null,
          icon: const Icon(Icons.add),
          style: IconButton.styleFrom(
            backgroundColor: kSurfaceColor,
            foregroundColor: quantity < maxQuantity ? kPrimaryColor : Colors.grey,
          ),
        ),
      ],
    );
  }
}

// Empty State
class ShopperEmptyState extends StatelessWidget {
  final String title;
  final String? message;
  final IconData icon;
  final Widget? action;

  const ShopperEmptyState({
    super.key,
    required this.title,
    this.message,
    required this.icon,
    this.action,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(kSpacing32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              icon,
              size: 64,
              color: Colors.grey,
            ),
            const SizedBox(height: kSpacing16),
            Text(
              title,
              style: kHeadline5.copyWith(color: Colors.grey),
              textAlign: TextAlign.center,
            ),
            if (message != null) ...[
              const SizedBox(height: kSpacing8),
              Text(
                message!,
                style: kBodyMedium.copyWith(color: Colors.grey),
                textAlign: TextAlign.center,
              ),
            ],
            if (action != null) ...[
              const SizedBox(height: kSpacing24),
              action!,
            ],
          ],
        ),
      ),
    );
  }
}
