/// Model representing a resume entry with measurable bullets
class Resume {
  final String id;
  final String name;
  final String email;
  final String phone;
  final String city;
  final String state;
  final String objective;
  final List<WorkExperience> workHistory;
  final List<Education> education;
  final List<String> certifications;
  final SkillSet skills;
  final DateTime createdAt;
  final DateTime updatedAt;

  Resume({
    required this.id,
    required this.name,
    required this.email,
    required this.phone,
    required this.city,
    required this.state,
    required this.objective,
    required this.workHistory,
    required this.education,
    required this.certifications,
    required this.skills,
    required this.createdAt,
    required this.updatedAt,
  });

  Map<String, dynamic> toJson() => {
    'id': id,
    'name': name,
    'email': email,
    'phone': phone,
    'city': city,
    'state': state,
    'objective': objective,
    'workHistory': workHistory.map((e) => e.toJson()).toList(),
    'education': education.map((e) => e.toJson()).toList(),
    'certifications': certifications,
    'skills': skills.toJson(),
    'createdAt': createdAt.toIso8601String(),
    'updatedAt': updatedAt.toIso8601String(),
  };

  factory Resume.fromJson(Map<String, dynamic> json) => Resume(
    id: json['id'],
    name: json['name'],
    email: json['email'],
    phone: json['phone'],
    city: json['city'],
    state: json['state'],
    objective: json['objective'],
    workHistory: (json['workHistory'] as List)
        .map((e) => WorkExperience.fromJson(e))
        .toList(),
    education: (json['education'] as List)
        .map((e) => Education.fromJson(e))
        .toList(),
    certifications: List<String>.from(json['certifications']),
    skills: SkillSet.fromJson(json['skills']),
    createdAt: DateTime.parse(json['createdAt']),
    updatedAt: DateTime.parse(json['updatedAt']),
  );
}

/// Work experience with measurable bullet points
class WorkExperience {
  final String role;
  final String company;
  final String location;
  final String startDate;
  final String endDate;
  final List<MeasurableBullet> bullets;

  WorkExperience({
    required this.role,
    required this.company,
    required this.location,
    required this.startDate,
    required this.endDate,
    required this.bullets,
  });

  Map<String, dynamic> toJson() => {
    'role': role,
    'company': company,
    'location': location,
    'startDate': startDate,
    'endDate': endDate,
    'bullets': bullets.map((e) => e.toJson()).toList(),
  };

  factory WorkExperience.fromJson(Map<String, dynamic> json) => WorkExperience(
    role: json['role'],
    company: json['company'],
    location: json['location'],
    startDate: json['startDate'],
    endDate: json['endDate'],
    bullets: (json['bullets'] as List)
        .map((e) => MeasurableBullet.fromJson(e))
        .toList(),
  );
}

/// Measurable bullet point with action + quantity/tool/spec + safety/quality + verification
class MeasurableBullet {
  final String id;
  final String action;
  final String quantityOrTool;
  final String safetyQuality;
  final String verification;
  final List<String> inferredSkills;

  MeasurableBullet({
    required this.id,
    required this.action,
    required this.quantityOrTool,
    required this.safetyQuality,
    required this.verification,
    this.inferredSkills = const [],
  });

  String get fullText =>
      '$action $quantityOrTool; $safetyQuality; $verification';

  Map<String, dynamic> toJson() => {
    'id': id,
    'action': action,
    'quantityOrTool': quantityOrTool,
    'safetyQuality': safetyQuality,
    'verification': verification,
    'inferredSkills': inferredSkills,
  };

  factory MeasurableBullet.fromJson(Map<String, dynamic> json) =>
      MeasurableBullet(
        id: json['id'],
        action: json['action'],
        quantityOrTool: json['quantityOrTool'],
        safetyQuality: json['safetyQuality'],
        verification: json['verification'],
        inferredSkills: List<String>.from(json['inferredSkills'] ?? []),
      );
}

/// Education entry
class Education {
  final String institution;
  final String degree;
  final String field;
  final String graduationDate;

  Education({
    required this.institution,
    required this.degree,
    required this.field,
    required this.graduationDate,
  });

  Map<String, dynamic> toJson() => {
    'institution': institution,
    'degree': degree,
    'field': field,
    'graduationDate': graduationDate,
  };

  factory Education.fromJson(Map<String, dynamic> json) => Education(
    institution: json['institution'],
    degree: json['degree'],
    field: json['field'],
    graduationDate: json['graduationDate'],
  );
}

/// Skills organized into categories
class SkillSet {
  final List<String> suggested;  // Extracted from text
  final List<String> inferred;   // Inferred from bullets
  final List<String> quickAdd;   // Canon/predefined skills

  SkillSet({
    this.suggested = const [],
    this.inferred = const [],
    this.quickAdd = const [],
  });

  List<String> get all {
    final Set<String> unique = {};
    unique.addAll(suggested);
    unique.addAll(inferred);
    unique.addAll(quickAdd);
    return unique.toList();
  }

  Map<String, dynamic> toJson() => {
    'suggested': suggested,
    'inferred': inferred,
    'quickAdd': quickAdd,
  };

  factory SkillSet.fromJson(Map<String, dynamic> json) => SkillSet(
    suggested: List<String>.from(json['suggested'] ?? []),
    inferred: List<String>.from(json['inferred'] ?? []),
    quickAdd: List<String>.from(json['quickAdd'] ?? []),
  );
}
