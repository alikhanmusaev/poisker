import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api/api_client.dart';
import '../../core/api/api_config.dart';
import '../../core/api/models.dart';
import '../../core/api/repositories.dart';
import '../../core/auth/auth_controller.dart';
import '../../core/theme/poisker_icons.dart';
import '../../core/theme/poisker_theme.dart';
import '../../core/widgets/async_body.dart';
import '../../push/push_service.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthController>();
    if (!auth.isAuthenticated) {
      return Scaffold(
        appBar: AppBar(title: const Text('Профиль')),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(PoiskerIcons.profile, size: 48, color: PoiskerColors.slate300),
                const SizedBox(height: 16),
                const Text(
                  'Войдите, чтобы управлять объявлениями и чатами',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: () => context.push('/login'),
                  child: const Text('Войти'),
                ),
                TextButton(
                  onPressed: () => context.push('/register'),
                  child: const Text('Регистрация'),
                ),
              ],
            ),
          ),
        ),
      );
    }

    final user = auth.user!;
    return Scaffold(
      appBar: AppBar(title: const Text('Профиль')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: ListTile(
              leading: CircleAvatar(
                backgroundColor: PoiskerColors.primarySoft,
                child: Text(
                  user.displayName.isNotEmpty
                      ? user.displayName.substring(0, 1).toUpperCase()
                      : '?',
                  style: const TextStyle(color: PoiskerColors.primary),
                ),
              ),
              title: Text(user.displayName),
              subtitle: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${user.email}\n${user.phone}'),
                  if (user.ratingCount > 0) ...[
                    const SizedBox(height: 6),
                    Row(
                      children: [
                        const Icon(
                          PoiskerIcons.star,
                          size: 14,
                          color: Color(0xFFF59E0B),
                        ),
                        const SizedBox(width: 4),
                        Text(
                          '${user.ratingAvg.toStringAsFixed(1)} · ${user.ratingCount}',
                          style: const TextStyle(
                            fontSize: 13,
                            color: PoiskerColors.muted,
                          ),
                        ),
                      ],
                    ),
                  ],
                ],
              ),
              isThreeLine: true,
              trailing: IconButton(
                icon: const Icon(PoiskerIcons.edit),
                onPressed: () => context.push('/profile/edit'),
              ),
            ),
          ),
          const SizedBox(height: 12),
          ListTile(
            leading: const Icon(PoiskerIcons.profile),
            title: const Text('Публичный профиль'),
            onTap: () => _openUrl('${ApiConfig.siteUrl}sellers/${user.id}/'),
          ),
          ListTile(
            leading: const Icon(PoiskerIcons.listings),
            title: const Text('Мои объявления'),
            onTap: () => context.push('/my-listings'),
          ),
          ListTile(
            leading: const Icon(PoiskerIcons.bookmark),
            title: const Text('Избранное'),
            onTap: () => context.go('/bookmarks'),
          ),
          ListTile(
            leading: const Icon(PoiskerIcons.create),
            title: const Text('Подать объявление'),
            onTap: () => context.push('/create'),
          ),
          ListTile(
            leading: const Icon(PoiskerIcons.bell),
            title: const Text('Уведомления'),
            onTap: () => context.push('/profile/notifications'),
          ),
          const Divider(),
          ListTile(
            leading: const Icon(PoiskerIcons.settings),
            title: const Text('Смена пароля'),
            onTap: () =>
                _openUrl('${ApiConfig.siteUrl}accounts/password-change/'),
          ),
          ListTile(
            leading: const Icon(PoiskerIcons.trash),
            title: const Text('Удаление аккаунта'),
            onTap: () =>
                _openUrl('${ApiConfig.siteUrl}accounts/profile/delete/'),
          ),
          ListTile(
            leading: const Icon(PoiskerIcons.shield),
            title: const Text('Конфиденциальность'),
            onTap: () => _openUrl(ApiConfig.privacyUrl),
          ),
          ListTile(
            leading: const Icon(PoiskerIcons.fileText),
            title: const Text('Условия'),
            onTap: () => _openUrl(ApiConfig.termsUrl),
          ),
          ListTile(
            leading: const Icon(PoiskerIcons.alert),
            title: const Text('Правила сообщества'),
            onTap: () => _openUrl(ApiConfig.guidelinesUrl),
          ),
          const SizedBox(height: 12),
          FilledButton.tonal(
            onPressed: () async {
              await context.read<PushService>().requestPermissionAndRegister();
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Уведомления обновлены')),
                );
              }
            },
            child: const Text('Включить push-уведомления'),
          ),
          const SizedBox(height: 12),
          OutlinedButton(
            onPressed: () async {
              await context.read<PushService>().unregister();
              await auth.logout();
            },
            child: const Text('Выйти'),
          ),
        ],
      ),
    );
  }

  Future<void> _openUrl(String url) async {
    await launchUrl(
      Uri.parse(url),
      mode: LaunchMode.externalApplication,
    );
  }
}

