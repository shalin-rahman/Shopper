import 'package:equatable/equatable.dart';
import '../../core/validation/validation.dart';

/// Represents a product in the inventory system.
/// Supports various product types through flexible attributes and variants.
///
/// Usage examples:
/// - Clothing: Use `color`, `size`, and `attributes` for material/fabric
/// - Electronics: Use `specifications` for technical specs, `attributes` for features
/// - Food: Use `attributes` for expiration, ingredients, allergens
/// - General: Use `variants` for different combinations (color+size, etc.)
class Product extends Equatable {
  final String id;
  final String name;
  final String? description;
  final String? barcode;
  final String? sku;
  final double price; // Base selling price
  final double? costPrice; // Purchase cost
  final double? sellPrice; // Special promotional/sale price
  final String? category;
  final String? brand;
  final String? imageUrl;
  final int stockQuantity;
  final int? minStockLevel;
  final bool isActive;
  final bool isTaxable;
  final double? taxRate;
  final String? unit;
  final String? color; // Product color
  final String? size; // Product size
  final Map<String, dynamic>? attributes; // Flexible attributes (material, weight, dimensions, etc.)
  final Map<String, dynamic>? specifications; // Technical specifications
  final List<String>? images; // Multiple product images
  final List<ProductVariant>? variants; // Product variants for different combinations
  final DateTime createdAt;
  final DateTime updatedAt;

  const Product({
    required this.id,
    required this.name,
    this.description,
    this.barcode,
    this.sku,
    required this.price,
    this.costPrice,
    this.sellPrice, // Special promotional/sale price
    this.category,
    this.brand,
    this.imageUrl,
    required this.stockQuantity,
    this.minStockLevel,
    required this.isActive,
    required this.isTaxable,
    this.taxRate,
    this.unit,
    this.color, // Product color
    this.size, // Product size
    this.attributes, // Flexible attributes
    this.specifications, // Technical specifications
    this.images, // Multiple product images
    this.variants, // Product variants
    required this.createdAt,
    required this.updatedAt,
  });

  /// Returns the effective selling price (sell price if available, otherwise regular price)
  double get effectivePrice => sellPrice ?? price;

  /// Returns the discount amount if sell price is set
  double? get discountAmount => sellPrice != null ? price - sellPrice! : null;

  /// Returns the discount percentage if sell price is set
  double? get discountPercentage => sellPrice != null ? ((price - sellPrice!) / price) * 100 : null;

  /// Returns all available images (main image + additional images)
  List<String> get allImages {
    final List<String> result = [];
    if (imageUrl != null) result.add(imageUrl!);
    if (images != null) result.addAll(images!);
    return result;
  }

  /// Returns a formatted attribute string for display
  String get formattedAttributes {
    final List<String> parts = [];
    if (color != null) parts.add('Color: $color');
    if (size != null) parts.add('Size: $size');
    if (attributes != null) {
      attributes!.forEach((key, value) {
        parts.add('$key: $value');
      });
    }
    return parts.join(', ');
  }

  /// Checks if the product has specific attribute
  bool hasAttribute(String key) {
    if (attributes == null) return false;
    return attributes!.containsKey(key);
  }

  /// Gets attribute value by key
  dynamic getAttribute(String key) {
    return attributes?[key];
  }

  /// Checks if product has variants
  bool get hasVariants => variants != null && variants!.isNotEmpty;

  /// Gets variants by specific attribute value
  List<ProductVariant> getVariantsByAttribute(String attributeKey, String attributeValue) {
    if (variants == null) return [];
    return variants!.where((variant) =>
      variant.attributes[attributeKey] == attributeValue
    ).toList();
  }

