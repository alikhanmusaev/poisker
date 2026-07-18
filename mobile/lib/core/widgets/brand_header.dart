import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../theme/poisker_icons.dart';
import '../theme/poisker_theme.dart';

class PoiskerBrandHeader extends StatelessWidget
    implements PreferredSizeWidget {
  const PoiskerBrandHeader({
    super.key,
    this.actions = const [],
    this.showSubtitle = true,
    this.bottom,
  });

  final List<Widget> actions;
  final bool showSubtitle;
  final PreferredSizeWidget? bottom;

  @override
  Size get preferredSize => Size.fromHeight(
        kToolbarHeight + (bottom?.preferredSize.height ?? 0),
      );

  @override
  Widget build(BuildContext context) {
    return AppBar(
      titleSpacing: 16,
      title: Row(
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(PoiskerRadii.md),
            child: Image.asset(
              'assets/logo.png',
              width: 40,
              height: 40,
              fit: BoxFit.contain,
              errorBuilder: (_, _, _) => Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: PoiskerColors.primary700,
                  borderRadius: BorderRadius.circular(PoiskerRadii.md),
                ),
                child: const Icon(PoiskerIcons.bolt, color: Colors.white),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Поискер',
                  style: GoogleFonts.inter(
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.3,
                    color: PoiskerColors.slate900,
                    height: 1.2,
                  ),
                ),
                if (showSubtitle)
                  Text(
                    'Доска объявлений по ЧР',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: GoogleFonts.inter(
                      fontSize: 12,
                      color: PoiskerColors.muted,
                      height: 1.2,
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
      actions: actions,
      bottom: bottom,
      shape: const Border(
        bottom: BorderSide(color: PoiskerColors.border),
      ),
    );
  }
}
