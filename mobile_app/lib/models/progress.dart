/// Model for progress tracking (interviews, rank movement)
class ProgressTracker {
  final String id;
  final String studentName;
  final List<InterviewRecord> interviews;
  final List<RankMovement> rankHistory;
  final Map<String, ApplicationStatus> applications;
  final DateTime createdAt;
  final DateTime updatedAt;

  ProgressTracker({
    required this.id,
    required this.studentName,
    required this.interviews,
    required this.rankHistory,
    required this.applications,
    required this.createdAt,
    required this.updatedAt,
  });

  int get totalInterviews => interviews.length;
  
  int get pendingApplications => applications.values
      .where((status) => status == ApplicationStatus.pending)
      .length;
  
  RankMovement? get currentRank => rankHistory.isNotEmpty 
      ? rankHistory.last 
      : null;

  Map<String, dynamic> toJson() => {
    'id': id,
    'studentName': studentName,
    'interviews': interviews.map((e) => e.toJson()).toList(),
    'rankHistory': rankHistory.map((e) => e.toJson()).toList(),
    'applications': applications.map((k, v) => MapEntry(k, v.toString())),
    'createdAt': createdAt.toIso8601String(),
    'updatedAt': updatedAt.toIso8601String(),
  };

  factory ProgressTracker.fromJson(Map<String, dynamic> json) =>
      ProgressTracker(
        id: json['id'],
        studentName: json['studentName'],
        interviews: (json['interviews'] as List)
            .map((e) => InterviewRecord.fromJson(e))
            .toList(),
        rankHistory: (json['rankHistory'] as List)
            .map((e) => RankMovement.fromJson(e))
            .toList(),
        applications: (json['applications'] as Map<String, dynamic>).map(
          (k, v) => MapEntry(
            k,
            ApplicationStatus.values.firstWhere((e) => e.toString() == v),
          ),
        ),
        createdAt: DateTime.parse(json['createdAt']),
        updatedAt: DateTime.parse(json['updatedAt']),
      );
}

/// Interview record
class InterviewRecord {
  final String id;
  final String company;
  final String position;
  final DateTime scheduledDate;
  final InterviewType type;
  final InterviewOutcome? outcome;
  final String? notes;
  final DateTime createdAt;

  InterviewRecord({
    required this.id,
    required this.company,
    required this.position,
    required this.scheduledDate,
    required this.type,
    this.outcome,
    this.notes,
    required this.createdAt,
  });

  Map<String, dynamic> toJson() => {
    'id': id,
    'company': company,
    'position': position,
    'scheduledDate': scheduledDate.toIso8601String(),
    'type': type.toString(),
    'outcome': outcome?.toString(),
    'notes': notes,
    'createdAt': createdAt.toIso8601String(),
  };

  factory InterviewRecord.fromJson(Map<String, dynamic> json) =>
      InterviewRecord(
        id: json['id'],
        company: json['company'],
        position: json['position'],
        scheduledDate: DateTime.parse(json['scheduledDate']),
        type: InterviewType.values.firstWhere((e) => e.toString() == json['type']),
        outcome: json['outcome'] != null
            ? InterviewOutcome.values.firstWhere((e) => e.toString() == json['outcome'])
            : null,
        notes: json['notes'],
        createdAt: DateTime.parse(json['createdAt']),
      );
}

enum InterviewType {
  phone,
  inPerson,
  video,
  group,
}

enum InterviewOutcome {
  pending,
  advanced,
  offered,
  declined,
  noResponse,
}

/// Rank movement tracking for apprenticeship programs
class RankMovement {
  final String programName;
  final int rank;
  final int totalApplicants;
  final DateTime recordedAt;
  final String? notes;

  RankMovement({
    required this.programName,
    required this.rank,
    required this.totalApplicants,
    required this.recordedAt,
    this.notes,
  });

  double get percentile => (1 - (rank / totalApplicants)) * 100;

  Map<String, dynamic> toJson() => {
    'programName': programName,
    'rank': rank,
    'totalApplicants': totalApplicants,
    'recordedAt': recordedAt.toIso8601String(),
    'notes': notes,
  };

  factory RankMovement.fromJson(Map<String, dynamic> json) => RankMovement(
    programName: json['programName'],
    rank: json['rank'],
    totalApplicants: json['totalApplicants'],
    recordedAt: DateTime.parse(json['recordedAt']),
    notes: json['notes'],
  );
}

enum ApplicationStatus {
  pending,
  submitted,
  underReview,
  interviewed,
  offered,
  accepted,
  declined,
  rejected,
}
