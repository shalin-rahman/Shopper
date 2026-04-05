# Shopper Mobile - Reusable Components Library

This document outlines all the reusable UI components available in the Shopper Mobile Flutter app.

## 📦 Component Categories

### Buttons (`widgets/buttons.dart`)
- `ShopperPrimaryButton` - Main action button with loading state
- `ShopperSecondaryButton` - Secondary action button with outline style
- `ShopperGhostButton` - Minimal button for less prominent actions
- `ShopperLoadingIndicator` - Reusable loading spinner

### Common Components (`widgets/common.dart`)
- `ShopperAppBar` - Consistent app bar with design system styling
- `ShopperScreen` - Base screen scaffold with padding and app bar
- `ShopperCard` - Basic card container with optional tap and elevation
- `ShopperBottomSheet` - Modal bottom sheet with handle
- `ShopperFieldLabel` - Form field label with optional required indicator
- `ShopperErrorText` - Error message display
- `ShopperProductCard` - Product display card with image, name, price
- `ShopperQuantitySelector` - +/- quantity controls
- `ShopperEmptyState` - Empty state display with icon and action

### Data Display (`widgets/data_display.dart`)
- `ShopperSearchBar` - Search input with clear button
- `ShopperFilterChip` - Filter selection chips
- `ShopperGrid` - Responsive grid layout
- `ShopperDropdown<T>` - Generic dropdown with validation
- `ShopperDatePicker` - Date selection with calendar picker
- `ShopperCardList` - List of cards with consistent spacing
- `ShopperInfiniteScroll` - Infinite scroll list with loading indicator
- `ShopperPagination` - Page navigation controls
- `ShopperSortDropdown` - Sort options dropdown
- `ShopperFilterBar` - Filter controls container

### Layout Components (`widgets/layouts.dart`)
- `ShopperResponsiveLayout` - Responsive layout builder
- `ShopperResponsiveGrid` - Grid that adapts to screen size
- `ShopperSliverGrid` - Grid for custom scroll views
- `ShopperSectionHeader` - Section titles with optional actions
- `ShopperSpacer` - Consistent spacing widgets
- `ShopperDivider` - Custom styled dividers
- `ShopperCardContainer` - Enhanced card with background options
- `ShopperRow` - Row with automatic spacing
- `ShopperColumn` - Column with automatic spacing
- `ShopperExpandablePanel` - Collapsible content panels
- `ShopperTabBar` - Custom styled tab navigation

## 🎯 Usage Examples

### Basic Screen Structure
```dart
class MyScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return ShopperScreen(
      title: 'My Screen',
      body: ShopperColumn(
        spacing: kSpacing16,
        children: [
          ShopperSearchBar(
            hintText: 'Search...',
            onChanged: (value) => print(value),
          ),
          ShopperPrimaryButton(
            text: 'Submit',
            onPressed: () => print('Submitted'),
          ),
        ],
      ),
    );
  }
}
```

### Product Grid with Search
```dart
ShopperColumn(
  children: [
    ShopperSearchBar(
      controller: _searchController,
      onChanged: _onSearchChanged,
    ),
    ShopperResponsiveGrid(
      children: products.map((product) => ShopperProductCard(
        name: product.name,
        price: product.price,
        imageUrl: product.imageUrl,
        onTap: () => _onProductTap(product),
      )).toList(),
    ),
  ],
)
```

### Form with Validation
```dart
ShopperColumn(
  children: [
    ShopperInputField(
      label: 'Email',
      hint: 'Enter your email',
      validator: (value) => value?.contains('@') ?? false ? null : 'Invalid email',
    ),
    ShopperDatePicker(
      label: 'Birth Date',
      onDateSelected: (date) => print(date),
    ),
    ShopperDropdown<String>(
      label: 'Category',
      items: categories.map((cat) => DropdownMenuItem(
        value: cat,
        child: Text(cat),
      )).toList(),
      onChanged: (value) => print(value),
    ),
  ],
)
```

### Infinite Scroll List
```dart
ShopperInfiniteScroll(
  itemBuilder: (context, index) => ShopperCard(
    child: ListTile(
      title: Text('Item $index'),
      subtitle: Text('Description $index'),
    ),
  ),
  itemCount: _items.length,
  onLoadMore: _loadMoreItems,
  isLoading: _isLoading,
  hasMoreData: _hasMoreData,
)
```

### Responsive Layout
```dart
ShopperResponsiveLayout(
  mobile: ShopperColumn(children: [/* mobile layout */]),
  tablet: ShopperRow(children: [/* tablet layout */]),
  desktop: ShopperGrid(children: [/* desktop layout */]),
)
```

## 🎨 Design System Integration

All components follow the established design system:
- Colors: `kPrimaryColor`, `kSecondaryColor`, `kSurfaceColor`, etc.
- Typography: `kHeadline1` through `kCaption`
- Spacing: `kSpacing4`, `kSpacing8`, `kSpacing16`, etc.
- Border radius: `kBorderRadiusSmall`, `kBorderRadiusMedium`, etc.

## 📱 Responsive Design

Components automatically adapt to different screen sizes:
- `ShopperResponsiveGrid` adjusts columns based on screen width
- `ShopperRow` can wrap on smaller screens with `responsive: true`
- Touch targets meet minimum size requirements (`kMinTouchTarget`)

## 🔧 Customization

Most components accept customization parameters:
- Colors, spacing, and styling can be overridden
- Callbacks for user interactions
- Loading states and error handling
- Accessibility considerations

## 📋 Demo Screen

Navigate to the Components Demo screen from the home page to see all components in action with interactive examples.