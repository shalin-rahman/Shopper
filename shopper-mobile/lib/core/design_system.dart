import 'package:flutter/material.dart';

// 8pt Grid System
const double kGridUnit = 8.0;

// Spacing Tokens (4pt micro + 8pt grid)
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
const TextStyle kHeadline1 = TextStyle(
  fontSize: 32.0,
  fontWeight: FontWeight.w700,
  height: 1.25,
);

const TextStyle kHeadline2 = TextStyle(
  fontSize: 28.0,
  fontWeight: FontWeight.w600,
  height: 1.29,
);

const TextStyle kHeadline3 = TextStyle(
  fontSize: 24.0,
  fontWeight: FontWeight.w600,
  height: 1.33,
);

const TextStyle kHeadline4 = TextStyle(
  fontSize: 20.0,
  fontWeight: FontWeight.w600,
  height: 1.4,
);

const TextStyle kHeadline5 = TextStyle(
  fontSize: 18.0,
  fontWeight: FontWeight.w600,
  height: 1.44,
);

const TextStyle kHeadline6 = TextStyle(
  fontSize: 16.0,
  fontWeight: FontWeight.w600,
  height: 1.5,
);

const TextStyle kBodyLarge = TextStyle(
  fontSize: 16.0,
  fontWeight: FontWeight.w400,
  height: 1.5,
);

const TextStyle kBodyMedium = TextStyle(
  fontSize: 14.0,
  fontWeight: FontWeight.w400,
  height: 1.43,
);

const TextStyle kBodySmall = TextStyle(
  fontSize: 12.0,
  fontWeight: FontWeight.w400,
  height: 1.33,
);

const TextStyle kCaption = TextStyle(
  fontSize: 12.0,
  fontWeight: FontWeight.w400,
  height: 1.33,
);

// Color System (Light Mode)
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

// Dark Mode Colors
const Color kPrimaryColorDark = Color(0xFF90CAF9);
const Color kSecondaryColorDark = Color(0xFFF48FB1);
const Color kBackgroundColorDark = Color(0xFF121212);
const Color kSurfaceColorDark = Color(0xFF1E1E1E);

// Minimum Touch Target
const double kMinTouchTarget = 48.0;

// Border Radius
const double kBorderRadiusSmall = 4.0;
const double kBorderRadiusMedium = 8.0;
const double kBorderRadiusLarge = 12.0;
const double kBorderRadiusXLarge = 16.0;

// Shadows
const BoxShadow kElevation1 = BoxShadow(
  color: Color(0x1F000000),
  offset: Offset(0, 1),
  blurRadius: 3,
);

const BoxShadow kElevation2 = BoxShadow(
  color: Color(0x24000000),
  offset: Offset(0, 2),
  blurRadius: 6,
);

const BoxShadow kElevation4 = BoxShadow(
  color: Color(0x29000000),
  offset: Offset(0, 4),
  blurRadius: 12,
);