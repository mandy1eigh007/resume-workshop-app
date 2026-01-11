import 'package:flutter/foundation.dart';
import '../models/resume.dart';
import '../services/storage_service.dart';
import '../utils/skills_inference.dart';

class ResumeProvider with ChangeNotifier {
  final StorageService _storage = StorageService();
  Resume? _currentResume;
  bool _isLoading = false;

  Resume? get currentResume => _currentResume;
  bool get isLoading => _isLoading;

  /// Create a new resume
  Future<void> createResume(Resume resume) async {
    _isLoading = true;
    notifyListeners();

    try {
      await _storage.saveResume(resume);
      _currentResume = resume;
    } catch (e) {
      debugPrint('Error creating resume: $e');
      rethrow;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Load resume by ID
  Future<void> loadResume(String id) async {
    _isLoading = true;
    notifyListeners();

    try {
      _currentResume = await _storage.getResume(id);
    } catch (e) {
      debugPrint('Error loading resume: $e');
      rethrow;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Add measurable bullet to work experience
  Future<void> addMeasurableBullet(int workIndex, MeasurableBullet bullet) async {
    if (_currentResume == null) return;

    final updatedWorkHistory = List<WorkExperience>.from(_currentResume!.workHistory);
    final experience = updatedWorkHistory[workIndex];
    
    final updatedBullets = List<MeasurableBullet>.from(experience.bullets)..add(bullet);
    
    updatedWorkHistory[workIndex] = WorkExperience(
      role: experience.role,
      company: experience.company,
      location: experience.location,
      startDate: experience.startDate,
      endDate: experience.endDate,
      bullets: updatedBullets,
    );

    _currentResume = Resume(
      id: _currentResume!.id,
      name: _currentResume!.name,
      email: _currentResume!.email,
      phone: _currentResume!.phone,
      city: _currentResume!.city,
      state: _currentResume!.state,
      objective: _currentResume!.objective,
      workHistory: updatedWorkHistory,
      education: _currentResume!.education,
      certifications: _currentResume!.certifications,
      skills: _currentResume!.skills,
      createdAt: _currentResume!.createdAt,
      updatedAt: DateTime.now(),
    );

    await _storage.saveResume(_currentResume!);
    notifyListeners();
  }

  /// Infer skills from bullets
  Future<void> inferSkillsFromBullets() async {
    if (_currentResume == null) return;

    final inferredSkills = <String>{};
    
    for (final experience in _currentResume!.workHistory) {
      for (final bullet in experience.bullets) {
        inferredSkills.addAll(bullet.inferredSkills);
      }
    }

    // Use skills inference utility to expand
    final expandedSkills = SkillsInference.inferFromBullets(
      _currentResume!.workHistory.expand((e) => e.bullets).toList(),
    );
    
    inferredSkills.addAll(expandedSkills);

    final updatedSkills = SkillSet(
      suggested: _currentResume!.skills.suggested,
      inferred: inferredSkills.toList(),
      quickAdd: _currentResume!.skills.quickAdd,
    );

    _currentResume = Resume(
      id: _currentResume!.id,
      name: _currentResume!.name,
      email: _currentResume!.email,
      phone: _currentResume!.phone,
      city: _currentResume!.city,
      state: _currentResume!.state,
      objective: _currentResume!.objective,
      workHistory: _currentResume!.workHistory,
      education: _currentResume!.education,
      certifications: _currentResume!.certifications,
      skills: updatedSkills,
      createdAt: _currentResume!.createdAt,
      updatedAt: DateTime.now(),
    );

    await _storage.saveResume(_currentResume!);
    notifyListeners();
  }

  /// Add quick-add skill
  Future<void> addQuickAddSkill(String skill) async {
    if (_currentResume == null) return;

    final updatedQuickAdd = List<String>.from(_currentResume!.skills.quickAdd);
    if (!updatedQuickAdd.contains(skill)) {
      updatedQuickAdd.add(skill);
    }

    final updatedSkills = SkillSet(
      suggested: _currentResume!.skills.suggested,
      inferred: _currentResume!.skills.inferred,
      quickAdd: updatedQuickAdd,
    );

    _currentResume = Resume(
      id: _currentResume!.id,
      name: _currentResume!.name,
      email: _currentResume!.email,
      phone: _currentResume!.phone,
      city: _currentResume!.city,
      state: _currentResume!.state,
      objective: _currentResume!.objective,
      workHistory: _currentResume!.workHistory,
      education: _currentResume!.education,
      certifications: _currentResume!.certifications,
      skills: updatedSkills,
      createdAt: _currentResume!.createdAt,
      updatedAt: DateTime.now(),
    );

    await _storage.saveResume(_currentResume!);
    notifyListeners();
  }

  /// Update resume objective
  Future<void> updateObjective(String objective) async {
    if (_currentResume == null) return;

    _currentResume = Resume(
      id: _currentResume!.id,
      name: _currentResume!.name,
      email: _currentResume!.email,
      phone: _currentResume!.phone,
      city: _currentResume!.city,
      state: _currentResume!.state,
      objective: objective,
      workHistory: _currentResume!.workHistory,
      education: _currentResume!.education,
      certifications: _currentResume!.certifications,
      skills: _currentResume!.skills,
      createdAt: _currentResume!.createdAt,
      updatedAt: DateTime.now(),
    );

    await _storage.saveResume(_currentResume!);
    notifyListeners();
  }
}
