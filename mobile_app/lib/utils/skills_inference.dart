import '../models/resume.dart';

/// Skills inference utility based on job history and bullets
class SkillsInference {
  // Mapping of keywords to inferred skills
  static const Map<String, List<String>> _skillKeywords = {
    // Electrical
    'conduit': ['Conduit Installation', 'EMT/Rigid Conduit', 'Electrical Layout'],
    'wire': ['Wire Pulling', 'Conductor Installation', 'Cable Management'],
    'circuit': ['Circuit Installation', 'Electrical Systems', 'Panel Work'],
    'voltage': ['Low Voltage', 'Electrical Testing', 'Safety Protocols'],
    'termination': ['Terminations', 'Electrical Connections', 'Quality Control'],
    
    // Pipe Trades / HVAC
    'pipe': ['Pipe Installation', 'Pipefitting', 'Layout & Measurement'],
    'brazing': ['Brazing', 'Soldering', 'Welding Basics'],
    'hvac': ['HVAC Systems', 'Climate Control', 'Mechanical Systems'],
    'refrigeration': ['Refrigeration', 'EPA 608', 'HVAC-R'],
    'leak': ['Leak Detection', 'Testing & Commissioning', 'Quality Assurance'],
    
    // General Construction
    'safety': ['Safety Compliance', 'OSHA Standards', 'PPE Usage'],
    'osha': ['OSHA Training', 'Workplace Safety', 'Hazard Recognition'],
    'forklift': ['Forklift Operation', 'Material Handling', 'Equipment Safety'],
    'blueprint': ['Blueprint Reading', 'Plan Interpretation', 'Technical Documentation'],
    'measure': ['Measurement & Layout', 'Precision Work', 'Quality Standards'],
    
    // Power Line / Tree Work
    'rigging': ['Rigging', 'Load Handling', 'Signal Communication'],
    'climbing': ['Climbing', 'Height Work', 'Fall Protection'],
    'chainsaw': ['Chainsaw Operation', 'Equipment Maintenance', 'Safety Protocols'],
    'cdl': ['CDL License', 'Vehicle Operation', 'Transportation'],
    
    // Soft Skills & Work Habits
    'team': ['Teamwork', 'Communication', 'Collaboration'],
    'maintained': ['Equipment Maintenance', 'Preventive Maintenance', 'Record Keeping'],
    'documented': ['Documentation', 'Record Keeping', 'Attention to Detail'],
    'verified': ['Quality Control', 'Verification', 'Inspection'],
    'supervised': ['Supervision', 'Leadership', 'Training Others'],
  };

  /// Infer skills from a list of measurable bullets
  static List<String> inferFromBullets(List<MeasurableBullet> bullets) {
    final Set<String> inferredSkills = {};

    for (final bullet in bullets) {
      final fullText = bullet.fullText.toLowerCase();
      
      // Check each keyword mapping
      for (final entry in _skillKeywords.entries) {
        if (fullText.contains(entry.key)) {
          inferredSkills.addAll(entry.value);
        }
      }
    }

    return inferredSkills.toList()..sort();
  }

  /// Suggest skills from text content
  static List<String> suggestFromText(String text) {
    final Set<String> suggestedSkills = {};
    final lowerText = text.toLowerCase();

    for (final entry in _skillKeywords.entries) {
      if (lowerText.contains(entry.key)) {
        suggestedSkills.addAll(entry.value);
      }
    }

    return suggestedSkills.toList()..sort();
  }

  /// Get canon/quick-add skills by trade
  static List<String> getCanonSkillsByTrade(String trade) {
    final tradeUpper = trade.toUpperCase();
    
    if (tradeUpper.contains('ELECTRIC')) {
      return [
        'Conduit Installation',
        'Wire Pulling & Terminations',
        'Blueprint Reading',
        'Electrical Testing',
        'OSHA-10 Outreach',
        'Hand & Power Tools',
        'Safety Compliance',
        'Team Communication',
      ];
    } else if (tradeUpper.contains('PIPE') || tradeUpper.contains('HVAC')) {
      return [
        'Pipe Threading & Cutting',
        'Brazing & Soldering',
        'EPA 608 Certification',
        'Blueprint Reading',
        'HVAC Systems',
        'Leak Testing',
        'Safety Protocols',
        'Equipment Maintenance',
      ];
    } else if (tradeUpper.contains('POWER') || tradeUpper.contains('LINE')) {
      return [
        'Rigging & Signaling',
        'Climbing & Height Work',
        'Equipment Operation',
        'Safety Awareness',
        'CDL License',
        'First Aid/CPR',
        'Right-of-Way Practices',
        'Team Coordination',
      ];
    } else {
      return [
        'Safety Compliance',
        'Blueprint Reading',
        'Hand & Power Tools',
        'Material Handling',
        'Quality Control',
        'Team Communication',
        'OSHA Training',
        'Equipment Maintenance',
      ];
    }
  }
}
