# Shopper Mobile - Theme System

This document outlines the comprehensive theme system implemented in the Shopper Mobile Flutter app.

##  Theme Architecture

### Theme Provider (`core/theme_provider.dart`)
The app uses a robust theme management system with the following features:

- **Three Theme Modes**: Light, Dark, and System (follows device setting)
- **Persistent Storage**: Theme preference saved using SharedPreferences
- **Reactive Updates**: Uses Provider for state management and automatic UI updates
- **Complete Theme Definitions**: Comprehensive Material Design 3 themes

### Theme Options
```dart
enum AppTheme {
  light,    // Always light theme
  dark,     // Always dark theme
  system,   // Follows system preference (default)
}
```

##  Light Theme

### Color Palette
- **Primary**: Blue (#1976D2) - Professional and trustworthy
- **Secondary**: Pink (#DC004E) - Energetic and modern
- **Surface**: White (#FFFFFF) - Clean and bright
- **Background**: White (#FFFFFF) - Consistent with surface
- **Error**: Red (#D32F2F) - Clear error indication

### Component Styling
- **App Bar**: Blue background with white text
- **Buttons**: Blue primary, outlined secondary, text ghost
- **Cards**: White background with subtle shadows
- **Inputs**: Light gray borders with blue focus
- **Navigation**: Blue selected, gray unselected

##  Dark Theme

### Color Palette
- **Primary**: Light Blue (#90CAF9) - Soft blue for dark backgrounds
- **Secondary**: Light Pink (#F48FB1) - Muted pink for contrast
- **Surface**: Dark Gray (#1E1E1E) - Elevated surfaces
- **Background**: Very Dark Gray (#121212) - Deep background
- **Error**: Red (#D32F2F) - Maintained for consistency

### Component Styling
- **App Bar**: Dark surface with white text
- **Buttons**: Light blue primary, outlined secondary, text ghost
- **Cards**: Dark gray background with no shadows
- **Inputs**: Dark borders with light blue focus
- **Navigation**: Light blue selected, gray unselected

##  Usage

### Basic Theme Switching
```dart
// Get theme provider
final themeProvider = Provider.of<ThemeProvider>(context);

// Set specific theme
themeProvider.setTheme(AppTheme.dark);

// Toggle between light and dark
themeProvider.toggleTheme();

// Check current theme
final isDark = themeProvider.isDarkMode;
final currentTheme = themeProvider.currentTheme;
```

### Theme Switcher Component
```dart
// Use the built-in theme switcher
const ShopperThemeSwitcher()

// Or create custom theme controls
Consumer<ThemeProvider>(
  builder: (context, themeProvider, child) {
    return ShopperPrimaryButton(
      text: 'Toggle Theme',
      onPressed: () => themeProvider.toggleTheme(),
    );
  },
)
```

##  Theme-Aware Components

All components automatically adapt to the current theme:

### Buttons
- Primary: Uses theme primary color
- Secondary: Uses theme primary for borders
- Ghost: Uses theme primary for text

### Cards & Surfaces
- Background: Uses theme surface color
- Text: Uses theme onSurface color
- Borders: Uses theme-aware colors

### Form Elements
- Input fields: Theme-aware borders and focus colors
- Labels: Theme onSurface color
- Error text: Consistent red across themes

### Navigation
- Bottom nav: Theme-aware selected/unselected colors
- App bar: Theme-aware background and text

##  Persistence

Theme preferences are automatically saved and restored:

- **Storage**: SharedPreferences
- **Key**: 'app_theme'
- **Default**: AppTheme.system
- **Persistence**: Survives app restarts

##  Dynamic Theme Switching

The theme system supports runtime switching without app restart:

1. User selects theme in settings
2. ThemeProvider updates state
3. All widgets rebuild with new theme
4. Preference saved to storage
5. Theme persists across sessions

##  System Theme Integration

When using `AppTheme.system`:

- **iOS**: Follows system appearance setting
- **Android**: Follows system dark mode toggle
- **Fallback**: Defaults to light theme if system preference unavailable

##  Customization

### Extending Themes
```dart
class CustomThemeProvider extends ThemeProvider {
  @override
  ThemeData _buildLightTheme() {
    final baseTheme = super._buildLightTheme();
    return baseTheme.copyWith(
      // Add customizations
      primaryColor: Colors.purple,
      // ... other customizations
    );
  }
}
```

### Adding Theme Colors
```dart
// In design_system.dart
const Color kAccentColor = Color(0xFFFFC107);
const Color kWarningColor = Color(0xFFFF9800);

// In theme_provider.dart
colorScheme: const ColorScheme.light(
  // ... existing colors
  tertiary: kAccentColor,
),
```

##  Testing Themes

### Manual Testing
1. Use the theme switcher in Settings
2. Use the toggle button on Home screen
3. Test Components Demo with different themes
4. Verify all components adapt properly

### Automated Testing
```dart
testWidgets('Theme switching works', (tester) async {
  await tester.pumpWidget(const MyApp());

  // Test light theme
  expect(find.byType(ShopperPrimaryButton), findsWidgets);

  // Switch to dark theme
  await tester.tap(find.text('Dark'));
  await tester.pump();

  // Verify dark theme applied
  // Add assertions for dark theme colors
});
```

##  Best Practices

### Component Development
- Always use theme-aware colors from Theme.of(context)
- Test components in both light and dark themes
- Use semantic color names (onPrimary, onSurface, etc.)

### Theme Consistency
- Maintain contrast ratios for accessibility
- Use consistent color relationships across themes
- Test on different devices and screen conditions

### Performance
- Theme changes trigger rebuilds - keep component trees efficient
- Use const constructors where possible
- Avoid unnecessary theme-dependent calculations

##  Theme Checklist

- [x] Light theme implementation
- [x] Dark theme implementation
- [x] System theme support
- [x] Theme persistence
- [x] Theme switcher component
- [x] All components theme-aware
- [x] Settings integration
- [x] Demo screen integration
- [x] Documentation complete

The theme system is now fully functional and provides a professional, accessible, and user-friendly theming experience! 