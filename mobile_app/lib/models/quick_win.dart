/// Model for Quick Win action items (≤2 weeks)
class QuickWin {
  final String id;
  final String title;
  final String description;
  final QuickWinCategory category;
  final QuickWinPriority priority;
  final DateTime deadline; // Must be ≤2 weeks from creation
  final QuickWinStatus status;
  final List<String> actionSteps;
  final DateTime createdAt;
  final DateTime? completedAt;

  QuickWin({
    required this.id,
    required this.title,
    required this.description,
    required this.category,
    required this.priority,
    required this.deadline,
    required this.status,
    required this.actionSteps,
    required this.createdAt,
    this.completedAt,
  });

  bool get isOverdue => DateTime.now().isAfter(deadline) && status != QuickWinStatus.completed;
  
  int get daysRemaining => deadline.difference(DateTime.now()).inDays;

  Map<String, dynamic> toJson() => {
    'id': id,
    'title': title,
    'description': description,
    'category': category.toString(),
    'priority': priority.toString(),
    'deadline': deadline.toIso8601String(),
    'status': status.toString(),
    'actionSteps': actionSteps,
    'createdAt': createdAt.toIso8601String(),
    'completedAt': completedAt?.toIso8601String(),
  };

  factory QuickWin.fromJson(Map<String, dynamic> json) => QuickWin(
    id: json['id'],
    title: json['title'],
    description: json['description'],
    category: QuickWinCategory.values.firstWhere(
      (e) => e.toString() == json['category'],
    ),
    priority: QuickWinPriority.values.firstWhere(
      (e) => e.toString() == json['priority'],
    ),
    deadline: DateTime.parse(json['deadline']),
    status: QuickWinStatus.values.firstWhere(
      (e) => e.toString() == json['status'],
    ),
    actionSteps: List<String>.from(json['actionSteps']),
    createdAt: DateTime.parse(json['createdAt']),
    completedAt: json['completedAt'] != null 
        ? DateTime.parse(json['completedAt']) 
        : null,
  );
}

enum QuickWinCategory {
  certification,    // Get/renew certifications
  documentation,   // Gather evidence, update resume
  networking,      // Connect with programs/employers
  skillBuilding,   // Practice or training
  application,     // Submit applications
}

enum QuickWinPriority {
  high,
  medium,
  low,
}

enum QuickWinStatus {
  notStarted,
  inProgress,
  completed,
  blocked,
}
