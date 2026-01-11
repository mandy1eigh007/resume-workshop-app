import 'package:flutter_test/flutter_test.dart';
import 'package:resume_workshop_mobile/models/resume.dart';

void main() {
  group('Resume Model Tests', () {
    test('Resume can be created with required fields', () {
      final resume = Resume(
        id: '1',
        name: 'John Doe',
        email: 'john@example.com',
        phone: '(206) 555-1234',
        city: 'Seattle',
        state: 'WA',
        objective: 'Seeking electrical apprenticeship',
        workHistory: [],
        education: [],
        certifications: [],
        skills: SkillSet(),
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );

      expect(resume.name, 'John Doe');
      expect(resume.email, 'john@example.com');
      expect(resume.state, 'WA');
    });

    test('MeasurableBullet generates correct fullText', () {
      final bullet = MeasurableBullet(
        id: '1',
        action: 'Staged and labeled',
        quantityOrTool: '120+ devices; matched counts to plan sheets',
        safetyQuality: 'maintained clear aisles and PPE',
        verification: 'QC\'d by lead',
      );

      expect(
        bullet.fullText,
        'Staged and labeled 120+ devices; matched counts to plan sheets; maintained clear aisles and PPE; QC\'d by lead',
      );
    });

    test('SkillSet deduplicates skills across categories', () {
      final skillSet = SkillSet(
        suggested: ['Safety Compliance', 'Blueprint Reading'],
        inferred: ['Safety Compliance', 'OSHA Training'],
        quickAdd: ['Blueprint Reading', 'Hand Tools'],
      );

      final allSkills = skillSet.all;
      expect(allSkills.length, 4); // Deduplicated
      expect(allSkills.contains('Safety Compliance'), true);
      expect(allSkills.contains('Blueprint Reading'), true);
      expect(allSkills.contains('OSHA Training'), true);
      expect(allSkills.contains('Hand Tools'), true);
    });
  });

  group('MeasurableBullet Tests', () {
    test('Bullet can infer skills', () {
      final bullet = MeasurableBullet(
        id: '1',
        action: 'Measured and marked',
        quantityOrTool: '20+ EMT runs',
        safetyQuality: 'verified offsets with level',
        verification: 'staged hardware by circuit',
        inferredSkills: ['Conduit Installation', 'Measurement & Layout'],
      );

      expect(bullet.inferredSkills.length, 2);
      expect(bullet.inferredSkills.contains('Conduit Installation'), true);
    });
  });

  group('JSON Serialization Tests', () {
    test('Resume can be serialized and deserialized', () {
      final originalResume = Resume(
        id: '123',
        name: 'Test User',
        email: 'test@example.com',
        phone: '555-1234',
        city: 'Seattle',
        state: 'WA',
        objective: 'Test objective',
        workHistory: [],
        education: [],
        certifications: ['OSHA-10', 'Forklift'],
        skills: SkillSet(
          suggested: ['Safety'],
          inferred: ['Quality Control'],
          quickAdd: ['Blueprint Reading'],
        ),
        createdAt: DateTime(2025, 1, 1),
        updatedAt: DateTime(2025, 1, 1),
      );

      final json = originalResume.toJson();
      final deserializedResume = Resume.fromJson(json);

      expect(deserializedResume.id, originalResume.id);
      expect(deserializedResume.name, originalResume.name);
      expect(deserializedResume.certifications.length, 2);
      expect(deserializedResume.skills.suggested.first, 'Safety');
    });
  });
}
