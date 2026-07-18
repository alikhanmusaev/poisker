import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api/api_client.dart';
import '../../core/api/models.dart';
import '../../core/api/repositories.dart';
import '../../core/widgets/async_body.dart';
import '../../core/widgets/listing_card.dart';

class BookmarksScreen extends StatefulWidget {
  const BookmarksScreen({super.key});

  @override
  State<BookmarksScreen> createState() => _BookmarksScreenState();
}

class _BookmarksScreenState extends State<BookmarksScreen> {
  final _items = <Listing>[];
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
      final page = await context.read<CatalogRepository>().bookmarks();
      if (!mounted) return;
      setState(() {
        _items
          ..clear()
          ..addAll(page.results);
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

  Future<void> _toggleBookmark(Listing item) async {
    try {
      final bookmarked = await context.read<CatalogRepository>().toggleBookmark(
            item.id,
            currentlyBookmarked: item.isBookmarked,
          );
      if (!mounted) return;
      setState(() {
        if (bookmarked) {
          final i = _items.indexWhere((e) => e.id == item.id);
          if (i >= 0) _items[i] = _items[i].copyWith(isBookmarked: true);
        } else {
          _items.removeWhere((e) => e.id == item.id);
        }
      });
    } catch (e) {
      if (!mounted) return;
      showAppError(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Избранное')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: AsyncBody(
          loading: _loading,
          error: _error,
          onRetry: _load,
          empty: _items.isEmpty,
          emptyMessage: 'Нет сохранённых объявлений',
          child: ListView.separated(
            padding: const EdgeInsets.all(12),
            itemCount: _items.length,
            separatorBuilder: (_, _) => const SizedBox(height: 10),
            itemBuilder: (context, index) {
              final item = _items[index];
              return ListingCard(
                listing: item,
                onTap: () => context.push('/listing/${item.id}'),
                onBookmark: () => _toggleBookmark(item),
              );
            },
          ),
        ),
      ),
    );
  }
}
