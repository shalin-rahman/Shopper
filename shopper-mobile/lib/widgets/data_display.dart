import 'package:flutter/material.dart';
import '../core/design_system.dart';
import 'index.dart';

// Search Bar
class ShopperSearchBar extends StatelessWidget {
  final TextEditingController? controller;
  final String? hintText;
  final ValueChanged<String>? onChanged;
  final VoidCallback? onClear;
  final bool showClearButton;
  final Widget? leading;
  final Widget? trailing;

  const ShopperSearchBar({
    super.key,
    this.controller,
    this.hintText,
    this.onChanged,
    this.onClear,
    this.showClearButton = true,
    this.leading,
    this.trailing,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: kMinTouchTarget,
      decoration: BoxDecoration(
        color: kSurfaceColor,
        borderRadius: BorderRadius.circular(kBorderRadiusMedium),
        border: Border.all(color: Colors.grey[300]!),
      ),
      child: TextField(
        controller: controller,
        onChanged: onChanged,
        style: kBodyMedium.copyWith(color: kOnSurfaceColor),
        decoration: InputDecoration(
          hintText: hintText ?? 'Search...',
          hintStyle: kBodyMedium.copyWith(color: Colors.grey),
          prefixIcon: leading ?? const Icon(Icons.search, color: Colors.grey),
          suffixIcon: showClearButton && controller?.text.isNotEmpty == true
              ? IconButton(
                  icon: const Icon(Icons.clear),
                  onPressed: () {
                    controller?.clear();
                    onClear?.call();
                  },
                )
              : trailing,
          border: InputBorder.none,
          contentPadding: const EdgeInsets.symmetric(
            horizontal: kSpacing16,
            vertical: kSpacing12,
          ),
        ),
      ),
    );
  }
}

// Filter Chip
class ShopperFilterChip extends StatelessWidget {
  final String label;
  final bool selected;
  final ValueChanged<bool>? onSelected;
  final Widget? avatar;

  const ShopperFilterChip({
    super.key,
    required this.label,
    this.selected = false,
    this.onSelected,
    this.avatar,
  });

  @override
  Widget build(BuildContext context) {
    return FilterChip(
      label: Text(label),
      selected: selected,
      onSelected: onSelected,
      avatar: avatar,
      backgroundColor: kSurfaceColor,
      selectedColor: kPrimaryColor.withOpacity(0.1),
      checkmarkColor: kPrimaryColor,
      labelStyle: kBodyMedium.copyWith(
        color: selected ? kPrimaryColor : kOnSurfaceColor,
        fontWeight: selected ? FontWeight.w600 : FontWeight.normal,
      ),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(kBorderRadiusLarge),
        side: BorderSide(
          color: selected ? kPrimaryColor : Colors.grey[300]!,
        ),
      ),
    );
  }
}

// Responsive Grid Layout
class ShopperGrid extends StatelessWidget {
  final List<Widget> children;
  final int crossAxisCount;
  final double childAspectRatio;
  final double crossAxisSpacing;
  final double mainAxisSpacing;

  const ShopperGrid({
    super.key,
    required this.children,
    this.crossAxisCount = 2,
    this.childAspectRatio = 1.0,
    this.crossAxisSpacing = kSpacing16,
    this.mainAxisSpacing = kSpacing16,
  });

  @override
  Widget build(BuildContext context) {
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: crossAxisCount,
        childAspectRatio: childAspectRatio,
        crossAxisSpacing: crossAxisSpacing,
        mainAxisSpacing: mainAxisSpacing,
      ),
      itemCount: children.length,
      itemBuilder: (context, index) => children[index],
    );
  }
}

// Dropdown Field
class ShopperDropdown<T> extends StatelessWidget {
  final String? label;
  final T? value;
  final List<DropdownMenuItem<T>> items;
  final ValueChanged<T?>? onChanged;
  final String? hint;
  final String? error;
  final bool required;

  const ShopperDropdown({
    super.key,
    this.label,
    this.value,
    required this.items,
    this.onChanged,
    this.hint,
    this.error,
    this.required = false,
  });

