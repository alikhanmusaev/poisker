import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';

import '../../core/api/api_client.dart';
import '../../core/auth/auth_controller.dart';
import '../../core/theme/poisker_icons.dart';
import '../../core/theme/poisker_theme.dart';
import '../../core/widgets/async_body.dart';

class PasswordResetScreen extends StatefulWidget {
  const PasswordResetScreen({super.key});

  @override
  State<PasswordResetScreen> createState() => _PasswordResetScreenState();
}

class _PasswordResetScreenState extends State<PasswordResetScreen> {
  final _email = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  bool _loading = false;
  String? _banner;
  bool _done = false;

  @override
  void dispose() {
    _email.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    FocusScope.of(context).unfocus();
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _loading = true;
      _banner = null;
    });
    try {
      final msg = await context
          .read<AuthController>()
          .requestPasswordReset(_email.text);
      if (!mounted) return;
      setState(() {
        _done = true;
        _banner = null;
      });
      showAppSuccess(context, msg);
    } catch (e) {
      if (!mounted) return;
      setState(() => _banner = ApiClient.mapError(e).displayMessage);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: PoiskerColors.background,
      appBar: AppBar(title: const Text('Сброс пароля')),
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
                      'Восстановление доступа',
                      style: GoogleFonts.inter(
                        fontSize: 20,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      _done
                          ? 'Если аккаунт с таким email есть, мы отправили ссылку для сброса пароля.'
                          : 'Укажите email — если аккаунт есть, пришлём ссылку для сброса.',
                      style: GoogleFonts.inter(
                        fontSize: 14,
                        color: PoiskerColors.muted,
                        height: 1.4,
                      ),
                    ),
                    if (_banner != null) ...[
                      const SizedBox(height: 16),
                      ErrorBanner(
                        message: _banner!,
                        onDismiss: () => setState(() => _banner = null),
                      ),
                    ],
                    if (!_done) ...[
                      const SizedBox(height: 16),
                      TextFormField(
                        controller: _email,
                        keyboardType: TextInputType.emailAddress,
                        autofillHints: const [AutofillHints.email],
                        decoration: const InputDecoration(
                          labelText: 'Email',
                          prefixIcon: Icon(PoiskerIcons.mail, size: 20),
                        ),
                        validator: (v) => (v == null || !v.contains('@'))
                            ? 'Введите email'
                            : null,
                      ),
                      const SizedBox(height: 16),
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
                            : const Text('Отправить'),
                      ),
                    ] else ...[
                      const SizedBox(height: 16),
                      FilledButton(
                        onPressed: () => context.go('/login'),
                        child: const Text('Вернуться ко входу'),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
