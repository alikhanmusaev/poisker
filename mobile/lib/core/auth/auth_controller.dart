import 'package:flutter/foundation.dart';

import '../api/api_client.dart';
import '../api/api_config.dart';
import '../api/models.dart';
import 'token_store.dart';

class AuthController extends ChangeNotifier {
  AuthController({required this._tokenStore});

  final TokenStore _tokenStore;
  late final ApiClient api = ApiClient(
    tokenStore: _tokenStore,
    onUnauthorized: logout,
  );

  User? user;
  bool booting = true;
  String? error;
  ApiException? lastError;

  bool get isAuthenticated => user != null && _tokenStore.hasTokens;

  void clearError() {
    if (error == null && lastError == null) return;
    error = null;
    lastError = null;
    notifyListeners();
  }

  Future<void> bootstrap() async {
    booting = true;
    notifyListeners();
    try {
      if (_tokenStore.hasTokens) {
        await refreshMe();
      }
    } catch (_) {
      await _tokenStore.clear();
      user = null;
    } finally {
      booting = false;
      notifyListeners();
    }
  }

  Future<void> refreshMe() async {
    final response = await api.get<Map<String, dynamic>>('auth/me/');
    user = User.fromJson(response.data ?? {});
    notifyListeners();
  }

  Future<void> login({required String email, required String password}) async {
    clearError();
    try {
      final response = await api.post<Map<String, dynamic>>(
        'auth/login/',
        data: {'email': email.trim(), 'password': password},
      );
      final data = response.data ?? {};
      final tokens = data['tokens'] as Map<String, dynamic>? ?? {};
      final access = tokens['access']?.toString() ?? '';
      final refresh = tokens['refresh']?.toString() ?? '';
      if (access.isEmpty || refresh.isEmpty) {
        throw ApiException(message: 'Сервер не вернул токены');
      }
      await _tokenStore.save(access: access, refresh: refresh);
      user = User.fromJson(data['user'] as Map<String, dynamic>? ?? {});
      notifyListeners();
    } catch (e) {
      lastError = ApiClient.mapError(e);
      error = lastError!.displayMessage;
      notifyListeners();
      rethrow;
    }
  }

  Future<String> register({
    required String displayName,
    required String email,
    required String phone,
    required String password,
  }) async {
    clearError();
    try {
      final response = await api.post<Map<String, dynamic>>(
        'auth/register/',
        data: {
          'display_name': displayName.trim(),
          'email': email.trim(),
          'phone': phone.trim(),
          'password': password,
          'accept_terms': true,
          'accept_pdn': true,
        },
      );
      return (response.data?['message'] ??
              'Аккаунт создан. Подтвердите email для входа.')
          .toString();
    } catch (e) {
      lastError = ApiClient.mapError(e);
      error = lastError!.displayMessage;
      notifyListeners();
      rethrow;
    }
  }

  Future<String> resendVerification(String email) async {
    try {
      final response = await api.post<Map<String, dynamic>>(
        'auth/resend-verification/',
        data: {'email': email.trim()},
      );
      return (response.data?['message'] ??
              'Если аккаунт ждёт подтверждения, письмо отправлено')
          .toString();
    } catch (e) {
      throw ApiClient.mapError(e);
    }
  }

  Future<String> requestPasswordReset(String email) async {
    try {
      final response = await api.post<Map<String, dynamic>>(
        'auth/password-reset/',
        data: {'email': email.trim()},
      );
      return (response.data?['message'] ??
              'Если аккаунт существует, мы отправили ссылку')
          .toString();
    } catch (e) {
      throw ApiClient.mapError(e);
    }
  }

  Future<void> updateProfile({
    String? displayName,
    String? phone,
  }) async {
    clearError();
    try {
      final response = await api.patch<Map<String, dynamic>>(
        'me/profile/',
        data: {
          if (displayName != null) 'display_name': displayName.trim(),
          if (phone != null) 'phone': phone.trim(),
        },
      );
      user = User.fromJson(response.data ?? {});
      notifyListeners();
    } catch (e) {
      lastError = ApiClient.mapError(e);
      error = lastError!.displayMessage;
      notifyListeners();
      rethrow;
    }
  }

  Future<void> logout() async {
    final refresh = _tokenStore.refreshToken;
    try {
      if (refresh != null && refresh.isNotEmpty) {
        await api.post('auth/logout/', data: {'refresh': refresh});
      }
    } catch (_) {}
    await _tokenStore.clear();
    user = null;
    clearError();
    notifyListeners();
  }
}
