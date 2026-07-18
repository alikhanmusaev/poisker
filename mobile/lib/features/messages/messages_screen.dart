import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../core/api/api_client.dart';
import '../../core/api/models.dart';
import '../../core/api/repositories.dart';
import '../../core/auth/auth_controller.dart';
import '../../core/theme/poisker_icons.dart';
import '../../core/theme/poisker_theme.dart';
import '../../core/unread/unread_controller.dart';
import '../../core/widgets/async_body.dart';

class MessagesScreen extends StatefulWidget {
  const MessagesScreen({super.key});

  @override
  State<MessagesScreen> createState() => _MessagesScreenState();
}

class _MessagesScreenState extends State<MessagesScreen> {
  List<Conversation> _items = const [];
  bool _loading = true;
  String? _error;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _load();
      _timer = Timer.periodic(const Duration(seconds: 20), (_) => _load(silent: true));
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _load({bool silent = false}) async {
    if (!context.read<AuthController>().isAuthenticated) {
      setState(() {
        _loading = false;
        _items = const [];
      });
      return;
    }
    if (!silent) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }
    try {
      final items = await context.read<MessagingRepository>().conversations();
      if (!mounted) return;
      setState(() {
        _items = items;
        _loading = false;
      });
      context.read<UnreadController>().refresh();
    } catch (e) {
      if (!mounted || silent) return;
      setState(() {
        _error = ApiClient.mapError(e).displayMessage;
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final authed = context.watch<AuthController>().isAuthenticated;
    return Scaffold(
      appBar: AppBar(title: const Text('Сообщения')),
      body: !authed
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(PoiskerIcons.messages, size: 48, color: PoiskerColors.slate300),
                    const SizedBox(height: 16),
                    const Text(
                      'Войдите, чтобы видеть переписку с продавцами',
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 16),
                    FilledButton(
                      onPressed: () => context.push('/login'),
                      child: const Text('Войти'),
                    ),
                    TextButton(
                      onPressed: () => context.push('/register'),
                      child: const Text('Создать аккаунт'),
                    ),
                  ],
                ),
              ),
            )
          : RefreshIndicator(
              onRefresh: _load,
              child: AsyncBody(
                loading: _loading,
                error: _error,
                onRetry: _load,
                empty: _items.isEmpty,
                emptyMessage: 'Пока нет диалогов',
                child: Builder(
                  builder: (context) {
                    final fmt = DateFormat('dd.MM HH:mm');
                    return ListView.separated(
                      itemCount: _items.length,
                      separatorBuilder: (_, _) => const Divider(height: 1),
                      itemBuilder: (context, index) {
                        final c = _items[index];
                        return ListTile(
                          onTap: () => context.push('/messages/${c.id}'),
                          title: Text(
                            c.otherUserName?.isNotEmpty == true
                                ? c.otherUserName!
                                : (c.postTitle ?? 'Диалог'),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          subtitle: Text(
                            [
                              if (c.postTitle != null && c.postTitle!.isNotEmpty)
                                c.postTitle!,
                              if (c.lastMessage != null &&
                                  c.lastMessage!.isNotEmpty)
                                c.lastMessage!,
                            ].join('\n'),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                          trailing: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: [
                              if (c.updatedAt != null)
                                Text(
                                  fmt.format(c.updatedAt!.toLocal()),
                                  style: const TextStyle(
                                    fontSize: 12,
                                    color: PoiskerColors.muted,
                                  ),
                                ),
                              if (c.unreadCount > 0) ...[
                                const SizedBox(height: 4),
                                CircleAvatar(
                                  radius: 10,
                                  backgroundColor: PoiskerColors.primary,
                                  child: Text(
                                    '${c.unreadCount}',
                                    style: const TextStyle(
                                      fontSize: 11,
                                      color: Colors.white,
                                    ),
                                  ),
                                ),
                              ],
                            ],
                          ),
                        );
                      },
                    );
                  },
                ),
              ),
            ),
    );
  }
}
