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
import '../../core/widgets/brand_header.dart';
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
  int? _minPrice;
  int? _maxPrice;
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
            minPrice: _minPrice,
            maxPrice: _maxPrice,
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
            minPrice: _minPrice,
            maxPrice: _maxPrice,
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

  Future<void> _pickPrice() async {
    final result = await showModalBottomSheet<({int? min, int? max})>(
      context: context,
      isScrollControlled: true,
      builder: (context) => _PriceFilterSheet(
        minPrice: _minPrice,
        maxPrice: _maxPrice,
      ),
    );
    if (result == null) return;
    setState(() {
      _minPrice = result.min;
      _maxPrice = result.max;
    });
    _reload();
  }

  bool get _hasPriceFilter => _minPrice != null || _maxPrice != null;

  String get _priceFilterLabel {
    if (_minPrice != null && _maxPrice != null) {
      return '$_minPrice – $_maxPrice ₽';
    }
    if (_minPrice != null) return 'от $_minPrice ₽';
    if (_maxPrice != null) return 'до $_maxPrice ₽';
    return 'Цена';
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
    return Scaffold(
      backgroundColor: PoiskerColors.background,
      appBar: PoiskerBrandHeader(
        actions: [
          if (!authed)
            TextButton(
              onPressed: () => context.push('/login'),
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
      body: RefreshIndicator(
        color: PoiskerColors.primary700,
        onRefresh: _reload,
        child: CustomScrollView(
          controller: _scroll,
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            SliverToBoxAdapter(child: _buildSearchRow()),
            SliverToBoxAdapter(child: _buildCategories()),
            SliverToBoxAdapter(child: _buildFiltersRow()),
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
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _search,
              textInputAction: TextInputAction.search,
              onSubmitted: (_) => _reload(),
              decoration: InputDecoration(
                hintText: 'iPhone, квартира, автомобиль…',
                prefixIcon: const Icon(PoiskerIcons.search, color: PoiskerColors.slate400),
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
        padding: const EdgeInsets.symmetric(horizontal: 16),
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

  Widget _buildFiltersRow() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 0),
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: [
          ActionChip(
            avatar: Icon(
              PoiskerIcons.bolt,
              size: 16,
              color: _hasPriceFilter
                  ? PoiskerColors.primary700
                  : PoiskerColors.slate500,
            ),
            label: Text(_priceFilterLabel),
            backgroundColor: _hasPriceFilter
                ? PoiskerColors.primary50
                : PoiskerColors.surface,
            side: BorderSide(
              color: _hasPriceFilter
                  ? PoiskerColors.primary600
                  : PoiskerColors.border,
            ),
            onPressed: _pickPrice,
          ),
          if (_hasPriceFilter)
            InputChip(
              label: const Text('Сбросить цену'),
              onDeleted: () {
                setState(() {
                  _minPrice = null;
                  _maxPrice = null;
                });
                _reload();
              },
              onPressed: () {
                setState(() {
                  _minPrice = null;
                  _maxPrice = null;
                });
                _reload();
              },
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

class _PriceFilterSheet extends StatefulWidget {
  const _PriceFilterSheet({this.minPrice, this.maxPrice});

  final int? minPrice;
  final int? maxPrice;

  @override
  State<_PriceFilterSheet> createState() => _PriceFilterSheetState();
}

class _PriceFilterSheetState extends State<_PriceFilterSheet> {
  late final TextEditingController _min;
  late final TextEditingController _max;

  @override
  void initState() {
    super.initState();
    _min = TextEditingController(
      text: widget.minPrice?.toString() ?? '',
    );
    _max = TextEditingController(
      text: widget.maxPrice?.toString() ?? '',
    );
  }

  @override
  void dispose() {
    _min.dispose();
    _max.dispose();
    super.dispose();
  }

  int? _parse(String raw) {
    final t = raw.trim();
    if (t.isEmpty) return null;
    return int.tryParse(t);
  }

  @override
  Widget build(BuildContext context) {
    final bottom = MediaQuery.viewInsetsOf(context).bottom;
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 16, 16, 16 + bottom),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Цена',
            style: GoogleFonts.inter(
              fontSize: 16,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _min,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    labelText: 'От',
                    hintText: '0',
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: TextField(
                  controller: _max,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    labelText: 'До',
                    hintText: '∞',
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: () {
              Navigator.pop(
                context,
                (min: _parse(_min.text), max: _parse(_max.text)),
              );
            },
            child: const Text('Применить'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, (min: null, max: null)),
            child: const Text('Сбросить'),
          ),
        ],
      ),
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
