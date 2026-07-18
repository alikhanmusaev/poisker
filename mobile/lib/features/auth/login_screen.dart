import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';

import '../../core/api/api_client.dart';
import '../../core/auth/auth_controller.dart';
import '../../core/theme/poisker_icons.dart';
import '../../core/theme/poisker_theme.dart';
import '../../core/widgets/async_body.dart';
import '../../core/widgets/brand_header.dart';
import '../../push/push_service.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  bool _loading = false;
  bool _obscure = true;
  bool _resending = false;
  String? _banner;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    FocusScope.of(context).unfocus();
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _loading = true;
      _banner = null;
    });
    final auth = context.read<AuthController>();
    auth.clearError();
    try {
      await auth.login(email: _email.text, password: _password.text);
      if (!mounted) return;
      await context.read<PushService>().requestPermissionAndRegister();
      if (!mounted) return;
      context.go('/');
    } catch (e) {
      if (!mounted) return;
      final err = ApiClient.mapError(e);
      setState(() => _banner = err.displayMessage);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _resend() async {
    if (_email.text.trim().isEmpty || !_email.text.contains('@')) {
      setState(() => _banner = 'Укажите email, чтобы отправить письмо снова');
      return;
    }
    setState(() => _resending = true);
    try {
      final msg =
          await context.read<AuthController>().resendVerification(_email.text);
      if (!mounted) return;
      showAppSuccess(context, msg);
    } catch (e) {
      if (!mounted) return;
      setState(() => _banner = ApiClient.mapError(e).displayMessage);
    } finally {
      if (mounted) setState(() => _resending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthController>();
    final fieldEmail = auth.lastError?.fieldError('email');
    final fieldPassword = auth.lastError?.fieldError('password');
    final needsVerify = auth.lastError?.isEmailVerification == true ||
        (_banner?.toLowerCase().contains('подтвердите email') ?? false);

    return Scaffold(
      backgroundColor: PoiskerColors.background,
      appBar: const PoiskerBrandHeader(showSubtitle: true),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      'Вход',
                      style: GoogleFonts.inter(
                        fontSize: 22,
                        fontWeight: FontWeight.w700,
                        letterSpacing: -0.4,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Войдите, чтобы писать продавцам и подавать объявления',
                      style: GoogleFonts.inter(
                        fontSize: 14,
                        color: PoiskerColors.muted,
                      ),
                    ),
                    if (_banner != null) ...[
                      const SizedBox(height: 16),
                      ErrorBanner(
                        message: _banner!,
                        onDismiss: () => setState(() => _banner = null),
                        actionLabel:
                            needsVerify ? 'Отправить письмо снова' : null,
                        onAction:
                            needsVerify && !_resending ? _resend : null,
                      ),
                    ],
                    const SizedBox(height: 20),
                    TextFormField(
                      controller: _email,
                      keyboardType: TextInputType.emailAddress,
                      textInputAction: TextInputAction.next,
                      autofillHints: const [AutofillHints.email],
                      onChanged: (_) {
                        if (_banner != null || auth.lastError != null) {
                          auth.clearError();
                          setState(() => _banner = null);
                        }
                      },
                      decoration: InputDecoration(
                        labelText: 'Email',
                        errorText: fieldEmail,
                        prefixIcon: const Icon(PoiskerIcons.mail, size: 20),
                      ),
                      validator: (v) {
                        if (v == null || v.trim().isEmpty) {
                          return 'Введите email';
                        }
                        if (!v.contains('@')) return 'Некорректный email';
                        return null;
                      },
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _password,
                      obscureText: _obscure,
                      textInputAction: TextInputAction.done,
                      onFieldSubmitted: (_) {
                        if (!_loading) _submit();
                      },
                      autofillHints: const [AutofillHints.password],
                      decoration: InputDecoration(
                        labelText: 'Пароль',
                        errorText: fieldPassword,
                        suffixIcon: IconButton(
                          onPressed: () =>
                              setState(() => _obscure = !_obscure),
                          icon: Icon(
                            _obscure ? PoiskerIcons.eye : PoiskerIcons.eyeOff,
                            size: 20,
                          ),
                          tooltip:
                              _obscure ? 'Показать пароль' : 'Скрыть пароль',
                        ),
                      ),
                      validator: (v) {
                        if (v == null || v.isEmpty) return 'Введите пароль';
                        if (v.length < 8) return 'Минимум 8 символов';
                        return null;
                      },
                    ),
                    Align(
                      alignment: Alignment.centerRight,
                      child: TextButton(
                        onPressed: () => context.push('/password-reset'),
                        child: const Text('Забыли пароль?'),
                      ),
                    ),
                    FilledButton(
                      onPressed: _loading ? null : _submit,
                      child: _loading
                          ? const SizedBox(
                              height: 20,
                              width: 20,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: Colors.white,
                              ),
                            )
                          : const Text('Войти'),
                    ),
                    const SizedBox(height: 10),
                    OutlinedButton(
                      onPressed:
                          _loading ? null : () => context.push('/register'),
                      child: const Text('Создать аккаунт'),
                    ),
                  ],
                ),
              ),
            ),
          ),
          TextButton(
            onPressed: () => context.go('/'),
            child: const Text('Смотреть ленту без входа'),
          ),
        ],
      ),
    );
  }
}
