import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/resume.dart';
import '../providers/resume_provider.dart';

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
              const SizedBox(height: 16),
              const Text(
                'Examples:',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
              ),
              const SizedBox(height: 4),
              const Text(
                '• "Cut and set 30+ ft of conduit per mark; verified offsets with level; QC\'d by lead before pull."\n'
                '• "Loaded/unloaded 20+ pallets; strapped and tagged; kept walkways clear per JHA."',
                style: TextStyle(fontSize: 11, fontStyle: FontStyle.italic),
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
