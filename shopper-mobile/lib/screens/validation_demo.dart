import 'package:flutter/material.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import '../widgets/index.dart';
import '../core/design_system.dart';

// Demo screen showcasing validation components
class ValidationDemoScreen extends StatefulWidget {
  const ValidationDemoScreen({super.key});

  @override
  State<ValidationDemoScreen> createState() => _ValidationDemoScreenState();
}

class _ValidationDemoScreenState extends State<ValidationDemoScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _nameController = TextEditingController();
  final _phoneController = TextEditingController();
  final _quantityController = TextEditingController();
  final _priceController = TextEditingController();

  List<String> _validationErrors = [];
  bool _showValidationErrors = false;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _nameController.dispose();
    _phoneController.dispose();
    _quantityController.dispose();
    _priceController.dispose();
    super.dispose();
  }

  void _validateForm() {
    setState(() {
      _validationErrors = [];
      _showValidationErrors = true;
    });

    // Simulate validation logic
    if (_emailController.text.isEmpty) {
      _validationErrors.add('Email is required');
    } else if (!_emailController.text.contains('@')) {
      _validationErrors.add('Email must be valid');
    }

    if (_passwordController.text.isEmpty) {
      _validationErrors.add('Password is required');
    } else if (_passwordController.text.length < 6) {
      _validationErrors.add('Password must be at least 6 characters');
    }

    if (_nameController.text.isEmpty) {
      _validationErrors.add('Name is required');
    } else if (_nameController.text.length < 2) {
      _validationErrors.add('Name must be at least 2 characters');
    }

    if (_phoneController.text.isNotEmpty && !_phoneController.text.startsWith('+')) {
      _validationErrors.add('Phone number should start with country code');
    }

    if (_quantityController.text.isNotEmpty) {
      final quantity = int.tryParse(_quantityController.text);
      if (quantity == null || quantity <= 0) {
        _validationErrors.add('Quantity must be a positive number');
      } else if (quantity > 9999) {
        _validationErrors.add('Quantity cannot exceed 9999');
      }
    }

    if (_priceController.text.isNotEmpty) {
      final price = double.tryParse(_priceController.text);
      if (price == null || price < 0) {
        _validationErrors.add('Price must be a positive number');
      } else if (price > 999999.99) {
        _validationErrors.add('Price cannot exceed 999,999.99');
      }
    }

    if (_validationErrors.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Form validated successfully!')),
      );
    }
  }

  void _clearValidation() {
    setState(() {
      _validationErrors = [];
      _showValidationErrors = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return ShopperScreen(
      title: 'Validation Demo',
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Validation Error Display Demo
            Text(
              'Validation Error Display',
              style: kHeadline6,
            ),
            const SizedBox(height: 16.0),

            if (_showValidationErrors && _validationErrors.isNotEmpty)
              ValidationErrorDisplay(errors: _validationErrors),

            const SizedBox(height: 24.0),

            // Form Fields Demo
            Text(
              'Form Fields with Validation',
              style: kHeadline6,
            ),
            const SizedBox(height: 16.0),

            Form(
              key: _formKey,
              child: Column(
                children: [
                  ValidatedTextFormField(
                    controller: _emailController,
                    labelText: 'Email',
                    hintText: 'Enter your email',
                    keyboardType: TextInputType.emailAddress,
                    errorText: _showValidationErrors && _emailController.text.isEmpty
                        ? 'Email is required'
                        : _showValidationErrors && !_emailController.text.contains('@')
                            ? 'Invalid email format'
                            : null,
                  ),
                  const SizedBox(height: 16.0),

                  ValidatedTextFormField(
                    controller: _passwordController,
                    labelText: 'Password',
                    hintText: 'Enter your password',
                    obscureText: true,
                    errorText: _showValidationErrors && _passwordController.text.isEmpty
                        ? 'Password is required'
                        : _showValidationErrors && _passwordController.text.length < 6
                            ? 'Password must be at least 6 characters'
                            : null,
                  ),
                  const SizedBox(height: 16.0),

                  ValidatedTextFormField(
                    controller: _nameController,
                    labelText: 'Full Name',
                    hintText: 'Enter your full name',
                    errorText: _showValidationErrors && _nameController.text.isEmpty
                        ? 'Name is required'
                        : _showValidationErrors && _nameController.text.length < 2
                            ? 'Name must be at least 2 characters'
                            : null,
                  ),
                  const SizedBox(height: 16.0),

                  ValidatedTextFormField(
                    controller: _phoneController,
                    labelText: 'Phone Number (Optional)',
                    hintText: '+1234567890',
                    keyboardType: TextInputType.phone,
                    errorText: _showValidationErrors && _phoneController.text.isNotEmpty &&
                               !_phoneController.text.startsWith('+')
                        ? 'Phone should start with country code'
                        : null,
                  ),
                  const SizedBox(height: 16.0),

                  ValidatedTextFormField(
                    controller: _quantityController,
                    labelText: 'Quantity (Optional)',
                    hintText: 'Enter quantity',
                    keyboardType: TextInputType.number,
                    errorText: _showValidationErrors && _quantityController.text.isNotEmpty
                        ? () {
                            final quantity = int.tryParse(_quantityController.text);
                            if (quantity == null || quantity <= 0) {
                              return 'Must be positive number';
                            } else if (quantity > 9999) {
                              return 'Cannot exceed 9999';
                            }
                            return null;
                          }()
                        : null,
                  ),
                  const SizedBox(height: 16.0),

                  ValidatedTextFormField(
                    controller: _priceController,
                    labelText: 'Price (Optional)',
                    hintText: 'Enter price',
                    keyboardType: TextInputType.numberWithOptions(decimal: true),
                    errorText: _showValidationErrors && _priceController.text.isNotEmpty
                        ? () {
                            final price = double.tryParse(_priceController.text);
                            if (price == null || price < 0) {
                              return 'Must be positive number';
                            } else if (price > 999999.99) {
                              return 'Cannot exceed 999,999.99';
                            }
                            return null;
                          }()
                        : null,
                  ),
                ],
              ),
            ),

            const SizedBox(height: 24.0),

            // Action Buttons
            Row(
              children: [
                Expanded(
                  child: ShopperPrimaryButton(
                    text: 'Validate Form',
                    onPressed: _validateForm,
                  ),
                ),
                const SizedBox(width: 16.0),
                Expanded(
                  child: ShopperSecondaryButton(
                    text: 'Clear Errors',
                    onPressed: _clearValidation,
                  ),
                ),
              ],
            ),

            const SizedBox(height: 24.0),

            // Individual Error Text Demo
            Text(
              'Individual Error Text Demo',
              style: kHeadline6,
            ),
            const SizedBox(height: 16.0),

            Container(
              padding: const EdgeInsets.all(16.0),
              decoration: BoxDecoration(
                border: Border.all(color: kOutlineColor),
                borderRadius: BorderRadius.circular(8.0),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Field with Error:',
                    style: kBodyText1,
                  ),
                  const SizedBox(height: 8.0),
                  ValidatedTextFormField(
                    initialValue: 'invalid-email',
                    labelText: 'Email',
                    errorText: 'This email format is invalid',
                  ),
                  const SizedBox(height: 16.0),
                  ValidationErrorText(
                    error: 'This is how individual errors appear below form fields',
                  ),
                ],
              ),
            ),

            const SizedBox(height: 24.0),

            // Usage Instructions
            Text(
              'Usage Instructions',
              style: kHeadline6,
            ),
            const SizedBox(height: 16.0),

            Container(
              padding: const EdgeInsets.all(16.0),
              decoration: BoxDecoration(
                color: kSurfaceColor,
                borderRadius: BorderRadius.circular(8.0),
                border: Border.all(color: kOutlineColor),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '• ValidationErrorDisplay: Shows multiple validation errors in a styled container',
                    style: kBodyText2,
                  ),
                  const SizedBox(height: 8.0),
                  Text(
                    '• ValidationErrorText: Shows single error message below form fields',
                    style: kBodyText2,
                  ),
                  const SizedBox(height: 8.0),
                  Text(
                    '• ValidatedTextFormField: Pre-styled form field with built-in error display',
                    style: kBodyText2,
                  ),
                  const SizedBox(height: 16.0),
                  Text(
                    'All components automatically integrate with the app\'s design system and support both light and dark themes.',
                    style: kBodyText2.copyWith(fontStyle: FontStyle.italic),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}