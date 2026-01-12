import 'package:flutter/services.dart';
import '../models/content_master.dart';

/// Service to parse and load content from CONTENT_MASTER.md
class ContentMasterService {
  static const String _assetPath = 'CONTENT_MASTER.md';

  /// Load and parse the CONTENT_MASTER.md file
  Future<ContentMaster> loadContent() async {
    try {
      final content = await rootBundle.loadString(_assetPath);
      return _parseContent(content);
    } catch (e) {
      // Return empty content on error with fallback
      return ContentMaster.empty();
    }
  }

  /// Parse the markdown content into structured data
  ContentMaster _parseContent(String content) {
    final lines = content.split('\n');
    
    final objectives = <String, TradeObjectives>{};
    final roleBullets = <String, List<String>>{};
    final certifications = <String>[];
    final credentialBadges = <String, List<CredentialBadge>>{};
    final artifactTemplates = <ArtifactTemplate>[];
    
    // Parse objectives section
    final objectivesMap = _parseObjectivesSection(lines);
    objectives.addAll(objectivesMap);
    
    // Parse role bullets section
    final bulletsMap = _parseRoleBulletsSection(lines);
    roleBullets.addAll(bulletsMap);
    
    // Parse skills canon
    final skillsCanon = _parseSkillsCanon(lines);
    
    // Parse certifications
    final certsList = _parseCertifications(lines);
    certifications.addAll(certsList);
    
    // Parse credential badges
    final badgesMap = _parseCredentialBadges(lines);
    credentialBadges.addAll(badgesMap);
    
    // Parse artifact templates
    final templates = _parseArtifactTemplates(lines);
    artifactTemplates.addAll(templates);
    
    return ContentMaster(
      objectives: objectives,
      roleBullets: roleBullets,
      skillsCanon: skillsCanon,
      certifications: certifications,
      credentialBadges: credentialBadges,
      artifactTemplates: artifactTemplates,
    );
  }

  /// Parse objectives section from CONTENT_MASTER.md
  Map<String, TradeObjectives> _parseObjectivesSection(List<String> lines) {
    final objectives = <String, TradeObjectives>{};
    
    // Find the start of objectives section
    int startIndex = -1;
    for (int i = 0; i < lines.length; i++) {
      if (lines[i].contains('## A) Objective Starters Bank')) {
        startIndex = i;
        break;
      }
    }
    
    if (startIndex == -1) return objectives;
    
    String? currentTrade;
    List<String> apprenticeshipObjectives = [];
    List<String> jobObjectives = [];
    bool inApprenticeshipSection = false;
    bool inJobSection = false;
    
    for (int i = startIndex; i < lines.length; i++) {
      final line = lines[i].trim();
      
      // Stop at next major section
      if (line.startsWith('## B)')) break;
      
      // Detect trade header (### TradeName)
      if (line.startsWith('###') && !line.contains('**')) {
        // Save previous trade if exists
        if (currentTrade != null) {
          objectives[currentTrade] = TradeObjectives(
            trade: currentTrade,
            apprenticeshipObjectives: List.from(apprenticeshipObjectives),
            jobObjectives: List.from(jobObjectives),
          );
        }
        
        // Start new trade
        currentTrade = line.replaceAll('###', '').trim();
        apprenticeshipObjectives = [];
        jobObjectives = [];
        inApprenticeshipSection = false;
        inJobSection = false;
        continue;
      }
      
      // Detect subsections
      if (line.startsWith('**Apprenticeship')) {
        inApprenticeshipSection = true;
        inJobSection = false;
        continue;
      }
      
      if (line.startsWith('**Job')) {
        inApprenticeshipSection = false;
        inJobSection = true;
        continue;
      }
      
      // Parse numbered objectives (e.g., "1. Seeking...")
      if (line.matches(RegExp(r'^\d+\.\s+.+'))) {
        final objective = line.replaceFirst(RegExp(r'^\d+\.\s+'), '');
        if (inApprenticeshipSection) {
          apprenticeshipObjectives.add(objective);
        } else if (inJobSection) {
          jobObjectives.add(objective);
        }
      }
    }
    
    // Save last trade
    if (currentTrade != null) {
      objectives[currentTrade] = TradeObjectives(
        trade: currentTrade,
        apprenticeshipObjectives: apprenticeshipObjectives,
        jobObjectives: jobObjectives,
      );
    }
    
    return objectives;
  }

