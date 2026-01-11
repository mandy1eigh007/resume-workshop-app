import 'package:flutter_test/flutter_test.dart';
import 'package:resume_workshop_mobile/utils/skills_inference.dart';
import 'package:resume_workshop_mobile/models/resume.dart';

void main() {
  group('Skills Inference Tests', () {
    test('Infers electrical skills from conduit-related bullets', () {
      final bullets = [
        MeasurableBullet(
          id: '1',
          action: 'Measured and marked',
          quantityOrTool: '20+ EMT runs',
          safetyQuality: 'verified offsets with level',
          verification: 'staged hardware by circuit',
        ),
      ];

      final skills = SkillsInference.inferFromBullets(bullets);
      
      expect(skills.isNotEmpty, true);
      expect(skills.any((s) => s.contains('Conduit')), true);
    });

    test('Infers HVAC skills from brazing-related bullets', () {
      final bullets = [
        MeasurableBullet(
          id: '1',
          action: 'Assisted',
          quantityOrTool: 'brazing setups (nitrogen purge)',
          safetyQuality: 'leak checks and recovery under supervision',
          verification: 'logged pressures/temps',
        ),
      ];

      final skills = SkillsInference.inferFromBullets(bullets);
      
      expect(skills.isNotEmpty, true);
      expect(skills.any((s) => s.contains('Brazing') || s.contains('HVAC')), true);
    });

    test('Infers safety skills from OSHA-related text', () {
      final text = 'Completed OSHA-10 training and maintained safety protocols on site';
      final skills = SkillsInference.suggestFromText(text);
      
      expect(skills.isNotEmpty, true);
      expect(skills.any((s) => s.contains('OSHA') || s.contains('Safety')), true);
    });

    test('Returns canon skills for Electrical trade', () {
      final skills = SkillsInference.getCanonSkillsByTrade('ELECTRICAL');
      
      expect(skills.isNotEmpty, true);
      expect(skills.contains('Conduit Installation'), true);
      expect(skills.contains('Wire Pulling & Terminations'), true);
      expect(skills.contains('Blueprint Reading'), true);
    });

    test('Returns canon skills for Pipe Trades', () {
      final skills = SkillsInference.getCanonSkillsByTrade('PIPE TRADES');
      
      expect(skills.isNotEmpty, true);
      expect(skills.contains('Pipe Threading & Cutting'), true);
      expect(skills.contains('Brazing & Soldering'), true);
      expect(skills.contains('EPA 608 Certification'), true);
    });

    test('Returns general skills for unknown trade', () {
      final skills = SkillsInference.getCanonSkillsByTrade('UNKNOWN');
      
      expect(skills.isNotEmpty, true);
      expect(skills.contains('Safety Compliance'), true);
      expect(skills.contains('Blueprint Reading'), true);
    });
  });
}
