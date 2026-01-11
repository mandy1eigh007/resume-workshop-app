import 'package:flutter/material.dart';
import 'file_upload_screen.dart';
import 'text_processing_screen.dart';
import 'docx_generation_screen.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Resume Workshop'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const SizedBox(height: 20),
            const Text(
              'Seattle Tri-County Construction',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            const Text(
              'Resume & Pathway Packet',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w500,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 40),
            _buildNavigationCard(
              context,
              icon: Icons.upload_file,
              title: 'File Upload',
              description: 'Upload your resume (PDF, DOCX, TXT)',
              onTap: () => Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const FileUploadScreen()),
              ),
            ),
            const SizedBox(height: 16),
            _buildNavigationCard(
              context,
              icon: Icons.text_fields,
              title: 'Text Processing',
              description: 'Process and analyze resume content',
              onTap: () => Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const TextProcessingScreen()),
              ),
            ),
            const SizedBox(height: 16),
            _buildNavigationCard(
              context,
              icon: Icons.description,
              title: 'DOCX Generation',
              description: 'Generate resume and pathway documents',
              onTap: () => Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const DocxGenerationScreen()),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildNavigationCard(
    BuildContext context, {
    required IconData icon,
    required String title,
    required String description,
    required VoidCallback onTap,
  }) {
    return Card(
      elevation: 4,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Row(
            children: [
              Icon(
                icon,
                size: 48,
                color: Theme.of(context).colorScheme.primary,
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      description,
                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.grey[600],
                      ),
                    ),
                  ],
                ),
              ),
              Icon(
                Icons.arrow_forward_ios,
                color: Colors.grey[400],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
