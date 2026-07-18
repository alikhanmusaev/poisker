import 'dart:async';

import 'package:flutter/foundation.dart';

import '../api/repositories.dart';
import '../auth/auth_controller.dart';

class UnreadController extends ChangeNotifier {
  UnreadController({
    required this._auth,
    required this._messaging,
  }) {
    _auth.addListener(_onAuth);
    if (_auth.isAuthenticated) {
      refresh();
      _start();
    }
  }

  final AuthController _auth;
  final MessagingRepository _messaging;
  Timer? _timer;
  int count = 0;

  void _onAuth() {
    if (_auth.isAuthenticated) {
      refresh();
      _start();
    } else {
      count = 0;
      _timer?.cancel();
      notifyListeners();
    }
  }

  void _start() {
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 30), (_) => refresh());
  }

  Future<void> refresh() async {
    if (!_auth.isAuthenticated) return;
    try {
      count = await _messaging.unreadCount();
      notifyListeners();
    } catch (_) {}
  }

  @override
  void dispose() {
    _timer?.cancel();
    _auth.removeListener(_onAuth);
    super.dispose();
  }
}
