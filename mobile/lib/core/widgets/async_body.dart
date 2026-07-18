import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';

import '../api/api_client.dart';
import '../api/api_config.dart';
import '../auth/auth_controller.dart';
import '../theme/poisker_icons.dart';
import '../theme/poisker_theme.dart';

void showAppError(BuildContext context, Object error) {
  final text = switch (error) {
    final String s => s,
    final ApiException e => e.displayMessage,
    _ => ApiClient.mapError(error).displayMessage,
  };
  final messenger = ScaffoldMessenger.of(context);
  messenger.clearSnackBars();
  messenger.showSnackBar(
    SnackBar(
      backgroundColor: PoiskerColors.slate800,
      behavior: SnackBarBehavior.floating,
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      content: Row(
        children: [
          const Icon(PoiskerIcons.alert, color: Colors.white, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              text,
              style: GoogleFonts.inter(color: Colors.white, height: 1.35),
            ),
          ),
        ],
      ),
    ),
  );
}

void showAppSuccess(BuildContext context, String message) {
  final messenger = ScaffoldMessenger.of(context);
  messenger.clearSnackBars();
  messenger.showSnackBar(
    SnackBar(
      backgroundColor: const Color(0xFF065F46),
      behavior: SnackBarBehavior.floating,
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      content: Text(
        message,
        style: GoogleFonts.inter(color: Colors.white, height: 1.35),
      ),
    ),
  );
}

/// @deprecated use [showAppError]
void showApiError(BuildContext context, Object error) =>
    showAppError(context, error);

class ErrorBanner extends StatelessWidget {
  const ErrorBanner({
    super.key,
    required this.message,
    this.onDismiss,
    this.actionLabel,
    this.onAction,
  });

  final String message;
  final VoidCallback? onDismiss;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: PoiskerColors.primary50,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(PoiskerRadii.sm),
        side: const BorderSide(color: Color(0xFFFECACA)),
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 10, 8, 10),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Padding(
              padding: EdgeInsets.only(top: 2),
              child: Icon(
                PoiskerIcons.alert,
                size: 18,
                color: PoiskerColors.primary700,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    message,
                    style: GoogleFonts.inter(
                      fontSize: 13,
                      height: 1.4,
                      color: PoiskerColors.primary800,
                    ),
                  ),
                  if (actionLabel != null && onAction != null) ...[
                    const SizedBox(height: 6),
                    TextButton(
                      onPressed: onAction,
                      style: TextButton.styleFrom(
                        padding: EdgeInsets.zero,
                        minimumSize: Size.zero,
                        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        foregroundColor: PoiskerColors.primary700,
                      ),
                      child: Text(actionLabel!),
                    ),
                  ],
                ],
              ),
            ),
            if (onDismiss != null)
              IconButton(
                onPressed: onDismiss,
                icon: const Icon(PoiskerIcons.close, size: 18),
                color: PoiskerColors.primary700,
                visualDensity: VisualDensity.compact,
              ),
          ],
        ),
      ),
    );
  }
}

class AsyncBody extends StatelessWidget {
  const AsyncBody({
    super.key,
    required this.loading,
    required this.error,
    required this.onRetry,
    required this.child,
    this.empty = false,
    this.emptyMessage = 'Пусто',
    this.emptyIcon = PoiskerIcons.search,
  });

  final bool loading;
  final String? error;
  final VoidCallback onRetry;
  final Widget child;
  final bool empty;
  final String emptyMessage;
  final IconData emptyIcon;

  @override
  Widget build(BuildContext context) {
    if (loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (error != null) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(24),
        children: [
          const SizedBox(height: 64),
          Icon(
            error!.contains('сети') || error!.contains('подключен')
                ? PoiskerIcons.wifiOff
                : PoiskerIcons.alert,
            size: 48,
            color: PoiskerColors.muted,
          ),
          const SizedBox(height: 16),
          Text(
            error!,
            textAlign: TextAlign.center,
            style: GoogleFonts.inter(
              fontSize: 15,
              height: 1.4,
              color: PoiskerColors.slate700,
            ),
          ),
          const SizedBox(height: 16),
          Center(
            child: FilledButton(
              onPressed: onRetry,
              child: const Text('Повторить'),
            ),
          ),
        ],
      );
    }
    if (empty) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(24),
        children: [
          const SizedBox(height: 64),
          Icon(emptyIcon, size: 48, color: PoiskerColors.slate300),
          const SizedBox(height: 16),
          Text(
            emptyMessage,
            textAlign: TextAlign.center,
            style: GoogleFonts.inter(
              fontSize: 15,
              color: PoiskerColors.muted,
            ),
          ),
        ],
      );
    }
    return child;
  }
}

/// Returns `true` if already authenticated. Otherwise shows a dialog and
/// navigates to login when the user confirms.
Future<bool> requireAuth(
  BuildContext context, {
  String message = 'Войдите в аккаунт, чтобы продолжить.',
}) async {
  if (context.read<AuthController>().isAuthenticated) return true;
  final go = await showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      title: const Text('Нужен вход'),
      content: Text(message),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, false),
          child: const Text('Отмена'),
        ),
        FilledButton(
          onPressed: () => Navigator.pop(context, true),
          child: const Text('Войти'),
        ),
      ],
    ),
  );
  if (go == true && context.mounted) {
    context.push('/login');
  }
  return false;
}
