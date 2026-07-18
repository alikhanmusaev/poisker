import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

/// Design tokens from poisker.ru `static/css/style.css`.
abstract final class PoiskerColors {
  static const primary50 = Color(0xFFFEF2F2);
  static const primary100 = Color(0xFFFEE2E2);
  static const primary500 = Color(0xFFEF4444);
  static const primary600 = Color(0xFFDC2626);
  static const primary700 = Color(0xFFB91C1C);
  static const primary800 = Color(0xFF991B1B);

  static const slate50 = Color(0xFFF8FAFC);
  static const slate100 = Color(0xFFF1F5F9);
  static const slate200 = Color(0xFFE2E8F0);
  static const slate300 = Color(0xFFCBD5E1);
  static const slate400 = Color(0xFF94A3B8);
  static const slate500 = Color(0xFF64748B);
  static const slate600 = Color(0xFF475569);
  static const slate700 = Color(0xFF334155);
  static const slate800 = Color(0xFF1E293B);
  static const slate900 = Color(0xFF0F172A);

  static const primary = primary700;
  static const primaryHover = primary600;
  static const primarySoft = primary50;
  static const background = slate50;
  static const surface = Color(0xFFFFFFFF);
  static const text = slate900;
  static const muted = slate500;
  static const border = slate200;
  static const danger = primary500;
}

abstract final class PoiskerRadii {
  static const sm = 8.0;
  static const md = 12.0;
  static const lg = 16.0;
  static const full = 999.0;
}

abstract final class PoiskerTheme {
  static ThemeData get light {
    final textTheme = GoogleFonts.interTextTheme().apply(
      bodyColor: PoiskerColors.text,
      displayColor: PoiskerColors.text,
    );
    final scheme = ColorScheme.fromSeed(
      seedColor: PoiskerColors.primary700,
      primary: PoiskerColors.primary700,
      onPrimary: Colors.white,
      surface: PoiskerColors.surface,
      error: PoiskerColors.danger,
      brightness: Brightness.light,
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      textTheme: textTheme,
      scaffoldBackgroundColor: PoiskerColors.background,
      dividerColor: PoiskerColors.border,
      appBarTheme: AppBarTheme(
        backgroundColor: PoiskerColors.surface,
        foregroundColor: PoiskerColors.slate900,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        systemOverlayStyle: SystemUiOverlayStyle.dark.copyWith(
          statusBarColor: Colors.transparent,
        ),
        titleTextStyle: GoogleFonts.inter(
          fontSize: 16,
          fontWeight: FontWeight.w700,
          color: PoiskerColors.slate900,
          letterSpacing: -0.02 * 16,
        ),
        iconTheme: const IconThemeData(color: PoiskerColors.slate700),
      ),
      cardTheme: CardThemeData(
        color: PoiskerColors.surface,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(PoiskerRadii.lg),
          side: const BorderSide(color: PoiskerColors.border),
        ),
        shadowColor: const Color(0x0D0F172A),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: PoiskerColors.surface,
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        hintStyle: const TextStyle(color: PoiskerColors.slate400),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(PoiskerRadii.sm),
          borderSide: const BorderSide(color: PoiskerColors.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(PoiskerRadii.sm),
          borderSide: const BorderSide(color: PoiskerColors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(PoiskerRadii.sm),
          borderSide: const BorderSide(color: PoiskerColors.primary600, width: 1.5),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: PoiskerColors.primary700,
          foregroundColor: Colors.white,
          minimumSize: const Size.fromHeight(48),
          elevation: 1,
          shadowColor: const Color(0x140F172A),
          textStyle: GoogleFonts.inter(
            fontSize: 15,
            fontWeight: FontWeight.w600,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(PoiskerRadii.sm),
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: PoiskerColors.slate800,
          minimumSize: const Size.fromHeight(48),
          side: const BorderSide(color: PoiskerColors.border),
          backgroundColor: PoiskerColors.slate100,
          textStyle: GoogleFonts.inter(
            fontSize: 15,
            fontWeight: FontWeight.w600,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(PoiskerRadii.sm),
          ),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: PoiskerColors.surface,
        elevation: 0,
        height: 72,
        indicatorColor: PoiskerColors.primary50,
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          final active = states.contains(WidgetState.selected);
          return GoogleFonts.inter(
            fontSize: 11,
            fontWeight: active ? FontWeight.w600 : FontWeight.w500,
            color: active ? PoiskerColors.primary700 : PoiskerColors.slate500,
          );
        }),
        iconTheme: WidgetStateProperty.resolveWith((states) {
          final active = states.contains(WidgetState.selected);
          return IconThemeData(
            size: 22,
            color: active ? PoiskerColors.primary700 : PoiskerColors.slate500,
          );
        }),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: PoiskerColors.surface,
        selectedColor: PoiskerColors.primary50,
        side: const BorderSide(color: PoiskerColors.border),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(PoiskerRadii.full),
        ),
        labelStyle: GoogleFonts.inter(
          fontSize: 12,
          fontWeight: FontWeight.w500,
          color: PoiskerColors.slate600,
        ),
      ),
    );
  }
}
