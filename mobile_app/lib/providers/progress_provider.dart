import 'package:flutter/foundation.dart';
import '../models/progress.dart';
import '../services/storage_service.dart';

class ProgressProvider with ChangeNotifier {
  final StorageService _storage = StorageService();
  ProgressTracker? _tracker;
  bool _isLoading = false;

  ProgressTracker? get tracker => _tracker;
  bool get isLoading => _isLoading;

  /// Load progress tracker
  Future<void> loadProgress(String studentName) async {
    _isLoading = true;
    notifyListeners();

    try {
      _tracker = await _storage.getProgressTracker(studentName);
    } catch (e) {
      debugPrint('Error loading progress: $e');
      rethrow;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Create new progress tracker
  Future<void> createProgress(String studentName) async {
    _isLoading = true;
    notifyListeners();

    try {
      _tracker = ProgressTracker(
        id: DateTime.now().millisecondsSinceEpoch.toString(),
        studentName: studentName,
        interviews: [],
        rankHistory: [],
        applications: {},
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );
      await _storage.saveProgressTracker(_tracker!);
    } catch (e) {
      debugPrint('Error creating progress: $e');
      rethrow;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Add interview record
  Future<void> addInterview(InterviewRecord interview) async {
    if (_tracker == null) return;

    _isLoading = true;
    notifyListeners();

    try {
      final updatedInterviews = List<InterviewRecord>.from(_tracker!.interviews)
        ..add(interview);

      _tracker = ProgressTracker(
        id: _tracker!.id,
        studentName: _tracker!.studentName,
        interviews: updatedInterviews,
        rankHistory: _tracker!.rankHistory,
        applications: _tracker!.applications,
        createdAt: _tracker!.createdAt,
        updatedAt: DateTime.now(),
      );

      await _storage.saveProgressTracker(_tracker!);
    } catch (e) {
      debugPrint('Error adding interview: $e');
      rethrow;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Update interview outcome
  Future<void> updateInterviewOutcome(
    String interviewId,
    InterviewOutcome outcome,
  ) async {
    if (_tracker == null) return;

    _isLoading = true;
    notifyListeners();

    try {
      final updatedInterviews = _tracker!.interviews.map((interview) {
        if (interview.id == interviewId) {
          return InterviewRecord(
            id: interview.id,
            company: interview.company,
            position: interview.position,
            scheduledDate: interview.scheduledDate,
            type: interview.type,
            outcome: outcome,
            notes: interview.notes,
            createdAt: interview.createdAt,
          );
        }
        return interview;
      }).toList();

      _tracker = ProgressTracker(
        id: _tracker!.id,
        studentName: _tracker!.studentName,
        interviews: updatedInterviews,
        rankHistory: _tracker!.rankHistory,
        applications: _tracker!.applications,
        createdAt: _tracker!.createdAt,
        updatedAt: DateTime.now(),
      );

      await _storage.saveProgressTracker(_tracker!);
    } catch (e) {
      debugPrint('Error updating interview outcome: $e');
      rethrow;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Add rank movement
  Future<void> addRankMovement(RankMovement rank) async {
    if (_tracker == null) return;

    _isLoading = true;
    notifyListeners();

    try {
      final updatedRankHistory = List<RankMovement>.from(_tracker!.rankHistory)
        ..add(rank);

      _tracker = ProgressTracker(
        id: _tracker!.id,
        studentName: _tracker!.studentName,
        interviews: _tracker!.interviews,
        rankHistory: updatedRankHistory,
        applications: _tracker!.applications,
        createdAt: _tracker!.createdAt,
        updatedAt: DateTime.now(),
      );

      await _storage.saveProgressTracker(_tracker!);
    } catch (e) {
      debugPrint('Error adding rank movement: $e');
      rethrow;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Update application status
  Future<void> updateApplicationStatus(
    String applicationId,
    ApplicationStatus status,
  ) async {
    if (_tracker == null) return;

    _isLoading = true;
    notifyListeners();

    try {
      final updatedApplications = Map<String, ApplicationStatus>.from(
        _tracker!.applications,
      )..[applicationId] = status;

      _tracker = ProgressTracker(
        id: _tracker!.id,
        studentName: _tracker!.studentName,
        interviews: _tracker!.interviews,
        rankHistory: _tracker!.rankHistory,
        applications: updatedApplications,
        createdAt: _tracker!.createdAt,
        updatedAt: DateTime.now(),
      );

      await _storage.saveProgressTracker(_tracker!);
    } catch (e) {
      debugPrint('Error updating application status: $e');
      rethrow;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}