  /// Validates the product data
  ValidationResult validate() {
    final List<ValidationResult> validations = [];

    // Required field validations
    validations.add(ValidationUtils.validateRequired(id, 'Product ID'));
    validations.add(ValidationUtils.validateRequired(name, 'Product name'));
    validations.add(ValidationUtils.validateLengthRange(name, 1, 200, 'Product name'));

    // Price validations
    validations.add(ValidationUtils.validatePrice(price, 'Price'));

    if (costPrice != null) {
      validations.add(ValidationUtils.validateNonNegativeNumber(costPrice!, 'Cost price'));
      // Cost price should not exceed selling price
      if (costPrice! > price) {
        validations.add(ValidationResult.invalid(['Cost price cannot exceed selling price']));
      }
    }

    if (sellPrice != null) {
      validations.add(ValidationUtils.validateNonNegativeNumber(sellPrice!, 'Sell price'));
      // Sell price should not exceed regular price
      if (sellPrice! > price) {
        validations.add(ValidationResult.invalid(['Sell price cannot exceed regular price']));
      }
    }

    // Stock validations
    validations.add(ValidationUtils.validateNonNegativeInteger(stockQuantity, 'Stock quantity'));

    if (minStockLevel != null) {
      validations.add(ValidationUtils.validateNonNegativeInteger(minStockLevel!, 'Minimum stock level'));
    }

    // Tax validations
    if (taxRate != null) {
      validations.add(ValidationUtils.validatePercentage(taxRate!, 'Tax rate'));
    }

    // Length validations for optional fields
    if (description != null) {
      validations.add(ValidationUtils.validateMaxLength(description!, 1000, 'Description'));
    }

    if (barcode != null) {
      validations.add(ValidationUtils.validateBarcode(barcode!, 'Barcode'));
    }

    if (sku != null) {
      validations.add(ValidationUtils.validateLengthRange(sku!, 1, 50, 'SKU'));
    }

    if (category != null) {
      validations.add(ValidationUtils.validateLengthRange(category!, 1, 100, 'Category'));
    }

    if (brand != null) {
      validations.add(ValidationUtils.validateLengthRange(brand!, 1, 100, 'Brand'));
    }

    if (unit != null) {
      validations.add(ValidationUtils.validateLengthRange(unit!, 1, 20, 'Unit'));
    }

    if (color != null) {
      validations.add(ValidationUtils.validateLengthRange(color!, 1, 50, 'Color'));
    }

    if (size != null) {
      validations.add(ValidationUtils.validateLengthRange(size!, 1, 20, 'Size'));
    }

    // URL validations
    if (imageUrl != null) {
      validations.add(ValidationUtils.validateUrl(imageUrl!, 'Image URL'));
    }

    if (images != null) {
      for (int i = 0; i < images!.length; i++) {
        validations.add(ValidationUtils.validateUrl(images![i], 'Image ${i + 1}'));
      }
    }

    // Date validations
    validations.add(ValidationUtils.validateDateNotInFuture(createdAt, 'Created date'));
    validations.add(ValidationUtils.validateDateNotInFuture(updatedAt, 'Updated date'));
    validations.add(ValidationUtils.validateDateNotTooOld(createdAt, 10, 'Created date'));
    validations.add(ValidationUtils.validateDateNotTooOld(updatedAt, 10, 'Updated date'));

    // Business logic validations
    if (isLowStock && stockQuantity == 0) {
      validations.add(ValidationResult.invalid(['Product is marked as low stock but has zero quantity']));
    }

    // Variant validations
    if (variants != null) {
      for (int i = 0; i < variants!.length; i++) {
        final variantValidation = variants![i].validate();
        if (!variantValidation.isValid) {
          validations.add(ValidationResult.invalid(
            variantValidation.errors.map((error) => 'Variant ${i + 1}: $error').toList()
          ));
        }
      }
    }

    // Combine all validations
    ValidationResult result = ValidationResult.valid();
    for (final validation in validations) {
      result = result.merge(validation);
    }

    return result;
  }

  /// Factory constructor for clothing products
  factory Product.clothing({
    required String id,
    required String name,
    required double price,
    required String color,
    required String size,
    String? description,
    String? brand,
    String? imageUrl,
    List<String>? images,
    Map<String, dynamic>? attributes, // e.g., {"material": "cotton", "care": "machine wash"}
    int stockQuantity = 0,
    double? costPrice,
    double? sellPrice,
  }) {
    return Product(
      id: id,
      name: name,
      description: description,
      price: price,
      costPrice: costPrice,
      sellPrice: sellPrice,
      category: 'clothing',
      brand: brand,
      imageUrl: imageUrl,
      images: images,
      stockQuantity: stockQuantity,
      isActive: true,
      isTaxable: true,
      color: color,
      size: size,
      attributes: attributes,
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
    );
  }

  /// Factory constructor for electronic products
  factory Product.electronics({
    required String id,
    required String name,
    required double price,
    String? description,
    String? brand,
    String? imageUrl,
    List<String>? images,
    required Map<String, dynamic> specifications, // e.g., {"processor": "i7", "ram": "16GB", "storage": "512GB"}
    Map<String, dynamic>? attributes, // e.g., {"warranty": "2 years", "color": "black"}
    int stockQuantity = 0,
    double? costPrice,
    double? sellPrice,
  }) {
    return Product(
      id: id,
      name: name,
      description: description,
      price: price,
      costPrice: costPrice,
      sellPrice: sellPrice,
      category: 'electronics',
      brand: brand,
      imageUrl: imageUrl,
      images: images,
      stockQuantity: stockQuantity,
      isActive: true,
      isTaxable: true,
      specifications: specifications,
      attributes: attributes,
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
    );
  }

  /// Factory constructor for food products
  factory Product.food({
    required String id,
    required String name,
    required double price,
    String? description,
    String? imageUrl,
    List<String>? images,
    required Map<String, dynamic> attributes, // e.g., {"expiration": "2024-12-31", "ingredients": [...], "allergens": [...]}
    int stockQuantity = 0,
    double? costPrice,
    double? sellPrice,
    String? unit = 'kg',
  }) {
    return Product(
      id: id,
      name: name,
      description: description,
      price: price,
      costPrice: costPrice,
      sellPrice: sellPrice,
      category: 'food',
      imageUrl: imageUrl,
      images: images,
      stockQuantity: stockQuantity,
      isActive: true,
      isTaxable: true,
      unit: unit,
      attributes: attributes,
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
    );
  }

