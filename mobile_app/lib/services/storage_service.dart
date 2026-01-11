import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/resume.dart';
import '../models/artifact.dart';
import '../models/quick_win.dart';
import '../models/progress.dart';
import '../models/pathway_packet.dart';

/// Local storage service using SharedPreferences
/// For production, consider migrating to SQLite for complex queries
class StorageService {
  static const String _resumeKey = 'resumes';
  static const String _artifactKey = 'artifacts';
  static const String _quickWinKey = 'quick_wins';
  static const String _progressKey = 'progress_trackers';
  static const String _pathwayPacketKey = 'pathway_packets';

  // Resume operations
  Future<void> saveResume(Resume resume) async {
    final prefs = await SharedPreferences.getInstance();
    final resumes = await _getResumes();
    resumes[resume.id] = resume.toJson();
    await prefs.setString(_resumeKey, jsonEncode(resumes));
  }

  Future<Resume?> getResume(String id) async {
    final resumes = await _getResumes();
    final resumeJson = resumes[id];
    return resumeJson != null ? Resume.fromJson(resumeJson) : null;
  }

  Future<Map<String, dynamic>> _getResumes() async {
    final prefs = await SharedPreferences.getInstance();
    final resumesString = prefs.getString(_resumeKey);
    if (resumesString == null) return {};
    return Map<String, dynamic>.from(jsonDecode(resumesString));
  }

  // Artifact operations
  Future<void> saveArtifact(Artifact artifact) async {
    final prefs = await SharedPreferences.getInstance();
    final artifacts = await _getArtifacts();
    artifacts[artifact.id] = artifact.toJson();
    await prefs.setString(_artifactKey, jsonEncode(artifacts));
  }

  Future<List<Artifact>> getArtifacts() async {
    final artifactsMap = await _getArtifacts();
    return artifactsMap.values.map((json) => Artifact.fromJson(json)).toList();
  }

  Future<void> deleteArtifact(String id) async {
    final prefs = await SharedPreferences.getInstance();
    final artifacts = await _getArtifacts();
    artifacts.remove(id);
    await prefs.setString(_artifactKey, jsonEncode(artifacts));
  }

  Future<Map<String, dynamic>> _getArtifacts() async {
    final prefs = await SharedPreferences.getInstance();
    final artifactsString = prefs.getString(_artifactKey);
    if (artifactsString == null) return {};
    return Map<String, dynamic>.from(jsonDecode(artifactsString));
  }

  // Quick Win operations
  Future<void> saveQuickWin(QuickWin quickWin) async {
    final prefs = await SharedPreferences.getInstance();
    final quickWins = await _getQuickWins();
    quickWins[quickWin.id] = quickWin.toJson();
    await prefs.setString(_quickWinKey, jsonEncode(quickWins));
  }

  Future<List<QuickWin>> getQuickWins() async {
    final quickWinsMap = await _getQuickWins();
    return quickWinsMap.values.map((json) => QuickWin.fromJson(json)).toList();
  }

  Future<void> deleteQuickWin(String id) async {
    final prefs = await SharedPreferences.getInstance();
    final quickWins = await _getQuickWins();
    quickWins.remove(id);
    await prefs.setString(_quickWinKey, jsonEncode(quickWins));
  }

  Future<Map<String, dynamic>> _getQuickWins() async {
    final prefs = await SharedPreferences.getInstance();
    final quickWinsString = prefs.getString(_quickWinKey);
    if (quickWinsString == null) return {};
    return Map<String, dynamic>.from(jsonDecode(quickWinsString));
  }

  // Progress Tracker operations
  Future<void> saveProgressTracker(ProgressTracker tracker) async {
    final prefs = await SharedPreferences.getInstance();
    final trackers = await _getProgressTrackers();
    trackers[tracker.id] = tracker.toJson();
    await prefs.setString(_progressKey, jsonEncode(trackers));
  }

  Future<ProgressTracker?> getProgressTracker(String studentName) async {
    final trackers = await _getProgressTrackers();
    final trackerJson = trackers.values.firstWhere(
      (json) => json['studentName'] == studentName,
      orElse: () => {},
    );
    return trackerJson.isNotEmpty ? ProgressTracker.fromJson(trackerJson) : null;
  }

  Future<Map<String, dynamic>> _getProgressTrackers() async {
    final prefs = await SharedPreferences.getInstance();
    final trackersString = prefs.getString(_progressKey);
    if (trackersString == null) return {};
    return Map<String, dynamic>.from(jsonDecode(trackersString));
  }

  // Pathway Packet operations
  Future<void> savePathwayPacket(PathwayPacket packet) async {
    final prefs = await SharedPreferences.getInstance();
    final packets = await _getPathwayPackets();
    packets[packet.id] = packet.toJson();
    await prefs.setString(_pathwayPacketKey, jsonEncode(packets));
  }

  Future<PathwayPacket?> getPathwayPacket(String id) async {
    final packets = await _getPathwayPackets();
    final packetJson = packets[id];
    return packetJson != null ? PathwayPacket.fromJson(packetJson) : null;
  }

  Future<Map<String, dynamic>> _getPathwayPackets() async {
    final prefs = await SharedPreferences.getInstance();
    final packetsString = prefs.getString(_pathwayPacketKey);
    if (packetsString == null) return {};
    return Map<String, dynamic>.from(jsonDecode(packetsString));
  }

  // Clear all data (for testing/reset)
  Future<void> clearAll() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
  }
}
