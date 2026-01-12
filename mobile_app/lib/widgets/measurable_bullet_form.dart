import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/resume.dart';
import '../providers/resume_provider.dart';
import '../providers/content_master_provider.dart';

class MeasurableBulletForm extends StatefulWidget {
  const MeasurableBulletForm({super.key});

  @override
  State<MeasurableBulletForm> createState() => _MeasurableBulletFormState();
}

class _MeasurableBulletFormState extends State<MeasurableBulletForm> {
  final _formKey = GlobalKey<FormState>();
  final _actionController = TextEditingController();
  final _quantityController = TextEditingController();
  final _safetyController = TextEditingController();
  final _verificationController = TextEditingController();
  
  String? _selectedRole;
  bool _showRoleSuggestions = false;

  @override
  void dispose() {
    _actionController.dispose();
    _quantityController.dispose();
    _safetyController.dispose();
    _verificationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Add Measurable Bullet'),
      content: SingleChildScrollView(
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Card(
                color: Colors.blue50,
                child: Padding(
                  padding: EdgeInsets.all(8),
                  child: Text(
                    'Template: Action + Quantity/Tool/Spec + Safety/Quality + Verification',
                    style: TextStyle(fontSize: 11),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              
              // Role selector for suggestions
              Consumer<ContentMasterProvider>(
                builder: (context, contentProvider, _) {
                  if (!contentProvider.isLoaded) {
                    return const SizedBox.shrink();
                  }
                  
                  final roles = contentProvider.getAvailableRoles();
                  
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              'Role-Based Suggestions',
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.bold,
                                color: Colors.grey[700],
                              ),
                            ),
                          ),
                          Switch(
                            value: _showRoleSuggestions,
                            onChanged: (value) {
                              setState(() {
                                _showRoleSuggestions = value;
                                if (!value) {
                                  _selectedRole = null;
                                }
                              });
                            },
                          ),
                        ],
                      ),
                      if (_showRoleSuggestions && roles.isNotEmpty) ...[
                        const SizedBox(height: 8),
                        DropdownButtonFormField<String>(
                          value: _selectedRole,
                          decoration: const InputDecoration(
                            labelText: 'Select Role for Examples',
                            border: OutlineInputBorder(),
                            contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                          ),
                          items: [
                            const DropdownMenuItem(
                              value: null,
                              child: Text('-- Select a role --'),
                            ),
                            ...roles.map((role) => DropdownMenuItem(
                                  value: role,
                                  child: Text(role, style: const TextStyle(fontSize: 12)),
                                )),
                          ],
                          onChanged: (value) {
                            setState(() {
                              _selectedRole = value;
                            });
                          },
                        ),
                        if (_selectedRole != null) ...[
                          const SizedBox(height: 8),
                          _buildRoleBulletSuggestions(contentProvider),
                        ],
                      ],
                      const SizedBox(height: 16),
                    ],
                  );
                },
              ),
              
              TextFormField(
                controller: _actionController,
                decoration: const InputDecoration(
                  labelText: 'Action',
                  hintText: 'Staged and labeled',
                  border: OutlineInputBorder(),
                ),
                validator: (value) => 
                    value?.isEmpty ?? true ? 'Required' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _quantityController,
                decoration: const InputDecoration(
                  labelText: 'Quantity/Tool/Spec',
                  hintText: '120+ devices; matched counts to plan sheets',
                  border: OutlineInputBorder(),
                ),
                validator: (value) => 
                    value?.isEmpty ?? true ? 'Required' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _safetyController,
                decoration: const InputDecoration(
                  labelText: 'Safety/Quality',
                  hintText: 'maintained clear aisles and PPE',
                  border: OutlineInputBorder(),
                ),
                validator: (value) => 
                    value?.isEmpty ?? true ? 'Required' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _verificationController,
                decoration: const InputDecoration(
                  labelText: 'Verification',
                  hintText: 'QC\'d by lead before pull',
                  border: OutlineInputBorder(),
                ),
                validator: (value) => 
                    value?.isEmpty ?? true ? 'Required' : null,
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: () => _saveBullet(context),
          child: const Text('Add Bullet'),
        ),
      ],
    );
  }
  
  Widget _buildRoleBulletSuggestions(ContentMasterProvider contentProvider) {
    final bullets = contentProvider.getBulletsForRole(_selectedRole!);
    
    if (bullets.isEmpty) {
      return const Card(
        child: Padding(
          padding: EdgeInsets.all(8),
          child: Text(
            'No bullet examples available for this role.',
            style: TextStyle(fontSize: 11, color: Colors.grey),
          ),
        ),
      );
    }
    
    return Card(
      color: Colors.green[50],
      child: Padding(
        padding: const EdgeInsets.all(8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Example bullets for $_selectedRole:',
              style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 4),
            ...bullets.take(3).map((bullet) => Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text(
                    '• $bullet',
                    style: const TextStyle(fontSize: 10, fontStyle: FontStyle.italic),
                  ),
                )),
            if (bullets.length > 3)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(
                  '... and ${bullets.length - 3} more',
                  style: const TextStyle(fontSize: 10, color: Colors.grey),
                ),
              ),
          ],
        ),
      ),
    );
  }

  void _saveBullet(BuildContext context) {
    if (!_formKey.currentState!.validate()) return;

    final bullet = MeasurableBullet(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      action: _actionController.text,
      quantityOrTool: _quantityController.text,
      safetyQuality: _safetyController.text,
      verification: _verificationController.text,
    );

    // TODO: Add to specific work experience
    // For now, just demonstrate the feature
    Navigator.pop(context);
    
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Bullet added! Skills will be inferred automatically.')),
    );
  }
}
