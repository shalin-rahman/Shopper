import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:connectivity_plus/connectivity_plus.dart';
import '../../../core/error/failures.dart';
import '../../../domain/entities/user.dart';
import '../../../domain/entities/auth_token.dart';
import '../../../domain/entities/product.dart';
import '../../../domain/entities/order.dart';
import '../../../domain/entities/cart.dart';
import '../../../domain/entities/settings.dart';
import '../../../core/validation/validation.dart';
import 'local/preferences/app_preferences.dart';

class ApiClient {
  final http.Client client;
  final AppPreferences preferences;
  final Connectivity connectivity;

  static const String baseUrl = 'https://api.shopper.com/v1'; // Replace with actual API URL

  ApiClient({
    required this.client,
    required this.preferences,
    required this.connectivity,
  });

  Future<bool> _isConnected() async {
    final result = await connectivity.checkConnectivity();
    return result != ConnectivityResult.none;
  }

  Future<Map<String, String>> _getHeaders() async {
    final token = await preferences.getAuthToken();
    return {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      if (token != null) 'Authorization': 'Bearer ${token.accessToken}',
    };
  }

  Future<Either<Failure, T>> _handleResponse<T>(
    http.Response response,
    T Function(Map<String, dynamic>) fromJson, {
    bool validateResponse = true,
  }) async {
    try {
      if (response.statusCode >= 200 && response.statusCode < 300) {
        final data = json.decode(response.body);

        // Validate response data if requested
        if (validateResponse && data is Map<String, dynamic>) {
          final validationResult = _validateApiResponse(data, T.toString());
          if (!validationResult.isValid) {
            return Left(ValidationFailure(validationResult.errors));
          }
        }

        final result = fromJson(data);

        // Validate the created object if it has validation
        if (validateResponse && result is dynamic && result.validate is Function) {
          final validationResult = result.validate();
          if (!validationResult.isValid) {
            return Left(ValidationFailure(validationResult.errors));
          }
        }

        return Right(result);
      } else if (response.statusCode == 401) {
        // Token expired, try to refresh
        final refreshResult = await _refreshTokenIfNeeded();
        if (refreshResult.isLeft()) {
          return Left(AuthFailure('Authentication failed'));
        }
        // Retry the request with new token
        return Left(ServerFailure('Request failed, please retry'));
      } else {
        final error = json.decode(response.body);
        final message = error['message'] ?? 'Unknown error occurred';
        return Left(ServerFailure(message, code: response.statusCode.toString()));
      }
    } catch (e) {
      return Left(ServerFailure('Failed to parse response: ${e.toString()}'));
    }
  }