  @override
  Widget build(BuildContext context) {
    final bool hasError = error != null && error!.isNotEmpty;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (label != null) ShopperFieldLabel(text: label!, required: required),
        Container(
          height: kMinTouchTarget,
          decoration: BoxDecoration(
            border: Border.all(color: hasError ? kErrorColor : Colors.grey[300]!),
            borderRadius: BorderRadius.circular(kBorderRadiusMedium),
          ),
          child: DropdownButtonFormField<T>(
            value: value,
            items: items,
            onChanged: onChanged,
            hint: hint != null ? Text(hint!) : null,
            style: kBodyMedium.copyWith(color: kOnSurfaceColor),
            decoration: const InputDecoration(
              border: InputBorder.none,
              contentPadding: EdgeInsets.symmetric(
                horizontal: kSpacing16,
                vertical: kSpacing12,
              ),
            ),
            icon: const Icon(Icons.arrow_drop_down),
            dropdownColor: kSurfaceColor,
          ),
        ),
        if (hasError) ShopperErrorText(error: error!),
      ],
    );
  }
}

// Date Picker Field
class ShopperDatePicker extends StatefulWidget {
  final String? label;
  final DateTime? initialDate;
  final DateTime? firstDate;
  final DateTime? lastDate;
  final ValueChanged<DateTime?>? onDateSelected;
  final String? hint;
  final String? error;
  final bool required;

  const ShopperDatePicker({
    super.key,
    this.label,
    this.initialDate,
    this.firstDate,
    this.lastDate,
    this.onDateSelected,
    this.hint,
    this.error,
    this.required = false,
  });

  @override
  State<ShopperDatePicker> createState() => _ShopperDatePickerState();
}

class _ShopperDatePickerState extends State<ShopperDatePicker> {
  DateTime? _selectedDate;

  @override
  void initState() {
    super.initState();
    _selectedDate = widget.initialDate;
  }

  Future<void> _selectDate(BuildContext context) async {
    final DateTime? picked = await showDatePicker(
      context: context,
      initialDate: _selectedDate ?? DateTime.now(),
      firstDate: widget.firstDate ?? DateTime(2000),
      lastDate: widget.lastDate ?? DateTime(2101),
    );
    if (picked != null && picked != _selectedDate) {
      setState(() {
        _selectedDate = picked;
      });
      widget.onDateSelected?.call(_selectedDate);
    }
  }

  @override
  Widget build(BuildContext context) {
    final bool hasError = widget.error != null && widget.error!.isNotEmpty;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (widget.label != null)
          ShopperFieldLabel(text: widget.label!, required: widget.required),
        InkWell(
          onTap: () => _selectDate(context),
          child: Container(
            height: kMinTouchTarget,
            padding: const EdgeInsets.symmetric(
              horizontal: kSpacing16,
              vertical: kSpacing12,
            ),
            decoration: BoxDecoration(
              border: Border.all(color: hasError ? kErrorColor : Colors.grey[300]!),
              borderRadius: BorderRadius.circular(kBorderRadiusMedium),
            ),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    _selectedDate != null
                        ? '${_selectedDate!.day}/${_selectedDate!.month}/${_selectedDate!.year}'
                        : widget.hint ?? 'Select date',
                    style: kBodyMedium.copyWith(
                      color: _selectedDate != null ? kOnSurfaceColor : Colors.grey,
                    ),
                  ),
                ),
                const Icon(Icons.calendar_today, color: Colors.grey),
              ],
            ),
          ),
        ),
        if (hasError) ShopperErrorText(error: widget.error!),
      ],
    );
  }
}

// Card List View
class ShopperCardList extends StatelessWidget {
  final List<Widget> children;
  final EdgeInsetsGeometry? padding;
  final double spacing;

  const ShopperCardList({
    super.key,
    required this.children,
    this.padding,
    this.spacing = kSpacing12,
  });

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      padding: padding,
      itemCount: children.length,
      separatorBuilder: (context, index) => SizedBox(height: spacing),
      itemBuilder: (context, index) => children[index],
    );
  }
}

// Infinite Scroll List
class ShopperInfiniteScroll extends StatefulWidget {
  final Widget Function(BuildContext, int) itemBuilder;
  final int itemCount;
  final VoidCallback? onLoadMore;
  final bool isLoading;
  final bool hasMoreData;
  final EdgeInsetsGeometry? padding;
  final ScrollPhysics? physics;

  const ShopperInfiniteScroll({
    super.key,
    required this.itemBuilder,
    required this.itemCount,
    this.onLoadMore,
    this.isLoading = false,
    this.hasMoreData = true,
    this.padding,
    this.physics,
  });

  @override
  State<ShopperInfiniteScroll> createState() => _ShopperInfiniteScrollState();
}

