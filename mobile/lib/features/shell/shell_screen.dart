import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/auth/auth_controller.dart';
import '../../core/theme/poisker_icons.dart';
import '../../core/theme/poisker_theme.dart';
import '../../core/unread/unread_controller.dart';

class ShellScreen extends StatelessWidget {
  const ShellScreen({super.key, required this.navigationShell});

  final StatefulNavigationShell navigationShell;

  @override
  Widget build(BuildContext context) {
    final unread = context.watch<UnreadController>().count;
    final authed = context.watch<AuthController>().isAuthenticated;
    final path = GoRouterState.of(context).uri.path;
    final index = navigationShell.currentIndex;

    return Scaffold(
      body: navigationShell,
      bottomNavigationBar: DecoratedBox(
        decoration: const BoxDecoration(
          color: PoiskerColors.surface,
          border: Border(top: BorderSide(color: PoiskerColors.border)),
        ),
        child: SafeArea(
          top: false,
          child: SizedBox(
            height: 72,
            child: authed
                ? Row(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      _NavItem(
                        icon: PoiskerIcons.home,
                        label: 'Главная',
                        selected: index == 0,
                        onTap: () => navigationShell.goBranch(
                          0,
                          initialLocation: index == 0,
                        ),
                      ),
                      _NavItem(
                        icon: PoiskerIcons.bookmark,
                        label: 'Закладки',
                        selected: index == 1,
                        onTap: () => navigationShell.goBranch(1),
                      ),
                      _FabItem(onTap: () => context.push('/create')),
                      _NavItem(
                        icon: PoiskerIcons.messages,
                        label: 'Сообщения',
                        badge: unread,
                        selected: index == 2,
                        onTap: () => navigationShell.goBranch(2),
                      ),
                      _NavItem(
                        icon: PoiskerIcons.profile,
                        label: 'Профиль',
                        selected: index == 3,
                        onTap: () => navigationShell.goBranch(3),
                      ),
                    ],
                  )
                : Row(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      _NavItem(
                        icon: PoiskerIcons.home,
                        label: 'Главная',
                        selected: index == 0,
                        onTap: () => navigationShell.goBranch(
                          0,
                          initialLocation: true,
                        ),
                      ),
                      _NavItem(
                        icon: PoiskerIcons.logIn,
                        label: 'Вход',
                        selected: path == '/login',
                        onTap: () => context.push('/login'),
                      ),
                      _NavItem(
                        icon: PoiskerIcons.userPlus,
                        label: 'Регистрация',
                        selected: path == '/register',
                        onTap: () => context.push('/register'),
                      ),
                    ],
                  ),
          ),
        ),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  const _NavItem({
    required this.icon,
    required this.label,
    required this.selected,
    required this.onTap,
    this.badge = 0,
  });

  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;
  final int badge;

  @override
  Widget build(BuildContext context) {
    final color =
        selected ? PoiskerColors.primary700 : PoiskerColors.slate500;
    return Expanded(
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.only(bottom: 8, top: 8),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.end,
            mainAxisSize: MainAxisSize.min,
            children: [
              Stack(
                clipBehavior: Clip.none,
                children: [
                  Container(
                    padding: const EdgeInsets.all(4),
                    decoration: selected
                        ? BoxDecoration(
                            color: PoiskerColors.primary50,
                            borderRadius:
                                BorderRadius.circular(PoiskerRadii.sm),
                          )
                        : null,
                    child: Icon(icon, size: 22, color: color),
                  ),
                  if (badge > 0)
                    Positioned(
                      right: -6,
                      top: -4,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 5,
                          vertical: 1,
                        ),
                        decoration: BoxDecoration(
                          color: PoiskerColors.primary700,
                          borderRadius: BorderRadius.circular(999),
                        ),
                        child: Text(
                          badge > 99 ? '99+' : '$badge',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 10,
                            fontWeight: FontWeight.w600,
                            height: 1.1,
                          ),
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 2),
              Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 11,
                  height: 1.1,
                  fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
                  color: color,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _FabItem extends StatelessWidget {
  const _FabItem({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.end,
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: PoiskerColors.primary700,
                  borderRadius: BorderRadius.circular(PoiskerRadii.md),
                  boxShadow: const [
                    BoxShadow(
                      color: Color(0x140F172A),
                      blurRadius: 8,
                      offset: Offset(0, 2),
                    ),
                  ],
                ),
                child: const Icon(
                  PoiskerIcons.plus,
                  color: Colors.white,
                  size: 24,
                ),
              ),
              const SizedBox(height: 2),
              const Text(
                'Подать',
                style: TextStyle(
                  fontSize: 11,
                  height: 1.1,
                  fontWeight: FontWeight.w600,
                  color: PoiskerColors.primary700,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
