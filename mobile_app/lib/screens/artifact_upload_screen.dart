import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:file_picker/file_picker.dart';
import 'package:image_picker/image_picker.dart';
import '../models/artifact.dart';
import '../providers/artifact_provider.dart';
import '../providers/content_master_provider.dart';

class ArtifactUploadScreen extends StatefulWidget {
  const ArtifactUploadScreen({super.key});

  @override
  State<ArtifactUploadScreen> createState() => _ArtifactUploadScreenState();
}

class _ArtifactUploadScreenState extends State<ArtifactUploadScreen> {
  final ImagePicker _imagePicker = ImagePicker();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<ArtifactProvider>(context, listen: false).loadArtifacts();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Upload Evidence'),
        subtitle: const Text('Files, Photos (No Faces), Certificates'),
      ),
      body: Consumer2<ArtifactProvider, ContentMasterProvider>(
        builder: (context, artifactProvider, contentProvider, _) {
          if (artifactProvider.isLoading) {
            return const Center(child: CircularProgressIndicator());
          }

          final templates = contentProvider.getArtifactTemplates();

          return Column(
            children: [
              Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Card(
                      color: Colors.amber50,
                      child: Padding(
                        padding: EdgeInsets.all(12),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '⚠️ Photo Guidelines:',
                              style: TextStyle(fontWeight: FontWeight.bold),
                            ),
                            SizedBox(height: 4),
                            Text(
                              '• Take photos of work, tools, or equipment\n'
                              '• DO NOT include faces for privacy\n'
                              '• Focus on evidence of skills and work',
                              style: TextStyle(fontSize: 12),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    
                    // Display artifact templates if available
                    if (templates.isNotEmpty) ...[
                      const Text(
                        'Artifact Templates (from CONTENT_MASTER.md):',
                        style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                      ),
                      const SizedBox(height: 8),
                      SizedBox(
                        height: 120,
                        child: ListView.builder(
                          scrollDirection: Axis.horizontal,
                          itemCount: templates.length,
                          itemBuilder: (context, index) {
                            final template = templates[index];
                            return Card(
                              margin: const EdgeInsets.only(right: 8),
                              child: Container(
                                width: 200,
                                padding: const EdgeInsets.all(8),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      template.name,
                                      style: const TextStyle(
                                        fontWeight: FontWeight.bold,
                                        fontSize: 12,
                                      ),
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                    const SizedBox(height: 4),
                                    Expanded(
                                      child: Text(
                                        '${template.fields.length} fields required',
                                        style: const TextStyle(fontSize: 10, color: Colors.grey),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            );
                          },
                        ),
                      ),
                      const SizedBox(height: 16),
                    ],
                    
                    Row(
                      children: [
                        Expanded(
                          child: ElevatedButton.icon(
                            onPressed: () => _pickFile(artifactProvider),
                            icon: const Icon(Icons.upload_file),
                            label: const Text('Upload File'),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: ElevatedButton.icon(
                            onPressed: () => _takePhoto(artifactProvider),
                            icon: const Icon(Icons.camera_alt),
                            label: const Text('Take Photo'),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const Divider(),
              Expanded(
                child: artifactProvider.artifacts.isEmpty
                    ? const Center(
                        child: Text('No artifacts uploaded yet'),
                      )
                    : ListView.builder(
                        itemCount: artifactProvider.artifacts.length,
                        itemBuilder: (context, index) {
                          final artifact = artifactProvider.artifacts[index];
                          return _buildArtifactCard(artifact, artifactProvider);
                        },
                      ),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildArtifactCard(Artifact artifact, ArtifactProvider provider) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: ListTile(
        leading: Icon(
          _getIconForType(artifact.type),
          size: 40,
          color: _getColorForType(artifact.type),
        ),
        title: Text(artifact.name),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('${(artifact.fileSize / 1024).toStringAsFixed(1)} KB'),
            Text('Uploaded by: ${artifact.uploadedBy}'),
            Text(
              'Date: ${artifact.uploadedAt.toString().split(' ')[0]}',
              style: const TextStyle(fontSize: 12),
            ),
          ],
        ),
        trailing: PopupMenuButton(
          itemBuilder: (context) => [
            const PopupMenuItem(
              value: 'view_audit',
              child: Text('View Audit Trail'),
            ),
            const PopupMenuItem(
              value: 'delete',
              child: Text('Delete'),
            ),
          ],
          onSelected: (value) {
            if (value == 'view_audit') {
              _showAuditTrail(artifact);
            } else if (value == 'delete') {
              _confirmDelete(artifact, provider);
            }
          },
        ),
      ),
    );
  }

  IconData _getIconForType(ArtifactType type) {
    switch (type) {
      case ArtifactType.document:
        return Icons.description;
      case ArtifactType.photo:
        return Icons.photo;
      case ArtifactType.certificate:
        return Icons.card_membership;
      case ArtifactType.other:
        return Icons.attach_file;
    }
  }

  Color _getColorForType(ArtifactType type) {
    switch (type) {
      case ArtifactType.document:
        return Colors.blue;
      case ArtifactType.photo:
        return Colors.green;
      case ArtifactType.certificate:
        return Colors.orange;
      case ArtifactType.other:
        return Colors.grey;
    }
  }

  Future<void> _pickFile(ArtifactProvider provider) async {
    final result = await FilePicker.platform.pickFiles();
    if (result != null) {
      final file = result.files.first;
      final artifact = Artifact(
        id: DateTime.now().millisecondsSinceEpoch.toString(),
        name: file.name,
        type: ArtifactType.document,
        filePath: file.path!,
        fileSize: file.size,
        uploadedAt: DateTime.now(),
        uploadedBy: 'Workshop User', // TODO: Get from user profile
      );
      
      await provider.addArtifact(artifact, 'Workshop User');
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('File uploaded successfully!')),
        );
      }
    }
  }

  Future<void> _takePhoto(ArtifactProvider provider) async {
    final XFile? photo = await _imagePicker.pickImage(
      source: ImageSource.camera,
      imageQuality: 80,
    );
    
    if (photo != null) {
      // Show reminder about no faces
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Photo Guidelines'),
          content: const Text(
            'Please confirm this photo:\n\n'
            '✓ Shows work, tools, or equipment\n'
            '✓ Does NOT include any faces\n'
            '✓ Provides evidence of skills',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Confirm'),
            ),
          ],
        ),
      );
      
      if (confirmed == true) {
        final artifact = Artifact(
          id: DateTime.now().millisecondsSinceEpoch.toString(),
          name: 'Photo_${DateTime.now().millisecondsSinceEpoch}.jpg',
          type: ArtifactType.photo,
          filePath: photo.path,
          fileSize: await photo.length(),
          uploadedAt: DateTime.now(),
          uploadedBy: 'Workshop User',
          description: 'Workshop evidence photo',
        );
        
        await provider.addArtifact(artifact, 'Workshop User');
        
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Photo uploaded successfully!')),
          );
        }
      }
    }
  }

  void _showAuditTrail(Artifact artifact) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Audit Trail'),
        content: SizedBox(
          width: double.maxFinite,
          child: ListView.builder(
            shrinkWrap: true,
            itemCount: artifact.auditTrail.length,
            itemBuilder: (context, index) {
              final entry = artifact.auditTrail[index];
              return ListTile(
                title: Text(entry.action),
                subtitle: Text(
                  'By: ${entry.performedBy}\n'
                  'At: ${entry.timestamp}',
                ),
              );
            },
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  void _confirmDelete(Artifact artifact, ArtifactProvider provider) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Artifact'),
        content: Text('Are you sure you want to delete ${artifact.name}?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              provider.deleteArtifact(artifact.id, 'Workshop User');
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Artifact deleted')),
              );
            },
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }
}