  bool get isLowStock => minStockLevel != null && stockQuantity <= minStockLevel!;

  bool get isOutOfStock => stockQuantity <= 0;

  @override
  List<Object?> get props => [
        id,
        name,
        description,
        barcode,
        sku,
        price,
        costPrice,
        sellPrice,
        category,
        brand,
        imageUrl,
        stockQuantity,
        minStockLevel,
        isActive,
        isTaxable,
        taxRate,
        unit,
        color,
        size,
        attributes,
        specifications,
        images,
        variants,
        createdAt,
        updatedAt,
      ];
}

class ProductCategory extends Equatable {
  final String id;
  final String name;
  final String? description;
  final String? imageUrl;
  final bool isActive;
  final DateTime createdAt;

  const ProductCategory({
    required this.id,
    required this.name,
    this.description,
    this.imageUrl,
    required this.isActive,
    required this.createdAt,
  });

  /// Validates the category data
  ValidationResult validate() {
    final List<ValidationResult> validations = [];

    // Required field validations
    validations.add(ValidationUtils.validateRequired(id, 'Category ID'));
    validations.add(ValidationUtils.validateRequired(name, 'Category name'));
    validations.add(ValidationUtils.validateLengthRange(name, 1, 100, 'Category name'));

    // Length validations for optional fields
    if (description != null) {
      validations.add(ValidationUtils.validateMaxLength(description!, 500, 'Category description'));
    }

    // URL validations
    if (imageUrl != null) {
      validations.add(ValidationUtils.validateUrl(imageUrl!, 'Category image URL'));
    }

    // Date validations
    validations.add(ValidationUtils.validateDateNotInFuture(createdAt, 'Category created date'));
    validations.add(ValidationUtils.validateDateNotTooOld(createdAt, 10, 'Category created date'));

    // Combine all validations
    ValidationResult result = ValidationResult.valid();
    for (final validation in validations) {
      result = result.merge(validation);
    }

    return result;
  }

  @override
  List<Object?> get props => [id, name, description, imageUrl, isActive, createdAt];
}

class ProductVariant extends Equatable {
  final String id;
  final String productId;
  final String? sku;
  final String? barcode;
  final Map<String, String> attributes; // e.g., {"color": "red", "size": "M"}
  final double? priceModifier; // Additional price for this variant
  final int stockQuantity;
  final String? imageUrl;
  final bool isActive;
  final DateTime createdAt;
  final DateTime updatedAt;

  const ProductVariant({
    required this.id,
    required this.productId,
    this.sku,
    this.barcode,
    required this.attributes,
    this.priceModifier,
    required this.stockQuantity,
    this.imageUrl,
    required this.isActive,
    required this.createdAt,
    required this.updatedAt,
  });

  /// Returns the display name for this variant (e.g., "Red - Medium")
  String get displayName {
    return attributes.values.join(' - ');
  }

  /// Returns the effective price for this variant
  double getEffectivePrice(double basePrice) {
    return basePrice + (priceModifier ?? 0);
  }

  /// Validates the variant data
  ValidationResult validate() {
    final List<ValidationResult> validations = [];

    // Required field validations
    validations.add(ValidationUtils.validateRequired(id, 'Variant ID'));
    validations.add(ValidationUtils.validateRequired(productId, 'Product ID'));

    // Stock validations
    validations.add(ValidationUtils.validateNonNegativeInteger(stockQuantity, 'Stock quantity'));

    // Price modifier validations
    if (priceModifier != null) {
      if (priceModifier!.abs() > 99999.99) {
        validations.add(ValidationResult.invalid(['Price modifier cannot exceed ±99,999.99']));
      }
    }

    // Length validations
    if (sku != null) {
      validations.add(ValidationUtils.validateLengthRange(sku!, 1, 50, 'Variant SKU'));
    }

    if (barcode != null) {
      validations.add(ValidationUtils.validateBarcode(barcode!, 'Variant barcode'));
    }

    // URL validations
    if (imageUrl != null) {
      validations.add(ValidationUtils.validateUrl(imageUrl!, 'Variant image URL'));
    }

    // Date validations
    validations.add(ValidationUtils.validateDateNotInFuture(createdAt, 'Variant created date'));
    validations.add(ValidationUtils.validateDateNotInFuture(updatedAt, 'Variant updated date'));
    validations.add(ValidationUtils.validateDateNotTooOld(createdAt, 10, 'Variant created date'));
    validations.add(ValidationUtils.validateDateNotTooOld(updatedAt, 10, 'Variant updated date'));

    // Attributes validations
    if (attributes.isEmpty) {
      validations.add(ValidationResult.invalid(['Variant must have at least one attribute']));
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
        id,
        productId,
        sku,
        barcode,
        attributes,
        priceModifier,
        stockQuantity,
        imageUrl,
        isActive,
        createdAt,
        updatedAt,
      ];
}