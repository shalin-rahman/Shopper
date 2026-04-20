import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:provider/provider.dart';
import 'core/di/injection.dart';
import 'core/theme_provider.dart';
import 'widgets/index.dart';
import 'navigation/app_router.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize dependency injection
  await setupDependencyInjection();

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(
          create: (context) => ThemeProvider(),
        ),
      ],
      child: MultiBlocProvider(
        providers: [
          BlocProvider<AuthBloc>(
            create: (context) => getIt<AuthBloc>(),
          ),
          BlocProvider<ProductsBloc>(
            create: (context) => getIt<ProductsBloc>(),
          ),
          BlocProvider<CartBloc>(
            create: (context) => getIt<CartBloc>(),
          ),
          BlocProvider<OrdersBloc>(
            create: (context) => getIt<OrdersBloc>(),
          ),
          BlocProvider<SettingsBloc>(
            create: (context) => getIt<SettingsBloc>(),
          ),
        ],
        child: const ShopperMobileApp(),
      ),
    ),
  );
}

class ShopperMobileApp extends StatelessWidget {
  const ShopperMobileApp({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<ThemeProvider>(
      builder: (context, themeProvider, child) {
        return MaterialApp(
          title: 'Shopper Mobile',
          localizationsDelegates: const [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          supportedLocales: const [
            Locale('en'), // English
            Locale('bn'), // Bengali
          ],
          theme: themeProvider.themeData,
          onGenerateRoute: AppRouter.generateRoute,
          home: const MainNavigation(),
        );
      },
    );
  }
}