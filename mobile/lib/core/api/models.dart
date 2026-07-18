class User {
  User({
    required this.id,
    required this.email,
    required this.displayName,
    required this.phone,
    required this.emailVerified,
    this.ratingAvg = 0,
    this.ratingCount = 0,
  });

  final String id;
  final String email;
  final String displayName;
  final String phone;
  final bool emailVerified;
  final double ratingAvg;
  final int ratingCount;

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'].toString(),
      email: (json['email'] ?? '').toString(),
      displayName: (json['display_name'] ?? '').toString(),
      phone: (json['phone'] ?? '').toString(),
      emailVerified: json['email_verified'] == true,
      ratingAvg: (json['rating_avg'] as num?)?.toDouble() ?? 0,
      ratingCount: (json['rating_count'] as num?)?.toInt() ?? 0,
    );
  }
}

/// Report reasons matching web `REPORT_REASONS`.
const reportReasons = <String, String>{
  'spam': 'Спам',
  'fraud': 'Мошенничество',
  'wrong_phone': 'Неверный номер телефона',
  'inappropriate': 'Недопустимый контент',
  'duplicate': 'Дубликат',
  'other': 'Другое',
};

class Listing {
  Listing({
    required this.id,
    required this.title,
    required this.category,
    required this.categoryLabel,
    required this.city,
    required this.cityLabel,
    required this.priceDisplay,
    required this.status,
    this.condition = 'used',
    this.conditionLabel,
    this.coverImage,
    this.price,
    this.isBookmarked = false,
    this.hasPhoto = false,
    this.views = 0,
    this.body,
    this.images = const [],
    this.isOwner = false,
    this.phoneMasked,
    this.publicUrl,
    this.sellerId,
    this.sellerName,
    this.sellerRatingAvg = 0,
    this.sellerRatingCount = 0,
    this.statusLabel,
    this.moderationNote,
  });

  final String id;
  final String title;
  final String category;
  final String categoryLabel;
  final String city;
  final String cityLabel;
  final String priceDisplay;
  final String status;
  final String condition;
  final String? conditionLabel;
  final String? coverImage;
  final int? price;
  final bool isBookmarked;
  final bool hasPhoto;
  final int views;
  final String? body;
  final List<String> images;
  final bool isOwner;
  final String? phoneMasked;
  final String? publicUrl;
  final String? sellerId;
  final String? sellerName;
  final double sellerRatingAvg;
  final int sellerRatingCount;
  final String? statusLabel;
  final String? moderationNote;

  bool get isDraft => status == 'draft';
  bool get canSubmit => status == 'draft';
  bool get canRepublish => status == 'hidden' || status == 'expired';
  bool get canEdit => status != 'deleted';

  factory Listing.fromJson(Map<String, dynamic> json) {
    final seller = json['seller'];
    return Listing(
      id: json['id'].toString(),
      title: (json['title'] ?? '').toString(),
      category: (json['category'] ?? '').toString(),
      categoryLabel: (json['category_label'] ?? json['category'] ?? '').toString(),
      city: (json['city'] ?? '').toString(),
      cityLabel: (json['city_label'] ?? json['city'] ?? '').toString(),
      priceDisplay: (json['price_display'] ?? '').toString(),
      status: (json['status'] ?? '').toString(),
      condition: (json['condition'] ?? 'used').toString(),
      conditionLabel: json['condition_label']?.toString(),
      coverImage: json['cover_image']?.toString(),
      price: (json['price'] as num?)?.toInt(),
      isBookmarked: json['is_bookmarked'] == true,
      hasPhoto: json['has_photo'] == true,
      views: (json['views'] as num?)?.toInt() ?? 0,
      body: json['body']?.toString(),
      images: (json['images'] as List?)?.map((e) => e.toString()).toList() ??
          const [],
      isOwner: json['is_owner'] == true,
      phoneMasked: json['phone_masked']?.toString(),
      publicUrl: json['public_url']?.toString(),
      sellerId: seller is Map ? seller['id']?.toString() : null,
      sellerName: seller is Map ? seller['display_name']?.toString() : null,
      sellerRatingAvg: seller is Map
          ? (seller['rating_avg'] as num?)?.toDouble() ?? 0
          : 0,
      sellerRatingCount: seller is Map
          ? (seller['rating_count'] as num?)?.toInt() ?? 0
          : 0,
      statusLabel: json['status_label']?.toString(),
      moderationNote: json['moderation_note']?.toString(),
    );
  }

  Listing copyWith({bool? isBookmarked}) {
    return Listing(
      id: id,
      title: title,
      category: category,
      categoryLabel: categoryLabel,
      city: city,
      cityLabel: cityLabel,
      priceDisplay: priceDisplay,
      status: status,
      condition: condition,
      conditionLabel: conditionLabel,
      coverImage: coverImage,
      price: price,
      isBookmarked: isBookmarked ?? this.isBookmarked,
      hasPhoto: hasPhoto,
      views: views,
      body: body,
      images: images,
      isOwner: isOwner,
      phoneMasked: phoneMasked,
      publicUrl: publicUrl,
      sellerId: sellerId,
      sellerName: sellerName,
      sellerRatingAvg: sellerRatingAvg,
      sellerRatingCount: sellerRatingCount,
      statusLabel: statusLabel,
      moderationNote: moderationNote,
    );
  }
}

class Category {
  Category({required this.slug, required this.label, this.icon});

  final String slug;
  final String label;
  final String? icon;

