import 'package:get_it/get_it.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:http/http.dart' as http;
import '../../data/repositories/auth_repository.dart';
import '../../data/repositories/product_repository.dart';
import '../../data/repositories/cart_repository.dart';
import '../../data/repositories/order_repository.dart';
import '../../data/repositories/settings_repository.dart';
import '../../data/sources/local/database/app_database.dart';
import '../../data/sources/local/preferences/app_preferences.dart';
import '../../data/sources/remote/api_client.dart';
import '../../domain/usecases/auth/login_usecase.dart';
import '../../domain/usecases/auth/logout_usecase.dart';
import '../../domain/usecases/products/get_products_usecase.dart';
import '../../domain/usecases/products/search_products_usecase.dart';
import '../../domain/usecases/cart/add_to_cart_usecase.dart';
import '../../domain/usecases/cart/get_cart_usecase.dart';
import '../../domain/usecases/cart/update_cart_item_usecase.dart';
import '../../domain/usecases/cart/remove_from_cart_usecase.dart';
import '../../domain/usecases/cart/clear_cart_usecase.dart';
import '../../domain/usecases/orders/create_order_usecase.dart';
import '../../domain/usecases/orders/get_orders_usecase.dart';
import '../../domain/usecases/settings/get_settings_usecase.dart';
import '../../domain/usecases/settings/update_settings_usecase.dart';
import '../bloc/auth/auth_bloc.dart';
import '../bloc/products/products_bloc.dart';
import '../bloc/cart/cart_bloc.dart';
import '../bloc/orders/orders_bloc.dart';
import '../bloc/settings/settings_bloc.dart';

final getIt = GetIt.instance;

Future<void> setupDependencyInjection() async {
  // External dependencies
  final sharedPreferences = await SharedPreferences.getInstance();
  const secureStorage = FlutterSecureStorage();
  final connectivity = Connectivity();

  // Core services
  getIt.registerLazySingleton<SharedPreferences>(() => sharedPreferences);
  getIt.registerLazySingleton<FlutterSecureStorage>(() => secureStorage);
  getIt.registerLazySingleton<Connectivity>(() => connectivity);
  getIt.registerLazySingleton<http.Client>(() => http.Client());

  // Database
  getIt.registerLazySingleton<AppDatabase>(() => AppDatabase());

  // Preferences
  getIt.registerLazySingleton<AppPreferences>(
    () => AppPreferences(sharedPreferences, secureStorage),
  );

  // API Client
  getIt.registerLazySingleton<ApiClient>(
    () => ApiClient(
      client: getIt<http.Client>(),
      preferences: getIt<AppPreferences>(),
      connectivity: getIt<Connectivity>(),
    ),
  );

  // Repositories
  getIt.registerLazySingleton<AuthRepository>(
    () => AuthRepository(
      apiClient: getIt<ApiClient>(),
      preferences: getIt<AppPreferences>(),
    ),
  );

  getIt.registerLazySingleton<ProductRepository>(
    () => ProductRepository(
      apiClient: getIt<ApiClient>(),
      database: getIt<AppDatabase>(),
      connectivity: getIt<Connectivity>(),
    ),
  );

  getIt.registerLazySingleton<CartRepository>(
    () => CartRepository(
      database: getIt<AppDatabase>(),
    ),
  );

  getIt.registerLazySingleton<OrderRepository>(
    () => OrderRepository(
      apiClient: getIt<ApiClient>(),
      database: getIt<AppDatabase>(),
      connectivity: getIt<Connectivity>(),
    ),
  );

  getIt.registerLazySingleton<SettingsRepository>(
    () => SettingsRepository(
      preferences: getIt<AppPreferences>(),
    ),
  );

  // Use Cases
  // Auth
  getIt.registerLazySingleton<LoginUseCase>(
    () => LoginUseCase(getIt<AuthRepository>()),
  );

  getIt.registerLazySingleton<LogoutUseCase>(
    () => LogoutUseCase(getIt<AuthRepository>()),
  );

  // Products
  getIt.registerLazySingleton<GetProductsUseCase>(
    () => GetProductsUseCase(getIt<ProductRepository>()),
  );

  getIt.registerLazySingleton<SearchProductsUseCase>(
    () => SearchProductsUseCase(getIt<ProductRepository>()),
  );

  // Cart
  getIt.registerLazySingleton<AddToCartUseCase>(
    () => AddToCartUseCase(getIt<CartRepository>()),
  );

  getIt.registerLazySingleton<GetCartUseCase>(
    () => GetCartUseCase(getIt<CartRepository>()),
  );

  getIt.registerLazySingleton<UpdateCartItemUseCase>(
    () => UpdateCartItemUseCase(getIt<CartRepository>()),
  );

  getIt.registerLazySingleton<RemoveFromCartUseCase>(
    () => RemoveFromCartUseCase(getIt<CartRepository>()),
  );

  getIt.registerLazySingleton<ClearCartUseCase>(
    () => ClearCartUseCase(getIt<CartRepository>()),
  );

  // Orders
  getIt.registerLazySingleton<CreateOrderUseCase>(
    () => CreateOrderUseCase(getIt<OrderRepository>()),
  );

  getIt.registerLazySingleton<GetOrdersUseCase>(
    () => GetOrdersUseCase(getIt<OrderRepository>()),
  );

  // Settings
  getIt.registerLazySingleton<GetSettingsUseCase>(
    () => GetSettingsUseCase(getIt<SettingsRepository>()),
  );

  getIt.registerLazySingleton<UpdateSettingsUseCase>(
    () => UpdateSettingsUseCase(getIt<SettingsRepository>()),
  );

  // BLoCs
  getIt.registerFactory<AuthBloc>(
    () => AuthBloc(
      loginUseCase: getIt<LoginUseCase>(),
      logoutUseCase: getIt<LogoutUseCase>(),
    ),
  );

  getIt.registerFactory<ProductsBloc>(
    () => ProductsBloc(
      getProductsUseCase: getIt<GetProductsUseCase>(),
      searchProductsUseCase: getIt<SearchProductsUseCase>(),
    ),
  );

  getIt.registerFactory<CartBloc>(
    () => CartBloc(
      addToCartUseCase: getIt<AddToCartUseCase>(),
      getCartUseCase: getIt<GetCartUseCase>(),
      updateCartItemUseCase: getIt<UpdateCartItemUseCase>(),
      removeFromCartUseCase: getIt<RemoveFromCartUseCase>(),
      clearCartUseCase: getIt<ClearCartUseCase>(),
    ),
  );

  getIt.registerFactory<OrdersBloc>(
    () => OrdersBloc(
      createOrderUseCase: getIt<CreateOrderUseCase>(),
      getOrdersUseCase: getIt<GetOrdersUseCase>(),
    ),
  );

  getIt.registerFactory<SettingsBloc>(
    () => SettingsBloc(
      getSettingsUseCase: getIt<GetSettingsUseCase>(),
      updateSettingsUseCase: getIt<UpdateSettingsUseCase>(),
    ),
  );
}