  /// Parse role bullets section
  Map<String, List<String>> _parseRoleBulletsSection(List<String> lines) {
    final roleBullets = <String, List<String>>{};
    
    // Find the start of role bullets section
    int startIndex = -1;
    for (int i = 0; i < lines.length; i++) {
      if (lines[i].contains('## B) Role → Bullet Bank')) {
        startIndex = i;
        break;
      }
    }
    
    if (startIndex == -1) return roleBullets;
    
    String? currentRole;
    List<String> bullets = [];
    
    for (int i = startIndex; i < lines.length; i++) {
      final line = lines[i].trim();
      
      // Stop at next major section
      if (line.startsWith('## C)')) break;
      
      // Detect role header (e.g., "**Line Cook**")
      if (line.startsWith('**') && line.endsWith('**') && !line.startsWith('***')) {
        // Save previous role if exists
        if (currentRole != null && bullets.isNotEmpty) {
          roleBullets[currentRole] = List.from(bullets);
        }
        
        // Start new role
        currentRole = line.replaceAll('**', '').trim();
        bullets = [];
        continue;
      }
      
      // Parse bullet points (lines starting with *)
      if (line.startsWith('*') && line.length > 2) {
        final bullet = line.replaceFirst('*', '').trim();
        bullets.add(bullet);
      }
    }
    
    // Save last role
    if (currentRole != null && bullets.isNotEmpty) {
      roleBullets[currentRole] = bullets;
    }
    
    return roleBullets;
  }

  /// Parse skills canon section
  SkillsCanon _parseSkillsCanon(List<String> lines) {
    final transferable = <String>[];
    final jobSpecific = <String>[];
    final selfManagement = <String>[];
    
    // Find the start of skills canon section
    int startIndex = -1;
    for (int i = 0; i < lines.length; i++) {
      if (lines[i].contains('## C) Skills Canon')) {
        startIndex = i;
        break;
      }
    }
    
    if (startIndex == -1) return SkillsCanon.empty();
    
    for (int i = startIndex; i < lines.length; i++) {
      final line = lines[i].trim();
      
      // Stop at next major section
      if (line.startsWith('## D)')) break;
      
      // Parse transferable skills
      if (line.startsWith('**Transferable**')) {
        if (i + 1 < lines.length) {
          final skillsLine = lines[i + 1];
          transferable.addAll(_parseSkillsList(skillsLine));
        }
      }
      
      // Parse job-specific skills
      if (line.startsWith('**Job-Specific**')) {
        if (i + 1 < lines.length) {
          final skillsLine = lines[i + 1];
          jobSpecific.addAll(_parseSkillsList(skillsLine));
        }
      }
      
      // Parse self-management skills
      if (line.startsWith('**Self-Management**')) {
        if (i + 1 < lines.length) {
          final skillsLine = lines[i + 1];
          selfManagement.addAll(_parseSkillsList(skillsLine));
        }
      }
    }
    
    return SkillsCanon(
      transferable: transferable,
      jobSpecific: jobSpecific,
      selfManagement: selfManagement,
    );
  }

  /// Parse a line of skills separated by bullet points
  List<String> _parseSkillsList(String line) {
    return line
        .split('•')
        .map((s) => s.trim())
        .where((s) => s.isNotEmpty)
        .toList();
  }

  /// Parse certifications section
  List<String> _parseCertifications(List<String> lines) {
    final certifications = <String>[];
    
    // Find the start of certification section
    int startIndex = -1;
    for (int i = 0; i < lines.length; i++) {
      if (lines[i].contains('## D) Certification Normalization')) {
        startIndex = i;
        break;
      }
    }
    
    if (startIndex == -1) return certifications;
    
    for (int i = startIndex; i < lines.length; i++) {
      final line = lines[i].trim();
      
      // Stop at next major section
      if (line.startsWith('## E)')) break;
      
      // Parse certification lines (lines starting with *)
      if (line.startsWith('*') && line.length > 2) {
        final cert = line.replaceFirst('*', '').trim();
        certifications.add(cert);
      }
    }
    
    return certifications;
  }

