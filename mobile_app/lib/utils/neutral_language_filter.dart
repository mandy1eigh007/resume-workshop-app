/// Neutral language filter to remove union/non-union terminology
class NeutralLanguageFilter {
  // Banned union/non-union terms
  static const List<String> _bannedTerms = [
    'union',
    'non-union',
    'union shop',
    'open shop',
    'closed shop',
    'union card',
    'right to work',
    'prevailing wage',
    'collective bargaining',
    'union rep',
    'union member',
    'non-union contractor',
    'merit shop',
  ];

  // Neutral replacements
  static const Map<String, String> _replacements = {
    'union apprenticeship': 'registered apprenticeship',
    'union program': 'apprenticeship program',
    'union contractor': 'contractor',
    'non-union contractor': 'contractor',
    'union job': 'construction job',
    'non-union job': 'construction job',
  };

  /// Filter text to remove union/non-union language
  static String filter(String text) {
    String filtered = text;

    // Apply replacements first
    _replacements.forEach((banned, neutral) {
      final regex = RegExp(banned, caseSensitive: false);
      filtered = filtered.replaceAll(regex, neutral);
    });

    // Remove remaining banned terms
    for (final term in _bannedTerms) {
      final regex = RegExp('\\b$term\\b', caseSensitive: false);
      filtered = filtered.replaceAll(regex, '[REMOVED]');
    }

    // Clean up multiple spaces and [REMOVED] markers
    filtered = filtered.replaceAll(RegExp(r'\s+'), ' ');
    filtered = filtered.replaceAll(RegExp(r'\[REMOVED\]\s*'), '');
    
    return filtered.trim();
  }

  /// Check if text contains banned terms
  static bool containsBannedTerms(String text) {
    final lowerText = text.toLowerCase();
    return _bannedTerms.any((term) => lowerText.contains(term));
  }

  /// Get list of banned terms found in text
  static List<String> findBannedTerms(String text) {
    final lowerText = text.toLowerCase();
    return _bannedTerms.where((term) => lowerText.contains(term)).toList();
  }
}
