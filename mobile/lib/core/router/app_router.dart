import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/login_screen.dart';
import '../../features/auth/password_reset_screen.dart';
import '../../features/auth/register_screen.dart';
import '../../features/home/home_screen.dart';
import '../../features/listing/bookmarks_screen.dart';
import '../../features/listing/listing_detail_screen.dart';
import '../../features/listing/listing_form_screen.dart';
import '../../features/listing/my_listings_screen.dart';
import '../../features/messages/conversation_screen.dart';
import '../../features/messages/messages_screen.dart';
import '../../features/shell/profile_screen.dart';
import '../../features/shell/shell_screen.dart';
import '../auth/auth_controller.dart';

final GlobalKey<NavigatorState> rootNavigatorKey = GlobalKey<NavigatorState>();

bool _isPublicPath(String loc) {
  if (loc == '/boot' ||
      loc == '/login' ||
      loc == '/register' ||
      loc == '/password-reset' ||
      loc == '/' ||
      loc == '/profile') {
    return true;
  }
  return RegExp(r'^/listing/[^/]+$').hasMatch(loc);
}

GoRouter createAppRouter(AuthController auth) {
  return GoRouter(
    navigatorKey: rootNavigatorKey,
    initialLocation: '/',
    refreshListenable: auth,
    redirect: (context, state) {
      final loc = state.matchedLocation;
      if (auth.booting) {
        return loc == '/boot' ? null : '/boot';
      }
      if (loc == '/boot') {
        return '/';
      }
      if (!auth.isAuthenticated && !_isPublicPath(loc)) {
        return '/login';
      }
      if (auth.isAuthenticated &&
          (loc == '/login' || loc == '/register' || loc == '/password-reset')) {
        return '/';
      }
      return null;
    },
    routes: [
      GoRoute(
        path: '/boot',
        builder: (context, state) => const Scaffold(
          body: Center(child: CircularProgressIndicator()),
        ),
      ),
      GoRoute(
        parentNavigatorKey: rootNavigatorKey,
        path: '/login',
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        parentNavigatorKey: rootNavigatorKey,
        path: '/register',
        builder: (context, state) => const RegisterScreen(),
      ),
      GoRoute(
        parentNavigatorKey: rootNavigatorKey,
        path: '/password-reset',
        builder: (context, state) => const PasswordResetScreen(),
      ),
      GoRoute(
        parentNavigatorKey: rootNavigatorKey,
        path: '/create',
        builder: (context, state) => const ListingFormScreen(),
      ),
      GoRoute(
        parentNavigatorKey: rootNavigatorKey,
        path: '/my-listings',
        builder: (context, state) => const MyListingsScreen(),
      ),
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) {
          return ShellScreen(navigationShell: navigationShell);
        },
        branches: [
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/',
                builder: (context, state) => const HomeScreen(),
                routes: [
                  GoRoute(
                    path: 'listing/:id',
                    builder: (context, state) => ListingDetailScreen(
                      listingId: state.pathParameters['id']!,
                    ),
                    routes: [
                      GoRoute(
                        parentNavigatorKey: rootNavigatorKey,
                        path: 'edit',
                        builder: (context, state) => ListingFormScreen(
                          listingId: state.pathParameters['id'],
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/bookmarks',
                builder: (context, state) => const BookmarksScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/messages',
                builder: (context, state) => const MessagesScreen(),
                routes: [
                  GoRoute(
                    path: ':id',
                    builder: (context, state) => ConversationScreen(
                      conversationId: state.pathParameters['id']!,
                    ),
                  ),
                ],
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/profile',
                builder: (context, state) => const ProfileScreen(),
                routes: [
                  GoRoute(
                    parentNavigatorKey: rootNavigatorKey,
                    path: 'edit',
                    builder: (context, state) => const ProfileEditScreen(),
                  ),
                  GoRoute(
                    parentNavigatorKey: rootNavigatorKey,
                    path: 'notifications',
                    builder: (context, state) =>
                        const NotificationPrefsScreen(),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    ],
  );
}
