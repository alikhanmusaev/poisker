class ApiException implements Exception {
  ApiException({
    required this.message,
    this.code = 'error',
    this.statusCode,
    this.fields = const {},
  });

  final String message;
  final String code;
  final int? statusCode;
  final Map<String, List<String>> fields;

  /// Best user-facing text (prefers non_field_errors from DRF).
  String get displayMessage {
    final nfe = fields['non_field_errors'];
    if (nfe != null && nfe.isNotEmpty) return nfe.first;
    for (final entry in fields.entries) {
      if (entry.key == 'non_field_errors') continue;
      if (entry.value.isNotEmpty) return entry.value.first;
    }
    return message;
  }

  String get fieldSummary {
    if (fields.isEmpty) return displayMessage;
    final parts = <String>[];
    fields.forEach((key, value) {
      if (key == 'non_field_errors') return;
      if (value.isEmpty) return;
      parts.add(value.join(', '));
    });
    if (parts.isEmpty) return displayMessage;
    if (displayMessage == message || displayMessage == 'Проверьте введённые данные') {
      return parts.join('\n');
    }
    return '$displayMessage\n${parts.join('\n')}';
  }

  String? fieldError(String key) {
    final direct = fields[key];
    if (direct != null && direct.isNotEmpty) return direct.first;
    // Common aliases between API snake_case and forms.
    final aliases = {
      'displayName': 'display_name',
      'name': 'display_name',
    };
    final mapped = aliases[key];
    if (mapped != null) {
      final v = fields[mapped];
      if (v != null && v.isNotEmpty) return v.first;
    }
    return null;
  }

  bool get isEmailVerification =>
      displayMessage.toLowerCase().contains('подтвердите email') ||
      displayMessage.toLowerCase().contains('подтвердить email');

  bool get isNetwork => code == 'network';

  bool get isRateLimited => code == 'rate_limited' || statusCode == 429;

  @override
  String toString() => displayMessage;
}

class ApiConfig {
  static const baseUrl = 'https://poisker.ru/api/v1/';
  static const siteUrl = 'https://poisker.ru/';
  static const privacyUrl = 'https://poisker.ru/privacy';
  static const termsUrl = 'https://poisker.ru/terms';
  static const guidelinesUrl = 'https://poisker.ru/guidelines';
}
