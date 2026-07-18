import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api/api_client.dart';
import '../../core/api/models.dart';
import '../../core/api/repositories.dart';
import '../../core/theme/poisker_icons.dart';
import '../../core/widgets/async_body.dart';
import '../../core/widgets/listing_card.dart';

class MyListingsScreen extends StatefulWidget {
  const MyListingsScreen({super.key});

  @override
  State<MyListingsScreen> createState() => _MyListingsScreenState();
}

class _MyListingsScreenState extends State<MyListingsScreen> {
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
      final page = await context.read<CatalogRepository>().myListings();
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Мои объявления')),
      floatingActionButton: FloatingActionButton(
        onPressed: () => context.push('/create'),
        child: const Icon(PoiskerIcons.plus),
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: AsyncBody(
          loading: _loading,
          error: _error,
          onRetry: _load,
          empty: _items.isEmpty,
          emptyMessage: 'Пока нет объявлений',
          child: ListView.separated(
            padding: const EdgeInsets.all(12),
            itemCount: _items.length,
            separatorBuilder: (_, _) => const SizedBox(height: 10),
            itemBuilder: (context, index) {
              final item = _items[index];
              return ListingCard(
                listing: item,
                onTap: () => context.push('/listing/${item.id}'),
              );
            },
          ),
        ),
      ),
    );
  }
}
