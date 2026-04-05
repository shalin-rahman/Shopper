import 'package:flutter/material.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import '../widgets/index.dart';

// Demo screen showcasing all the reusable components
class ComponentsDemoScreen extends StatefulWidget {
  const ComponentsDemoScreen({super.key});

  @override
  State<ComponentsDemoScreen> createState() => _ComponentsDemoScreenState();
}

class _ComponentsDemoScreenState extends State<ComponentsDemoScreen> {
  final TextEditingController _searchController = TextEditingController();
  String? _selectedCategory;
  String? _selectedSort;
  DateTime? _selectedDate;
  int _currentPage = 1;
  final int _totalPages = 5;
  bool _isLoadingMore = false;
  int _itemCount = 10;

  final List<String> _categories = ['Electronics', 'Clothing', 'Books', 'Home', 'Sports'];
  final List<String> _sortOptions = ['Name A-Z', 'Name Z-A', 'Price Low-High', 'Price High-Low', 'Newest'];

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _loadMoreItems() {
    setState(() {
      _isLoadingMore = true;
    });

    // Simulate API call
    Future.delayed(const Duration(seconds: 2), () {
      setState(() {
        _itemCount += 10;
        _isLoadingMore = false;
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    return ShopperScreen(
      title: 'Components Demo',
      body: ShopperInfiniteScroll(
        itemBuilder: (context, index) {
          if (index == 0) return _buildSearchAndFilters();
          if (index == 1) return _buildProductGrid();
          if (index == 2) return _buildFormSection();
          if (index == 3) return _buildPaginationDemo();
          return _buildMiscComponents();
        },
        itemCount: 5,
        onLoadMore: _loadMoreItems,
        isLoading: _isLoadingMore,
        hasMoreData: _itemCount < 50,
        padding: EdgeInsets.zero,
      ),
    );
  }

  Widget _buildSearchAndFilters() {
    return ShopperColumn(
      spacing: kSpacing16,
      children: [
        ShopperSectionHeader(title: 'Search & Filters'),
        ShopperSearchBar(
          controller: _searchController,
          hintText: 'Search products...',
          onChanged: (value) {
            // Handle search
          },
        ),
        ShopperRow(
          spacing: kSpacing8,
          children: [
            Expanded(
              child: ShopperDropdown<String>(
                label: 'Category',
                value: _selectedCategory,
                items: _categories.map((category) => DropdownMenuItem(
                  value: category,
                  child: Text(category),
                )).toList(),
                onChanged: (value) {
                  setState(() {
                    _selectedCategory = value;
                  });
                },
              ),
            ),
            Expanded(
              child: ShopperSortDropdown(
                value: _selectedSort,
                options: _sortOptions,
                onChanged: (value) {
                  setState(() {
                    _selectedSort = value;
                  });
                },
              ),
            ),
          ],
        ),
        Wrap(
          spacing: kSpacing8,
          runSpacing: kSpacing8,
          children: [
            ShopperFilterChip(
              label: 'In Stock',
              selected: true,
              onSelected: (selected) {},
            ),
            ShopperFilterChip(
              label: 'On Sale',
              selected: false,
              onSelected: (selected) {},
            ),
            ShopperFilterChip(
              label: 'New Arrivals',
              selected: true,
              onSelected: (selected) {},
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildProductGrid() {
    return ShopperColumn(
      spacing: kSpacing16,
      children: [
        ShopperSectionHeader(title: 'Product Grid'),
        ShopperResponsiveGrid(
          children: List.generate(6, (index) => ShopperProductCard(
            name: 'Product ${index + 1}',
            description: 'This is a sample product description that shows how the card handles longer text.',
            price: '\$${(index + 1) * 25}.99',
            imageUrl: 'https://via.placeholder.com/200',
            onTap: () {},
          )),
        ),
      ],
    );
  }

  Widget _buildFormSection() {
    return ShopperColumn(
      spacing: kSpacing16,
      children: [
        ShopperSectionHeader(title: 'Form Components'),
        ShopperDatePicker(
          label: 'Select Date',
          initialDate: DateTime.now(),
          onDateSelected: (date) {
            setState(() {
              _selectedDate = date;
            });
          },
        ),
        ShopperInputField(
          label: 'Full Name',
          hint: 'Enter your full name',
          validator: (value) {
            if (value?.isEmpty ?? true) return 'Name is required';
            return null;
          },
        ),
        ShopperRow(
          spacing: kSpacing12,
          children: [
            Expanded(
              child: ShopperPrimaryButton(
                text: 'Submit',
                onPressed: () {},
              ),
            ),
            Expanded(
              child: ShopperSecondaryButton(
                text: 'Cancel',
                onPressed: () {},
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildPaginationDemo() {
    return ShopperColumn(
      spacing: kSpacing16,
      children: [
        ShopperSectionHeader(title: 'Pagination'),
        ShopperCardList(
          children: List.generate(5, (index) => ShopperCard(
            child: ListTile(
              title: Text('Item ${(_currentPage - 1) * 5 + index + 1}'),
              subtitle: Text('Description for item ${(_currentPage - 1) * 5 + index + 1}'),
              trailing: const Icon(Icons.arrow_forward_ios),
            ),
          )),
        ),
        ShopperPagination(
          currentPage: _currentPage,
          totalPages: _totalPages,
          onPageChanged: (page) {
            setState(() {
              _currentPage = page;
            });
          },
        ),
      ],
    );
  }

  Widget _buildMiscComponents() {
    return ShopperColumn(
      spacing: kSpacing16,
      children: [
        ShopperSectionHeader(title: 'Other Components'),
        ShopperExpandablePanel(
          title: 'Expandable Panel',
          child: ShopperColumn(
            spacing: kSpacing8,
            children: [
              Text('This is the expanded content.', style: kBodyMedium),
              ShopperQuantitySelector(
                quantity: 2,
                onChanged: (quantity) {},
              ),
            ],
          ),
        ),
        ShopperEmptyState(
          title: 'No Items Found',
          message: 'Try adjusting your search or filters.',
          icon: Icons.search_off,
          action: ShopperPrimaryButton(
            text: 'Clear Filters',
            onPressed: () {},
          ),
        ),
        // Theme demonstration
        Consumer<ThemeProvider>(
          builder: (context, themeProvider, child) {
            return ShopperCard(
              child: ShopperColumn(
                spacing: kSpacing12,
                children: [
                  ShopperSectionHeader(
                    title: 'Theme Demo',
                    subtitle: 'Current theme: ${themeProvider.currentTheme.name}',
                  ),
                  ShopperRow(
                    spacing: kSpacing8,
                    children: [
                      Expanded(
                        child: ShopperPrimaryButton(
                          text: 'Light',
                          onPressed: () => themeProvider.setTheme(AppTheme.light),
                        ),
                      ),
                      Expanded(
                        child: ShopperPrimaryButton(
                          text: 'Dark',
                          onPressed: () => themeProvider.setTheme(AppTheme.dark),
                        ),
                      ),
                      Expanded(
                        child: ShopperPrimaryButton(
                          text: 'System',
                          onPressed: () => themeProvider.setTheme(AppTheme.system),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            );
          },
        ),
      ],
    );
  }
}