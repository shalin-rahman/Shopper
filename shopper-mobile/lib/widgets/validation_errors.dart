import 'package:flutter/material.dart';
import '../core/design_system.dart';

/// A widget that displays validation errors in a user-friendly way
class ValidationErrorDisplay extends StatelessWidget {
  final List<String> errors;
  final EdgeInsetsGeometry? margin;
  final EdgeInsetsGeometry? padding;

  const ValidationErrorDisplay({
    super.key,
    required this.errors,
    this.margin,
    this.padding,
  });

  @override
  Widget build(BuildContext context) {
    if (errors.isEmpty) {
      return const SizedBox.shrink();
    }

    return Container(
      margin: margin ?? const EdgeInsets.symmetric(vertical: 8.0),
      padding: padding ?? const EdgeInsets.all(12.0),
      decoration: BoxDecoration(
        color: kErrorColor.withOpacity(0.1),
        border: Border.all(color: kErrorColor.withOpacity(0.3)),
        borderRadius: BorderRadius.circular(8.0),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.error_outline,
                color: kErrorColor,
                size: 20.0,
              ),
              const SizedBox(width: 8.0),
              Text(
                'Validation Error${errors.length > 1 ? 's' : ''}',
                style: kBodyText2.copyWith(
                  color: kErrorColor,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8.0),
          ...errors.map((error) => Padding(
                padding: const EdgeInsets.only(bottom: 4.0),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '• ',
                      style: kBodyText2.copyWith(color: kErrorColor),
                    ),
                    Expanded(
                      child: Text(
                        error,
                        style: kBodyText2.copyWith(color: kErrorColor),
                      ),
                    ),
                  ],
                ),
              )),
        ],
      ),
    );
  }
}

/// A widget that displays a single validation error as a text
class ValidationErrorText extends StatelessWidget {
  final String? error;
  final TextStyle? style;
  final EdgeInsetsGeometry? padding;

  const ValidationErrorText({
    super.key,
    this.error,
    this.style,
    this.padding,
  });

  @override
  Widget build(BuildContext context) {
    if (error == null || error!.isEmpty) {
      return const SizedBox.shrink();
    }

    return Padding(
      padding: padding ?? const EdgeInsets.only(top: 4.0),
      child: Text(
        error!,
        style: style ??
            kCaption.copyWith(
              color: kErrorColor,
              fontWeight: FontWeight.w500,
            ),
      ),
    );
  }
}

/// A form field wrapper that shows validation errors
class ValidatedTextFormField extends StatelessWidget {
  final TextEditingController? controller;
  final String? initialValue;
  final String? labelText;
  final String? hintText;
  final String? errorText;
  final bool obscureText;
  final TextInputType? keyboardType;
  final TextInputAction? textInputAction;
  final int? maxLength;
  final int? maxLines;
  final bool enabled;
  final ValueChanged<String>? onChanged;
  final ValueChanged<String>? onSubmitted;
  final FormFieldValidator<String>? validator;
  final InputDecoration? decoration;
  final EdgeInsetsGeometry? contentPadding;

  const ValidatedTextFormField({
    super.key,
    this.controller,
    this.initialValue,
    this.labelText,
    this.hintText,
    this.errorText,
    this.obscureText = false,
    this.keyboardType,
    this.textInputAction,
    this.maxLength,
    this.maxLines = 1,
    this.enabled = true,
    this.onChanged,
    this.onSubmitted,
    this.validator,
    this.decoration,
    this.contentPadding,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextFormField(
          controller: controller,
          initialValue: initialValue,
          decoration: decoration ??
              InputDecoration(
                labelText: labelText,
                hintText: hintText,
                contentPadding: contentPadding ?? const EdgeInsets.all(16.0),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8.0),
                  borderSide: BorderSide(color: kOutlineColor),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8.0),
                  borderSide: BorderSide(color: kOutlineColor),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8.0),
                  borderSide: BorderSide(color: kPrimaryColor),
                ),
                errorBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8.0),
                  borderSide: BorderSide(color: kErrorColor),
                ),
                focusedErrorBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8.0),
                  borderSide: BorderSide(color: kErrorColor),
                ),
              ),
          obscureText: obscureText,
          keyboardType: keyboardType,
          textInputAction: textInputAction,
          maxLength: maxLength,
          maxLines: maxLines,
          enabled: enabled,
          onChanged: onChanged,
          onFieldSubmitted: onSubmitted,
          validator: validator,
        ),
        if (errorText != null && errorText!.isNotEmpty)
          ValidationErrorText(error: errorText),
      ],
    );
  }
}