import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import 'core/theme/poisker_theme.dart';
import 'push/push_service.dart';

class PoiskerApp extends StatefulWidget {
  const PoiskerApp({super.key, required this.router});

  final GoRouter router;

  @override
  State<PoiskerApp> createState() => _PoiskerAppState();
}

class _PoiskerAppState extends State<PoiskerApp> {
  var _wired = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_wired) return;
    _wired = true;
    final push = context.read<PushService>();
    push.onOpen = (data) {
      final route = PushService.routeForPayload(data);
      if (route != null) {
        widget.router.go(route);
      }
    };
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Поискер',
      debugShowCheckedModeBanner: false,
      theme: PoiskerTheme.light,
      routerConfig: widget.router,
    );
  }
}
