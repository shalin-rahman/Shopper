import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../core/design_system.dart';

enum AppTheme { indigo, midnight, emerald, ruby, amber, amethyst, cyberpunk, coffee, minimalist, sunset }

class ThemeProvider extends ChangeNotifier {
  static const String _themeKey = 'app_theme_type';
  AppTheme _currentThemeType = AppTheme.indigo;

  ThemeProvider() {
    _loadThemeFromPrefs();
  }

  AppTheme get currentTheme => _currentThemeType;
  
  ThemeData get themeData => _buildTheme(_currentThemeType);

  void setTheme(AppTheme theme) {
    _currentThemeType = theme;
    _saveThemeToPrefs();
    notifyListeners();
  }

  Future<void> _loadThemeFromPrefs() async {
    final prefs = await SharedPreferences.getInstance();
    final themeIndex = prefs.getInt(_themeKey) ?? AppTheme.indigo.index;
    _currentThemeType = AppTheme.values[themeIndex];
    notifyListeners();
  }

  Future<void> _saveThemeToPrefs() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_themeKey, _currentThemeType.index);
  }

  ThemeData _buildTheme(AppTheme themeType) {
    final palette = kThemePalettes[themeType.name] ?? kThemePalettes['indigo']!;
    final brightness = palette.isDark ? Brightness.dark : Brightness.light;
    final onBG = palette.onBackground;

    return ThemeData(
      useMaterial3: true,
      brightness: brightness,
      scaffoldBackgroundColor: palette.background,
      colorScheme: ColorScheme(
        brightness: brightness,
        primary: palette.primary,
        onPrimary: palette.onPrimary,
        primaryContainer: palette.primaryVariant,
        secondary: palette.secondary,
        onSecondary: Colors.white,
        error: kErrorColor,
        onError: Colors.white,
        background: palette.background,
        onBackground: onBG,
        surface: palette.surface,
        onSurface: onBG,
      ),

      textTheme: TextTheme(
        headlineLarge: kHeadline1.copyWith(color: onBG),
        headlineMedium: kHeadline2.copyWith(color: onBG),
        headlineSmall: kHeadline3.copyWith(color: onBG),
        titleLarge: kHeadline4.copyWith(color: onBG),
        titleMedium: kHeadline5.copyWith(color: onBG),
        titleSmall: kHeadline6.copyWith(color: onBG),
        bodyLarge: kBodyLarge.copyWith(color: onBG),
        bodyMedium: kBodyMedium.copyWith(color: onBG),
        bodySmall: kBodySmall.copyWith(color: onBG),
      ),

      appBarTheme: AppBarTheme(
        backgroundColor: palette.primary,
        foregroundColor: palette.onPrimary,
        elevation: 0,
        titleTextStyle: kHeadline6.copyWith(color: palette.onPrimary),
      ),

      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: palette.primary,
          foregroundColor: palette.onPrimary,
          minimumSize: const Size(double.infinity, kMinTouchTarget),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(kBorderRadiusMedium)),
          textStyle: kBodyMedium.copyWith(fontWeight: FontWeight.w600),
        ),
      ),

      cardTheme: CardTheme(
        color: palette.surface,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(kBorderRadiusLarge)),
      ),
      
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: palette.surface,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(kBorderRadiusMedium),
          borderSide: BorderSide(color: palette.isDark ? Colors.white24 : Colors.grey.shade300),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(kBorderRadiusMedium),
          borderSide: BorderSide(color: palette.primary, width: 2),
        ),
      ),
    );
  }
}