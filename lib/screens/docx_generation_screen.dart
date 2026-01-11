import 'package:flutter/material.dart';

class DocxGenerationScreen extends StatefulWidget {
  const DocxGenerationScreen({super.key});

  @override
  State<DocxGenerationScreen> createState() => _DocxGenerationScreenState();
}

class _DocxGenerationScreenState extends State<DocxGenerationScreen> {
  String? _selectedDocumentType;
  bool _isGenerating = false;

  final List<Map<String, dynamic>> _documentTypes = [
    {
      'id': 'resume',
      'title': 'Resume',
      'description': 'Construction-focused resume document',
      'icon': Icons.description,
    },
    {
      'id': 'cover_letter',
      'title': 'Cover Letter',
      'description': 'Crew-forward cover letter with measurable language',
      'icon': Icons.email,
    },
    {
      'id': 'pathway_packet',
      'title': 'Pathway Packet',
      'description': 'Instructor pathway packet with reflections and playbook',
      'icon': Icons.folder_special,
    },
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('DOCX Generation'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'Generate Documents',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            const Text(
              'Select the type of document you want to generate.',
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey,
              ),
            ),
            const SizedBox(height: 24),
            const Text(
              'Document Type',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            ..._documentTypes.map((docType) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: _buildDocumentTypeCard(docType),
                )),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: _selectedDocumentType != null && !_isGenerating
                  ? _generateDocument
                  : null,
              icon: _isGenerating
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.file_download),
              label: Text(_isGenerating ? 'Generating...' : 'Generate Document'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
            ),
            const SizedBox(height: 24),
            const Divider(),
            const SizedBox(height: 24),
            const Text(
              'Generation Options',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            _buildOptionCard(
              icon: Icons.article,
              title: 'Resume Template',
              description: 'Uses resume_app_template.docx',
              enabled: _selectedDocumentType == 'resume',
            ),
            const SizedBox(height: 12),
            _buildOptionCard(
              icon: Icons.work,
              title: 'Job History Master',
              description: 'Maps roles to duty bullets',
              enabled: _selectedDocumentType == 'resume',
            ),
            const SizedBox(height: 12),
            _buildOptionCard(
              icon: Icons.school,
              title: 'Stand Out Playbook',
              description: 'Includes trade-specific sections',
              enabled: _selectedDocumentType == 'pathway_packet',
            ),
            const SizedBox(height: 24),
            const Divider(),
            const SizedBox(height: 24),
            const Text(
              'Document Preview',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            Container(
              height: 200,
              decoration: BoxDecoration(
                color: Colors.grey[100],
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.grey[300]!),
              ),
              child: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.preview,
                      size: 64,
                      color: Colors.grey[400],
                    ),
                    const SizedBox(height: 16),
                    Text(
                      _selectedDocumentType != null
                          ? 'Preview will appear here after generation'
                          : 'Select a document type to preview',
                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.grey[600],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDocumentTypeCard(Map<String, dynamic> docType) {
    final isSelected = _selectedDocumentType == docType['id'];
    
    return Card(
      elevation: isSelected ? 8 : 2,
      color: isSelected ? Theme.of(context).colorScheme.primaryContainer : null,
      child: InkWell(
        onTap: () => setState(() => _selectedDocumentType = docType['id']),
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Row(
            children: [
              Icon(
                docType['icon'] as IconData,
                size: 40,
                color: isSelected
                    ? Theme.of(context).colorScheme.primary
                    : Colors.grey[600],
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      docType['title'],
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: isSelected
                            ? Theme.of(context).colorScheme.primary
                            : null,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      docType['description'],
                      style: TextStyle(
                        fontSize: 14,
                        color: isSelected ? Colors.grey[700] : Colors.grey[600],
                      ),
                    ),
                  ],
                ),
              ),
              if (isSelected)
                Icon(
                  Icons.check_circle,
                  color: Theme.of(context).colorScheme.primary,
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildOptionCard({
    required IconData icon,
    required String title,
    required String description,
    required bool enabled,
  }) {
    return Opacity(
      opacity: enabled ? 1.0 : 0.5,
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(12.0),
          child: Row(
            children: [
              Icon(
                icon,
                size: 32,
                color: enabled
                    ? Theme.of(context).colorScheme.primary
                    : Colors.grey,
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
              if (enabled)
                const Icon(
                  Icons.check,
                  color: Colors.green,
                ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _generateDocument() async {
    setState(() => _isGenerating = true);

    // Simulate document generation
    await Future.delayed(const Duration(seconds: 2));

    setState(() => _isGenerating = false);

    if (mounted) {
      final docName = _documentTypes
          .firstWhere((doc) => doc['id'] == _selectedDocumentType)['title'];
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('$docName generated successfully!'),
          action: SnackBarAction(
            label: 'View',
            onPressed: () {
              // Placeholder for viewing generated document
            },
          ),
        ),
      );
    }
  }
}
