import 'package:equatable/equatable.dart';
import '../../core/validation/validation.dart';

enum ThemeMode {
  system('system'),
  light('light'),
  dark('dark');

  const ThemeMode(this.value);
  final String value;

  static ThemeMode fromString(String value) {
    return ThemeMode.values.firstWhere(
      (mode) => mode.value == value,
      orElse: () => ThemeMode.system,
    );
  }
}

enum Language {
  english('en'),
  bengali('bn');

  const Language(this.value);
  final String value;

  static Language fromString(String value) {
    return Language.values.firstWhere(
      (lang) => lang.value == value,
      orElse: () => Language.english,
    );
  }

  String get displayName {
    switch (this) {
      case Language.english:
        return 'English';
      case Language.bengali:
        return 'বাংলা';
    }
  }
}

class AppSettings extends Equatable {
  final ThemeMode themeMode;
  final Language language;
  final bool enableBiometric;
  final bool enableNotifications;
  final bool enableSound;
  final bool enableVibration;
  final bool autoSync;
  final int syncIntervalMinutes;
  final String? printerAddress;
  final String? receiptPrinterType;
  final bool enableAutoBackup;
  final int backupIntervalDays;
  final String currencySymbol;
  final int decimalPlaces;

  const AppSettings({
    this.themeMode = ThemeMode.system,
    this.language = Language.english,
    this.enableBiometric = false,
    this.enableNotifications = true,
    this.enableSound = true,
    this.enableVibration = true,
    this.autoSync = true,
    this.syncIntervalMinutes = 15,
    this.printerAddress,
    this.receiptPrinterType,
    this.enableAutoBackup = true,
    this.backupIntervalDays = 7,
    this.currencySymbol = '৳',
    this.decimalPlaces = 2,
  });

  AppSettings copyWith({
    ThemeMode? themeMode,
    Language? language,
    bool? enableBiometric,
    bool? enableNotifications,
    bool? enableSound,
    bool? enableVibration,
    bool? autoSync,
    int? syncIntervalMinutes,
    String? printerAddress,
    String? receiptPrinterType,
    bool? enableAutoBackup,
    int? backupIntervalDays,
    String? currencySymbol,
    int? decimalPlaces,
  }) {
    return AppSettings(
      themeMode: themeMode ?? this.themeMode,
      language: language ?? this.language,
      enableBiometric: enableBiometric ?? this.enableBiometric,
      enableNotifications: enableNotifications ?? this.enableNotifications,
      enableSound: enableSound ?? this.enableSound,
      enableVibration: enableVibration ?? this.enableVibration,
      autoSync: autoSync ?? this.autoSync,
      syncIntervalMinutes: syncIntervalMinutes ?? this.syncIntervalMinutes,
      printerAddress: printerAddress ?? this.printerAddress,
      receiptPrinterType: receiptPrinterType ?? this.receiptPrinterType,
      enableAutoBackup: enableAutoBackup ?? this.enableAutoBackup,
      backupIntervalDays: backupIntervalDays ?? this.backupIntervalDays,
      currencySymbol: currencySymbol ?? this.currencySymbol,
      decimalPlaces: decimalPlaces ?? this.decimalPlaces,
    );
  }

  /// Validates the app settings data
  ValidationResult validate() {
    final List<ValidationResult> validations = [];

    // Required field validations
    // Other fields are non-nullable and validated below
    validations.add(ValidationUtils.validateRequired(currencySymbol, 'Currency symbol'));
    // Decimal places is non-nullable and validated below

    // Sync interval validation
    if (syncIntervalMinutes < 5) {
      validations.add(ValidationResult.invalid(['Sync interval must be at least 5 minutes']));
    }
    if (syncIntervalMinutes > 1440) {
      validations.add(ValidationResult.invalid(['Sync interval cannot exceed 24 hours (1440 minutes)']));
    }

    // Backup interval validation
    if (backupIntervalDays < 1) {
      validations.add(ValidationResult.invalid(['Backup interval must be at least 1 day']));
    }
    if (backupIntervalDays > 365) {
      validations.add(ValidationResult.invalid(['Backup interval cannot exceed 365 days']));
    }

    // Printer address validation
    if (printerAddress != null) {
      validations.add(ValidationUtils.validateLengthRange(printerAddress!, 1, 100, 'Printer address'));
      // Basic IP address or hostname validation
      final ipRegex = RegExp(r'^(\d{1,3}\.){3}\d{1,3}(:\d{1,5})?$|^[a-zA-Z0-9.-]+(:\d{1,5})?$');
      if (!ipRegex.hasMatch(printerAddress!)) {
        validations.add(ValidationResult.invalid(['Printer address must be a valid IP address or hostname']));
      }
    }

    // Receipt printer type validation
    if (receiptPrinterType != null) {
      validations.add(ValidationUtils.validateLengthRange(receiptPrinterType!, 1, 50, 'Receipt printer type'));
      final allowedTypes = ['thermal', 'dot-matrix', 'inkjet', 'laser'];
      if (!allowedTypes.contains(receiptPrinterType!.toLowerCase())) {
        validations.add(ValidationResult.invalid(['Receipt printer type must be one of: ${allowedTypes.join(', ')}']));
      }
    }

    // Currency symbol validation
    validations.add(ValidationUtils.validateLengthRange(currencySymbol, 1, 5, 'Currency symbol'));

    // Decimal places validation
    if (decimalPlaces < 0) {
      validations.add(ValidationResult.invalid(['Decimal places cannot be negative']));
    }
    if (decimalPlaces > 4) {
      validations.add(ValidationResult.invalid(['Decimal places cannot exceed 4']));
    }

    // Business logic validations
    if (enableBiometric && !enableNotifications) {
      validations.add(ValidationResult.invalid(['Biometric authentication requires notifications to be enabled']));
    }

    if (autoSync && syncIntervalMinutes < 10) {
      validations.add(ValidationResult.invalid(['Auto sync with interval less than 10 minutes may impact performance']));
    }

    // Combine all validations
    ValidationResult result = ValidationResult.valid();
    for (final validation in validations) {
      result = result.merge(validation);
    }

    return result;
  }

  @override
  List<Object?> get props => [
        themeMode,
        language,
        enableBiometric,
        enableNotifications,
        enableSound,
        enableVibration,
        autoSync,
        syncIntervalMinutes,
        printerAddress,
        receiptPrinterType,
        enableAutoBackup,
        backupIntervalDays,
        currencySymbol,
        decimalPlaces,
      ];
}
