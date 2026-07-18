import 'dart:io';

import 'package:dio/dio.dart';
import 'package:http_parser/http_parser.dart';
import 'package:path/path.dart' as p;

import 'api_client.dart';
import 'models.dart';

class CatalogRepository {
  CatalogRepository(this._api);

  final ApiClient _api;

  Future<Paginated<Listing>> listings({
    String? search,
    String? city,
    String? category,
    String? ordering,
    int? minPrice,
    int? maxPrice,
    int page = 1,
  }) async {
    final response = await _api.get<Map<String, dynamic>>(
      'listings/',
      query: {
        if (search != null && search.isNotEmpty) 'search': search,
        if (city != null && city.isNotEmpty) 'city': city,
        if (category != null && category.isNotEmpty) 'category': category,
        if (ordering != null && ordering.isNotEmpty) 'ordering': ordering,
        'min_price': ?minPrice,
        'max_price': ?maxPrice,
        'page': page,
        'page_size': 20,
      },
    );
    return _parseListings(response.data ?? {});
  }

  Future<Paginated<Listing>> myListings({int page = 1}) async {
    final response = await _api.get<Map<String, dynamic>>(
      'me/listings/',
      query: {'page': page, 'page_size': 20},
    );
    return _parseListings(response.data ?? {});
  }

  Future<Paginated<Listing>> bookmarks({int page = 1}) async {
    final response = await _api.get<Map<String, dynamic>>(
      'me/bookmarks/',
      query: {'page': page, 'page_size': 20},
    );
    final data = response.data ?? {};
    final results = (data['results'] as List? ?? [])
        .whereType<Map>()
        .map((e) {
          final listing = e['listing'];
          if (listing is Map) {
            return Listing.fromJson(Map<String, dynamic>.from(listing))
                .copyWith(isBookmarked: true);
          }
          return Listing.fromJson(Map<String, dynamic>.from(e));
        })
        .toList();
    return Paginated(
      count: (data['count'] as num?)?.toInt() ?? results.length,
      results: results,
      next: data['next']?.toString(),
    );
  }

  Future<Listing> listingDetail(String id) async {
    final response = await _api.get<Map<String, dynamic>>('listings/$id/');
    return Listing.fromJson(response.data ?? {});
  }

  Future<List<Category>> categories() async {
    final response = await _api.get<List<dynamic>>('categories/');
    return (response.data ?? [])
        .whereType<Map>()
        .map((e) => Category.fromJson(Map<String, dynamic>.from(e)))
        .toList();
  }

  Future<List<City>> cities({String? search}) async {
    final response = await _api.get<List<dynamic>>(
      'cities/',
      query: {
        if (search != null && search.isNotEmpty) 'search': search,
      },
    );
    return (response.data ?? [])
        .whereType<Map>()
        .map((e) => City.fromJson(Map<String, dynamic>.from(e)))
        .toList();
  }

  Future<String> contactPhone(String listingId) async {
    final response = await _api.post<Map<String, dynamic>>(
      'listings/$listingId/contact/',
    );
    return (response.data?['phone'] ?? '').toString();
  }

  Future<bool> toggleBookmark(
    String listingId, {
    required bool currentlyBookmarked,
  }) async {
    if (currentlyBookmarked) {
      await _api.delete('listings/$listingId/bookmark/');
      return false;
    }
    final response = await _api.post<Map<String, dynamic>>(
      'listings/$listingId/bookmark/',
    );
    return response.data?['bookmarked'] == true;
  }

  Future<Listing> createListing({
    required String title,
    required String body,
    required String category,
    required String city,
    String condition = 'used',
    int? price,
    bool asDraft = false,
    List<File> images = const [],
  }) async {
    final form = FormData.fromMap({
      'title': title,
      'body': body,
      'category': category,
      'city': city,
      'condition': condition,
      'price': ?price,
      'as_draft': asDraft ? 'true' : 'false',
    });
    for (final file in images) {
      form.files.add(MapEntry('images', await _multipartFile(file)));
    }
    final response = await _api.postMultipart<Map<String, dynamic>>(
      'listings/',
      form,
    );
    return Listing.fromJson(response.data ?? {});
  }

  Future<Listing> updateListing({
    required String id,
    required String title,
    required String body,
    required String category,
    required String city,
    String condition = 'used',
    int? price,
    bool clearPrice = false,
    bool asDraft = false,
    List<File> newImages = const [],
    List<int> removeImageIndexes = const [],
  }) async {
    final map = <String, dynamic>{
      'title': title,
      'body': body,
      'category': category,
      'city': city,
      'condition': condition,
      if (asDraft) 'as_draft': 'true',
    };
    if (clearPrice) {
      map['price'] = '';
    } else if (price != null) {
      map['price'] = price;
    }
    final form = FormData.fromMap(map);
    for (final index in removeImageIndexes) {
      form.fields.add(MapEntry('remove_images', '$index'));
    }
    for (final file in newImages) {
      form.files.add(MapEntry('images', await _multipartFile(file)));
    }
    final response = await _api.patchMultipart<Map<String, dynamic>>(
      'listings/$id/',
      form,
    );
    return Listing.fromJson(response.data ?? {});
  }