  /// Validates API response structure based on expected data type
  ValidationResult _validateApiResponse(Map<String, dynamic> data, String type) {
    final List<ValidationResult> validations = [];

    // Common API response validation
    validations.add(ValidationUtils.validateRequired(data, 'API response data'));

    // Type-specific validations
    switch (type) {
      case 'AuthToken':
        validations.add(ValidationUtils.validateRequired(data['access_token'], 'access_token'));
        validations.add(ValidationUtils.validateRequired(data['refresh_token'], 'refresh_token'));
        validations.add(ValidationUtils.validateRequired(data['expires_at'], 'expires_at'));
        if (data['access_token'] != null) {
          final tokenRegex = RegExp(r'^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]*$');
          if (!tokenRegex.hasMatch(data['access_token'])) {
            validations.add(ValidationResult.invalid(['Invalid access token format']));
          }
        }
        break;

      case 'User':
        validations.add(ValidationUtils.validateRequired(data['id'], 'id'));
        validations.add(ValidationUtils.validateRequired(data['email'], 'email'));
        validations.add(ValidationUtils.validateRequired(data['name'], 'name'));
        if (data['email'] != null) {
          validations.add(ValidationUtils.validateEmail(data['email'], 'email'));
        }
        break;

      case 'List<Product>':
        if (data['products'] is List) {
          final products = data['products'] as List;
          for (int i = 0; i < products.length; i++) {
            final product = products[i];
            if (product is Map<String, dynamic>) {
              validations.add(ValidationUtils.validateRequired(product['id'], 'product[$i].id'));
              validations.add(ValidationUtils.validateRequired(product['name'], 'product[$i].name'));
              if (product['price'] != null) {
                final price = product['price'];
                if (price is num && (price < 0 || price > 999999.99)) {
                  validations.add(ValidationResult.invalid(['product[$i].price must be between 0 and 999,999.99']));
                }
              }
            }
          }
        }
        break;

      case 'List<Order>':
        if (data['orders'] is List) {
          final orders = data['orders'] as List;
          for (int i = 0; i < orders.length; i++) {
            final order = orders[i];
            if (order is Map<String, dynamic>) {
              validations.add(ValidationUtils.validateRequired(order['id'], 'order[$i].id'));
              validations.add(ValidationUtils.validateRequired(order['order_number'], 'order[$i].order_number'));
              if (order['order_number'] != null) {
                final orderNumberRegex = RegExp(r'^ORD-\d{6}$');
                if (!orderNumberRegex.hasMatch(order['order_number'])) {
                  validations.add(ValidationResult.invalid(['order[$i].order_number must be in format ORD-XXXXXX']));
                }
              }
            }
          }
        }
        break;

      case 'Cart':
        validations.add(ValidationUtils.validateRequired(data['id'], 'id'));
        validations.add(ValidationUtils.validateRequired(data['items'], 'items'));
        validations.add(ValidationUtils.validateRequired(data['created_at'], 'created_at'));
        validations.add(ValidationUtils.validateRequired(data['updated_at'], 'updated_at'));
        if (data['items'] is List) {
          final items = data['items'] as List;
          for (int i = 0; i < items.length; i++) {
            final item = items[i];
            if (item is Map<String, dynamic>) {
              validations.add(ValidationUtils.validateRequired(item['id'], 'item[$i].id'));
              validations.add(ValidationUtils.validateRequired(item['product'], 'item[$i].product'));
              validations.add(ValidationUtils.validateRequired(item['quantity'], 'item[$i].quantity'));
              validations.add(ValidationUtils.validateRequired(item['unit_price'], 'item[$i].unit_price'));
              validations.add(ValidationUtils.validateRequired(item['added_at'], 'item[$i].added_at'));
              if (item['quantity'] is int && (item['quantity'] <= 0 || item['quantity'] > 9999)) {
                validations.add(ValidationResult.invalid(['item[$i].quantity must be between 1 and 9999']));
              }
              if (item['unit_price'] is num && (item['unit_price'] < 0 || item['unit_price'] > 999999.99)) {
                validations.add(ValidationResult.invalid(['item[$i].unit_price must be between 0 and 999,999.99']));
              }
            }
          }
        }
        break;

      case 'AppSettings':
        validations.add(ValidationUtils.validateRequired(data['theme_mode'], 'theme_mode'));
        validations.add(ValidationUtils.validateRequired(data['language'], 'language'));
        validations.add(ValidationUtils.validateRequired(data['sync_interval_minutes'], 'sync_interval_minutes'));
        validations.add(ValidationUtils.validateRequired(data['backup_interval_days'], 'backup_interval_days'));
        validations.add(ValidationUtils.validateRequired(data['currency_symbol'], 'currency_symbol'));
        validations.add(ValidationUtils.validateRequired(data['decimal_places'], 'decimal_places'));
        if (data['sync_interval_minutes'] is int && (data['sync_interval_minutes'] < 5 || data['sync_interval_minutes'] > 1440)) {
          validations.add(ValidationResult.invalid(['sync_interval_minutes must be between 5 and 1440']));
        }
        if (data['backup_interval_days'] is int && (data['backup_interval_days'] < 1 || data['backup_interval_days'] > 365)) {
          validations.add(ValidationResult.invalid(['backup_interval_days must be between 1 and 365']));
        }
        if (data['decimal_places'] is int && (data['decimal_places'] < 0 || data['decimal_places'] > 4)) {
          validations.add(ValidationResult.invalid(['decimal_places must be between 0 and 4']));
        }
        break;
    }

    ValidationResult result = ValidationResult.valid();
    for (final validation in validations) {
      result = result.merge(validation);
    }

    return result;
  }

