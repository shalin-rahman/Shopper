import 'package:flutter_test/flutter_test.dart';
import 'package:shopper_mobile/core/theme_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('ThemeProvider Tests', () {
    late ThemeProvider themeProvider;

    setUp(() async {
      SharedPreferences.setMockInitialValues({});
      themeProvider = ThemeProvider();
      await themeProvider.init();
    });

    test('Initial theme should be indigo (default)', () {
      expect(themeProvider.currentThemeName, 'indigo');
    });

    test('Setting theme should update currentThemeName', () {
      themeProvider.setTheme('cyberpunk');
      expect(themeProvider.currentThemeName, 'cyberpunk');
    });

    test('Colors should change when theme changes', () {
      final indigoPrimary = themeProvider.colors.primary;
      themeProvider.setTheme('ruby');
      final rubyPrimary = themeProvider.colors.primary;
      
      expect(indigoPrimary, isNot(rubyPrimary));
    });
  });
}
