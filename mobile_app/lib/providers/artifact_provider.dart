import 'package:flutter/foundation.dart';
import '../models/artifact.dart';
import '../services/storage_service.dart';

class ArtifactProvider with ChangeNotifier {
  final StorageService _storage = StorageService();
  List<Artifact> _artifacts = [];
  bool _isLoading = false;

  List<Artifact> get artifacts => _artifacts;
  bool get isLoading => _isLoading;

  /// Load all artifacts
  Future<void> loadArtifacts() async {
    _isLoading = true;
    notifyListeners();

    try {
      _artifacts = await _storage.getArtifacts();
    } catch (e) {
      debugPrint('Error loading artifacts: $e');
      rethrow;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Add new artifact with audit trail
  Future<void> addArtifact(Artifact artifact, String uploadedBy) async {
    _isLoading = true;
    notifyListeners();

    try {
      final auditEntry = AuditEntry(
        action: 'Uploaded',
        timestamp: DateTime.now(),
        performedBy: uploadedBy,
        details: 'Initial upload',
      );

      final artifactWithAudit = Artifact(
        id: artifact.id,
        name: artifact.name,
        type: artifact.type,
        filePath: artifact.filePath,
        fileSize: artifact.fileSize,
        uploadedAt: artifact.uploadedAt,
        uploadedBy: uploadedBy,
        description: artifact.description,
        auditTrail: [auditEntry],
      );

      await _storage.saveArtifact(artifactWithAudit);
      _artifacts.add(artifactWithAudit);
    } catch (e) {
      debugPrint('Error adding artifact: $e');
      rethrow;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Delete artifact with audit trail
  Future<void> deleteArtifact(String id, String deletedBy) async {
    _isLoading = true;
    notifyListeners();

    try {
      final artifact = _artifacts.firstWhere((a) => a.id == id);
      
      final auditEntry = AuditEntry(
        action: 'Deleted',
        timestamp: DateTime.now(),
        performedBy: deletedBy,
        details: 'Artifact removed',
      );

      final updatedAuditTrail = List<AuditEntry>.from(artifact.auditTrail)
        ..add(auditEntry);

      final updatedArtifact = Artifact(
        id: artifact.id,
        name: artifact.name,
        type: artifact.type,
        filePath: artifact.filePath,
        fileSize: artifact.fileSize,
        uploadedAt: artifact.uploadedAt,
        uploadedBy: artifact.uploadedBy,
        description: artifact.description,
        auditTrail: updatedAuditTrail,
      );

      await _storage.saveArtifact(updatedArtifact);
      await _storage.deleteArtifact(id);
      _artifacts.removeWhere((a) => a.id == id);
    } catch (e) {
      debugPrint('Error deleting artifact: $e');
      rethrow;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Get artifacts by type
  List<Artifact> getArtifactsByType(ArtifactType type) {
    return _artifacts.where((a) => a.type == type).toList();
  }

  /// Get artifact by ID
  Artifact? getArtifactById(String id) {
    try {
      return _artifacts.firstWhere((a) => a.id == id);
    } catch (e) {
      return null;
    }
  }
}
