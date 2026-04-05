import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../core/design_system.dart';

enum AppTheme { light, dark, system }

class ThemeProvider extends ChangeNotifier {
  static const String _themeKey = 'app_theme';
  AppTheme _currentTheme = AppTheme.system;
  bool _isDarkMode = false;

  ThemeProvider() {
    _loadThemeFromPrefs();
  }

  AppTheme get currentTheme => _currentTheme;
  bool get isDarkMode => _isDarkMode;

  ThemeData get lightTheme => _buildLightTheme();
  ThemeData get darkTheme => _buildDarkTheme();

  ThemeMode get themeMode {
    switch (_currentTheme) {
      case AppTheme.light:
        return ThemeMode.light;
      case AppTheme.dark:
        return ThemeMode.dark;
      case AppTheme.system:
        return ThemeMode.system;
    }
  }

  void setTheme(AppTheme theme) {
    _currentTheme = theme;
    _updateDarkMode();
    _saveThemeToPrefs();
    notifyListeners();
  }

  void toggleTheme() {
    setTheme(_currentTheme == AppTheme.light ? AppTheme.dark : AppTheme.light);
  }

  void _updateDarkMode() {
    if (_currentTheme == AppTheme.system) {
      // For system theme, we'll determine this based on platform brightness
      // This will be handled by the MaterialApp themeMode
      _isDarkMode = WidgetsBinding.instance.platformDispatcher.platformBrightness == Brightness.dark;
    } else {
      _isDarkMode = _currentTheme == AppTheme.dark;
    }
  }

  Future<void> _loadThemeFromPrefs() async {
    final prefs = await SharedPreferences.getInstance();
    final themeIndex = prefs.getInt(_themeKey) ?? AppTheme.system.index;
    _currentTheme = AppTheme.values[themeIndex];
    _updateDarkMode();
    notifyListeners();
  }

