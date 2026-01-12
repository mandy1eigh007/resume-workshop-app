import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/content_master_provider.dart';
import 'resume_generation_screen.dart';
import 'artifact_upload_screen.dart';
import 'pathway_packet_screen.dart';
import 'quick_wins_screen.dart';
import 'progress_tracking_screen.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Resume Workshop'),
        subtitle: const Text('Seattle Tri-County Construction'),
      ),
      body: Consumer<ContentMasterProvider>(
        builder: (context, contentProvider, _) {
          return Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text(
                  'Welcome to the Seattle Tri-County Construction Resume Workshop',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 8),
                const Text(
                  'Optimized for mobile workshops in King, Pierce, and Snohomish counties',
                  style: TextStyle(fontSize: 14, color: Colors.grey),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                
                // Show content loading status
                if (contentProvider.isLoading)
                  const Card(
                    color: Colors.blue50,
                    child: Padding(
                      padding: EdgeInsets.all(12),
                      child: Row(
                        children: [
                          SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          ),
                          SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              'Loading content from CONTENT_MASTER.md...',
                              style: TextStyle(fontSize: 12),
                            ),
                          ),
                        ],
                      ),
                    ),
                  )
                else if (contentProvider.error != null)
                  Card(
                    color: Colors.orange[50],
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Row(
                        children: [
                          const Icon(Icons.warning, color: Colors.orange, size: 20),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              contentProvider.error!,
                              style: const TextStyle(fontSize: 12),
                            ),
                          ),
                        ],
                      ),
                    ),
                  )
                else
                  Card(
                    color: Colors.green[50],
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Row(
                        children: [
                          const Icon(Icons.check_circle, color: Colors.green, size: 20),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              'Content loaded: ${contentProvider.getAvailableTrades().length} trades, '
                              '${contentProvider.getAllSkills().length} skills, '
                              '${contentProvider.getCertifications().length} certifications',
                              style: const TextStyle(fontSize: 11),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                
                const SizedBox(height: 16),
                Expanded(
                  child: GridView.count(
                    crossAxisCount: 2,
                    crossAxisSpacing: 16,
                    mainAxisSpacing: 16,
                    children: [
                      _buildFeatureCard(
                        context,
                        title: 'Resume Builder',
                        icon: Icons.description,
                        color: Colors.blue,
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => const ResumeGenerationScreen(),
                          ),
                        ),
                      ),
                      _buildFeatureCard(
                        context,
                        title: 'Upload Evidence',
                        icon: Icons.upload_file,
                        color: Colors.green,
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => const ArtifactUploadScreen(),
                          ),
                        ),
                      ),
                      _buildFeatureCard(
                        context,
                        title: 'Pathway Packet',
                        icon: Icons.folder_special,
                        color: Colors.orange,
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => const PathwayPacketScreen(),
                          ),
                        ),
                      ),
                      _buildFeatureCard(
                        context,
                        title: 'Quick Wins',
                        icon: Icons.fast_forward,
                        color: Colors.purple,
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => const QuickWinsScreen(),
                          ),
                        ),
                      ),
                      _buildFeatureCard(
                        context,
                        title: 'Progress',
                        icon: Icons.trending_up,
                        color: Colors.teal,
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => const ProgressTrackingScreen(),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildFeatureCard(
    BuildContext context, {
    required String title,
    required IconData icon,
    required Color color,
    required VoidCallback onTap,
  }) {
    return Card(
      elevation: 4,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 48, color: color),
            const SizedBox(height: 12),
            Text(
              title,
              style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
