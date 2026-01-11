/// Model for artifact uploads with audit trail
class Artifact {
  final String id;
  final String name;
  final ArtifactType type;
  final String filePath;
  final int fileSize;
  final DateTime uploadedAt;
  final String uploadedBy;
  final String? description;
  final List<AuditEntry> auditTrail;

  Artifact({
    required this.id,
    required this.name,
    required this.type,
    required this.filePath,
    required this.fileSize,
    required this.uploadedAt,
    required this.uploadedBy,
    this.description,
    this.auditTrail = const [],
  });

  Map<String, dynamic> toJson() => {
    'id': id,
    'name': name,
    'type': type.toString(),
    'filePath': filePath,
    'fileSize': fileSize,
    'uploadedAt': uploadedAt.toIso8601String(),
    'uploadedBy': uploadedBy,
    'description': description,
    'auditTrail': auditTrail.map((e) => e.toJson()).toList(),
  };

  factory Artifact.fromJson(Map<String, dynamic> json) => Artifact(
    id: json['id'],
    name: json['name'],
    type: ArtifactType.values.firstWhere(
      (e) => e.toString() == json['type'],
    ),
    filePath: json['filePath'],
    fileSize: json['fileSize'],
    uploadedAt: DateTime.parse(json['uploadedAt']),
    uploadedBy: json['uploadedBy'],
    description: json['description'],
    auditTrail: (json['auditTrail'] as List)
        .map((e) => AuditEntry.fromJson(e))
        .toList(),
  );
}

enum ArtifactType {
  document,  // PDF, DOCX, etc.
  photo,     // Photos (no faces)
  certificate,
  other,
}

/// Audit trail entry for artifacts
class AuditEntry {
  final String action;
  final DateTime timestamp;
  final String performedBy;
  final String? details;

  AuditEntry({
    required this.action,
    required this.timestamp,
    required this.performedBy,
    this.details,
  });

  Map<String, dynamic> toJson() => {
    'action': action,
    'timestamp': timestamp.toIso8601String(),
    'performedBy': performedBy,
    'details': details,
  };

  factory AuditEntry.fromJson(Map<String, dynamic> json) => AuditEntry(
    action: json['action'],
    timestamp: DateTime.parse(json['timestamp']),
    performedBy: json['performedBy'],
    details: json['details'],
  );
}
