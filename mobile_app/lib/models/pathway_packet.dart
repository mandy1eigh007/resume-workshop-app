/// Model for Stand-Out Pathway Packet with trade-specific sections
class PathwayPacket {
  final String id;
  final String studentName;
  final Trade trade;
  final List<String> reflections;
  final List<String> uploadedContentIds; // References to artifacts
  final TradeSpecificSection tradeSection;
  final DateTime createdAt;
  final DateTime updatedAt;

  PathwayPacket({
    required this.id,
    required this.studentName,
    required this.trade,
    required this.reflections,
    required this.uploadedContentIds,
    required this.tradeSection,
    required this.createdAt,
    required this.updatedAt,
  });

  Map<String, dynamic> toJson() => {
    'id': id,
    'studentName': studentName,
    'trade': trade.toString(),
    'reflections': reflections,
    'uploadedContentIds': uploadedContentIds,
    'tradeSection': tradeSection.toJson(),
    'createdAt': createdAt.toIso8601String(),
    'updatedAt': updatedAt.toIso8601String(),
  };

  factory PathwayPacket.fromJson(Map<String, dynamic> json) => PathwayPacket(
    id: json['id'],
    studentName: json['studentName'],
    trade: Trade.values.firstWhere((e) => e.toString() == json['trade']),
    reflections: List<String>.from(json['reflections']),
    uploadedContentIds: List<String>.from(json['uploadedContentIds']),
    tradeSection: TradeSpecificSection.fromJson(json['tradeSection']),
    createdAt: DateTime.parse(json['createdAt']),
    updatedAt: DateTime.parse(json['updatedAt']),
  );
}

/// Available trades based on Seattle Tri-County programs
enum Trade {
  electrical,           // Inside, Residential, Limited Energy
  pipeTrades,          // Plumber, Steamfitter, HVAC-R
  outsidePower,        // Power Line
  powerLineClearance,  // Tree Trimmer
  carpentry,
  ironworkers,
  laborers,
  operators,
  sheetMetal,
}

extension TradeExtension on Trade {
  String get displayName {
    switch (this) {
      case Trade.electrical:
        return 'Electrical (Inside, Residential, Limited Energy)';
      case Trade.pipeTrades:
        return 'Pipe Trades / HVAC-R';
      case Trade.outsidePower:
        return 'Outside Power';
      case Trade.powerLineClearance:
        return 'Power Line Clearance Tree Trimmer';
      case Trade.carpentry:
        return 'Carpentry';
      case Trade.ironworkers:
        return 'Ironworkers';
      case Trade.laborers:
        return 'Laborers';
      case Trade.operators:
        return 'Operating Engineers';
      case Trade.sheetMetal:
        return 'Sheet Metal';
    }
  }

  List<String> get standOutMoves {
    switch (this) {
      case Trade.electrical:
        return [
          'Documented tool time: conduit measuring, simple bends, layout, wire pulls',
          'Low-voltage crossover: labeling, continuity testing',
          'Holdover jobs: warehouse/runner at ECs, prefab shop, material handler',
        ];
      case Trade.pipeTrades:
        return [
          'EPA 608 (Type I/II/III or Universal)',
          'Shop helper/parts counter; sheet-metal fab helper',
          'Maintenance tech trainee',
        ];
      case Trade.outsidePower:
      case Trade.powerLineClearance:
        return [
          'CDL-B/A progress, ISA coursework exposure',
          'Ground operations: rigging hand signals, staging, chipper safety',
          'Pesticide Laws & Safety (Right-of-Way), First Aid/CPR',
        ];
      default:
        return [
          'OSHA-30 for crew leads',
          'Forklift certification with employer evaluation',
          'Material handler or prefab helper roles',
        ];
    }
  }

  String get programRealityCheck {
    switch (this) {
      case Trade.electrical:
        return 'Inside Wire apprenticeship ~8,000 OJT + ~1,000 classroom hours before WA (01) exam. Expect algebra and steady attendance.';
      case Trade.pipeTrades:
        return 'Multiple programs with classroom + OJT; math, brazing/soldering foundations, and safe handling are emphasized.';
      case Trade.outsidePower:
      case Trade.powerLineClearance:
        return 'Applications are typically ranked monthly; extra points for documented skills/credentials.';
      default:
        return 'Check specific program requirements and application timelines.';
    }
  }
}

/// Trade-specific section for pathway packet
class TradeSpecificSection {
  final Trade trade;
  final String programRealityCheck;
  final List<String> standOutStack;
  final List<String> evidenceBullets;
  final List<String> studyCues;

  TradeSpecificSection({
    required this.trade,
    required this.programRealityCheck,
    required this.standOutStack,
    required this.evidenceBullets,
    required this.studyCues,
  });

  Map<String, dynamic> toJson() => {
    'trade': trade.toString(),
    'programRealityCheck': programRealityCheck,
    'standOutStack': standOutStack,
    'evidenceBullets': evidenceBullets,
    'studyCues': studyCues,
  };

  factory TradeSpecificSection.fromJson(Map<String, dynamic> json) =>
      TradeSpecificSection(
        trade: Trade.values.firstWhere((e) => e.toString() == json['trade']),
        programRealityCheck: json['programRealityCheck'],
        standOutStack: List<String>.from(json['standOutStack']),
        evidenceBullets: List<String>.from(json['evidenceBullets']),
        studyCues: List<String>.from(json['studyCues']),
      );
}