  Future<void> _saveThemeToPrefs() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_themeKey, _currentTheme.index);
  }

  ThemeData _buildLightTheme() {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,

      // Color Scheme
      colorScheme: const ColorScheme.light(
        primary: kPrimaryColor,
        primaryContainer: kPrimaryVariant,
        secondary: kSecondaryColor,
        secondaryContainer: kSecondaryVariant,
        surface: kSurfaceColor,
        surfaceContainerHighest: Color(0xFFE0E0E0),
        background: kBackgroundColor,
        error: kErrorColor,
        onPrimary: kOnPrimaryColor,
        onSecondary: kOnSecondaryColor,
        onSurface: kOnSurfaceColor,
        onBackground: kOnBackgroundColor,
        onError: kOnErrorColor,
      ),

      // Typography
      textTheme: TextTheme(
        headlineLarge: kHeadline1.copyWith(color: kOnBackgroundColor),
        headlineMedium: kHeadline2.copyWith(color: kOnBackgroundColor),
        headlineSmall: kHeadline3.copyWith(color: kOnBackgroundColor),
        titleLarge: kHeadline4.copyWith(color: kOnBackgroundColor),
        titleMedium: kHeadline5.copyWith(color: kOnBackgroundColor),
        titleSmall: kHeadline6.copyWith(color: kOnBackgroundColor),
        bodyLarge: kBodyLarge.copyWith(color: kOnBackgroundColor),
        bodyMedium: kBodyMedium.copyWith(color: kOnBackgroundColor),
        bodySmall: kBodySmall.copyWith(color: kOnBackgroundColor),
        labelLarge: kBodyMedium.copyWith(color: kOnBackgroundColor, fontWeight: FontWeight.w500),
        labelMedium: kBodySmall.copyWith(color: kOnBackgroundColor, fontWeight: FontWeight.w500),
        labelSmall: kCaption.copyWith(color: kOnBackgroundColor),
      ),

      // Component Themes
      appBarTheme: AppBarTheme(
        backgroundColor: kPrimaryColor,
        foregroundColor: kOnPrimaryColor,
        elevation: 0,
        shadowColor: Colors.transparent,
        surfaceTintColor: Colors.transparent,
        titleTextStyle: kHeadline6.copyWith(color: kOnPrimaryColor),
      ),

      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: kPrimaryColor,
          foregroundColor: kOnPrimaryColor,
          elevation: 0,
          shadowColor: Colors.transparent,
          minimumSize: const Size(double.infinity, kMinTouchTarget),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(kBorderRadiusMedium),
          ),
          textStyle: kBodyMedium.copyWith(
            fontWeight: FontWeight.w600,
            color: kOnPrimaryColor,
          ),
        ),
      ),

      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: kPrimaryColor,
          side: const BorderSide(color: kPrimaryColor),
          minimumSize: const Size(double.infinity, kMinTouchTarget),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(kBorderRadiusMedium),
          ),
          textStyle: kBodyMedium.copyWith(
            fontWeight: FontWeight.w600,
            color: kPrimaryColor,
          ),
        ),
      ),

      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: kPrimaryColor,
          minimumSize: const Size(double.infinity, kMinTouchTarget),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(kBorderRadiusMedium),
          ),
          textStyle: kBodyMedium.copyWith(
            fontWeight: FontWeight.w600,
            color: kPrimaryColor,
          ),
        ),
      ),

      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: kSurfaceColor,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(kBorderRadiusMedium),
          borderSide: const BorderSide(color: Color(0xFFE0E0E0)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(kBorderRadiusMedium),
          borderSide: const BorderSide(color: Color(0xFFE0E0E0)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(kBorderRadiusMedium),
          borderSide: const BorderSide(color: kPrimaryColor, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(kBorderRadiusMedium),
          borderSide: const BorderSide(color: kErrorColor),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(kBorderRadiusMedium),
          borderSide: const BorderSide(color: kErrorColor, width: 2),
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: kSpacing16,
          vertical: kSpacing12,
        ),
        labelStyle: kBodyMedium.copyWith(color: kOnSurfaceColor),
        hintStyle: kBodyMedium.copyWith(color: Colors.grey),
        errorStyle: kCaption.copyWith(color: kErrorColor),
      ),

      cardTheme: CardTheme(
        color: kSurfaceColor,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(kBorderRadiusLarge),
        ),
        shadowColor: Colors.transparent,
        surfaceTintColor: Colors.transparent,
      ),

      bottomNavigationBarTheme: BottomNavigationBarThemeData(
        backgroundColor: kSurfaceColor,
        selectedItemColor: kPrimaryColor,
        unselectedItemColor: Colors.grey,
        elevation: 8,
        type: BottomNavigationBarType.fixed,
      ),

      chipTheme: ChipThemeData(
        backgroundColor: const Color(0xFFE0E0E0),
        selectedColor: kPrimaryColor.withOpacity(0.1),
        checkmarkColor: kPrimaryColor,
        deleteIconColor: kPrimaryColor,
        labelStyle: kBodyMedium.copyWith(color: kOnSurfaceColor),
        secondaryLabelStyle: kBodyMedium.copyWith(color: kPrimaryColor),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(kBorderRadiusLarge),
        ),
      ),

      dividerTheme: DividerThemeData(
        color: const Color(0xFFE0E0E0),
        thickness: 1,
        space: kSpacing16,
      ),

      dialogTheme: DialogTheme(
        backgroundColor: kSurfaceColor,
        elevation: 8,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(kBorderRadiusLarge),
        ),
      ),

      snackBarTheme: SnackBarThemeData(
        backgroundColor: kSurfaceColor,
        contentTextStyle: kBodyMedium.copyWith(color: kOnSurfaceColor),
        actionTextColor: kPrimaryColor,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(kBorderRadiusMedium),
        ),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  ThemeData _buildDarkTheme() {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,

      // Color Scheme
      colorScheme: const ColorScheme.dark(
        primary: kPrimaryColorDark,
        primaryContainer: Color(0xFF42A5F5),
        secondary: kSecondaryColorDark,
        secondaryContainer: Color(0xFFAD1457),
        surface: kSurfaceColorDark,
        surfaceContainerHighest: Color(0xFF2D2D2D),
        background: kBackgroundColorDark,
        error: kErrorColor,
        onPrimary: kOnBackgroundColor,
        onSecondary: kOnBackgroundColor,
        onSurface: Colors.white,
        onBackground: Colors.white,
        onError: kOnErrorColor,
      ),

      // Typography
      textTheme: TextTheme(
        headlineLarge: kHeadline1.copyWith(color: Colors.white),
        headlineMedium: kHeadline2.copyWith(color: Colors.white),
        headlineSmall: kHeadline3.copyWith(color: Colors.white),
        titleLarge: kHeadline4.copyWith(color: Colors.white),
        titleMedium: kHeadline5.copyWith(color: Colors.white),
        titleSmall: kHeadline6.copyWith(color: Colors.white),
        bodyLarge: kBodyLarge.copyWith(color: Colors.white),
        bodyMedium: kBodyMedium.copyWith(color: Colors.white),
        bodySmall: kBodySmall.copyWith(color: Colors.white),
        labelLarge: kBodyMedium.copyWith(color: Colors.white, fontWeight: FontWeight.w500),
        labelMedium: kBodySmall.copyWith(color: Colors.white, fontWeight: FontWeight.w500),
        labelSmall: kCaption.copyWith(color: Colors.white),
      ),

      // Component Themes
      appBarTheme: AppBarTheme(
        backgroundColor: kSurfaceColorDark,
        foregroundColor: Colors.white,
        elevation: 0,
        shadowColor: Colors.transparent,
        surfaceTintColor: Colors.transparent,
        titleTextStyle: kHeadline6.copyWith(color: Colors.white),
      ),

      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: kPrimaryColorDark,
          foregroundColor: kOnBackgroundColor,
          elevation: 0,
          shadowColor: Colors.transparent,
          minimumSize: const Size(double.infinity, kMinTouchTarget),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(kBorderRadiusMedium),
          ),
          textStyle: kBodyMedium.copyWith(
            fontWeight: FontWeight.w600,
            color: kOnBackgroundColor,
          ),
        ),
      ),

      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: kPrimaryColorDark,
          side: BorderSide(color: kPrimaryColorDark),
          minimumSize: const Size(double.infinity, kMinTouchTarget),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(kBorderRadiusMedium),
          ),
          textStyle: kBodyMedium.copyWith(
            fontWeight: FontWeight.w600,
            color: kPrimaryColorDark,
          ),
        ),
      ),

      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: kPrimaryColorDark,
          minimumSize: const Size(double.infinity, kMinTouchTarget),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(kBorderRadiusMedium),
          ),
          textStyle: kBodyMedium.copyWith(
            fontWeight: FontWeight.w600,
            color: kPrimaryColorDark,
          ),
        ),
      ),

      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: kSurfaceColorDark,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(kBorderRadiusMedium),
          borderSide: const BorderSide(color: Color(0xFF424242)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(kBorderRadiusMedium),
          borderSide: const BorderSide(color: Color(0xFF424242)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(kBorderRadiusMedium),
          borderSide: BorderSide(color: kPrimaryColorDark, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(kBorderRadiusMedium),
          borderSide: const BorderSide(color: kErrorColor),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(kBorderRadiusMedium),
          borderSide: const BorderSide(color: kErrorColor, width: 2),
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: kSpacing16,
          vertical: kSpacing12,
        ),
        labelStyle: kBodyMedium.copyWith(color: Colors.white),
        hintStyle: kBodyMedium.copyWith(color: Colors.grey),
        errorStyle: kCaption.copyWith(color: kErrorColor),
      ),

      cardTheme: CardTheme(
        color: kSurfaceColorDark,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(kBorderRadiusLarge),
        ),
        shadowColor: Colors.transparent,
        surfaceTintColor: Colors.transparent,
      ),

      bottomNavigationBarTheme: BottomNavigationBarThemeData(
        backgroundColor: kSurfaceColorDark,
        selectedItemColor: kPrimaryColorDark,
        unselectedItemColor: Colors.grey,
        elevation: 8,
        type: BottomNavigationBarType.fixed,
      ),

      chipTheme: ChipThemeData(
        backgroundColor: const Color(0xFF424242),
        selectedColor: kPrimaryColorDark.withOpacity(0.1),
        checkmarkColor: kPrimaryColorDark,
        deleteIconColor: kPrimaryColorDark,
        labelStyle: kBodyMedium.copyWith(color: Colors.white),
        secondaryLabelStyle: kBodyMedium.copyWith(color: kPrimaryColorDark),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(kBorderRadiusLarge),
        ),
      ),

      dividerTheme: DividerThemeData(
        color: const Color(0xFF424242),
        thickness: 1,
        space: kSpacing16,
      ),

      dialogTheme: DialogTheme(
        backgroundColor: kSurfaceColorDark,
        elevation: 8,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(kBorderRadiusLarge),
        ),
      ),

      snackBarTheme: SnackBarThemeData(
        backgroundColor: kSurfaceColorDark,
        contentTextStyle: kBodyMedium.copyWith(color: Colors.white),
        actionTextColor: kPrimaryColorDark,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(kBorderRadiusMedium),
        ),
        behavior: SnackBarBehavior.floating,
      ),

      // Additional dark theme specific overrides
      scaffoldBackgroundColor: kBackgroundColorDark,
      canvasColor: kBackgroundColorDark,
      dialogBackgroundColor: kSurfaceColorDark,
    );
  }
}