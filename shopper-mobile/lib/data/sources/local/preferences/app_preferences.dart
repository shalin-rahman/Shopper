import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../../../domain/entities/auth_token.dart';
import '../../../../domain/entities/settings.dart';

class AppPreferences {
  static const String _authTokenKey = 'auth_token';
  static const String _settingsKey = 'app_settings';
  static const String _themeModeKey = 'theme_mode';
  static const String _languageKey = 'language';
  static const String _biometricEnabledKey = 'biometric_enabled';
  static const String _notificationsEnabledKey = 'notifications_enabled';
  static const String _soundEnabledKey = 'sound_enabled';
  static const String _vibrationEnabledKey = 'vibration_enabled';
  static const String _autoSyncEnabledKey = 'auto_sync_enabled';
  static const String _syncIntervalKey = 'sync_interval_minutes';

  final SharedPreferences _sharedPreferences;
  final FlutterSecureStorage _secureStorage;

  AppPreferences(this._sharedPreferences, this._secureStorage);

  // Auth Token Management
  Future<void> saveAuthToken(AuthToken token) async {
    final tokenJson = json.encode({
      'access_token': token.accessToken,
      'refresh_token': token.refreshToken,
      'expires_at': token.expiresAt.toIso8601String(),
      'token_type': token.tokenType,
    });

    await _secureStorage.write(key: _authTokenKey, value: tokenJson);
  }

  Future<AuthToken?> getAuthToken() async {
    final tokenJson = await _secureStorage.read(key: _authTokenKey);
    if (tokenJson == null) return null;

    try {
      final tokenData = json.decode(tokenJson);
      return AuthToken(
        accessToken: tokenData['access_token'],
        refreshToken: tokenData['refresh_token'],
        expiresAt: DateTime.parse(tokenData['expires_at']),
        tokenType: tokenData['token_type'] ?? 'Bearer',
      );
    } catch (e) {
      return null;
    }
  }

  Future<void> clearAuthToken() async {
    await _secureStorage.delete(key: _authTokenKey);
  }

  Future<bool> isLoggedIn() async {
    final token = await getAuthToken();
    return token != null && !token.isExpired;
  }

  // Settings Management
  Future<void> saveSettings(AppSettings settings) async {
    await _sharedPreferences.setString(_themeModeKey, settings.themeMode.value);
    await _sharedPreferences.setString(_languageKey, settings.language.value);
    await _sharedPreferences.setBool(_biometricEnabledKey, settings.enableBiometric);
    await _sharedPreferences.setBool(_notificationsEnabledKey, settings.enableNotifications);
    await _sharedPreferences.setBool(_soundEnabledKey, settings.enableSound);
    await _sharedPreferences.setBool(_vibrationEnabledKey, settings.enableVibration);
    await _sharedPreferences.setBool(_autoSyncEnabledKey, settings.autoSync);
    await _sharedPreferences.setInt(_syncIntervalKey, settings.syncIntervalMinutes);
  }

  Future<AppSettings> getSettings() async {
    return AppSettings(
      themeMode: ThemeMode.fromString(
        _sharedPreferences.getString(_themeModeKey) ?? ThemeMode.system.value,
      ),
      language: Language.fromString(
        _sharedPreferences.getString(_languageKey) ?? Language.english.value,
      ),
      enableBiometric: _sharedPreferences.getBool(_biometricEnabledKey) ?? false,
      enableNotifications: _sharedPreferences.getBool(_notificationsEnabledKey) ?? true,
      enableSound: _sharedPreferences.getBool(_soundEnabledKey) ?? true,
      enableVibration: _sharedPreferences.getBool(_vibrationEnabledKey) ?? true,
      autoSync: _sharedPreferences.getBool(_autoSyncEnabledKey) ?? true,
      syncIntervalMinutes: _sharedPreferences.getInt(_syncIntervalKey) ?? 15,
    );
  }

  // Clear all data
  Future<void> clearAll() async {
    await _sharedPreferences.clear();
    await _secureStorage.deleteAll();
  }
}