  Future<Either<Failure, void>> _refreshTokenIfNeeded() async {
    try {
      final token = await preferences.getAuthToken();
      if (token == null || !token.isExpired) {
        return const Right(null);
      }

      final refreshResult = await refreshToken(token.refreshToken);
      return refreshResult.fold(
        (failure) => Left(failure),
        (_) => const Right(null),
      );
    } catch (e) {
      return Left(AuthFailure('Token refresh failed'));
    }
  }

  // Auth endpoints
  Future<Either<Failure, AuthToken>> login({
    required String email,
    required String password,
  }) async {
    if (!await _isConnected()) {
      return Left(NetworkFailure('No internet connection'));
    }

    try {
      final response = await client.post(
        Uri.parse('$baseUrl/auth/login'),
        headers: await _getHeaders(),
        body: json.encode({
          'email': email,
          'password': password,
        }),
      );

      return _handleResponse(
        response,
        (data) => AuthToken(
          accessToken: data['access_token'],
          refreshToken: data['refresh_token'],
          expiresAt: DateTime.now().add(Duration(seconds: data['expires_in'] ?? 3600)),
        ),
      );
    } catch (e) {
      return Left(NetworkFailure('Network error: ${e.toString()}'));
    }
  }

  Future<Either<Failure, AuthToken>> refreshToken(String refreshToken) async {
    if (!await _isConnected()) {
      return Left(NetworkFailure('No internet connection'));
    }

    try {
      final response = await client.post(
        Uri.parse('$baseUrl/auth/refresh'),
        headers: await _getHeaders(),
        body: json.encode({
          'refresh_token': refreshToken,
        }),
      );

      return _handleResponse(
        response,
        (data) => AuthToken(
          accessToken: data['access_token'],
          refreshToken: data['refresh_token'] ?? refreshToken,
          expiresAt: DateTime.now().add(Duration(seconds: data['expires_in'] ?? 3600)),
        ),
      );
    } catch (e) {
      return Left(NetworkFailure('Network error: ${e.toString()}'));
    }
  }

  Future<Either<Failure, User>> getCurrentUser() async {
    if (!await _isConnected()) {
      return Left(NetworkFailure('No internet connection'));
    }

    try {
      final response = await client.get(
        Uri.parse('$baseUrl/auth/me'),
        headers: await _getHeaders(),
      );

      return _handleResponse(
        response,
        (data) => User(
          id: data['id'],
          email: data['email'],
          name: data['name'],
          phone: data['phone'],
          role: data['role'],
          isActive: data['is_active'] ?? true,
          createdAt: DateTime.parse(data['created_at']),
          updatedAt: DateTime.parse(data['updated_at']),
        ),
      );
    } catch (e) {
      return Left(NetworkFailure('Network error: ${e.toString()}'));
    }
  }

