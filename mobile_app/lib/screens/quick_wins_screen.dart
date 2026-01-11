import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/quick_win.dart';
import '../providers/quick_win_provider.dart';
import '../widgets/quick_win_form.dart';

class QuickWinsScreen extends StatefulWidget {
  const QuickWinsScreen({super.key});

  @override
  State<QuickWinsScreen> createState() => _QuickWinsScreenState();
}

class _QuickWinsScreenState extends State<QuickWinsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<QuickWinProvider>(context, listen: false).loadQuickWins();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Quick Wins'),
        subtitle: const Text('Actions ≤2 Weeks'),
      ),
      body: Consumer<QuickWinProvider>(
        builder: (context, quickWinProvider, _) {
          if (quickWinProvider.isLoading) {
            return const Center(child: CircularProgressIndicator());
          }

          final activeQuickWins = quickWinProvider.activeQuickWins;
          final overdueQuickWins = quickWinProvider.overdueQuickWins;

          return Column(
            children: [
              const Padding(
                padding: EdgeInsets.all(16),
                child: Card(
                  color: Colors.purple50,
                  child: Padding(
                    padding: EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Quick Wins Strategy:',
                          style: TextStyle(fontWeight: FontWeight.bold),
                        ),
                        SizedBox(height: 4),
                        Text(
                          '• Focus on actions you can complete within 2 weeks\n'
                          '• Prioritize high-impact, achievable tasks\n'
                          '• Track progress toward apprenticeship goals',
                          style: TextStyle(fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              if (overdueQuickWins.isNotEmpty) ...[
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Card(
                    color: Colors.red50,
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Row(
                        children: [
                          const Icon(Icons.warning, color: Colors.red),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              '${overdueQuickWins.length} overdue action(s)',
                              style: const TextStyle(
                                fontWeight: FontWeight.bold,
                                color: Colors.red,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
              Expanded(
                child: activeQuickWins.isEmpty
                    ? const Center(
                        child: Text('No quick wins yet. Add one to get started!'),
                      )
                    : ListView.builder(
                        padding: const EdgeInsets.all(16),
                        itemCount: activeQuickWins.length,
                        itemBuilder: (context, index) {
                          final quickWin = activeQuickWins[index];
                          return _buildQuickWinCard(quickWin, quickWinProvider);
                        },
                      ),
              ),
            ],
          );
        },
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _showAddQuickWinDialog(),
        icon: const Icon(Icons.add),
        label: const Text('Add Quick Win'),
      ),
    );
  }

  Widget _buildQuickWinCard(QuickWin quickWin, QuickWinProvider provider) {
    final isOverdue = quickWin.isOverdue;
    final daysRemaining = quickWin.daysRemaining;

    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      color: isOverdue ? Colors.red50 : null,
      child: ExpansionTile(
        leading: Icon(
          _getIconForCategory(quickWin.category),
          color: _getColorForPriority(quickWin.priority),
          size: 32,
        ),
        title: Text(
          quickWin.title,
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 4),
            Text(quickWin.description),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [
                Chip(
                  label: Text(
                    quickWin.priority.name.toUpperCase(),
                    style: const TextStyle(fontSize: 10),
                  ),
                  backgroundColor: _getColorForPriority(quickWin.priority).withOpacity(0.2),
                  padding: EdgeInsets.zero,
                  materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
                Chip(
                  label: Text(
                    isOverdue
                        ? 'OVERDUE'
                        : '$daysRemaining days left',
                    style: const TextStyle(fontSize: 10),
                  ),
                  backgroundColor: isOverdue ? Colors.red : Colors.green,
                  labelStyle: const TextStyle(color: Colors.white),
                  padding: EdgeInsets.zero,
                  materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
              ],
            ),
          ],
        ),
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Action Steps:',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                ...quickWin.actionSteps.map((step) => Padding(
                      padding: const EdgeInsets.only(bottom: 4),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('• '),
                          Expanded(child: Text(step)),
                        ],
                      ),
                    )),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: () => provider.updateQuickWinStatus(
                          quickWin.id,
                          QuickWinStatus.inProgress,
                        ),
                        child: const Text('In Progress'),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: ElevatedButton(
                        onPressed: () => provider.updateQuickWinStatus(
                          quickWin.id,
                          QuickWinStatus.completed,
                        ),
                        child: const Text('Complete'),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  IconData _getIconForCategory(QuickWinCategory category) {
    switch (category) {
      case QuickWinCategory.certification:
        return Icons.card_membership;
      case QuickWinCategory.documentation:
        return Icons.description;
      case QuickWinCategory.networking:
        return Icons.people;
      case QuickWinCategory.skillBuilding:
        return Icons.build;
      case QuickWinCategory.application:
        return Icons.send;
    }
  }

  Color _getColorForPriority(QuickWinPriority priority) {
    switch (priority) {
      case QuickWinPriority.high:
        return Colors.red;
      case QuickWinPriority.medium:
        return Colors.orange;
      case QuickWinPriority.low:
        return Colors.blue;
    }
  }

  void _showAddQuickWinDialog() {
    showDialog(
      context: context,
      builder: (_) => const QuickWinForm(),
    );
  }
}
