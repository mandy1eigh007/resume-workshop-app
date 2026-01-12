import 'package:flutter/foundation.dart';
import '../models/content_master.dart';
import '../services/content_master_service.dart';

/// Provider for managing CONTENT_MASTER.md content
class ContentMasterProvider with ChangeNotifier {
  final ContentMasterService _service = ContentMasterService();
  
  ContentMaster? _content;
  bool _isLoading = false;
  String? _error;

  ContentMaster? get content => _content;
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get isLoaded => _content != null;

  /// Load content from CONTENT_MASTER.md
  Future<void> loadContent() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _content = await _service.loadContent();
      
      // Fallback to empty content if parsing failed
      if (_content == null) {
        _content = ContentMaster.empty();
        _error = 'Failed to load content. Using fallback data.';
      }
    } catch (e) {
      debugPrint('Error loading content master: $e');
      _content = ContentMaster.empty();
      _error = 'Failed to load content: ${e.toString()}';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Get objectives for a specific trade
  TradeObjectives? getObjectivesForTrade(String trade) {
    return _content?.objectives[trade];
  }

  /// Get all trade names that have objectives
  List<String> getAvailableTrades() {
    return _content?.objectives.keys.toList() ?? [];
  }

  /// Get bullets for a specific role
  List<String> getBulletsForRole(String role) {
    return _content?.roleBullets[role] ?? [];
  }

  /// Get all available roles
  List<String> getAvailableRoles() {
    return _content?.roleBullets.keys.toList() ?? [];
  }

  /// Get all transferable skills
  List<String> getTransferableSkills() {
    return _content?.skillsCanon.transferable ?? [];
  }

  /// Get all job-specific skills
  List<String> getJobSpecificSkills() {
    return _content?.skillsCanon.jobSpecific ?? [];
  }

  /// Get all self-management skills
  List<String> getSelfManagementSkills() {
    return _content?.skillsCanon.selfManagement ?? [];
  }

  /// Get all skills combined
  List<String> getAllSkills() {
    return _content?.skillsCanon.all ?? [];
  }

  /// Get all normalized certifications
  List<String> getCertifications() {
    return _content?.certifications ?? [];
  }

  /// Get credential badges for a specific trade
  List<CredentialBadge> getCredentialBadgesForTrade(String trade) {
    return _content?.credentialBadges[trade] ?? [];
  }

  /// Get all artifact templates
  List<ArtifactTemplate> getArtifactTemplates() {
    return _content?.artifactTemplates ?? [];
  }

  /// Get artifact template by name
  ArtifactTemplate? getArtifactTemplateByName(String name) {
    try {
      return _content?.artifactTemplates.firstWhere(
        (template) => template.name.toLowerCase() == name.toLowerCase(),
      );
    } catch (e) {
      return null;
    }
  }
}
