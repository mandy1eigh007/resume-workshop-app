import 'package:flutter/material.dart';

class TextProcessingScreen extends StatefulWidget {
  const TextProcessingScreen({super.key});

  @override
  State<TextProcessingScreen> createState() => _TextProcessingScreenState();
}

class _TextProcessingScreenState extends State<TextProcessingScreen> {
  final TextEditingController _inputController = TextEditingController();
  String _processedText = '';
  bool _isProcessing = false;

  @override
  void dispose() {
    _inputController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Text Processing'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'Process Resume Content',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            const Text(
              'Parse and analyze resume text to extract key information for construction-facing resume generation.',
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey,
              ),
            ),
            const SizedBox(height: 24),
            const Text(
              'Input Text',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _inputController,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                hintText: 'Paste resume text or job history here...',
              ),
              maxLines: 8,
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: _isProcessing ? null : _processText,
              icon: _isProcessing
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.play_arrow),
              label: Text(_isProcessing ? 'Processing...' : 'Process Text'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
            ),
            const SizedBox(height: 24),
            const Divider(),
            const SizedBox(height: 24),
            const Text(
              'Processing Features',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            _buildFeatureCard(
              icon: Icons.work,
              title: 'Job Role Detection',
              description: 'Automatically detect and categorize past job roles',
            ),
            const SizedBox(height: 12),
            _buildFeatureCard(
              icon: Icons.psychology,
              title: 'Skills Inference',
              description: 'Infer transferable skills from job history',
            ),
            const SizedBox(height: 12),
            _buildFeatureCard(
              icon: Icons.construction,
              title: 'Construction Mapping',
              description: 'Map experience to construction industry roles',
            ),
            if (_processedText.isNotEmpty) ...[
              const SizedBox(height: 24),
              const Divider(),
              const SizedBox(height: 24),
              const Text(
                'Processed Output',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.grey[100],
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.grey[300]!),
                ),
                child: Text(
                  _processedText,
                  style: const TextStyle(
                    fontFamily: 'monospace',
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildFeatureCard({
    required IconData icon,
    required String title,
    required String description,
  }) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Row(
          children: [
            Icon(
              icon,
              size: 32,
              color: Theme.of(context).colorScheme.primary,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    description,
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.grey[600],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _processText() async {
    if (_inputController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please enter some text to process'),
        ),
      );
      return;
    }

    setState(() {
      _isProcessing = true;
      _processedText = '';
    });

    // Simulate processing delay
    await Future.delayed(const Duration(seconds: 2));

    setState(() {
      _isProcessing = false;
      _processedText = '''
Detected Roles:
- Project Manager
- Team Lead
- Operations Coordinator

Transferable Skills:
- Leadership
- Project Management
- Team Coordination
- Problem Solving
- Communication

Construction-Related Matches:
- Site Supervision
- Project Coordination
- Safety Compliance
''';
    });

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Text processing complete!'),
        ),
      );
    }
  }
}
