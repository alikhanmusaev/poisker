import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api/api_client.dart';
import '../../core/api/api_config.dart';
import '../../core/api/models.dart';
import '../../core/api/repositories.dart';
import '../../core/theme/poisker_icons.dart';
import '../../core/theme/poisker_theme.dart';
import '../../core/widgets/async_body.dart';

class ListingDetailScreen extends StatefulWidget {
  const ListingDetailScreen({super.key, required this.listingId});

  final String listingId;

  @override
  State<ListingDetailScreen> createState() => _ListingDetailScreenState();
}

class _ListingDetailScreenState extends State<ListingDetailScreen> {
  Listing? _listing;
  bool _loading = true;
  String? _error;
  String? _phone;
  bool _busy = false;

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
      final listing = await context
          .read<CatalogRepository>()
          .listingDetail(widget.listingId);
      if (!mounted) return;
      setState(() {
        _listing = listing;
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

  Future<void> _showPhone() async {
    if (!await requireAuth(
      context,
      message: 'Войдите, чтобы увидеть телефон продавца.',
    )) {
      return;
    }
    if (!mounted) return;
    setState(() => _busy = true);
    try {
      final phone = await context
          .read<CatalogRepository>()
          .contactPhone(widget.listingId);
      if (!mounted) return;
      setState(() => _phone = phone);
      if (phone.isNotEmpty) {
        await launchUrl(Uri(scheme: 'tel', path: phone));
      }
    } catch (e) {
      if (!mounted) return;
      showAppError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _startChat() async {
    if (!await requireAuth(
      context,
      message: 'Войдите, чтобы написать продавцу.',
    )) {
      return;
    }
    if (!mounted) return;
    setState(() => _busy = true);
    try {
      final id = await context
          .read<MessagingRepository>()
          .startConversation(widget.listingId);
      if (!mounted) return;
      if (id.isEmpty) throw Exception('Не удалось создать чат');
      context.go('/messages/$id');
    } catch (e) {
      if (!mounted) return;
      showAppError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _toggleBookmark() async {
    if (!await requireAuth(
      context,
      message: 'Войдите, чтобы сохранять объявления в закладки.',
    )) {
      return;
    }
    if (!mounted) return;
    final listing = _listing;
    if (listing == null) return;
    setState(() => _busy = true);
    try {
      final bookmarked = await context.read<CatalogRepository>().toggleBookmark(
            listing.id,
            currentlyBookmarked: listing.isBookmarked,
          );
      if (!mounted) return;
      setState(() => _listing = listing.copyWith(isBookmarked: bookmarked));
    } catch (e) {
      if (!mounted) return;
      showAppError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _share() async {
    final listing = _listing;
    if (listing == null) return;
    final url = listing.publicUrl?.isNotEmpty == true
        ? listing.publicUrl!
        : '${ApiConfig.siteUrl}listings/${listing.id}/';
    await SharePlus.instance.share(
      ShareParams(text: '${listing.title}\n$url'),
    );
  }

  Future<void> _report() async {
    if (!await requireAuth(
      context,
      message: 'Войдите, чтобы пожаловаться на объявление.',
    )) {
      return;
    }
    if (!mounted) return;
    final listing = _listing;
    if (listing == null || listing.isOwner) return;

    final result = await showModalBottomSheet<({String reason, String comment})>(
      context: context,
      isScrollControlled: true,
      builder: (context) => const _ReportSheet(),
    );
    if (result == null || !mounted) return;

    setState(() => _busy = true);
    try {
      await context.read<CatalogRepository>().reportListing(
            listing.id,
            reason: result.reason,
            comment: result.comment,
          );
      if (!mounted) return;
      showAppSuccess(context, 'Жалоба отправлена');
    } catch (e) {
      if (!mounted) return;
      showAppError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _ownerAction(Future<Listing> Function() action) async {
    setState(() => _busy = true);
    try {
      final listing = await action();
      if (!mounted) return;
      setState(() => _listing = listing);
      showAppSuccess(context, 'Готово');
    } catch (e) {
      if (!mounted) return;
      showAppError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final listing = _listing;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Объявление'),
        actions: [
          if (listing != null) ...[
            IconButton(
              tooltip: 'Поделиться',
              onPressed: _share,
              icon: const Icon(PoiskerIcons.share),
            ),
            if (!listing.isOwner)
              IconButton(
                tooltip: 'Пожаловаться',
                onPressed: _busy ? null : _report,
                icon: const Icon(PoiskerIcons.flag),
              ),
            if (listing.isOwner)
              IconButton(
                tooltip: 'Редактировать',
                onPressed: () => context.push('/listing/${listing.id}/edit'),
                icon: const Icon(PoiskerIcons.edit),
              ),
            IconButton(
              onPressed: _busy ? null : _toggleBookmark,
              icon: Icon(
                PoiskerIcons.bookmark,
                color: listing.isBookmarked ? PoiskerColors.primary700 : null,
              ),
            ),
          ],
        ],
      ),
      body: AsyncBody(
        loading: _loading,
        error: _error,
        onRetry: _load,
        child: listing == null
            ? const SizedBox.shrink()
            : _DetailBody(listing: listing),
      ),
      bottomNavigationBar: listing == null
          ? null
          : SafeArea(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
                child: listing.isOwner
                    ? _OwnerActions(
                        listing: listing,
                        busy: _busy,
                        onSubmit: () => _ownerAction(
                          () => context
                              .read<CatalogRepository>()
                              .submitListing(listing.id),
                        ),
                        onRepublish: () => _ownerAction(
                          () => context
                              .read<CatalogRepository>()
                              .republishListing(listing.id),
                        ),
                        onDelete: () async {
                          final repo = context.read<CatalogRepository>();
                          final router = GoRouter.of(context);
                          final ok = await showDialog<bool>(
                            context: context,
                            builder: (context) => AlertDialog(
                              title: const Text('Снять объявление?'),
                              actions: [
                                TextButton(
                                  onPressed: () =>
                                      Navigator.pop(context, false),
                                  child: const Text('Отмена'),
                                ),
                                FilledButton(
                                  onPressed: () =>
                                      Navigator.pop(context, true),
                                  child: const Text('Снять'),
                                ),
                              ],
                            ),
                          );
                          if (ok != true || !mounted) return;
                          setState(() => _busy = true);
                          try {
                            final result = await repo.deleteListing(listing.id);
                            if (!mounted) return;
                            if (result == null) {
                              router.pop();
                            } else {
                              setState(() => _listing = result);
                            }
                          } catch (e) {
                            if (!mounted) return;
                            showAppError(this.context, e);
                          } finally {
                            if (mounted) setState(() => _busy = false);
                          }
                        },
                      )
                    : Row(
                        children: [
                          Expanded(
                            child: OutlinedButton(
                              onPressed: _busy ? null : _showPhone,
                              child: Text(_phone ?? 'Показать телефон'),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: FilledButton(
                              onPressed: _busy ? null : _startChat,
                              child: const Text('Написать'),
                            ),
                          ),
                        ],
                      ),
              ),
            ),
    );
  }
}

class _DetailBody extends StatefulWidget {
  const _DetailBody({required this.listing});

  final Listing listing;

  @override
  State<_DetailBody> createState() => _DetailBodyState();
}

class _DetailBodyState extends State<_DetailBody> {
  int _page = 0;

  Listing get listing => widget.listing;

  List<String> get _images {
    if (listing.images.isNotEmpty) return listing.images;
    if (listing.coverImage != null && listing.coverImage!.isNotEmpty) {
      return [listing.coverImage!];
    }
    return const [];
  }

  void _openFullscreen(List<String> images, int index) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (context) => _FullscreenGallery(
          images: images,
          initialIndex: index,
        ),
      ),
    );
  }

  Future<void> _openSeller() async {
    final id = listing.sellerId;
    if (id == null || id.isEmpty) return;
    await launchUrl(
      Uri.parse('${ApiConfig.siteUrl}sellers/$id/'),
      mode: LaunchMode.externalApplication,
    );
  }

  @override
  Widget build(BuildContext context) {
    final images = _images;
    final condition = listing.conditionLabel?.isNotEmpty == true
        ? listing.conditionLabel!
        : (listing.condition == 'new' ? 'Новый' : 'Б/У');

    return ListView(
      children: [
        if (images.isNotEmpty)
          Column(
            children: [
              SizedBox(
                height: 280,
                child: PageView.builder(
                  itemCount: images.length,
                  onPageChanged: (i) => setState(() => _page = i),
                  itemBuilder: (context, index) {
                    return GestureDetector(
                      onTap: () => _openFullscreen(images, index),
                      child: CachedNetworkImage(
                        imageUrl: images[index],
                        fit: BoxFit.cover,
                        width: double.infinity,
                        errorWidget: (_, _, _) => const ColoredBox(
                          color: PoiskerColors.primarySoft,
                          child: Icon(PoiskerIcons.imageOff),
                        ),
                      ),
                    );
                  },
                ),
              ),
              if (images.length > 1)
                Padding(
                  padding: const EdgeInsets.only(top: 10),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: List.generate(images.length, (i) {
                      final active = i == _page;
                      return AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        margin: const EdgeInsets.symmetric(horizontal: 3),
                        width: active ? 8 : 6,
                        height: active ? 8 : 6,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: active
                              ? PoiskerColors.primary700
                              : PoiskerColors.slate300,
                        ),
                      );
                    }),
                  ),
                ),
            ],
          )
        else
          const SizedBox(
            height: 180,
            child: ColoredBox(
              color: PoiskerColors.primarySoft,
              child: Center(child: Icon(PoiskerIcons.image, size: 48)),
            ),
          ),
        Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Material(
                color: PoiskerColors.primary50,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(PoiskerRadii.sm),
                  side: const BorderSide(color: Color(0xFFFECACA)),
                ),
                child: const Padding(
                  padding: EdgeInsets.all(12),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(
                        PoiskerIcons.shield,
                        size: 18,
                        color: PoiskerColors.primary700,
                      ),
                      SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          'Не переводите предоплату, пока не осмотрите товар и не убедитесь в надёжности продавца.',
                          style: TextStyle(height: 1.4, fontSize: 13),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Text(
                listing.priceDisplay.isNotEmpty
                    ? listing.priceDisplay
                    : 'Цена не указана',
                style: const TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                  color: PoiskerColors.primary,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                listing.title,
                style:
                    const TextStyle(fontSize: 20, fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 8),
              Text(
                [
                  if (listing.cityLabel.isNotEmpty) listing.cityLabel,
                  if (listing.categoryLabel.isNotEmpty) listing.categoryLabel,
                  condition,
                  '${listing.views} просм.',
                  if (listing.statusLabel != null) listing.statusLabel!,
                ].join(' · '),
                style: const TextStyle(color: PoiskerColors.muted),
              ),
              if (listing.sellerName != null) ...[
                const SizedBox(height: 14),
                InkWell(
                  onTap: listing.sellerId != null ? _openSeller : null,
                  borderRadius: BorderRadius.circular(PoiskerRadii.sm),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: Row(
                      children: [
                        CircleAvatar(
                          radius: 18,
                          backgroundColor: PoiskerColors.primarySoft,
                          child: Text(
                            listing.sellerName!.isNotEmpty
                                ? listing.sellerName!
                                    .substring(0, 1)
                                    .toUpperCase()
                                : '?',
                            style: const TextStyle(
                              color: PoiskerColors.primary,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                listing.sellerName!,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              if (listing.sellerRatingCount > 0)
                                Row(
                                  children: [
                                    const Icon(
                                      PoiskerIcons.star,
                                      size: 14,
                                      color: Color(0xFFF59E0B),
                                    ),
                                    const SizedBox(width: 4),
                                    Text(
                                      '${listing.sellerRatingAvg.toStringAsFixed(1)} · ${listing.sellerRatingCount}',
                                      style: const TextStyle(
                                        fontSize: 13,
                                        color: PoiskerColors.muted,
                                      ),
                                    ),
                                  ],
                                ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
              if (listing.moderationNote?.isNotEmpty == true) ...[
                const SizedBox(height: 12),
                Card(
                  color: PoiskerColors.primarySoft,
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Text('Модерация: ${listing.moderationNote}'),
                  ),
                ),
              ],
              const SizedBox(height: 16),
              Text(
                listing.body?.trim().isNotEmpty == true
                    ? listing.body!
                    : 'Без описания',
                style: const TextStyle(height: 1.45),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _FullscreenGallery extends StatefulWidget {
  const _FullscreenGallery({
    required this.images,
    required this.initialIndex,
  });

  final List<String> images;
  final int initialIndex;

  @override
  State<_FullscreenGallery> createState() => _FullscreenGalleryState();
}

class _FullscreenGalleryState extends State<_FullscreenGallery> {
  late final PageController _controller;
  late int _index;

  @override
  void initState() {
    super.initState();
    _index = widget.initialIndex;
    _controller = PageController(initialPage: widget.initialIndex);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: Text('${_index + 1} / ${widget.images.length}'),
      ),
      body: PageView.builder(
        controller: _controller,
        itemCount: widget.images.length,
        onPageChanged: (i) => setState(() => _index = i),
        itemBuilder: (context, index) {
          return InteractiveViewer(
            minScale: 1,
            maxScale: 4,
            child: Center(
              child: CachedNetworkImage(
                imageUrl: widget.images[index],
                fit: BoxFit.contain,
                errorWidget: (_, _, _) => const Icon(
                  PoiskerIcons.imageOff,
                  color: Colors.white54,
                  size: 48,
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

class _ReportSheet extends StatefulWidget {
  const _ReportSheet();

  @override
  State<_ReportSheet> createState() => _ReportSheetState();
}

class _ReportSheetState extends State<_ReportSheet> {
  String? _reason;
  final _comment = TextEditingController();

  @override
  void dispose() {
    _comment.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final bottom = MediaQuery.viewInsetsOf(context).bottom;
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 12, 16, 16 + bottom),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'Пожаловаться',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 8),
            ...reportReasons.entries.map(
              (e) => ListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                title: Text(e.value),
                leading: Icon(
                  _reason == e.key
                      ? Icons.radio_button_checked
                      : Icons.radio_button_off,
                  color: _reason == e.key
                      ? PoiskerColors.primary700
                      : PoiskerColors.slate400,
                ),
                onTap: () => setState(() => _reason = e.key),
              ),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _comment,
              maxLines: 3,
              maxLength: 500,
              decoration: const InputDecoration(
                labelText: 'Комментарий (необязательно)',
              ),
            ),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: _reason == null
                  ? null
                  : () => Navigator.pop(
                        context,
                        (reason: _reason!, comment: _comment.text.trim()),
                      ),
              child: const Text('Отправить'),
            ),
          ],
        ),
      ),
    );
  }
}

class _OwnerActions extends StatelessWidget {
  const _OwnerActions({
    required this.listing,
    required this.busy,
    required this.onSubmit,
    required this.onRepublish,
    required this.onDelete,
  });

  final Listing listing;
  final bool busy;
  final VoidCallback onSubmit;
  final VoidCallback onRepublish;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        if (listing.canSubmit)
          Expanded(
            child: FilledButton(
              onPressed: busy ? null : onSubmit,
              child: const Text('На модерацию'),
            ),
          ),
        if (listing.canRepublish)
          Expanded(
            child: FilledButton(
              onPressed: busy ? null : onRepublish,
              child: const Text('Опубликовать снова'),
            ),
          ),
        if (!listing.canSubmit && !listing.canRepublish)
          Expanded(
            child: OutlinedButton(
              onPressed: busy ? null : onDelete,
              child: const Text('Снять с публикации'),
            ),
          )
        else ...[
          const SizedBox(width: 8),
          IconButton.outlined(
            onPressed: busy ? null : onDelete,
            icon: const Icon(PoiskerIcons.trash),
          ),
        ],
      ],
    );
  }
}
