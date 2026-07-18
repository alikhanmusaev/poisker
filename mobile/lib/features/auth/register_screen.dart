import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api/api_client.dart';
import '../../core/api/api_config.dart';
import '../../core/auth/auth_controller.dart';
import '../../core/theme/poisker_icons.dart';
import '../../core/theme/poisker_theme.dart';
import '../../core/widgets/async_body.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _phone = TextEditingController();
  final _password = TextEditingController();
  bool _accept = false;
  bool _loading = false;
  bool _obscure = true;
  String? _banner;

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    _phone.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    FocusScope.of(context).unfocus();
    if (!_formKey.currentState!.validate()) return;
    if (!_accept) {
      setState(() => _banner = 'Примите условия и согласие на обработку ПДн');
      return;
    }
    setState(() {
      _loading = true;
      _banner = null;
    });
    final auth = context.read<AuthController>();
    auth.clearError();
    try {
      final message = await auth.register(
        displayName: _name.text,
        email: _email.text,
        phone: _phone.text,
        password: _password.text,
      );
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Проверьте почту'),
          content: Text(message),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Понятно'),
            ),
          ],
        ),
      );
      if (mounted) {
        context.go('/login');
        showAppSuccess(context, 'Теперь войдите после подтверждения email');
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => _banner = ApiClient.mapError(e).displayMessage);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthController>();
    final err = auth.lastError;

    return Scaffold(
      backgroundColor: PoiskerColors.background,
      appBar: AppBar(
        title: const Text('Регистрация'),
        leading: IconButton(
          icon: const Icon(PoiskerIcons.close),
          onPressed: () => context.pop(),
        ),
      ),
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
                      'Создать аккаунт',
                      style: GoogleFonts.inter(
                        fontSize: 20,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'После регистрации подтвердите email — без этого вход недоступен.',
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
                      ),
                    ],
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _name,
                      textInputAction: TextInputAction.next,
                      decoration: InputDecoration(
                        labelText: 'Имя',
                        errorText: err?.fieldError('display_name'),
                      ),
                      validator: (v) => (v == null || v.trim().length < 2)
                          ? 'Укажите имя'
                          : null,
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _email,
                      keyboardType: TextInputType.emailAddress,
                      textInputAction: TextInputAction.next,
                      decoration: InputDecoration(
                        labelText: 'Email',
                        prefixIcon: const Icon(PoiskerIcons.mail, size: 20),
                        errorText: err?.fieldError('email'),
                      ),
                      validator: (v) {
                        if (v == null || !v.contains('@')) {
                          return 'Введите email';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _phone,
                      keyboardType: TextInputType.phone,
                      textInputAction: TextInputAction.next,
                      decoration: InputDecoration(
                        labelText: 'Телефон',
                        hintText: '+7 …',
                        prefixIcon: const Icon(PoiskerIcons.phone, size: 20),
                        errorText: err?.fieldError('phone'),
                      ),
                      validator: (v) => (v == null || v.trim().length < 10)
                          ? 'Укажите телефон'
                          : null,
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _password,
                      obscureText: _obscure,
                      decoration: InputDecoration(
                        labelText: 'Пароль',
                        errorText: err?.fieldError('password'),
                        suffixIcon: IconButton(
                          onPressed: () =>
                              setState(() => _obscure = !_obscure),
                          icon: Icon(
                            _obscure ? PoiskerIcons.eye : PoiskerIcons.eyeOff,
                            size: 20,
                          ),
                        ),
                      ),
                      validator: (v) =>
                          (v == null || v.length < 8) ? 'Минимум 8 символов' : null,
                    ),
                    const SizedBox(height: 8),
                    CheckboxListTile(
                      value: _accept,
                      onChanged: (v) => setState(() => _accept = v ?? false),
                      controlAffinity: ListTileControlAffinity.leading,
                      contentPadding: EdgeInsets.zero,
                      title: Wrap(
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          const Text('Принимаю '),
                          GestureDetector(
                            onTap: () =>
                                launchUrl(Uri.parse(ApiConfig.termsUrl)),
                            child: const Text(
                              'условия',
                              style: TextStyle(
                                color: PoiskerColors.primary,
                                decoration: TextDecoration.underline,
                              ),
                            ),
                          ),
                          const Text(' и '),
                          GestureDetector(
                            onTap: () =>
                                launchUrl(Uri.parse(ApiConfig.privacyUrl)),
                            child: const Text(
                              'обработку ПДн',
                              style: TextStyle(
                                color: PoiskerColors.primary,
                                decoration: TextDecoration.underline,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 8),
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
                          : const Text('Зарегистрироваться'),
                    ),
                    TextButton(
                      onPressed: () => context.go('/login'),
                      child: const Text('Уже есть аккаунт? Войти'),
                    ),
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
