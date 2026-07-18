import 'package:dio/dio.dart';

import '../auth/token_store.dart';
import 'api_config.dart';

typedef OnUnauthorized = Future<void> Function();

class ApiClient {
  ApiClient({
    required this._tokenStore,
    required this._onUnauthorized,
  }) {
    _dio = Dio(
      BaseOptions(
        baseUrl: ApiConfig.baseUrl,
        connectTimeout: const Duration(seconds: 20),
        receiveTimeout: const Duration(seconds: 60),
        headers: {
          'Accept': 'application/json',
          'User-Agent': 'PoiskerFlutter/1.0',
        },
      ),
    );
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          final token = _tokenStore.accessToken;
          if (token != null && token.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          handler.next(options);
        },
        onError: (error, handler) async {
          if (error.response?.statusCode == 401 && !_refreshing) {
            final ok = await _tryRefresh();
            if (ok) {
              final req = error.requestOptions;
              req.headers['Authorization'] = 'Bearer ${_tokenStore.accessToken}';
              try {
                final response = await _dio.fetch(req);
                return handler.resolve(response);
              } catch (_) {
                return handler.next(error);
              }
            }
            await _onUnauthorized();
          }
          handler.next(error);
        },
      ),
    );
  }

  late final Dio _dio;
  final TokenStore _tokenStore;
  final OnUnauthorized _onUnauthorized;
  bool _refreshing = false;

  Dio get raw => _dio;

  Future<bool> _tryRefresh() async {
    final refresh = _tokenStore.refreshToken;
    if (refresh == null || refresh.isEmpty) return false;
    _refreshing = true;
    try {
      final response = await Dio(
        BaseOptions(baseUrl: ApiConfig.baseUrl),
      ).post<Map<String, dynamic>>(
        'auth/refresh/',
        data: {'refresh': refresh},
      );
      final data = response.data ?? {};
      final access = data['access'] as String?;
      final newRefresh = (data['refresh'] as String?) ?? refresh;
      if (access == null || access.isEmpty) return false;
      await _tokenStore.save(access: access, refresh: newRefresh);
      return true;
    } catch (_) {
      return false;
    } finally {
      _refreshing = false;
    }
  }

  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? query,
  }) {
    return _dio.get<T>(path, queryParameters: query);
  }

  Future<Response<T>> post<T>(
    String path, {
    Object? data,
  }) {
    return _dio.post<T>(path, data: data);
  }

  Future<Response<T>> patch<T>(
    String path, {
    Object? data,
  }) {
    return _dio.patch<T>(path, data: data);
  }

  Future<Response<T>> delete<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? query,
  }) {
    return _dio.delete<T>(path, data: data, queryParameters: query);
  }

  Future<Response<T>> postMultipart<T>(String path, FormData data) {
    return _dio.post<T>(
      path,
      data: data,
      options: Options(contentType: 'multipart/form-data'),
    );
  }

  Future<Response<T>> patchMultipart<T>(String path, FormData data) {
    return _dio.patch<T>(
      path,
      data: data,
      options: Options(contentType: 'multipart/form-data'),
    );
  }

  static ApiException mapError(Object error) {
    if (error is ApiException) return error;
    if (error is! DioException) {
      return ApiException(message: error.toString());
    }
    if (error.type == DioExceptionType.connectionError ||
        error.type == DioExceptionType.connectionTimeout ||
        error.type == DioExceptionType.receiveTimeout) {
      return ApiException(
        message: 'Нет сети. Проверьте подключение и попробуйте снова.',
        code: 'network',
      );
    }
    final data = error.response?.data;
    if (data is Map) {
      final fields = <String, List<String>>{};
      void absorbFields(Map raw) {
        raw.forEach((key, value) {
          final k = key.toString();
          if (k == 'message' || k == 'detail' || k == 'code') return;
          if (k == 'fields' && value is Map) {
            absorbFields(value);
            return;
          }
          if (value is List) {
            fields[k] = value.map((e) => e.toString()).toList();
          } else if (value is String && value.isNotEmpty) {
            fields[k] = [value];
          }
        });
      }

      absorbFields(Map<dynamic, dynamic>.from(data));

      String message;
      if (data['message'] != null) {
        message = data['message'].toString();
      } else if (data['detail'] != null) {
        message = data['detail'].toString();
      } else if (fields['non_field_errors']?.isNotEmpty == true) {
        message = fields['non_field_errors']!.first;
      } else if (fields.isNotEmpty) {
        message = 'Проверьте введённые данные';
      } else {
        message = 'Ошибка запроса';
      }

      final code = (data['code'] ??
              (error.response?.statusCode == 429 ? 'rate_limited' : 'error'))
          .toString();
      return ApiException(
        message: message,
        code: code,
        statusCode: error.response?.statusCode,
        fields: fields,
      );
    }
    return ApiException(
      message: error.message ?? 'Сетевая ошибка',
      statusCode: error.response?.statusCode,
    );
  }
}
