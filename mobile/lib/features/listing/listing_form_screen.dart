import 'dart:io';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../../core/api/api_client.dart';
import '../../core/api/models.dart';
import '../../core/api/repositories.dart';
import '../../core/theme/poisker_icons.dart';
import '../../core/widgets/async_body.dart';

class ListingFormScreen extends StatefulWidget {
  const ListingFormScreen({super.key, this.listingId});

  final String? listingId;

  bool get isEdit => listingId != null;

  @override
  State<ListingFormScreen> createState() => _ListingFormScreenState();
}

class _ListingFormScreenState extends State<ListingFormScreen> {
  final _formKey = GlobalKey<FormState>();
  final _title = TextEditingController();
  final _body = TextEditingController();
  final _price = TextEditingController();
  final _picker = ImagePicker();

  List<Category> _categories = const [];
  List<City> _cities = const [];
  String? _category;
  String? _city;
  String _condition = 'used';
  final _existingImages = <String>[];
  final _removedIndexes = <int>{};
  final _newImages = <XFile>[];
  bool _loading = true;
  bool _saving = false;
  String? _error;
  String? _status;
  String? _formError;
  Map<String, List<String>> _fieldErrors = const {};

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _bootstrap());
  }

  @override
  void dispose() {
    _title.dispose();
    _body.dispose();
    _price.dispose();
    super.dispose();
  }

  Future<void> _bootstrap() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final repo = context.read<CatalogRepository>();
      final cats = await repo.categories();
      final cities = await repo.cities();
      if (widget.isEdit) {
        final listing = await repo.listingDetail(widget.listingId!);
        _title.text = listing.title;
        _body.text = listing.body ?? '';
        if (listing.price != null) _price.text = '${listing.price}';
        _category = listing.category;
        _city = listing.city;
        _condition = listing.condition;
        _existingImages.addAll(listing.images);
        _status = listing.status;
      }
      if (!mounted) return;
      setState(() {
        _categories = cats;
        _cities = cities;
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

  int get _visibleExistingCount =>
      _existingImages.length - _removedIndexes.length;

  Future<void> _pickImages() async {
    final room = 5 - _visibleExistingCount - _newImages.length;
    if (room <= 0) {
      showAppError(context, 'Максимум 5 фото');
      return;
    }
    final files = await _picker.pickMultiImage(imageQuality: 85);
    if (files.isEmpty) return;
    setState(() {
      _newImages.addAll(files.take(room));
    });
  }

  Future<void> _save({required bool asDraft}) async {
    FocusScope.of(context).unfocus();
    if (!_formKey.currentState!.validate()) return;
    if (_category == null || _city == null) {
      setState(() => _formError = 'Выберите город и категорию');
      return;
    }
    setState(() {
      _saving = true;
      _formError = null;
      _fieldErrors = const {};
    });
    try {
      final repo = context.read<CatalogRepository>();
      final priceText = _price.text.trim();
      final price =
          priceText.isEmpty ? null : int.tryParse(priceText.replaceAll(' ', ''));
      final Listing listing;
      if (widget.isEdit) {
        listing = await repo.updateListing(
          id: widget.listingId!,
          title: _title.text.trim(),
          body: _body.text.trim(),
          category: _category!,
          city: _city!,
          condition: _condition,
          price: price,
          clearPrice: priceText.isEmpty,
          asDraft: asDraft && _status == 'draft',
          newImages: _newImages.map((e) => File(e.path)).toList(),
          removeImageIndexes: _removedIndexes.toList()..sort(),
        );
      } else {
        listing = await repo.createListing(
          title: _title.text.trim(),
          body: _body.text.trim(),
          category: _category!,
          city: _city!,
          condition: _condition,
          price: price,
          asDraft: asDraft,
          images: _newImages.map((e) => File(e.path)).toList(),
        );
      }
      if (!mounted) return;
      showAppSuccess(
        context,
        asDraft ? 'Черновик сохранён' : 'Объявление отправлено',
      );
      context.go('/listing/${listing.id}');
    } catch (e) {
      if (!mounted) return;
      final err = ApiClient.mapError(e);
      setState(() {
        _formError = err.displayMessage;
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
      appBar: AppBar(
        title: Text(widget.isEdit ? 'Редактирование' : 'Новое объявление'),
      ),
      body: AsyncBody(
        loading: _loading,
        error: _error,
        onRetry: _bootstrap,
        child: Form(
          key: _formKey,
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              if (_formError != null) ...[
                ErrorBanner(
                  message: _formError!,
                  onDismiss: () => setState(() => _formError = null),
                ),
                const SizedBox(height: 12),
              ],
              TextFormField(
                controller: _title,
                decoration: InputDecoration(
                  labelText: 'Заголовок',
                  errorText: _fieldErrors['title']?.firstOrNull,
                ),
                maxLength: 50,
                validator: (v) {
                  final t = v?.trim() ?? '';
                  if (t.length < 5) return 'Минимум 5 символов';
                  return null;
                },
              ),
              const SizedBox(height: 8),
              TextFormField(
                controller: _body,
                decoration: InputDecoration(
                  labelText: 'Описание',
                  errorText: _fieldErrors['body']?.firstOrNull,
                ),
                maxLines: 6,
                maxLength: 3000,
                validator: (v) {
                  final t = v?.trim() ?? '';
                  if (t.length < 20) return 'Минимум 20 символов';
                  return null;
                },
              ),
              const SizedBox(height: 8),
              DropdownMenu<String>(
                key: ValueKey('category-$_category-${_categories.length}'),
                initialSelection: _category,
                label: const Text('Категория'),
                errorText: _fieldErrors['category']?.firstOrNull,
                expandedInsets: EdgeInsets.zero,
                onSelected: (v) => setState(() => _category = v),
                dropdownMenuEntries: _categories
                    .map(
                      (c) => DropdownMenuEntry(value: c.slug, label: c.label),
                    )
                    .toList(),
              ),
              const SizedBox(height: 12),
              DropdownMenu<String>(
                key: ValueKey('city-$_city-${_cities.length}'),
                initialSelection: _city,
                label: const Text('Город'),
                errorText: _fieldErrors['city']?.firstOrNull,
                expandedInsets: EdgeInsets.zero,
                onSelected: (v) => setState(() => _city = v),
                dropdownMenuEntries: _cities
                    .map(
                      (c) => DropdownMenuEntry(value: c.slug, label: c.label),
                    )
                    .toList(),
              ),
              const SizedBox(height: 12),
              DropdownMenu<String>(
                key: ValueKey('condition-$_condition'),
                initialSelection: _condition,
                label: const Text('Состояние'),
                expandedInsets: EdgeInsets.zero,
                onSelected: (v) => setState(() => _condition = v ?? 'used'),
                dropdownMenuEntries: const [
                  DropdownMenuEntry(value: 'used', label: 'Б/у'),
                  DropdownMenuEntry(value: 'new', label: 'Новое'),
                ],
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _price,
                keyboardType: TextInputType.number,
                decoration: InputDecoration(
                  labelText: 'Цена (пусто = по договорённости)',
                  errorText: _fieldErrors['price']?.firstOrNull,
                ),
              ),
              const SizedBox(height: 16),
              const Text('Фото (до 5)', style: TextStyle(fontWeight: FontWeight.w600)),
              const SizedBox(height: 8),
              SizedBox(
                height: 96,
                child: ListView(
                  scrollDirection: Axis.horizontal,
                  children: [
                    for (var i = 0; i < _existingImages.length; i++)
                      if (!_removedIndexes.contains(i))
                        _Thumb(
                          child: CachedNetworkImage(
                            imageUrl: _existingImages[i],
                            fit: BoxFit.cover,
                          ),
                          onRemove: () =>
                              setState(() => _removedIndexes.add(i)),
                        ),
                    for (var i = 0; i < _newImages.length; i++)
                      _Thumb(
                        child: Image.file(
                          File(_newImages[i].path),
                          fit: BoxFit.cover,
                        ),
                        onRemove: () => setState(() => _newImages.removeAt(i)),
                      ),
                    if (_visibleExistingCount + _newImages.length < 5)
                      InkWell(
                        onTap: _pickImages,
                        child: Container(
                          width: 96,
                          height: 96,
                          margin: const EdgeInsets.only(right: 8),
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: Colors.black26),
                          ),
                          child: const Icon(PoiskerIcons.camera),
                        ),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              FilledButton(
                onPressed: _saving ? null : () => _save(asDraft: false),
                child: Text(
                  widget.isEdit ? 'Сохранить' : 'Отправить на модерацию',
                ),
              ),
              if (!widget.isEdit || _status == 'draft') ...[
                const SizedBox(height: 8),
                OutlinedButton(
                  onPressed: _saving ? null : () => _save(asDraft: true),
                  child: const Text('Сохранить черновик'),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _Thumb extends StatelessWidget {
  const _Thumb({required this.child, required this.onRemove});

  final Widget child;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 96,
      height: 96,
      margin: const EdgeInsets.only(right: 8),
      child: Stack(
        children: [
          Positioned.fill(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: child,
            ),
          ),
          Positioned(
            top: 0,
            right: 0,
            child: IconButton.filled(
              style: IconButton.styleFrom(
                backgroundColor: Colors.black54,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.all(4),
                minimumSize: const Size(28, 28),
              ),
              onPressed: onRemove,
              icon: const Icon(PoiskerIcons.close, size: 16),
            ),
          ),
        ],
      ),
    );
  }
}
