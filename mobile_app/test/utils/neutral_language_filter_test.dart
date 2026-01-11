import 'package:flutter_test/flutter_test.dart';
import 'package:resume_workshop_mobile/utils/neutral_language_filter.dart';

void main() {
  group('Neutral Language Filter Tests', () {
    test('Filters union terminology', () {
      final text = 'Apply to union apprenticeship program';
      final filtered = NeutralLanguageFilter.filter(text);
      
      expect(filtered.contains('union'), false);
      expect(filtered.contains('registered apprenticeship'), true);
    });

    test('Filters non-union terminology', () {
      final text = 'Work with non-union contractors';
      final filtered = NeutralLanguageFilter.filter(text);
      
      expect(filtered.contains('non-union'), false);
      expect(filtered.contains('contractor'), true);
    });

    test('Detects banned terms in text', () {
      final text = 'This is a union shop with union members';
      final hasBanned = NeutralLanguageFilter.containsBannedTerms(text);
      
      expect(hasBanned, true);
    });

    test('Does not flag neutral text', () {
      final text = 'Apply to registered apprenticeship programs in construction';
      final hasBanned = NeutralLanguageFilter.containsBannedTerms(text);
      
      expect(hasBanned, false);
    });

    test('Finds specific banned terms', () {
      final text = 'Join the union and support collective bargaining';
      final bannedTerms = NeutralLanguageFilter.findBannedTerms(text);
      
      expect(bannedTerms.isNotEmpty, true);
      expect(bannedTerms.contains('union'), true);
      expect(bannedTerms.contains('collective bargaining'), true);
    });

    test('Replaces union job with construction job', () {
      final text = 'Looking for a union job in electrical';
      final filtered = NeutralLanguageFilter.filter(text);
      
      expect(filtered.contains('construction job'), true);
      expect(filtered.contains('union job'), false);
    });

    test('Handles multiple banned terms in one sentence', () {
      final text = 'The union shop offers union cards to union members';
      final filtered = NeutralLanguageFilter.filter(text);
      
      expect(filtered.contains('union'), false);
    });

    test('Preserves non-banned content', () {
      final text = 'Complete OSHA-10 and apply to registered apprenticeship programs';
      final filtered = NeutralLanguageFilter.filter(text);
      
      expect(filtered, text); // Should be unchanged
    });
  });
}
