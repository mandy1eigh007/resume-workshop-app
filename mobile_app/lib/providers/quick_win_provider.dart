import 'package:flutter/foundation.dart';
import '../models/quick_win.dart';
import '../services/storage_service.dart';

class QuickWinProvider with ChangeNotifier {
  final StorageService _storage = StorageService();
  List<QuickWin> _quickWins = [];
  bool _isLoading = false;

  List<QuickWin> get quickWins => _quickWins;
  bool get isLoading => _isLoading;

  /// Get active quick wins (not completed)
  List<QuickWin> get activeQuickWins => 
      _quickWins.where((qw) => qw.status != QuickWinStatus.completed).toList();

  /// Get overdue quick wins
  List<QuickWin> get overdueQuickWins => 
      _quickWins.where((qw) => qw.isOverdue).toList();

  /// Get quick wins by priority
  List<QuickWin> getQuickWinsByPriority(QuickWinPriority priority) =>
      _quickWins.where((qw) => qw.priority == priority).toList();

  /// Load all quick wins
  Future<void> loadQuickWins() async {
    _isLoading = true;
    notifyListeners();

    try {
      _quickWins = await _storage.getQuickWins();
      // Sort by deadline
      _quickWins.sort((a, b) => a.deadline.compareTo(b.deadline));
    } catch (e) {
      debugPrint('Error loading quick wins: $e');
      rethrow;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Add new quick win (ensure ≤2 weeks deadline)
  Future<void> addQuickWin(QuickWin quickWin) async {
    _isLoading = true;
    notifyListeners();

    try {
      // Validate deadline is ≤2 weeks
      final twoWeeksFromNow = DateTime.now().add(const Duration(days: 14));
      if (quickWin.deadline.isAfter(twoWeeksFromNow)) {
        throw Exception('Quick Win deadline must be within 2 weeks');
      }

      await _storage.saveQuickWin(quickWin);
      _quickWins.add(quickWin);
      _quickWins.sort((a, b) => a.deadline.compareTo(b.deadline));
    } catch (e) {
      debugPrint('Error adding quick win: $e');
      rethrow;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Update quick win status
  Future<void> updateQuickWinStatus(String id, QuickWinStatus status) async {
    _isLoading = true;
    notifyListeners();

    try {
      final index = _quickWins.indexWhere((qw) => qw.id == id);
      if (index == -1) throw Exception('Quick Win not found');

      final quickWin = _quickWins[index];
      final updatedQuickWin = QuickWin(
        id: quickWin.id,
        title: quickWin.title,
        description: quickWin.description,
        category: quickWin.category,
        priority: quickWin.priority,
        deadline: quickWin.deadline,
        status: status,
        actionSteps: quickWin.actionSteps,
        createdAt: quickWin.createdAt,
        completedAt: status == QuickWinStatus.completed ? DateTime.now() : null,
      );

      await _storage.saveQuickWin(updatedQuickWin);
      _quickWins[index] = updatedQuickWin;
    } catch (e) {
      debugPrint('Error updating quick win status: $e');
      rethrow;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Delete quick win
  Future<void> deleteQuickWin(String id) async {
    _isLoading = true;
    notifyListeners();

    try {
      await _storage.deleteQuickWin(id);
      _quickWins.removeWhere((qw) => qw.id == id);
    } catch (e) {
      debugPrint('Error deleting quick win: $e');
      rethrow;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}