class _ShopperInfiniteScrollState extends State<ShopperInfiniteScroll> {
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.position.pixels ==
        _scrollController.position.maxScrollExtent) {
      if (!widget.isLoading && widget.hasMoreData) {
        widget.onLoadMore?.call();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      controller: _scrollController,
      padding: widget.padding,
      physics: widget.physics,
      itemCount: widget.itemCount + (widget.isLoading ? 1 : 0),
      itemBuilder: (context, index) {
        if (index == widget.itemCount) {
          return const Padding(
            padding: EdgeInsets.all(kSpacing16),
            child: Center(child: ShopperLoadingIndicator()),
          );
        }
        return widget.itemBuilder(context, index);
      },
    );
  }
}

// Pagination Controls
class ShopperPagination extends StatelessWidget {
  final int currentPage;
  final int totalPages;
  final ValueChanged<int> onPageChanged;
  final bool showPageNumbers;
  final int maxVisiblePages;

  const ShopperPagination({
    super.key,
    required this.currentPage,
    required this.totalPages,
    required this.onPageChanged,
    this.showPageNumbers = true,
    this.maxVisiblePages = 5,
  });

  @override
  Widget build(BuildContext context) {
    if (totalPages <= 1) return const SizedBox.shrink();

    return Container(
      padding: const EdgeInsets.symmetric(vertical: kSpacing16),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Previous button
          IconButton(
            onPressed: currentPage > 1 ? () => onPageChanged(currentPage - 1) : null,
            icon: const Icon(Icons.chevron_left),
            style: IconButton.styleFrom(
              backgroundColor: kSurfaceColor,
              foregroundColor: currentPage > 1 ? kPrimaryColor : Colors.grey,
            ),
          ),

          if (showPageNumbers) ..._buildPageNumbers(),

          // Next button
          IconButton(
            onPressed: currentPage < totalPages ? () => onPageChanged(currentPage + 1) : null,
            icon: const Icon(Icons.chevron_right),
            style: IconButton.styleFrom(
              backgroundColor: kSurfaceColor,
              foregroundColor: currentPage < totalPages ? kPrimaryColor : Colors.grey,
            ),
          ),
        ],
      ),
    );
  }

  List<Widget> _buildPageNumbers() {
    final List<Widget> pages = [];
    final int startPage = (currentPage - maxVisiblePages ~/ 2).clamp(1, totalPages - maxVisiblePages + 1);
    final int endPage = (startPage + maxVisiblePages - 1).clamp(1, totalPages);

    for (int i = startPage; i <= endPage; i++) {
      pages.add(
        Container(
          margin: const EdgeInsets.symmetric(horizontal: kSpacing4),
          child: InkWell(
            onTap: () => onPageChanged(i),
            borderRadius: BorderRadius.circular(kBorderRadiusSmall),
            child: Container(
              width: 40,
              height: 40,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: i == currentPage ? kPrimaryColor : kSurfaceColor,
                borderRadius: BorderRadius.circular(kBorderRadiusSmall),
                border: Border.all(color: i == currentPage ? kPrimaryColor : Colors.grey[300]!),
              ),
              child: Text(
                i.toString(),
                style: kBodyMedium.copyWith(
                  color: i == currentPage ? kOnPrimaryColor : kOnSurfaceColor,
                  fontWeight: i == currentPage ? FontWeight.w600 : FontWeight.normal,
                ),
              ),
            ),
          ),
        ),
      );
    }

    return pages;
  }
}

// Sort Dropdown
class ShopperSortDropdown extends StatelessWidget {
  final String? label;
  final String? value;
  final List<String> options;
  final ValueChanged<String?>? onChanged;

  const ShopperSortDropdown({
    super.key,
    this.label,
    this.value,
    required this.options,
    this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return ShopperDropdown<String>(
      label: label ?? 'Sort by',
      value: value,
      items: options.map((option) => DropdownMenuItem(
        value: option,
        child: Text(option),
      )).toList(),
      onChanged: onChanged,
    );
  }
}

// Filter Bar
class ShopperFilterBar extends StatelessWidget {
  final List<Widget> filters;
  final VoidCallback? onClearAll;

  const ShopperFilterBar({
    super.key,
    required this.filters,
    this.onClearAll,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(kSpacing16),
      decoration: BoxDecoration(
        color: kSurfaceColor,
        border: Border(bottom: BorderSide(color: Colors.grey[200]!)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Filters',
                style: kHeadline6,
              ),
              if (onClearAll != null)
                TextButton(
                  onPressed: onClearAll,
                  child: Text(
                    'Clear All',
                    style: kBodyMedium.copyWith(color: kPrimaryColor),
                  ),
                ),
            ],
          ),
          const SizedBox(height: kSpacing12),
          Wrap(
            spacing: kSpacing8,
            runSpacing: kSpacing8,
            children: filters,
          ),
        ],
      ),
    );
  }
}