class ProfileEditScreen extends StatefulWidget {
  const ProfileEditScreen({super.key});

  @override
  State<ProfileEditScreen> createState() => _ProfileEditScreenState();
}

class _ProfileEditScreenState extends State<ProfileEditScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _phone = TextEditingController();
  bool _saving = false;
  String? _banner;
  Map<String, List<String>> _fieldErrors = const {};

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final user = context.read<AuthController>().user;
      _name.text = user?.displayName ?? '';
      _phone.text = user?.phone ?? '';
    });
  }

  @override
  void dispose() {
    _name.dispose();
    _phone.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    FocusScope.of(context).unfocus();
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _saving = true;
      _banner = null;
      _fieldErrors = const {};
    });
    try {
      await context.read<AuthController>().updateProfile(
            displayName: _name.text,
            phone: _phone.text,
          );
      if (!mounted) return;
      showAppSuccess(context, 'Профиль сохранён');
      context.pop();
    } catch (e) {
      if (!mounted) return;
      final err = ApiClient.mapError(e);
      setState(() {
        _banner = err.displayMessage;
        _fieldErrors = err.fields;
      });
      showAppError(context, err);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Редактировать профиль')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            children: [
              if (_banner != null) ...[
                ErrorBanner(
                  message: _banner!,
                  onDismiss: () => setState(() => _banner = null),
                ),
                const SizedBox(height: 12),
              ],
              TextFormField(
                controller: _name,
                decoration: InputDecoration(
                  labelText: 'Имя',
                  errorText: _fieldErrors['display_name']?.firstOrNull ??
                      _fieldErrors['name']?.firstOrNull,
                ),
                validator: (v) =>
                    (v == null || v.trim().length < 2) ? 'Укажите имя' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _phone,
                keyboardType: TextInputType.phone,
                decoration: InputDecoration(
                  labelText: 'Телефон',
                  errorText: _fieldErrors['phone']?.firstOrNull,
                ),
                validator: (v) =>
                    (v == null || v.trim().length < 10) ? 'Укажите телефон' : null,
              ),
              const SizedBox(height: 20),
              FilledButton(
                onPressed: _saving ? null : _save,
                child: _saving
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Сохранить'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class NotificationPrefsScreen extends StatefulWidget {
  const NotificationPrefsScreen({super.key});

  @override
  State<NotificationPrefsScreen> createState() =>
      _NotificationPrefsScreenState();
}

class _NotificationPrefsScreenState extends State<NotificationPrefsScreen> {
  PushPreferences? _prefs;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final prefs = await context.read<CatalogRepository>().pushPreferences();
      if (!mounted) return;
      setState(() {
        _prefs = prefs;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = ApiClient.mapError(e).displayMessage;
        _loading = false;
      });
    }
  }

  Future<void> _update(PushPreferences next) async {
    setState(() => _prefs = next);
    try {
      final saved =
          await context.read<CatalogRepository>().updatePushPreferences(next);
      if (!mounted) return;
      setState(() => _prefs = saved);
    } catch (e) {
      if (!mounted) return;
      showAppError(context, e);
      _load();
    }
  }

  @override
  Widget build(BuildContext context) {
    final prefs = _prefs;
    return Scaffold(
      appBar: AppBar(title: const Text('Уведомления')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(_error!),
                      TextButton(onPressed: _load, child: const Text('Повторить')),
                    ],
                  ),
                )
              : ListView(
                  children: [
                    SwitchListTile(
                      title: const Text('Сообщения'),
                      value: prefs!.messagesEnabled,
                      onChanged: (v) =>
                          _update(prefs.copyWith(messagesEnabled: v)),
                    ),
                    SwitchListTile(
                      title: const Text('Объявления'),
                      value: prefs.listingsEnabled,
                      onChanged: (v) =>
                          _update(prefs.copyWith(listingsEnabled: v)),
                    ),
                    SwitchListTile(
                      title: const Text('Системные'),
                      value: prefs.systemEnabled,
                      onChanged: (v) =>
                          _update(prefs.copyWith(systemEnabled: v)),
                    ),
                    SwitchListTile(
                      title: const Text('Маркетинг'),
                      value: prefs.marketingEnabled,
                      onChanged: (v) =>
                          _update(prefs.copyWith(marketingEnabled: v)),
                    ),
                  ],
                ),
    );
  }
}
