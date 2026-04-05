import 'package:flutter/material.dart';
import '../core/design_system.dart';

// Responsive Layout Builder
class ShopperResponsiveLayout extends StatelessWidget {
  final Widget mobile;
  final Widget? tablet;
  final Widget? desktop;

  const ShopperResponsiveLayout({
    super.key,
    required this.mobile,
    this.tablet,
    this.desktop,
  });

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth >= 1200 && desktop != null) {
          return desktop!;
        } else if (constraints.maxWidth >= 600 && tablet != null) {
          return tablet!;
        } else {
          return mobile;
        }
      },
    );
  }
}

// Responsive Grid Layout with Breakpoints
class ShopperResponsiveGrid extends StatelessWidget {
  final List<Widget> children;
  final int mobileCrossAxisCount;
  final int tabletCrossAxisCount;
  final int desktopCrossAxisCount;
  final double childAspectRatio;
  final double spacing;

  const ShopperResponsiveGrid({
    super.key,
    required this.children,
    this.mobileCrossAxisCount = 2,
    this.tabletCrossAxisCount = 3,
    this.desktopCrossAxisCount = 4,
    this.childAspectRatio = 1.0,
    this.spacing = kSpacing16,
  });

  @override
  Widget build(BuildContext context) {
    return ShopperResponsiveLayout(
      mobile: ShopperGrid(
        children: children,
        crossAxisCount: mobileCrossAxisCount,
        childAspectRatio: childAspectRatio,
        crossAxisSpacing: spacing,
        mainAxisSpacing: spacing,
      ),
      tablet: ShopperGrid(
        children: children,
        crossAxisCount: tabletCrossAxisCount,
        childAspectRatio: childAspectRatio,
        crossAxisSpacing: spacing,
        mainAxisSpacing: spacing,
      ),
      desktop: ShopperGrid(
        children: children,
        crossAxisCount: desktopCrossAxisCount,
        childAspectRatio: childAspectRatio,
        crossAxisSpacing: spacing,
        mainAxisSpacing: spacing,
      ),
    );
  }
}

// Sliver Grid for Custom Scroll Views
class ShopperSliverGrid extends StatelessWidget {
  final List<Widget> children;
  final int crossAxisCount;
  final double childAspectRatio;
  final double crossAxisSpacing;
  final double mainAxisSpacing;

  const ShopperSliverGrid({
    super.key,
    required this.children,
    this.crossAxisCount = 2,
    this.childAspectRatio = 1.0,
    this.crossAxisSpacing = kSpacing16,
    this.mainAxisSpacing = kSpacing16,
  });

  @override
  Widget build(BuildContext context) {
    return SliverGrid(
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: crossAxisCount,
        childAspectRatio: childAspectRatio,
        crossAxisSpacing: crossAxisSpacing,
        mainAxisSpacing: mainAxisSpacing,
      ),
      delegate: SliverChildBuilderDelegate(
        (context, index) => children[index],
        childCount: children.length,
      ),
    );
  }
}

// Section Header
class ShopperSectionHeader extends StatelessWidget {
  final String title;
  final String? subtitle;
  final Widget? action;
  final EdgeInsetsGeometry? padding;

  const ShopperSectionHeader({
    super.key,
    required this.title,
    this.subtitle,
    this.action,
    this.padding = const EdgeInsets.symmetric(vertical: kSpacing16),
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: padding!,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: kHeadline5,
                ),
                if (subtitle != null) ...[
                  const SizedBox(height: kSpacing4),
                  Text(
                    subtitle!,
                    style: kBodyMedium.copyWith(color: Colors.grey),
                  ),
                ],
              ],
            ),
          ),
          if (action != null) action!,
        ],
      ),
    );
  }
}

// Spacer Widgets
class ShopperSpacer extends StatelessWidget {
  final double height;
  final double? width;

  const ShopperSpacer({
    super.key,
    this.height = kSpacing16,
    this.width,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(height: height, width: width);
  }
}

// Horizontal Spacer
class ShopperHorizontalSpacer extends ShopperSpacer {
  const ShopperHorizontalSpacer({
    super.key,
    double width = kSpacing16,
  }) : super(width: width, height: 0);
}

// Vertical Spacer
class ShopperVerticalSpacer extends ShopperSpacer {
  const ShopperVerticalSpacer({
    super.key,
    double height = kSpacing16,
  }) : super(height: height, width: 0);
}

// Divider with custom styling
class ShopperDivider extends StatelessWidget {
  final double thickness;
  final Color? color;
  final EdgeInsetsGeometry? margin;

  const ShopperDivider({
    super.key,
    this.thickness = 1,
    this.color,
    this.margin = const EdgeInsets.symmetric(vertical: kSpacing16),
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: margin,
      height: thickness,
      color: color ?? Colors.grey[200],
    );
  }
}

// Card Container with different variants
class ShopperCardContainer extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final VoidCallback? onTap;
  final bool elevated;
  final Color? backgroundColor;
  final BorderRadius? borderRadius;

  const ShopperCardContainer({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(kSpacing16),
    this.onTap,
    this.elevated = false,
    this.backgroundColor,
    this.borderRadius,
  });

  @override
  Widget build(BuildContext context) {
    return ShopperCard(
      padding: padding,
      onTap: onTap,
      elevated: elevated,
      child: Container(
        decoration: BoxDecoration(
          color: backgroundColor ?? kSurfaceColor,
          borderRadius: borderRadius ?? BorderRadius.circular(kBorderRadiusLarge),
        ),
        child: child,
      ),
    );
  }
}

