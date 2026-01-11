import 'package:flutter_test/flutter_test.dart';
import 'package:resume_workshop_mobile/models/quick_win.dart';

void main() {
  group('QuickWin Tests', () {
    test('QuickWin can be created with deadline ≤2 weeks', () {
      final deadline = DateTime.now().add(const Duration(days: 10));
      final quickWin = QuickWin(
        id: '1',
        title: 'Get OSHA-10 Card',
        description: 'Complete OSHA-10 training',
        category: QuickWinCategory.certification,
        priority: QuickWinPriority.high,
        deadline: deadline,
        status: QuickWinStatus.notStarted,
        actionSteps: ['Register for course', 'Attend training', 'Get card'],
        createdAt: DateTime.now(),
      );

      expect(quickWin.title, 'Get OSHA-10 Card');
      expect(quickWin.actionSteps.length, 3);
      expect(quickWin.status, QuickWinStatus.notStarted);
    });

    test('QuickWin correctly identifies overdue status', () {
      final pastDeadline = DateTime.now().subtract(const Duration(days: 1));
      final quickWin = QuickWin(
        id: '1',
        title: 'Overdue Task',
        description: 'Test',
        category: QuickWinCategory.documentation,
        priority: QuickWinPriority.medium,
        deadline: pastDeadline,
        status: QuickWinStatus.inProgress,
        actionSteps: ['Step 1'],
        createdAt: DateTime.now(),
      );

      expect(quickWin.isOverdue, true);
    });

    test('QuickWin calculates days remaining correctly', () {
      final futureDeadline = DateTime.now().add(const Duration(days: 5));
      final quickWin = QuickWin(
        id: '1',
        title: 'Future Task',
        description: 'Test',
        category: QuickWinCategory.skillBuilding,
        priority: QuickWinPriority.low,
        deadline: futureDeadline,
        status: QuickWinStatus.notStarted,
        actionSteps: ['Step 1'],
        createdAt: DateTime.now(),
      );

      expect(quickWin.daysRemaining, greaterThanOrEqualTo(4));
      expect(quickWin.daysRemaining, lessThanOrEqualTo(5));
    });

    test('Completed QuickWin is not marked as overdue', () {
      final pastDeadline = DateTime.now().subtract(const Duration(days: 1));
      final quickWin = QuickWin(
        id: '1',
        title: 'Completed Task',
        description: 'Test',
        category: QuickWinCategory.application,
        priority: QuickWinPriority.high,
        deadline: pastDeadline,
        status: QuickWinStatus.completed,
        actionSteps: ['Step 1'],
        createdAt: DateTime.now(),
        completedAt: DateTime.now(),
      );

      expect(quickWin.isOverdue, false);
    });
  });
}
