import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import 'app.dart';
import 'core/api/repositories.dart';
import 'core/auth/auth_controller.dart';
import 'core/auth/token_store.dart';
import 'core/router/app_router.dart';
import 'core/unread/unread_controller.dart';
import 'push/push_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.dark,
      statusBarBrightness: Brightness.light,
    ),
  );
  await Firebase.initializeApp();

  final tokenStore = TokenStore();
  await tokenStore.init();
  final auth = AuthController(tokenStore: tokenStore);
  await auth.bootstrap();

  final catalog = CatalogRepository(auth.api);
  final messaging = MessagingRepository(auth.api);
  final unread = UnreadController(auth: auth, messaging: messaging);
  final push = PushService(auth: auth);
  await push.init();
  final router = createAppRouter(auth);

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider.value(value: auth),
        ChangeNotifierProvider.value(value: unread),
        Provider.value(value: push),
        Provider.value(value: catalog),
        Provider.value(value: messaging),
      ],
      child: PoiskerApp(router: router),
    ),
  );
}