  /// Parse credential badges section
  Map<String, List<CredentialBadge>> _parseCredentialBadges(List<String> lines) {
    final badges = <String, List<CredentialBadge>>{};
    
    // Find the start of credential badges section
    int startIndex = -1;
    for (int i = 0; i < lines.length; i++) {
      if (lines[i].contains('## E) Credential Micro-Badges Library')) {
        startIndex = i;
        break;
      }
    }
    
    if (startIndex == -1) return badges;
    
    String? currentTrade;
    List<CredentialBadge> tradeBadges = [];
    
    for (int i = startIndex; i < lines.length; i++) {
      final line = lines[i].trim();
      
      // Stop at next major section
      if (line.startsWith('## F)')) break;
      
      // Detect trade header (### TradeName)
      if (line.startsWith('###')) {
        // Save previous trade if exists
        if (currentTrade != null && tradeBadges.isNotEmpty) {
          badges[currentTrade] = List.from(tradeBadges);
        }
        
        // Start new trade
        currentTrade = line.replaceAll('###', '').trim();
        tradeBadges = [];
        continue;
      }
      
      // Parse credential badge (e.g., "* **Badge Name** — *Resume:* ...")
      if (line.startsWith('* **') && line.contains('Resume:')) {
        final badge = _parseCredentialBadge(line);
        if (badge != null) {
          tradeBadges.add(badge);
        }
      }
    }
    
    // Save last trade
    if (currentTrade != null && tradeBadges.isNotEmpty) {
      badges[currentTrade] = tradeBadges;
    }
    
    return badges;
  }

  /// Parse a single credential badge line
  CredentialBadge? _parseCredentialBadge(String line) {
    try {
      // Extract name between ** and **
      final nameMatch = RegExp(r'\*\*(.+?)\*\*').firstMatch(line);
      if (nameMatch == null) return null;
      final name = nameMatch.group(1)!.trim();
      
      // Extract resume phrase between *Resume:* and *Proof:*
      final resumeMatch = RegExp(r'Resume:\*\s*"(.+?)"').firstMatch(line);
      final resumePhrase = resumeMatch?.group(1)?.trim() ?? '';
      
      // Extract proof after *Proof:*
      final proofMatch = RegExp(r'Proof:\*\s*(.+)$').firstMatch(line);
      final proof = proofMatch?.group(1)?.trim() ?? '';
      
      return CredentialBadge(
        name: name,
        resumePhrase: resumePhrase,
        proof: proof,
      );
    } catch (e) {
      return null;
    }
  }

  /// Parse artifact templates section
  List<ArtifactTemplate> _parseArtifactTemplates(List<String> lines) {
    final templates = <ArtifactTemplate>[];
    
    // Find the start of artifact templates section
    int startIndex = -1;
    for (int i = 0; i < lines.length; i++) {
      if (lines[i].contains('## G) Proof Artifact Templates')) {
        startIndex = i;
        break;
      }
    }
    
    if (startIndex == -1) return templates;
    
    for (int i = startIndex; i < lines.length; i++) {
      final line = lines[i].trim();
      
      // Stop at next major section
      if (line.startsWith('## H)')) break;
      
      // Parse template (e.g., "**Drop-Zone Control Checklist**")
      if (line.startsWith('**') && line.endsWith('**')) {
        final name = line.replaceAll('**', '').trim();
        
        // Get description/fields from next line
        if (i + 1 < lines.length) {
          final descLine = lines[i + 1].trim();
          final fields = descLine.split('•').map((s) => s.trim()).where((s) => s.isNotEmpty).toList();
          
          templates.add(ArtifactTemplate(
            name: name,
            description: descLine,
            fields: fields,
          ));
        }
      }
    }
    
    return templates;
  }
}

// Extension to check if a string matches a RegExp
extension StringRegExpExtension on String {
  bool matches(RegExp regExp) {
    return regExp.hasMatch(this);
  }
}
