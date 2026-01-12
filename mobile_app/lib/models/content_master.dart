/// Models for CONTENT_MASTER.md parsed content
class ContentMaster {
  final Map<String, TradeObjectives> objectives;
  final Map<String, List<String>> roleBullets;
  final SkillsCanon skillsCanon;
  final List<String> certifications;
  final Map<String, List<CredentialBadge>> credentialBadges;
  final List<ArtifactTemplate> artifactTemplates;

  ContentMaster({
    required this.objectives,
    required this.roleBullets,
    required this.skillsCanon,
    required this.certifications,
    required this.credentialBadges,
    required this.artifactTemplates,
  });

  factory ContentMaster.empty() {
    return ContentMaster(
      objectives: {},
      roleBullets: {},
      skillsCanon: SkillsCanon.empty(),
      certifications: [],
      credentialBadges: {},
      artifactTemplates: [],
    );
  }
}

/// Trade-specific objectives
class TradeObjectives {
  final String trade;
  final List<String> apprenticeshipObjectives;
  final List<String> jobObjectives;

  TradeObjectives({
    required this.trade,
    required this.apprenticeshipObjectives,
    required this.jobObjectives,
  });

  List<String> get all => [
        ...apprenticeshipObjectives,
        ...jobObjectives,
      ];
}

/// Skills organized into three buckets
class SkillsCanon {
  final List<String> transferable;
  final List<String> jobSpecific;
  final List<String> selfManagement;

  SkillsCanon({
    required this.transferable,
    required this.jobSpecific,
    required this.selfManagement,
  });

  List<String> get all => [
        ...transferable,
        ...jobSpecific,
        ...selfManagement,
      ];

  factory SkillsCanon.empty() {
    return SkillsCanon(
      transferable: [],
      jobSpecific: [],
      selfManagement: [],
    );
  }
}

/// Credential micro-badge with resume phrase and proof requirements
class CredentialBadge {
  final String name;
  final String resumePhrase;
  final String proof;

  CredentialBadge({
    required this.name,
    required this.resumePhrase,
    required this.proof,
  });
}

/// Artifact template for evidence tracking
class ArtifactTemplate {
  final String name;
  final String description;
  final List<String> fields;

  ArtifactTemplate({
    required this.name,
    required this.description,
    required this.fields,
  });
}
