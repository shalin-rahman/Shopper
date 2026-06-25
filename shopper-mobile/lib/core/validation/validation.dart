class ValidationResult {
  final bool isValid;
  final List<String> errors;

  const ValidationResult({
    required this.isValid,
    this.errors = const [],
  });

  factory ValidationResult.valid() => const ValidationResult(isValid: true);

  factory ValidationResult.invalid(List<String> errors) =>
      ValidationResult(isValid: false, errors: errors);

  ValidationResult merge(ValidationResult other) {
    return ValidationResult(
      isValid: isValid && other.isValid,
      errors: [...errors, ...other.errors],
    );
  }
}

class ValidationUtils {
  static ValidationResult validateRequired(String? value, String fieldName) {
    if (value == null || value.trim().isEmpty) {
      return ValidationResult.invalid(['$fieldName is required']);
    }
    return ValidationResult.valid();
  }

  static ValidationResult validateMinLength(String value, int minLength, String fieldName) {
    if (value.length < minLength) {
      return ValidationResult.invalid(['$fieldName must be at least $minLength characters long']);
    }
    return ValidationResult.valid();
  }

  static ValidationResult validateMaxLength(String value, int maxLength, String fieldName) {
    if (value.length > maxLength) {
      return ValidationResult.invalid(['$fieldName must not exceed $maxLength characters']);
    }
    return ValidationResult.valid();
  }

  static ValidationResult validateLengthRange(String value, int minLength, int maxLength, String fieldName) {
    return validateMinLength(value, minLength, fieldName)
        .merge(validateMaxLength(value, maxLength, fieldName));
  }

  static ValidationResult validatePositiveNumber(double value, String fieldName) {
    if (value <= 0) {
      return ValidationResult.invalid(['$fieldName must be greater than 0']);
    }
    return ValidationResult.valid();
  }

  static ValidationResult validateNonNegativeNumber(double value, String fieldName) {
    if (value < 0) {
      return ValidationResult.invalid(['$fieldName cannot be negative']);
    }
    return ValidationResult.valid();
  }

  static ValidationResult validateNonNegativeInteger(int value, String fieldName) {
    if (value < 0) {
      return ValidationResult.invalid(['$fieldName cannot be negative']);
    }
    return ValidationResult.valid();
  }

  static ValidationResult validatePrice(double price, String fieldName) {
    final positiveCheck = validatePositiveNumber(price, fieldName);
    if (!positiveCheck.isValid) return positiveCheck;

    if (price > 999999.99) {
      return ValidationResult.invalid(['$fieldName cannot exceed 999,999.99']);
    }
    return ValidationResult.valid();
  }

  static ValidationResult validatePercentage(double percentage, String fieldName) {
    if (percentage < 0 || percentage > 100) {
      return ValidationResult.invalid(['$fieldName must be between 0 and 100']);
    }
    return ValidationResult.valid();
  }

  static ValidationResult validateEmail(String email, String fieldName) {
    final emailRegex = RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$');
    if (!emailRegex.hasMatch(email)) {
      return ValidationResult.invalid(['$fieldName must be a valid email address']);
    }
    return ValidationResult.valid();
  }

  static ValidationResult validatePhone(String phone, String fieldName) {
    // Basic phone validation - allows digits, spaces, hyphens, parentheses, plus sign
    final phoneRegex = RegExp(r'^[\+]?[0-9\s\-\(\)]{7,15}$');
    if (!phoneRegex.hasMatch(phone)) {
      return ValidationResult.invalid(['$fieldName must be a valid phone number']);
    }
    return ValidationResult.valid();
  }

  static ValidationResult validateUrl(String url, String fieldName) {
    final urlRegex = RegExp(
      r'^https?://(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
    );
    if (!urlRegex.hasMatch(url)) {
      return ValidationResult.invalid(['$fieldName must be a valid URL']);
    }
    return ValidationResult.valid();
  }

  static ValidationResult validateBarcode(String barcode, String fieldName) {
    // Basic barcode validation - should be numeric and reasonable length
    if (!RegExp(r'^\d{8,18}$').hasMatch(barcode)) {
      return ValidationResult.invalid(['$fieldName must be 8-18 digits']);
    }
    return ValidationResult.valid();
  }

  static ValidationResult validateDateNotInFuture(DateTime date, String fieldName) {
    if (date.isAfter(DateTime.now())) {
      return ValidationResult.invalid(['$fieldName cannot be in the future']);
    }
    return ValidationResult.valid();
  }

  static ValidationResult validateDateNotInPast(DateTime date, String fieldName) {
    if (date.isBefore(DateTime.now())) {
      return ValidationResult.invalid(['$fieldName cannot be in the past']);
    }
    return ValidationResult.valid();
  }

  static ValidationResult validateDateNotTooOld(DateTime date, int maxYears, String fieldName) {
    final maxAge = DateTime.now().subtract(Duration(days: maxYears * 365));
    if (date.isBefore(maxAge)) {
      return ValidationResult.invalid(['$fieldName cannot be more than $maxYears years old']);
    }
    return ValidationResult.valid();
  }
}