  factory Category.fromJson(Map<String, dynamic> json) {
    return Category(
      slug: json['slug'].toString(),
      label: (json['label'] ?? json['slug']).toString(),
      icon: json['icon']?.toString(),
    );
  }
}

class City {
  City({required this.slug, required this.label});

  final String slug;
  final String label;

  factory City.fromJson(Map<String, dynamic> json) {
    return City(
      slug: json['slug'].toString(),
      label: (json['label'] ?? json['slug']).toString(),
    );
  }
}

class Conversation {
  Conversation({
    required this.id,
    required this.updatedAt,
    this.postTitle,
    this.postId,
    this.postCoverImage,
    this.postCityLabel,
    this.postPriceDisplay,
    this.otherUserName,
    this.otherUserId,
    this.lastMessage,
    this.unreadCount = 0,
    this.dealConfirmedByMe = false,
    this.dealConfirmedByOther = false,
    this.bothDealConfirmed = false,
    this.canConfirmDeal = false,
    this.canReviewSeller = false,
    this.hasExistingReview = false,
    this.reviewUnlockAt,
    this.reviewViaTimeout = false,
  });

  final String id;
  final DateTime? updatedAt;
  final String? postTitle;
  final String? postId;
  final String? postCoverImage;
  final String? postCityLabel;
  final String? postPriceDisplay;
  final String? otherUserName;
  final String? otherUserId;
  final String? lastMessage;
  final int unreadCount;
  final bool dealConfirmedByMe;
  final bool dealConfirmedByOther;
  final bool bothDealConfirmed;
  final bool canConfirmDeal;
  final bool canReviewSeller;
  final bool hasExistingReview;
  final DateTime? reviewUnlockAt;
  final bool reviewViaTimeout;

  factory Conversation.fromJson(Map<String, dynamic> json) {
    final post = json['post'];
    final other = json['other_user'];
    return Conversation(
      id: json['id'].toString(),
      updatedAt: DateTime.tryParse((json['updated_at'] ?? '').toString()),
      postTitle: post is Map ? post['title']?.toString() : null,
      postId: post is Map ? post['id']?.toString() : null,
      postCoverImage: post is Map ? post['cover_image']?.toString() : null,
      postCityLabel: post is Map ? post['city_label']?.toString() : null,
      postPriceDisplay: post is Map ? post['price_display']?.toString() : null,
      otherUserName: other is Map ? other['display_name']?.toString() : null,
      otherUserId: json['other_user_id']?.toString() ??
          (other is Map ? other['id']?.toString() : null),
      lastMessage:
          (json['last_message_body'] ?? json['last_message'] ?? '').toString(),
      unreadCount: (json['unread_count'] as num?)?.toInt() ?? 0,
      dealConfirmedByMe: json['deal_confirmed_by_me'] == true,
      dealConfirmedByOther: json['deal_confirmed_by_other'] == true,
      bothDealConfirmed: json['both_deal_confirmed'] == true,
      canConfirmDeal: json['can_confirm_deal'] == true,
      canReviewSeller: json['can_review_seller'] == true,
      hasExistingReview: json['has_existing_review'] == true,
      reviewUnlockAt:
          DateTime.tryParse((json['review_unlock_at'] ?? '').toString()),
      reviewViaTimeout: json['review_via_timeout'] == true,
    );
  }
}

class ChatMessage {
  ChatMessage({
    required this.id,
    required this.body,
    required this.isMine,
    required this.createdAt,
    this.imageUrl,
  });

  final String id;
  final String body;
  final bool isMine;
  final DateTime? createdAt;
  final String? imageUrl;

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      id: json['id'].toString(),
      body: (json['body'] ?? '').toString(),
      isMine: json['is_mine'] == true,
      createdAt: DateTime.tryParse((json['created_at'] ?? '').toString()),
      imageUrl: json['image_url']?.toString(),
    );
  }
}

class PushPreferences {
  PushPreferences({
    this.messagesEnabled = true,
    this.listingsEnabled = true,
    this.systemEnabled = true,
    this.marketingEnabled = false,
  });

  final bool messagesEnabled;
  final bool listingsEnabled;
  final bool systemEnabled;
  final bool marketingEnabled;

  factory PushPreferences.fromJson(Map<String, dynamic> json) {
    return PushPreferences(
      messagesEnabled: json['messages_enabled'] != false,
      listingsEnabled: json['listings_enabled'] != false,
      systemEnabled: json['system_enabled'] != false,
      marketingEnabled: json['marketing_enabled'] == true,
    );
  }

  Map<String, dynamic> toJson() => {
        'messages_enabled': messagesEnabled,
        'listings_enabled': listingsEnabled,
        'system_enabled': systemEnabled,
        'marketing_enabled': marketingEnabled,
      };

  PushPreferences copyWith({
    bool? messagesEnabled,
    bool? listingsEnabled,
    bool? systemEnabled,
    bool? marketingEnabled,
  }) {
    return PushPreferences(
      messagesEnabled: messagesEnabled ?? this.messagesEnabled,
      listingsEnabled: listingsEnabled ?? this.listingsEnabled,
      systemEnabled: systemEnabled ?? this.systemEnabled,
      marketingEnabled: marketingEnabled ?? this.marketingEnabled,
    );
  }
}

class Paginated<T> {
  Paginated({
    required this.count,
    required this.results,
    this.next,
  });

  final int count;
  final List<T> results;
  final String? next;

  bool get hasMore => next != null && next!.isNotEmpty;
}
