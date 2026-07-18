import 'dart:async';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api/api_client.dart';
import '../../core/api/api_config.dart';
import '../../core/api/models.dart';
import '../../core/api/repositories.dart';
import '../../core/theme/poisker_icons.dart';
import '../../core/theme/poisker_theme.dart';
import '../../core/unread/unread_controller.dart';
import '../../core/widgets/async_body.dart';

class ConversationScreen extends StatefulWidget {
  const ConversationScreen({super.key, required this.conversationId});

  final String conversationId;

  @override
  State<ConversationScreen> createState() => _ConversationScreenState();
}

class _ConversationScreenState extends State<ConversationScreen> {
  final _input = TextEditingController();
  final _scroll = ScrollController();
  Conversation? _conversation;
  final _messages = <ChatMessage>[];
  bool _loading = true;
  bool _sending = false;
  bool _busy = false;
  String? _error;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _load();
      _timer =
          Timer.periodic(const Duration(seconds: 8), (_) => _load(silent: true));
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _load({bool silent = false}) async {
    if (!silent) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }
    try {
      final thread = await context
          .read<MessagingRepository>()
          .thread(widget.conversationId);
      if (!mounted) return;
      final atEnd = _scroll.hasClients &&
          _scroll.position.pixels >= _scroll.position.maxScrollExtent - 80;
      setState(() {
        _conversation = thread.conversation;
        _messages
          ..clear()
          ..addAll(thread.messages);
        _loading = false;
      });
      context.read<UnreadController>().refresh();
      if (!silent || atEnd) _scrollToEnd();
    } catch (e) {
      if (!mounted || silent) return;
      setState(() {
        _error = ApiClient.mapError(e).displayMessage;
        _loading = false;
      });
    }
  }

  void _scrollToEnd() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scroll.hasClients) return;
      _scroll.jumpTo(_scroll.position.maxScrollExtent);
    });
  }

  Future<void> _send() async {
    final body = _input.text.trim();
    if (body.isEmpty || _sending) return;
    setState(() => _sending = true);
    try {
      final msg = await context
          .read<MessagingRepository>()
          .sendMessage(widget.conversationId, body);
      if (!mounted) return;
      setState(() {
        _messages.add(msg);
        _input.clear();
      });
      _scrollToEnd();
      _load(silent: true);
    } catch (e) {
      if (!mounted) return;
      showAppError(context, e);
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  Future<void> _confirmDeal() async {
    setState(() => _busy = true);
    try {
      await context
          .read<MessagingRepository>()
          .confirmDeal(widget.conversationId);
      if (!mounted) return;
      showAppSuccess(context, 'Сделка подтверждена');
      await _load(silent: true);
    } catch (e) {
      if (!mounted) return;
      showAppError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _deleteChat() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Удалить чат?'),
        content: const Text('Чат будет удалён из вашего списка.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Отмена'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Удалить'),
          ),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    setState(() => _busy = true);
    try {
      await context
          .read<MessagingRepository>()
          .deleteConversation(widget.conversationId);
      if (!mounted) return;
      context.pop();
    } catch (e) {
      if (!mounted) return;
      showAppError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _openReview() async {
    final id = _conversation?.otherUserId;
    if (id == null || id.isEmpty) return;
    await launchUrl(
      Uri.parse('${ApiConfig.siteUrl}sellers/$id/review/'),
      mode: LaunchMode.externalApplication,
    );
  }

  void _openImage(String url) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (context) => Scaffold(
          backgroundColor: Colors.black,
          appBar: AppBar(
            backgroundColor: Colors.black,
            foregroundColor: Colors.white,
          ),
          body: Center(
            child: InteractiveViewer(
              minScale: 1,
              maxScale: 4,
              child: CachedNetworkImage(
                imageUrl: url,
                fit: BoxFit.contain,
                errorWidget: (_, _, _) => const Icon(
                  PoiskerIcons.imageOff,
                  color: Colors.white54,
                  size: 48,
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final conversation = _conversation;
    final title =
        conversation?.otherUserName ?? conversation?.postTitle ?? 'Диалог';
    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontSize: 16)),
            if (conversation?.postTitle != null &&
                conversation!.postTitle != title)
              Text(
                conversation.postTitle!,
                style: const TextStyle(fontSize: 12, color: PoiskerColors.muted),
              ),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'Удалить чат',
            onPressed: _busy ? null : _deleteChat,
            icon: const Icon(PoiskerIcons.trash),
          ),
        ],
      ),
      body: AsyncBody(
        loading: _loading && _messages.isEmpty,
        error: _error,
        onRetry: _load,
        child: Column(
          children: [
            if (conversation != null) _ListingContextCard(conversation: conversation),
            if (conversation != null && _messages.isNotEmpty)
              _DealSection(
                conversation: conversation,
                busy: _busy,
                onConfirm: _confirmDeal,
                onReview: _openReview,
              ),
            Expanded(
              child: _messages.isEmpty
                  ? const Center(child: Text('Напишите первое сообщение'))
                  : Builder(
                      builder: (context) {
                        final fmt = DateFormat('HH:mm');
                        return ListView.builder(
                          controller: _scroll,
                          padding: const EdgeInsets.all(12),
                          itemCount: _messages.length,
                          itemBuilder: (context, index) {
                            final msg = _messages[index];
                            final align = msg.isMine
                                ? Alignment.centerRight
                                : Alignment.centerLeft;
                            final bg = msg.isMine
                                ? PoiskerColors.primary
                                : PoiskerColors.surface;
                            final fg = msg.isMine
                                ? Colors.white
                                : PoiskerColors.text;
                            return Align(
                              alignment: align,
                              child: Container(
                                margin: const EdgeInsets.only(bottom: 8),
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 12,
                                  vertical: 8,
                                ),
                                constraints: BoxConstraints(
                                  maxWidth:
                                      MediaQuery.sizeOf(context).width * 0.78,
                                ),
                                decoration: BoxDecoration(
                                  color: bg,
                                  borderRadius: BorderRadius.circular(12),
                                  border: msg.isMine
                                      ? null
                                      : Border.all(color: PoiskerColors.border),
                                ),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    if (msg.imageUrl != null &&
                                        msg.imageUrl!.isNotEmpty) ...[
                                      GestureDetector(
                                        onTap: () => _openImage(msg.imageUrl!),
                                        child: ClipRRect(
                                          borderRadius:
                                              BorderRadius.circular(8),
                                          child: CachedNetworkImage(
                                            imageUrl: msg.imageUrl!,
                                            width: 200,
                                            fit: BoxFit.cover,
                                            errorWidget: (_, _, _) =>
                                                const SizedBox(
                                              width: 120,
                                              height: 80,
                                              child: ColoredBox(
                                                color: PoiskerColors.slate200,
                                                child: Icon(
                                                  PoiskerIcons.imageOff,
                                                ),
                                              ),
                                            ),
                                          ),
                                        ),
                                      ),
                                      if (msg.body.trim().isNotEmpty)
                                        const SizedBox(height: 8),
                                    ],
                                    if (msg.body.trim().isNotEmpty)
                                      Text(
                                        msg.body,
                                        style:
                                            TextStyle(color: fg, height: 1.35),
                                      ),
                                    if (msg.createdAt != null) ...[
                                      const SizedBox(height: 4),
                                      Text(
                                        fmt.format(msg.createdAt!.toLocal()),
                                        style: TextStyle(
                                          color: msg.isMine
                                              ? Colors.white70
                                              : PoiskerColors.muted,
                                          fontSize: 11,
                                        ),
                                      ),
                                    ],
                                  ],
                                ),
                              ),
                            );
                          },
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _input,
                  minLines: 1,
                  maxLines: 4,
                  textInputAction: TextInputAction.send,
                  onSubmitted: (_) => _send(),
                  decoration: const InputDecoration(
                    hintText: 'Сообщение',
                    isDense: true,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              IconButton.filled(
                onPressed: _sending ? null : _send,
                icon: _sending
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(PoiskerIcons.send),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ListingContextCard extends StatelessWidget {
  const _ListingContextCard({required this.conversation});

  final Conversation conversation;

  @override
  Widget build(BuildContext context) {
    final title = conversation.postTitle ?? 'Объявление';
    final meta = [
      if (conversation.postCityLabel?.isNotEmpty == true)
        conversation.postCityLabel!,
      if (conversation.postPriceDisplay?.isNotEmpty == true)
        conversation.postPriceDisplay!,
    ].join(' · ');

    return Material(
      color: PoiskerColors.surface,
      child: InkWell(
        onTap: conversation.postId == null
            ? null
            : () => context.push('/listing/${conversation.postId}'),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.all(12),
          decoration: const BoxDecoration(
            border: Border(bottom: BorderSide(color: PoiskerColors.border)),
          ),
          child: Row(
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: SizedBox(
                  width: 56,
                  height: 56,
                  child: conversation.postCoverImage?.isNotEmpty == true
                      ? CachedNetworkImage(
                          imageUrl: conversation.postCoverImage!,
                          fit: BoxFit.cover,
                          errorWidget: (_, _, _) => const ColoredBox(
                            color: PoiskerColors.slate100,
                            child: Icon(PoiskerIcons.image, size: 20),
                          ),
                        )
                      : const ColoredBox(
                          color: PoiskerColors.slate100,
                          child: Icon(PoiskerIcons.image, size: 20),
                        ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Объявление',
                      style: TextStyle(
                        fontSize: 12,
                        color: PoiskerColors.muted,
                      ),
                    ),
                    Text(
                      title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    if (meta.isNotEmpty)
                      Text(
                        meta,
                        style: const TextStyle(
                          fontSize: 13,
                          color: PoiskerColors.muted,
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DealSection extends StatelessWidget {
  const _DealSection({
    required this.conversation,
    required this.busy,
    required this.onConfirm,
    required this.onReview,
  });

  final Conversation conversation;
  final bool busy;
  final VoidCallback onConfirm;
  final VoidCallback onReview;

  @override
  Widget build(BuildContext context) {
    final c = conversation;
    Widget? status;
    if (c.bothDealConfirmed) {
      status = const Text(
        'Сделка подтверждена обеими сторонами',
        style: TextStyle(fontSize: 13, color: Color(0xFF065F46)),
      );
    } else if (c.canReviewSeller && c.reviewViaTimeout) {
      status = const Text(
        'Отзыв доступен: продавец не подтвердил сделку в срок',
        style: TextStyle(fontSize: 13, color: Color(0xFF065F46)),
      );
    } else if (c.dealConfirmedByMe) {
      final unlock = c.reviewUnlockAt;
      final unlockText = unlock != null
          ? ' Если ответа не будет, отзыв откроется ${DateFormat('dd.MM HH:mm').format(unlock.toLocal())}.'
          : '';
      status = Text(
        'Вы подтвердили сделку. Ждём подтверждения второй стороны.$unlockText',
        style: const TextStyle(fontSize: 13, color: PoiskerColors.slate700),
      );
    } else if (c.dealConfirmedByOther) {
      status = const Text(
        'Собеседник уже подтвердил сделку.',
        style: TextStyle(fontSize: 13, color: PoiskerColors.slate700),
      );
    }

    final showConfirm = c.canConfirmDeal;
    final showReview = c.canReviewSeller;

    if (status == null && !showConfirm && !showReview) {
      return const SizedBox.shrink();
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
      decoration: const BoxDecoration(
        color: PoiskerColors.slate50,
        border: Border(bottom: BorderSide(color: PoiskerColors.border)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          ?status,
          if (showConfirm) ...[
            if (status != null) const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: busy ? null : onConfirm,
              icon: const Icon(PoiskerIcons.handshake, size: 18),
              label: const Text('Подтвердить успешную сделку'),
            ),
          ],
          if (showReview) ...[
            if (status != null || showConfirm) const SizedBox(height: 8),
            FilledButton.tonalIcon(
              onPressed: onReview,
              icon: const Icon(PoiskerIcons.star, size: 18),
              label: Text(
                c.hasExistingReview ? 'Изменить отзыв' : 'Оставить отзыв',
              ),
            ),
          ],
        ],
      ),
    );
  }
}
