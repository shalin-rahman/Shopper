# Validation System Documentation

## Overview

The Shopper Mobile POS application implements a comprehensive validation system that ensures data integrity across all layers of the application. The validation system provides early error detection, user-friendly error messages, and consistent validation behavior throughout the app.

## Architecture

### Core Components

1. **ValidationResult Class** (`lib/core/validation/validation.dart`)
   - Represents the result of a validation operation
   - Contains `isValid` boolean and `errors` list
   - Provides `merge()` method for combining multiple validations

2. **ValidationUtils Class** (`lib/core/validation/validation.dart`)
   - Static utility methods for common validation rules
   - Includes email, phone, URL, date, numeric, and string validations

3. **ValidationFailure Class** (`lib/core/error/failures.dart`)
   - Extends the base Failure class
   - Handles validation-specific error information
   - Supports both single and multiple error messages

### Validation Flow

```
User Input → BLoC Event → Use Case → Parameter Validation → Repository → API/Local Storage
     ↓              ↓              ↓              ↓              ↓
Validation     Validation     Validation     Business     Network/
Failure        Failure        Failure        Logic        Database
     ↓              ↓              ↓              ↓              ↓
UI Error       UI Error       UI Error       UI Error     UI Error
Display        Display        Display        Display      Display
```

## Entity Validation

All domain entities implement a `validate()` method that returns a `ValidationResult`.

### User Entity
- **Required Fields**: id, email, name, role
- **Email Validation**: RFC-compliant email format
- **Role Validation**: Must be one of [admin, manager, cashier, staff]
- **Date Validation**: Created/updated dates cannot be in future or too old

### AuthToken Entity
- **Required Fields**: accessToken, refreshToken, expiresAt, tokenType
- **Token Format**: JWT-like format validation
- **Token Type**: Must be one of [Bearer, Basic, Digest]
- **Expiry Validation**: Cannot be expired or in past

### Product Entity
- **Required Fields**: id, name, price, category
- **Price Validation**: Must be positive, max 999,999.99
- **Stock Validation**: Non-negative integers
- **Tax Validation**: 0-100% range
- **URL Validation**: Valid HTTP/HTTPS URLs for images

### Cart/CartItem Entities
- **Quantity Validation**: 1-9999 range
- **Price Validation**: Positive values, max 999,999.99
- **Discount Validation**: Cannot exceed unit price
- **Business Rules**: Bulk discounts require manager approval

### Order/OrderItem Entities
- **Order Number**: Must follow ORD-XXXXXX format
- **Status Validation**: Business logic for status transitions
- **Total Validation**: Cannot exceed 999,999.99
- **Item Limits**: Max 999 total items per order

### Settings Entity
- **Sync Interval**: 5-1440 minutes
- **Backup Interval**: 1-365 days
- **Printer Address**: Valid IP/hostname format
- **Currency Symbol**: 1-5 characters
- **Decimal Places**: 0-4 range

## Use Case Validation

All use case parameter classes implement validation:

### Auth Use Cases
- **LoginParams**: Email format, password length (6-128 chars)

### Cart Use Cases
- **AddToCartParams**: Product ID, quantity, discount, notes validation

### Order Use Cases
- **CreateOrderParams**: Cart validation, customer info validation

### Product Use Cases
- **GetProductsParams**: Pagination limits, search query validation
- **SearchProductsParams**: Query length validation

### Settings Use Cases
- **UpdateSettingsParams**: Full settings object validation

## BLoC Layer Integration

All BLoC classes handle `ValidationFailure` specifically:

```dart
result.fold(
  (failure) {
    if (failure is ValidationFailure) {
      emit(ErrorState(failure.errors.isNotEmpty ? failure.errors.first : failure.message));
    } else {
      emit(ErrorState(failure.message));
    }
  },
  (data) => emit(SuccessState(data)),
);
```

## UI Components

### ValidationErrorDisplay
- Displays multiple validation errors in a styled container
- Includes error icon and bullet-pointed error list
- Consistent with app design system

### ValidationErrorText
- Shows single error message below form fields
- Customizable styling and positioning

### ValidatedTextFormField
- Pre-styled form field with built-in error display
- Consistent theming with app design system
- Supports all standard TextFormField properties

## Testing

Comprehensive test suite covers:
- Entity validation (valid/invalid scenarios)
- Use case parameter validation
- ValidationUtils utility methods
- ValidationFailure error handling
- Edge cases and boundary conditions

Run tests with:
```bash
flutter test test/validation_test.dart
```

## Usage Examples

### Entity Validation
```dart
final user = User(...);
final result = user.validate();
if (!result.isValid) {
  // Handle validation errors
  print(result.errors);
}
```

### Use Case Validation
```dart
final params = LoginParams(email: 'user@example.com', password: 'pass123');
final result = params.validate();
if (!result.isValid) {
  return Left(ValidationFailure(result.errors));
}
```

### UI Error Display
```dart
ValidationErrorDisplay(errors: validationErrors)

ValidationErrorText(error: 'Invalid email format')

ValidatedTextFormField(
  controller: emailController,
  labelText: 'Email',
  errorText: emailError,
)
```

## Business Rules Enforced

1. **Authentication**: Secure password requirements, valid email formats
2. **Inventory**: Stock limits, pricing constraints, discount rules
3. **Orders**: Order number formats, status transitions, total limits
4. **Settings**: Configuration ranges, printer validation, sync intervals
5. **Data Integrity**: Required fields, format validation, range checking

## Error Messages

All error messages are:
- User-friendly and actionable
- Consistent in tone and format
- Specific to the validation rule violated
- Include field names and expected values where helpful

## Future Enhancements

- Localization support for error messages
- Custom validation rules per tenant
- Real-time validation feedback
- Validation rule configuration via API
- Advanced business rule engine integration