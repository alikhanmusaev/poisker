import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';

import '../../core/api/api_client.dart';
import '../../core/api/models.dart';
import '../../core/api/repositories.dart';
import '../../core/auth/auth_controller.dart';
import '../../core/theme/lucide_resolve.dart';
import '../../core/theme/poisker_icons.dart';
import '../../core/theme/poisker_theme.dart';
import '../../core/widgets/async_body.dart';
import '../../core/widgets/listing_card.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _search = TextEditingController();
  final _scroll = ScrollController();
  final _items = <Listing>[];
  List<Category> _categories = const [];
  List<City> _cities = const [];
  String? _city;
  String? _category;
  String _ordering = 'date_desc';
  int _page = 1;
  int _count = 0;
  bool _loading = true;
  bool _loadingMore = false;
  bool _hasMore = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _scroll.addListener(_onScroll);
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      await _loadMeta();
      await _reload();
    });
  }

  @override
  void dispose() {
    _search.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _loadMeta() async {
    try {
      final repo = context.read<CatalogRepository>();
      final cats = await repo.categories();
      final cities = await repo.cities();
      if (!mounted) return;
      setState(() {
        _categories = cats;
        _cities = cities;
      });
    } catch (_) {}
  }

  void _onScroll() {
    if (!_hasMore || _loadingMore || _loading) return;
    if (_scroll.position.pixels > _scroll.position.maxScrollExtent - 400) {
      _loadMore();
    }
  }

  Future<void> _reload() async {
    setState(() {
      _loading = true;
      _error = null;
      _page = 1;
    });
    try {
      final page = await context.read<CatalogRepository>().listings(
            search: _search.text.trim(),
            city: _city,
            category: _category,
            ordering: _ordering,
            page: 1,
          );
      if (!mounted) return;
      setState(() {
        _items
          ..clear()
          ..addAll(page.results);
        _count = page.count;
        _hasMore = page.hasMore;
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

  Future<void> _loadMore() async {
    setState(() => _loadingMore = true);
    try {
      final next = _page + 1;
      final page = await context.read<CatalogRepository>().listings(
            search: _search.text.trim(),
            city: _city,
            category: _category,
            ordering: _ordering,
            page: next,
          );
      if (!mounted) return;
      setState(() {
        _page = next;
        _items.addAll(page.results);
        _hasMore = page.hasMore;
        _loadingMore = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _loadingMore = false);
    }
  }

  Future<void> _pickCity() async {
    final selected = await showModalBottomSheet<String?>(
      context: context,
      isScrollControlled: true,
      builder: (context) {
        return _CityPickerSheet(cities: _cities, selected: _city);
      },
    );
    if (selected == null) return;
    setState(() => _city = selected.isEmpty ? null : selected);
    _reload();
  }

  String get _cityLabel {
    if (_city == null) return 'Город';
    return _cities
            .where((c) => c.slug == _city)
            .map((c) => c.label)
            .firstOrNull ??
        'Город';
  }

  Future<void> _toggleBookmark(Listing item) async {
    if (!await requireAuth(
      context,
      message: 'Войдите, чтобы сохранять объявления в закладки.',
    )) {
      return;
    }
    if (!mounted) return;
    try {
      final bookmarked = await context.read<CatalogRepository>().toggleBookmark(
            item.id,
            currentlyBookmarked: item.isBookmarked,
          );
      if (!mounted) return;
      setState(() {
        final i = _items.indexWhere((e) => e.id == item.id);
        if (i >= 0) _items[i] = _items[i].copyWith(isBookmarked: bookmarked);
      });
    } catch (e) {
      if (!mounted) return;
      showAppError(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    final authed = context.watch<AuthController>().isAuthenticated;
    final topPad = MediaQuery.paddingOf(context).top;

    return Scaffold(
      backgroundColor: PoiskerColors.background,
      body: RefreshIndicator(
        color: PoiskerColors.primary700,
        onRefresh: _reload,
        edgeOffset: topPad + 8,
        child: CustomScrollView(
          controller: _scroll,
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            SliverToBoxAdapter(
              child: _BrandStrip(
                topPadding: topPad,
                showLogin: !authed,
                onLogin: () => context.push('/login'),
              ),
            ),
            // Search + city + categories stick on scroll; brand scrolls away.
            SliverPersistentHeader(
              pinned: true,
              delegate: _StickyFiltersDelegate(
                search: _buildSearchRow(),
                categories: _buildCategories(),
              ),
            ),
            SliverToBoxAdapter(child: _buildMetaRow()),
            if (_loading)
              const SliverFillRemaining(
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_error != null)
              SliverFillRemaining(
                child: AsyncBody(
                  loading: false,
                  error: _error,
                  onRetry: _reload,
                  child: const SizedBox.shrink(),
                ),
              )
            else if (_items.isEmpty)
              const SliverFillRemaining(
                child: Center(
                  child: Text(
                    'Ничего не найдено',
                    style: TextStyle(color: PoiskerColors.muted),
                  ),
                ),
              )
            else
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                sliver: SliverList.separated(
                  itemCount: _items.length + (_loadingMore ? 1 : 0),
                  separatorBuilder: (_, _) => const SizedBox(height: 16),
                  itemBuilder: (context, index) {
                    if (index >= _items.length) {
                      return const Padding(
                        padding: EdgeInsets.all(16),
                        child: Center(child: CircularProgressIndicator()),
                      );
                    }
                    final item = _items[index];
                    return ListingCard(
                      listing: item,
                      onTap: () => context.push('/listing/${item.id}'),
                      onBookmark: () => _toggleBookmark(item),
                    );
                  },
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildSearchRow() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 10, 16, 8),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _search,
              textInputAction: TextInputAction.search,
              onSubmitted: (_) => _reload(),
              decoration: const InputDecoration(
                hintText: 'iPhone, квартира, автомобиль…',
                prefixIcon: Icon(PoiskerIcons.search, color: PoiskerColors.slate400),
                isDense: true,
              ),
            ),
          ),
          const SizedBox(width: 8),
          Material(
            color: PoiskerColors.surface,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(PoiskerRadii.sm),
              side: BorderSide(
                color: _city != null
                    ? PoiskerColors.primary600
                    : PoiskerColors.border,
              ),
            ),
            child: InkWell(
              onTap: _pickCity,
              borderRadius: BorderRadius.circular(PoiskerRadii.sm),
              child: Padding(
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
                child: Row(
                  children: [
                    Icon(
                      PoiskerIcons.mapPin,
                      size: 18,
                      color: _city != null
                          ? PoiskerColors.primary700
                          : PoiskerColors.slate500,
                    ),
                    const SizedBox(width: 4),
                    ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 88),
                      child: Text(
                        _cityLabel,
                        overflow: TextOverflow.ellipsis,
                        style: GoogleFonts.inter(
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                          color: _city != null
                              ? PoiskerColors.primary800
                              : PoiskerColors.slate700,
                        ),
                      ),
                    ),
                    const Icon(PoiskerIcons.chevronDown, size: 18),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCategories() {
    return SizedBox(
      height: 52,
      child: ListView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
        children: [
          _CategoryChip(
            label: 'Все',
            iconName: 'layout-grid',
            selected: _category == null,
            onTap: () {
              setState(() => _category = null);
              _reload();
            },
          ),
          ..._categories.map(
            (c) => _CategoryChip(
              label: c.label,
              iconName: c.icon,
              selected: _category == c.slug,
              onTap: () {
                setState(() => _category = c.slug);
                _reload();
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMetaRow() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 8, 12),
      child: Row(
        children: [
          Expanded(
            child: Text(
              _count == 0
                  ? 'Нет объявлений'
                  : '$_count ${_plural(_count)}',
              style: GoogleFonts.inter(
                fontSize: 13,
                color: PoiskerColors.muted,
              ),
            ),
          ),
          PopupMenuButton<String>(
            initialValue: _ordering,
            onSelected: (v) {
              setState(() => _ordering = v);
              _reload();
            },
            itemBuilder: (context) => const [
              PopupMenuItem(value: 'date_desc', child: Text('Сначала новые')),
              PopupMenuItem(value: 'price_asc', child: Text('Сначала дешевле')),
              PopupMenuItem(value: 'price_desc', child: Text('Сначала дороже')),
            ],
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
              child: Row(
                children: [
                  Text(
                    switch (_ordering) {
                      'price_asc' => 'Дешевле',
                      'price_desc' => 'Дороже',
                      _ => 'Сначала новые',
                    },
                    style: GoogleFonts.inter(
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                      color: PoiskerColors.slate700,
                    ),
                  ),
                  const Icon(PoiskerIcons.chevronDown, size: 18),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _plural(int n) {
    final mod10 = n % 10;
    final mod100 = n % 100;
    if (mod10 == 1 && mod100 != 11) return 'объявление';
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
      return 'объявления';
    }
    return 'объявлений';
  }
}

class _BrandStrip extends StatelessWidget {
  const _BrandStrip({
    required this.topPadding,
    required this.showLogin,
    required this.onLogin,
  });

  final double topPadding;
  final bool showLogin;
  final VoidCallback onLogin;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: PoiskerColors.surface,
      padding: EdgeInsets.fromLTRB(16, topPadding + 8, 8, 8),
      child: Row(
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(PoiskerRadii.md),
            child: Image.asset(
              'assets/logo.png',
              width: 40,
              height: 40,
              fit: BoxFit.contain,
              errorBuilder: (_, _, _) => Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: PoiskerColors.primary700,
                  borderRadius: BorderRadius.circular(PoiskerRadii.md),
                ),
                child: const Icon(PoiskerIcons.bolt, color: Colors.white),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Поискер',
                  style: GoogleFonts.inter(
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.3,
                    color: PoiskerColors.slate900,
                    height: 1.2,
                  ),
                ),
                Text(
                  'Доска объявлений по ЧР',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    color: PoiskerColors.muted,
                    height: 1.2,
                  ),
                ),
              ],
            ),
          ),
          if (showLogin)
            TextButton(
              onPressed: onLogin,
              child: Text(
                'Войти',
                style: GoogleFonts.inter(
                  fontWeight: FontWeight.w600,
                  color: PoiskerColors.primary700,
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _StickyFiltersDelegate extends SliverPersistentHeaderDelegate {
  _StickyFiltersDelegate({
    required this.search,
    required this.categories,
  });

  final Widget search;
  final Widget categories;

  // search row (~66) + categories (52)
  static const double _height = 118;

  @override
  double get minExtent => _height;

  @override
  double get maxExtent => _height;

  @override
  Widget build(
    BuildContext context,
    double shrinkOffset,
    bool overlapsContent,
  ) {
    return Material(
      color: PoiskerColors.surface,
      elevation: overlapsContent || shrinkOffset > 0 ? 1 : 0,
      shadowColor: Colors.black26,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          search,
          categories,
          const Divider(height: 1, color: PoiskerColors.border),
        ],
      ),
    );
  }

  @override
  bool shouldRebuild(covariant _StickyFiltersDelegate oldDelegate) {
    return search != oldDelegate.search ||
        categories != oldDelegate.categories;
  }
}

class _CityPickerSheet extends StatefulWidget {
  const _CityPickerSheet({required this.cities, this.selected});

  final List<City> cities;
  final String? selected;

  @override
  State<_CityPickerSheet> createState() => _CityPickerSheetState();
}

class _CityPickerSheetState extends State<_CityPickerSheet> {
  final _query = TextEditingController();

  @override
  void dispose() {
    _query.dispose();
    super.dispose();
  }

  List<City> get _filtered {
    final q = _query.text.trim().toLowerCase();
    if (q.isEmpty) return widget.cities;
    return widget.cities
        .where((c) => c.label.toLowerCase().contains(q))
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    final cities = _filtered;
    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.7,
      builder: (context, controller) {
        return Column(
          children: [
            const SizedBox(height: 12),
            Text(
              'Город',
              style: GoogleFonts.inter(
                fontSize: 16,
                fontWeight: FontWeight.w700,
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
              child: TextField(
                controller: _query,
                onChanged: (_) => setState(() {}),
                decoration: const InputDecoration(
                  hintText: 'Поиск города',
                  prefixIcon: Icon(PoiskerIcons.search),
                  isDense: true,
                ),
              ),
            ),
            ListTile(
              title: const Text('Все города'),
              onTap: () => Navigator.pop(context, ''),
            ),
            const Divider(height: 1),
            Expanded(
              child: ListView.builder(
                controller: controller,
                itemCount: cities.length,
                itemBuilder: (context, index) {
                  final city = cities[index];
                  return ListTile(
                    title: Text(city.label),
                    selected: city.slug == widget.selected,
                    onTap: () => Navigator.pop(context, city.slug),
                  );
                },
              ),
            ),
          ],
        );
      },
    );
  }
}

class _CategoryChip extends StatelessWidget {
  const _CategoryChip({
    required this.label,
    required this.selected,
    required this.onTap,
    this.iconName,
  });

  final String label;
  final String? iconName;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final icon = lucideIcon(iconName, fallback: PoiskerIcons.home);
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: Material(
        color: selected ? PoiskerColors.primary50 : PoiskerColors.surface,
        shape: StadiumBorder(
          side: BorderSide(
            color: selected ? PoiskerColors.primary600 : PoiskerColors.border,
          ),
        ),
        child: InkWell(
          onTap: onTap,
          customBorder: const StadiumBorder(),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(6, 6, 12, 6),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: selected
                        ? PoiskerColors.primary600
                        : PoiskerColors.slate100,
                  ),
                  child: Icon(
                    icon,
                    size: 16,
                    color: selected ? Colors.white : PoiskerColors.slate600,
                  ),
                ),
                const SizedBox(width: 6),
                Text(
                  label,
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                    color: selected
                        ? PoiskerColors.primary800
                        : PoiskerColors.slate600,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
