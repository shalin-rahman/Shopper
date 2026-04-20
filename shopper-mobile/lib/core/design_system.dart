import 'package:flutter/material.dart';

// 8pt Grid System
const double kGridUnit = 8.0;

// Spacing Tokens
const double kSpacing4 = 4.0;
const double kSpacing8 = 8.0;
const double kSpacing12 = 12.0;
const double kSpacing16 = 16.0;
const double kSpacing24 = 24.0;
const double kSpacing32 = 32.0;
const double kSpacing48 = 48.0;
const double kSpacing64 = 64.0;
const double kSpacing80 = 80.0;
const double kSpacing96 = 96.0;

// Typography Scale
const TextStyle kHeadline1 = TextStyle(fontSize: 32.0, fontWeight: FontWeight.w700, height: 1.25);
const TextStyle kHeadline2 = TextStyle(fontSize: 28.0, fontWeight: FontWeight.w600, height: 1.29);
const TextStyle kHeadline3 = TextStyle(fontSize: 24.0, fontWeight: FontWeight.w600, height: 1.33);
const TextStyle kHeadline4 = TextStyle(fontSize: 20.0, fontWeight: FontWeight.w600, height: 1.4);
const TextStyle kHeadline5 = TextStyle(fontSize: 18.0, fontWeight: FontWeight.w600, height: 1.44);
const TextStyle kHeadline6 = TextStyle(fontSize: 16.0, fontWeight: FontWeight.w600, height: 1.5);
const TextStyle kBodyLarge = TextStyle(fontSize: 16.0, fontWeight: FontWeight.w400, height: 1.5);
const TextStyle kBodyMedium = TextStyle(fontSize: 14.0, fontWeight: FontWeight.w400, height: 1.43);
const TextStyle kBodySmall = TextStyle(fontSize: 12.0, fontWeight: FontWeight.w400, height: 1.33);
const TextStyle kCaption = TextStyle(fontSize: 12.0, fontWeight: FontWeight.w400, height: 1.33);

// Theme Color Palettes
class ShopperThemeColors {
  final Color primary;
  final Color primaryVariant;
  final Color secondary;
  final Color background;
  final Color surface;
  final Color onPrimary;
  final Color onBackground;
  final bool isDark;

  const ShopperThemeColors({
    required this.primary,
    required this.primaryVariant,
    required this.secondary,
    required this.background,
    required this.surface,
    this.onPrimary = Colors.white,
    this.onBackground = Colors.black,
    this.isDark = false,
  });
}

const Map<String, ShopperThemeColors> kThemePalettes = {
  'indigo': ShopperThemeColors(
    primary: Color(0xFF3F51B5),
    primaryVariant: Color(0xFF303F9F),
    secondary: Color(0xFFFF4081),
    background: Color(0xFFF5F5F5),
    surface: Colors.white,
  ),
  'midnight': ShopperThemeColors(
    primary: Color(0xFF90CAF9),
    primaryVariant: Color(0xFF42A5F5),
    secondary: Color(0xFFF48FB1),
    background: Color(0xFF121212),
    surface: Color(0xFF1E1E1E),
    onBackground: Colors.white,
    isDark: true,
  ),
  'emerald': ShopperThemeColors(
    primary: Color(0xFF2E7D32),
    primaryVariant: Color(0xFF1B5E20),
    secondary: Color(0xFFFFA000),
    background: Color(0xFFF1F8E9),
    surface: Colors.white,
  ),
  'ruby': ShopperThemeColors(
    primary: Color(0xFFC62828),
    primaryVariant: Color(0xFFB71C1C),
    secondary: Color(0xFF26C6DA),
    background: Color(0xFFFFEBEE),
    surface: Colors.white,
  ),
  'amber': ShopperThemeColors(
    primary: Color(0xFFFF8F00),
    primaryVariant: Color(0xFFFF6F00),
    secondary: Color(0xFF4527A0),
    background: Color(0xFFFFF8E1),
    surface: Colors.white,
  ),
  'amethyst': ShopperThemeColors(
    primary: Color(0xFF6A1B9A),
    primaryVariant: Color(0xFF4A148C),
    secondary: Color(0xFF00E676),
    background: Color(0xFFF3E5F5),
    surface: Colors.white,
  ),
  'cyberpunk': ShopperThemeColors(
    primary: Color(0xFF00FF41),
    primaryVariant: Color(0xFF003B00),
    secondary: Color(0xFFBC13FE),
    background: Color(0xFF0D0208),
    surface: Color(0xFF000000),
    onBackground: Color(0xFF00FF41),
    isDark: true,
  ),
  'coffee': ShopperThemeColors(
    primary: Color(0xFF4E342E),
    primaryVariant: Color(0xFF3E2723),
    secondary: Color(0xFFBF360C),
    background: Color(0xFFEFEBE9),
    surface: Colors.white,
  ),
  'minimalist': ShopperThemeColors(
    primary: Color(0xFF212121),
    primaryVariant: Color(0xFF000000),
    secondary: Color(0xFF757575),
    background: Color(0xFFFAFAFA),
    surface: Colors.white,
  ),
  'sunset': ShopperThemeColors(
    primary: Color(0xFFE65100),
    primaryVariant: Color(0xFFEF6C00),
    secondary: Color(0xFF1A237E),
    background: Color(0xFFFFF3E0),
    surface: Colors.white,
  ),
};

// Legacy constants for backward compatibility (Indigo)
const Color kPrimaryColor = Color(0xFF1976D2);
const Color kPrimaryVariant = Color(0xFF1565C0);
const Color kSecondaryColor = Color(0xFFDC004E);
const Color kSecondaryVariant = Color(0xFFC2185B);
const Color kBackgroundColor = Color(0xFFFFFFFF);
const Color kSurfaceColor = Color(0xFFFFFFFF);
const Color kErrorColor = Color(0xFFD32F2F);
const Color kSuccessColor = Color(0xFF388E3C);
const Color kOnPrimaryColor = Color(0xFFFFFFFF);
const Color kOnSecondaryColor = Color(0xFFFFFFFF);
const Color kOnBackgroundColor = Color(0xFF000000);
const Color kOnSurfaceColor = Color(0xFF000000);
const Color kOnErrorColor = Color(0xFFFFFFFF);

const double kMinTouchTarget = 48.0;
const double kBorderRadiusSmall = 4.0;
const double kBorderRadiusMedium = 8.0;
const double kBorderRadiusLarge = 12.0;
const double kBorderRadiusXLarge = 16.0;

const BoxShadow kElevation1 = BoxShadow(color: Color(0x1F000000), offset: Offset(0, 1), blurRadius: 3);
const BoxShadow kElevation2 = BoxShadow(color: Color(0x24000000), offset: Offset(0, 2), blurRadius: 6);
const BoxShadow kElevation4 = BoxShadow(color: Color(0x29000000), offset: Offset(0, 4), blurRadius: 12);