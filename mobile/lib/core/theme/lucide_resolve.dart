import 'package:flutter/widgets.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import 'poisker_icons.dart';

/// Maps Lucide kebab-case names from the API (`layout-grid`) to [IconData].
IconData lucideIcon(String? name, {IconData fallback = PoiskerIcons.home}) {
  if (name == null || name.isEmpty) return fallback;
  final key = name.trim().toLowerCase();
  return _icons[key] ?? fallback;
}

/// Explicit map for category icons used by poisker.ru + common fallbacks.
const Map<String, IconData> _icons = {
  'layout-grid': LucideIcons.layoutGrid,
  'home': LucideIcons.home,
  'car': LucideIcons.car,
  'cog': LucideIcons.cog,
  'smartphone': LucideIcons.smartphone,
  'shirt': LucideIcons.shirt,
  'shopping-bag': LucideIcons.shoppingBag,
  'sofa': LucideIcons.sofa,
  'wrench': LucideIcons.wrench,
  'briefcase': LucideIcons.briefcase,
  'baby': LucideIcons.baby,
  'paw-print': LucideIcons.pawPrint,
  'dumbbell': LucideIcons.dumbbell,
  'hammer': LucideIcons.hammer,
  'flower-2': LucideIcons.flower2,
  'apple': LucideIcons.apple,
  'store': LucideIcons.store,
  'bookmark': LucideIcons.bookmark,
  'messages-square': LucideIcons.messagesSquare,
  'user': LucideIcons.user,
  'plus': LucideIcons.plus,
  'search': LucideIcons.search,
  'map-pin': LucideIcons.mapPin,
  'bell': LucideIcons.bell,
  'log-in': LucideIcons.logIn,
  'log-out': LucideIcons.logOut,
  'user-plus': LucideIcons.userPlus,
};