  // Product endpoints
  Future<Either<Failure, List<Product>>> getProducts({
    int? limit,
    int? offset,
    String? category,
    String? searchQuery,
  }) async {
    if (!await _isConnected()) {
      return Left(NetworkFailure('No internet connection'));
    }

    try {
      final queryParams = <String, String>{};
      if (limit != null) queryParams['limit'] = limit.toString();
      if (offset != null) queryParams['offset'] = offset.toString();
      if (category != null) queryParams['category'] = category;
      if (searchQuery != null) queryParams['q'] = searchQuery;

      final uri = Uri.parse('$baseUrl/products').replace(queryParameters: queryParams);

      final response = await client.get(
        uri,
        headers: await _getHeaders(),
      );

      return _handleResponse(
        response,
        (data) => (data['products'] as List)
            .map((product) => Product(
                  id: product['id'],
                  name: product['name'],
                  description: product['description'],
                  barcode: product['barcode'],
                  sku: product['sku'],
                  price: product['price'].toDouble(),
                  costPrice: product['cost_price']?.toDouble(),
                  sellPrice: product['sell_price']?.toDouble(),
                  category: product['category'],
                  brand: product['brand'],
                  imageUrl: product['image_url'],
                  images: product['images'] != null ? List<String>.from(product['images']) : null,
                  stockQuantity: product['stock_quantity'],
                  minStockLevel: product['min_stock_level'],
                  isActive: product['is_active'] ?? true,
                  isTaxable: product['is_taxable'] ?? false,
                  taxRate: product['tax_rate']?.toDouble(),
                  unit: product['unit'],
                  color: product['color'],
                  size: product['size'],
                  attributes: product['attributes'] != null ? Map<String, dynamic>.from(product['attributes']) : null,
                  specifications: product['specifications'] != null ? Map<String, dynamic>.from(product['specifications']) : null,
                  variants: product['variants'] != null
                      ? (product['variants'] as List).map((variant) => ProductVariant(
                            id: variant['id'],
                            productId: variant['product_id'],
                            sku: variant['sku'],
                            barcode: variant['barcode'],
                            attributes: Map<String, String>.from(variant['attributes']),
                            priceModifier: variant['price_modifier']?.toDouble(),
                            stockQuantity: variant['stock_quantity'],
                            imageUrl: variant['image_url'],
                            isActive: variant['is_active'] ?? true,
                            createdAt: DateTime.parse(variant['created_at']),
                            updatedAt: DateTime.parse(variant['updated_at']),
                          )).toList()
                      : null,
                  createdAt: DateTime.parse(product['created_at']),
                  updatedAt: DateTime.parse(product['updated_at']),
                ))
            .toList(),
      );
    } catch (e) {
      return Left(NetworkFailure('Network error: ${e.toString()}'));
    }
  }

  // Order endpoints
  Future<Either<Failure, Order>> createOrder({
    required Map<String, dynamic> orderData,
  }) async {
    if (!await _isConnected()) {
      return Left(NetworkFailure('No internet connection'));
    }

    try {
      final response = await client.post(
        Uri.parse('$baseUrl/orders'),
        headers: await _getHeaders(),
        body: json.encode(orderData),
      );

      return _handleResponse(
        response,
        (data) => Order(
          id: data['id'],
          orderNumber: data['order_number'],
          items: (data['items'] as List)
              .map((item) => OrderItem(
                    id: item['id'],
                    productId: item['product_id'],
                    productName: item['product_name'],
                    quantity: item['quantity'],
                    unitPrice: item['unit_price'].toDouble(),
                    discount: item['discount']?.toDouble(),
                    taxAmount: item['tax_amount']?.toDouble(),
                    notes: item['notes'],
                  ))
              .toList(),
          subtotal: data['subtotal'].toDouble(),
          discount: data['discount']?.toDouble(),
          taxAmount: data['tax_amount']?.toDouble(),
          total: data['total'].toDouble(),
          status: OrderStatus.fromString(data['status']),
          paymentStatus: PaymentStatus.fromString(data['payment_status']),
          customerName: data['customer_name'],
          customerPhone: data['customer_phone'],
          notes: data['notes'],
          createdAt: DateTime.parse(data['created_at']),
          updatedAt: DateTime.parse(data['updated_at']),
        ),
      );
    } catch (e) {
      return Left(NetworkFailure('Network error: ${e.toString()}'));
    }
  }
}