import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/progress.dart';
import '../providers/progress_provider.dart';

class ProgressTrackingScreen extends StatefulWidget {
  const ProgressTrackingScreen({super.key});

  @override
  State<ProgressTrackingScreen> createState() => _ProgressTrackingScreenState();
}

class _ProgressTrackingScreenState extends State<ProgressTrackingScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadProgress();
    });
  }

  void _loadProgress() {
    // TODO: Get actual student name from auth or storage
    Provider.of<ProgressProvider>(context, listen: false)
        .loadProgress('Demo Student');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Progress Tracking'),
        subtitle: const Text('Interviews & Rank Movement'),
      ),
      body: Consumer<ProgressProvider>(
        builder: (context, progressProvider, _) {
          if (progressProvider.isLoading) {
            return const Center(child: CircularProgressIndicator());
          }

          final tracker = progressProvider.tracker;
          if (tracker == null) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.trending_up, size: 80, color: Colors.grey),
                  const SizedBox(height: 16),
                  const Text('No progress data yet'),
                  const SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: () {
                      progressProvider.createProgress('Demo Student');
                    },
                    child: const Text('Start Tracking'),
                  ),
                ],
              ),
            );
          }

          return SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Overview Card
                Card(
                  color: Colors.teal50,
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      children: [
                        const Text(
                          'Progress Overview',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 16),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceAround,
                          children: [
                            _buildStatColumn(
                              'Interviews',
                              tracker.totalInterviews.toString(),
                              Icons.event,
                            ),
                            _buildStatColumn(
                              'Applications',
                              tracker.applications.length.toString(),
                              Icons.send,
                            ),
                            _buildStatColumn(
                              'Rank Updates',
                              tracker.rankHistory.length.toString(),
                              Icons.trending_up,
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 24),
                
                // Current Rank
                if (tracker.currentRank != null) ...[
                  const Text(
                    'Current Rank',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            tracker.currentRank!.programName,
                            style: const TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                'Rank: ${tracker.currentRank!.rank} / ${tracker.currentRank!.totalApplicants}',
                                style: const TextStyle(fontSize: 16),
                              ),
                              Text(
                                'Top ${tracker.currentRank!.percentile.toStringAsFixed(1)}%',
                                style: const TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.green,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          LinearProgressIndicator(
                            value: 1 - (tracker.currentRank!.rank / 
                                tracker.currentRank!.totalApplicants),
                            backgroundColor: Colors.grey[300],
                            valueColor: const AlwaysStoppedAnimation<Color>(
                              Colors.green,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),
                ],

                // Interviews
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(
                      'Interviews',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                    ),
                    IconButton(
                      onPressed: _addInterview,
                      icon: const Icon(Icons.add_circle),
                      tooltip: 'Add interview',
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                if (tracker.interviews.isEmpty)
                  const Card(
                    child: Padding(
                      padding: EdgeInsets.all(16),
                      child: Text('No interviews recorded yet'),
                    ),
                  )
                else
                  ...tracker.interviews.map((interview) => 
                    _buildInterviewCard(interview, progressProvider)),
                
                const SizedBox(height: 24),

                // Rank History
                if (tracker.rankHistory.isNotEmpty) ...[
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Rank Movement',
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                      ),
                      IconButton(
                        onPressed: _addRankUpdate,
                        icon: const Icon(Icons.add_circle),
                        tooltip: 'Add rank update',
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  ...tracker.rankHistory.map((rank) => 
                    _buildRankCard(rank)),
                ],
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildStatColumn(String label, String value, IconData icon) {
    return Column(
      children: [
        Icon(icon, size: 32, color: Colors.teal),
        const SizedBox(height: 8),
        Text(
          value,
          style: const TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.bold,
          ),
        ),
        Text(label),
      ],
    );
  }

  Widget _buildInterviewCard(
    InterviewRecord interview,
    ProgressProvider provider,
  ) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Icon(
          _getIconForInterviewType(interview.type),
          size: 32,
          color: Colors.blue,
        ),
        title: Text(interview.company),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(interview.position),
            Text(
              'Date: ${interview.scheduledDate.toString().split(' ')[0]}',
              style: const TextStyle(fontSize: 12),
            ),
            if (interview.outcome != null)
              Chip(
                label: Text(
                  interview.outcome!.name.toUpperCase(),
                  style: const TextStyle(fontSize: 10),
                ),
                materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                padding: EdgeInsets.zero,
              ),
          ],
        ),
        trailing: interview.outcome == null
            ? PopupMenuButton<InterviewOutcome>(
                icon: const Icon(Icons.more_vert),
                itemBuilder: (context) => InterviewOutcome.values
                    .map((outcome) => PopupMenuItem(
                          value: outcome,
                          child: Text(outcome.name),
                        ))
                    .toList(),
                onSelected: (outcome) {
                  provider.updateInterviewOutcome(interview.id, outcome);
                },
              )
            : null,
      ),
    );
  }

  Widget _buildRankCard(RankMovement rank) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: const Icon(Icons.trending_up, size: 32, color: Colors.green),
        title: Text(rank.programName),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Rank: ${rank.rank} / ${rank.totalApplicants}'),
            Text(
              'Top ${rank.percentile.toStringAsFixed(1)}%',
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
            Text(
              'Updated: ${rank.recordedAt.toString().split(' ')[0]}',
              style: const TextStyle(fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }

  IconData _getIconForInterviewType(InterviewType type) {
    switch (type) {
      case InterviewType.phone:
        return Icons.phone;
      case InterviewType.inPerson:
        return Icons.person;
      case InterviewType.video:
        return Icons.videocam;
      case InterviewType.group:
        return Icons.groups;
    }
  }

  void _addInterview() {
    // TODO: Show interview form dialog
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Interview form coming soon...')),
    );
  }

  void _addRankUpdate() {
    // TODO: Show rank update form dialog
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Rank update form coming soon...')),
    );
  }
}