  Future<Listing> submitListing(String id) async {
    final response =
        await _api.post<Map<String, dynamic>>('listings/$id/submit/');
    return Listing.fromJson(response.data ?? {});
  }

  Future<Listing> republishListing(String id) async {
    final response =
        await _api.post<Map<String, dynamic>>('listings/$id/republish/');
    return Listing.fromJson(response.data ?? {});
  }

  Future<Listing?> deleteListing(String id) async {
    final response = await _api.delete<Map<String, dynamic>>('listings/$id/');
    if (response.statusCode == 204 || response.data == null) return null;
    return Listing.fromJson(response.data ?? {});
  }

  Future<void> reportListing(
    String id, {
    required String reason,
    String? comment,
  }) async {
    await _api.post<Map<String, dynamic>>(
      'listings/$id/report/',
      data: {
        'reason': reason,
        if (comment != null && comment.isNotEmpty) 'comment': comment,
      },
    );
  }

  Future<PushPreferences> pushPreferences() async {
    final response =
        await _api.get<Map<String, dynamic>>('push/preferences/');
    return PushPreferences.fromJson(response.data ?? {});
  }

  Future<PushPreferences> updatePushPreferences(PushPreferences prefs) async {
    final response = await _api.patch<Map<String, dynamic>>(
      'push/preferences/',
      data: prefs.toJson(),
    );
    return PushPreferences.fromJson(response.data ?? {});
  }

  Paginated<Listing> _parseListings(Map<String, dynamic> data) {
    final results = (data['results'] as List? ?? [])
        .whereType<Map>()
        .map((e) => Listing.fromJson(Map<String, dynamic>.from(e)))
        .toList();
    return Paginated(
      count: (data['count'] as num?)?.toInt() ?? results.length,
      results: results,
      next: data['next']?.toString(),
    );
  }

  Future<MultipartFile> _multipartFile(File file) async {
    final name = p.basename(file.path);
    final ext = p.extension(name).toLowerCase().replaceFirst('.', '');
    final mime = switch (ext) {
      'png' => MediaType('image', 'png'),
      'webp' => MediaType('image', 'webp'),
      'gif' => MediaType('image', 'gif'),
      _ => MediaType('image', 'jpeg'),
    };
    return MultipartFile.fromFile(file.path, filename: name, contentType: mime);
  }
}

class MessagingRepository {
  MessagingRepository(this._api);

  final ApiClient _api;

  Future<List<Conversation>> conversations() async {
    final response = await _api.get<Map<String, dynamic>>('me/conversations/');
    final results = response.data?['results'] as List? ?? [];
    return results
        .whereType<Map>()
        .map((e) => Conversation.fromJson(Map<String, dynamic>.from(e)))
        .toList();
  }

  Future<({Conversation conversation, List<ChatMessage> messages})> thread(
    String id,
  ) async {
    final response = await _api.get<Map<String, dynamic>>('conversations/$id/');
    final data = response.data ?? {};
    final messages = (data['messages'] as List? ?? [])
        .whereType<Map>()
        .map((e) => ChatMessage.fromJson(Map<String, dynamic>.from(e)))
        .toList();
    return (
      conversation: Conversation.fromJson(data),
      messages: messages,
    );
  }

  Future<ChatMessage> sendMessage(String conversationId, String body) async {
    final response = await _api.post<Map<String, dynamic>>(
      'conversations/$conversationId/messages/',
      data: {'body': body},
    );
    return ChatMessage.fromJson(response.data ?? {});
  }

  Future<String> startConversation(String listingId, {String? body}) async {
    final response = await _api.post<Map<String, dynamic>>(
      'listings/$listingId/conversations/',
      data: {
        if (body != null && body.isNotEmpty) 'body': body,
      },
    );
    return (response.data?['id'] ?? '').toString();
  }

  Future<int> unreadCount() async {
    final response = await _api.get<Map<String, dynamic>>(
      'me/conversations/unread-count/',
    );
    return (response.data?['count'] as num?)?.toInt() ?? 0;
  }

  Future<void> deleteConversation(String id) async {
    await _api.delete('conversations/$id/');
  }

  Future<Conversation> confirmDeal(String id) async {
    final response = await _api.post<Map<String, dynamic>>(
      'conversations/$id/confirm-deal/',
    );
    return Conversation.fromJson(response.data ?? {});
  }
}