// Row Layout with responsive behavior
class ShopperRow extends StatelessWidget {
  final List<Widget> children;
  final MainAxisAlignment mainAxisAlignment;
  final CrossAxisAlignment crossAxisAlignment;
  final MainAxisSize mainAxisSize;
  final bool responsive;
  final double spacing;

  const ShopperRow({
    super.key,
    required this.children,
    this.mainAxisAlignment = MainAxisAlignment.start,
    this.crossAxisAlignment = CrossAxisAlignment.center,
    this.mainAxisSize = MainAxisSize.max,
    this.responsive = false,
    this.spacing = kSpacing8,
  });

  @override
  Widget build(BuildContext context) {
    if (responsive) {
      return Wrap(
        spacing: spacing,
        runSpacing: spacing,
        children: children,
      );
    }

    return Row(
      mainAxisAlignment: mainAxisAlignment,
      crossAxisAlignment: crossAxisAlignment,
      mainAxisSize: mainAxisSize,
      children: _addSpacing(children, spacing),
    );
  }

  List<Widget> _addSpacing(List<Widget> children, double spacing) {
    if (children.isEmpty) return children;

    final List<Widget> spacedChildren = [children.first];
    for (int i = 1; i < children.length; i++) {
      spacedChildren.add(SizedBox(width: spacing));
      spacedChildren.add(children[i]);
    }
    return spacedChildren;
  }
}

// Column Layout with consistent spacing
class ShopperColumn extends StatelessWidget {
  final List<Widget> children;
  final MainAxisAlignment mainAxisAlignment;
  final CrossAxisAlignment crossAxisAlignment;
  final MainAxisSize mainAxisSize;
  final double spacing;

  const ShopperColumn({
    super.key,
    required this.children,
    this.mainAxisAlignment = MainAxisAlignment.start,
    this.crossAxisAlignment = CrossAxisAlignment.center,
    this.mainAxisSize = MainAxisSize.max,
    this.spacing = kSpacing8,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: mainAxisAlignment,
      crossAxisAlignment: crossAxisAlignment,
      mainAxisSize: mainAxisSize,
      children: _addSpacing(children, spacing),
    );
  }

  List<Widget> _addSpacing(List<Widget> children, double spacing) {
    if (children.isEmpty) return children;

    final List<Widget> spacedChildren = [children.first];
    for (int i = 1; i < children.length; i++) {
      spacedChildren.add(SizedBox(height: spacing));
      spacedChildren.add(children[i]);
    }
    return spacedChildren;
  }
}

// Expandable Panel
class ShopperExpandablePanel extends StatefulWidget {
  final String title;
  final Widget child;
  final bool initiallyExpanded;
  final ValueChanged<bool>? onExpansionChanged;

  const ShopperExpandablePanel({
    super.key,
    required this.title,
    required this.child,
    this.initiallyExpanded = false,
    this.onExpansionChanged,
  });

  @override
  State<ShopperExpandablePanel> createState() => _ShopperExpandablePanelState();
}

class _ShopperExpandablePanelState extends State<ShopperExpandablePanel> {
  late bool _isExpanded;

  @override
  void initState() {
    super.initState();
    _isExpanded = widget.initiallyExpanded;
  }

  void _toggleExpanded() {
    setState(() {
      _isExpanded = !_isExpanded;
    });
    widget.onExpansionChanged?.call(_isExpanded);
  }

  @override
  Widget build(BuildContext context) {
    return ShopperCard(
      child: Column(
        children: [
          InkWell(
            onTap: _toggleExpanded,
            child: Padding(
              padding: const EdgeInsets.all(kSpacing16),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      widget.title,
                      style: kHeadline6,
                    ),
                  ),
                  Icon(
                    _isExpanded ? Icons.expand_less : Icons.expand_more,
                    color: kPrimaryColor,
                  ),
                ],
              ),
            ),
          ),
          if (_isExpanded)
            Padding(
              padding: const EdgeInsets.only(
                left: kSpacing16,
                right: kSpacing16,
                bottom: kSpacing16,
              ),
              child: widget.child,
            ),
        ],
      ),
    );
  }
}

// Tab Bar with custom styling
class ShopperTabBar extends StatelessWidget {
  final List<String> tabs;
  final int selectedIndex;
  final ValueChanged<int> onTabSelected;
  final bool isScrollable;

  const ShopperTabBar({
    super.key,
    required this.tabs,
    required this.selectedIndex,
    required this.onTabSelected,
    this.isScrollable = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: kSurfaceColor,
        border: Border(bottom: BorderSide(color: Colors.grey[200]!)),
      ),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        physics: isScrollable ? const BouncingScrollPhysics() : const NeverScrollableScrollPhysics(),
        child: Row(
          children: List.generate(tabs.length, (index) {
            final isSelected = index == selectedIndex;
            return InkWell(
              onTap: () => onTabSelected(index),
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: kSpacing16,
                  vertical: kSpacing12,
                ),
                decoration: BoxDecoration(
                  border: Border(
                    bottom: BorderSide(
                      color: isSelected ? kPrimaryColor : Colors.transparent,
                      width: 2,
                    ),
                  ),
                ),
                child: Text(
                  tabs[index],
                  style: kBodyLarge.copyWith(
                    color: isSelected ? kPrimaryColor : kOnSurfaceColor,
                    fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
                  ),
                ),
              ),
            );
          }),
        ),
      ),
    );
  }
}