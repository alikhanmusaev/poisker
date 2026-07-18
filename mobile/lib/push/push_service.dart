import 'dart:convert';
import 'dart:io';

import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';

import '../core/api/api_client.dart';
import '../core/auth/auth_controller.dart';

typedef PushOpenHandler = void Function(Map<String, String> data);

@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {}

class PushService {
  PushService({required this._auth});

  final AuthController _auth;
  final _local = FlutterLocalNotificationsPlugin();
  String? _deviceId;
  PushOpenHandler? onOpen;

  Future<void> init() async {
    FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);
    const androidInit = AndroidInitializationSettings('@mipmap/ic_launcher');
    await _local.initialize(
      const InitializationSettings(android: androidInit),
      onDidReceiveNotificationResponse: (response) {
        final payload = response.payload;
        if (payload == null || payload.isEmpty) return;
        try {
          final map = Map<String, String>.from(
            (jsonDecode(payload) as Map).map(
              (k, v) => MapEntry(k.toString(), v.toString()),
            ),
          );
          onOpen?.call(map);
        } catch (_) {}
      },
    );
    await _ensureChannels();
    await _ensureDeviceId();

    FirebaseMessaging.onMessage.listen(_showForeground);
    FirebaseMessaging.onMessageOpenedApp.listen((message) {
      onOpen?.call(
        message.data.map((k, v) => MapEntry(k, v.toString())),
      );
    });

    final initial = await FirebaseMessaging.instance.getInitialMessage();
    if (initial != null) {
      // Defer until router is ready.
      Future.microtask(() {
        onOpen?.call(
          initial.data.map((k, v) => MapEntry(k, v.toString())),
        );
      });
    }

    _auth.addListener(_onAuthChanged);
    if (_auth.isAuthenticated) {
      await registerCurrentToken();
    }
  }

  Future<void> _ensureChannels() async {
    final android = _local.resolvePlatformSpecificImplementation<
        AndroidFlutterLocalNotificationsPlugin>();
    await android?.createNotificationChannel(
      const AndroidNotificationChannel(
        'messages',
        'Сообщения',
        importance: Importance.high,
      ),
    );
    await android?.createNotificationChannel(
      const AndroidNotificationChannel(
        'listings',
        'Объявления',
        importance: Importance.defaultImportance,
      ),
    );
    await android?.createNotificationChannel(
      const AndroidNotificationChannel(
        'system',
        'Системные',
        importance: Importance.defaultImportance,
      ),
    );
  }

  Future<void> _ensureDeviceId() async {
    final prefs = await SharedPreferences.getInstance();
    _deviceId = prefs.getString('device_id');
    if (_deviceId == null || _deviceId!.isEmpty) {
      _deviceId = const Uuid().v4();
      await prefs.setString('device_id', _deviceId!);
    }
  }

  Future<void> _onAuthChanged() async {
    if (_auth.isAuthenticated) {
      await registerCurrentToken();
    }
  }

  Future<void> requestPermissionAndRegister() async {
    final settings = await FirebaseMessaging.instance.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );
    if (settings.authorizationStatus == AuthorizationStatus.denied) return;
    await registerCurrentToken();
  }

  Future<void> registerCurrentToken() async {
    if (!_auth.isAuthenticated) return;
    try {
      final token = await FirebaseMessaging.instance.getToken();
      if (token == null || token.isEmpty) return;
      await _auth.api.post(
        'push/devices/',
        data: {
          'token': token,
          'platform': Platform.isIOS ? 'ios' : 'android',
          'device_id': _deviceId,
          'app_version': '1.0.0',
          'app_build': 1,
        },
      );
    } catch (e) {
      debugPrint('FCM register failed: ${ApiClient.mapError(e).message}');
    }
  }

  Future<void> unregister() async {
    if (_deviceId == null) return;
    try {
      await _auth.api.delete(
        'push/devices/current/',
        query: {'device_id': _deviceId},
      );
    } catch (_) {}
  }

  Future<void> _showForeground(RemoteMessage message) async {
    final data = message.data.map((k, v) => MapEntry(k, v.toString()));
    final title = data['title'] ?? message.notification?.title ?? 'Поискер';
    final body = data['body'] ?? message.notification?.body ?? '';
    final type = data['type'] ?? 'system';
    final channel = switch (type) {
      'message' => 'messages',
      'listing_approved' ||
      'listing_rejected' ||
      'listing_expiring' ||
      'listing_expired' =>
        'listings',
      _ => 'system',
    };
    await _local.show(
      title.hashCode ^ body.hashCode,
      title,
      body,
      NotificationDetails(
        android: AndroidNotificationDetails(
          channel,
          channel,
          importance:
              type == 'message' ? Importance.high : Importance.defaultImportance,
          priority:
              type == 'message' ? Priority.high : Priority.defaultPriority,
        ),
      ),
      payload: jsonEncode(data),
    );
  }

  /// Maps FCM data to an in-app route.
  static String? routeForPayload(Map<String, String> data) {
    final type = data['type'] ?? '';
    final entityId = data['entity_id'] ?? '';
    final url = data['url'] ?? '';

    if (type == 'message' && entityId.isNotEmpty) {
      return '/messages/$entityId';
    }
    if (type.startsWith('listing_') && entityId.isNotEmpty) {
      return '/listing/$entityId';
    }

    final messagesMatch = RegExp(r'/messages/([^/]+)').firstMatch(url);
    if (messagesMatch != null) {
      return '/messages/${messagesMatch.group(1)}';
    }
    final listingMatch = RegExp(r'/posts/([^/]+)').firstMatch(url);
    if (listingMatch != null) {
      // Public SEO URLs vary; prefer entity_id when present.
      return null;
    }
    return null;
  }
}
