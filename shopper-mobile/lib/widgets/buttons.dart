import 'package:flutter/material.dart';
import '../core/design_system.dart';
import 'common.dart';

// Loading Indicator
class ShopperLoadingIndicator extends StatelessWidget {
  final Color? color;
  final double size;

  const ShopperLoadingIndicator({
    super.key,
    this.color,
    this.size = 20,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: CircularProgressIndicator(
        strokeWidth: 2,
        valueColor: AlwaysStoppedAnimation<Color>(color ?? kPrimaryColor),
      ),
    );
  }
}

// Primary Button
class ShopperPrimaryButton extends StatelessWidget {
  final String text;
  final VoidCallback? onPressed;
  final bool isLoading;
  final bool isDisabled;

  const ShopperPrimaryButton({
    super.key,
    required this.text,
    this.onPressed,
    this.isLoading = false,
    this.isDisabled = false,
  });

  @override
  Widget build(BuildContext context) {
    final bool isEnabled = !isDisabled && !isLoading && onPressed != null;

    return SizedBox(
      height: kMinTouchTarget,
      child: ElevatedButton(
        onPressed: isEnabled ? onPressed : null,
        style: ElevatedButton.styleFrom(
          backgroundColor: isEnabled ? kPrimaryColor : Colors.grey,
          foregroundColor: kOnPrimaryColor,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(kBorderRadiusMedium),
          ),
          elevation: 0,
          shadowColor: Colors.transparent,
        ),
        child: isLoading
            ? ShopperLoadingIndicator(color: kOnPrimaryColor)
            : Text(
                text,
                style: kBodyMedium.copyWith(
                  color: kOnPrimaryColor,
                  fontWeight: FontWeight.w600,
                ),
              ),
      ),
    );
  }
}

// Secondary Button
class ShopperSecondaryButton extends StatelessWidget {
  final String text;
  final VoidCallback? onPressed;
  final bool isLoading;
  final bool isDisabled;

  const ShopperSecondaryButton({
    super.key,
    required this.text,
    this.onPressed,
    this.isLoading = false,
    this.isDisabled = false,
  });

  @override
  Widget build(BuildContext context) {
    final bool isEnabled = !isDisabled && !isLoading && onPressed != null;

    return SizedBox(
      height: kMinTouchTarget,
      child: OutlinedButton(
        onPressed: isEnabled ? onPressed : null,
        style: OutlinedButton.styleFrom(
          side: BorderSide(
            color: isEnabled ? kPrimaryColor : Colors.grey,
            width: 1,
          ),
          foregroundColor: isEnabled ? kPrimaryColor : Colors.grey,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(kBorderRadiusMedium),
          ),
        ),
        child: isLoading
            ? ShopperLoadingIndicator(color: kPrimaryColor)
            : Text(
                text,
                style: kBodyMedium.copyWith(
                  color: isEnabled ? kPrimaryColor : Colors.grey,
                  fontWeight: FontWeight.w600,
                ),
              ),
      ),
    );
  }
}

// Ghost Button
class ShopperGhostButton extends StatelessWidget {
  final String text;
  final VoidCallback? onPressed;
  final bool isLoading;
  final bool isDisabled;

  const ShopperGhostButton({
    super.key,
    required this.text,
    this.onPressed,
    this.isLoading = false,
    this.isDisabled = false,
  });

  @override
  Widget build(BuildContext context) {
    final bool isEnabled = !isDisabled && !isLoading && onPressed != null;

    return SizedBox(
      height: kMinTouchTarget,
      child: TextButton(
        onPressed: isEnabled ? onPressed : null,
        style: TextButton.styleFrom(
          foregroundColor: isEnabled ? kPrimaryColor : Colors.grey,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(kBorderRadiusMedium),
          ),
        ),
        child: isLoading
            ? ShopperLoadingIndicator(color: kPrimaryColor)
            : Text(
                text,
                style: kBodyMedium.copyWith(
                  color: isEnabled ? kPrimaryColor : Colors.grey,
                  fontWeight: FontWeight.w600,
                ),
              ),
      ),
    );
  }
}

// Input Field
class ShopperInputField extends StatelessWidget {
  final TextEditingController? controller;
  final String? label;
  final String? hint;
  final String? error;
  final bool obscureText;
  final TextInputType keyboardType;
  final ValueChanged<String>? onChanged;
  final FormFieldValidator<String>? validator;
  final Widget? prefixIcon;
  final Widget? suffixIcon;

  const ShopperInputField({
    super.key,
    this.controller,
    this.label,
    this.hint,
    this.error,
    this.obscureText = false,
    this.keyboardType = TextInputType.text,
    this.onChanged,
    this.validator,
    this.prefixIcon,
    this.suffixIcon,
  });

  @override
  Widget build(BuildContext context) {
    final bool hasError = error != null && error!.isNotEmpty;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (label != null) ShopperFieldLabel(text: label!, required: false),
        SizedBox(
          height: kMinTouchTarget,
          child: TextFormField(
            controller: controller,
            obscureText: obscureText,
            keyboardType: keyboardType,
            onChanged: onChanged,
            validator: validator,
            style: kBodyMedium.copyWith(color: kOnSurfaceColor),
            decoration: InputDecoration(
              hintText: hint,
              hintStyle: kBodyMedium.copyWith(color: Colors.grey),
              prefixIcon: prefixIcon,
              suffixIcon: suffixIcon,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(kBorderRadiusMedium),
                borderSide: const BorderSide(color: Colors.grey),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(kBorderRadiusMedium),
                borderSide: BorderSide(color: hasError ? kErrorColor : Colors.grey),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(kBorderRadiusMedium),
                borderSide: BorderSide(color: hasError ? kErrorColor : kPrimaryColor, width: 2),
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
            ),
          ),
        ),
        if (hasError) ShopperErrorText(error: error!),
      ],
    );
  }
}

// Card
class ShopperCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final VoidCallback? onTap;
  final bool elevated;

  const ShopperCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(kSpacing16),
    this.onTap,
    this.elevated = false,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: elevated ? 4 : 0,
      shadowColor: elevated ? null : Colors.transparent,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(kBorderRadiusLarge),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(kBorderRadiusLarge),
        child: Padding(
          padding: padding!,
          child: child,
        ),
      ),
    );
  }
}

// Bottom Sheet
class ShopperBottomSheet extends StatelessWidget {
  final Widget child;
  final double? height;

  const ShopperBottomSheet({
    super.key,
    required this.child,
    this.height,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: height,
      decoration: BoxDecoration(
        color: kSurfaceColor,
        borderRadius: const BorderRadius.vertical(
          top: Radius.circular(kBorderRadiusXLarge),
        ),
        boxShadow: const [kElevation4],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 40,
            height: 4,
            margin: const EdgeInsets.symmetric(vertical: kSpacing12),
            decoration: BoxDecoration(
              color: Colors.grey[300],
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          Expanded(child: child),
        ],
      ),
    );
  }
}