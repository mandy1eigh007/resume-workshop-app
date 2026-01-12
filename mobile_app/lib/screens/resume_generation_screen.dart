import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/resume.dart';
import '../providers/resume_provider.dart';
import '../providers/content_master_provider.dart';
import '../widgets/measurable_bullet_form.dart';
import '../widgets/skills_selector.dart';

class ResumeGenerationScreen extends StatefulWidget {
  const ResumeGenerationScreen({super.key});

  @override
  State<ResumeGenerationScreen> createState() => _ResumeGenerationScreenState();
}

class _ResumeGenerationScreenState extends State<ResumeGenerationScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  final _phoneController = TextEditingController();
  final _cityController = TextEditingController();
  final _stateController = TextEditingController(text: 'WA');
  final _objectiveController = TextEditingController();
  
  String? _selectedTrade;
  String? _selectedObjective;

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _phoneController.dispose();
    _cityController.dispose();
    _stateController.dispose();
    _objectiveController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Resume Builder'),
        subtitle: const Text('Evidence-First Approach'),
      ),
      body: Consumer<ResumeProvider>(
        builder: (context, resumeProvider, _) {
          if (resumeProvider.isLoading) {
            return const Center(child: CircularProgressIndicator());
          }

          return SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text(
                    'Personal Information',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _nameController,
                    decoration: const InputDecoration(
                      labelText: 'Full Name',
                      border: OutlineInputBorder(),
                      prefixIcon: Icon(Icons.person),
                    ),
                    validator: (value) =>
                        value?.isEmpty ?? true ? 'Required' : null,
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _emailController,
                    decoration: const InputDecoration(
                      labelText: 'Email',
                      border: OutlineInputBorder(),
                      prefixIcon: Icon(Icons.email),
                    ),
                    keyboardType: TextInputType.emailAddress,
                    validator: (value) {
                      if (value?.isEmpty ?? true) return 'Required';
                      if (!value!.contains('@')) return 'Invalid email';
                      return null;
                    },
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _phoneController,
                    decoration: const InputDecoration(
                      labelText: 'Phone',
                      border: OutlineInputBorder(),
                      prefixIcon: Icon(Icons.phone),
                    ),
                    keyboardType: TextInputType.phone,
                    validator: (value) =>
                        value?.isEmpty ?? true ? 'Required' : null,
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Expanded(
                        flex: 2,
                        child: TextFormField(
                          controller: _cityController,
                          decoration: const InputDecoration(
                            labelText: 'City',
                            border: OutlineInputBorder(),
                            prefixIcon: Icon(Icons.location_city),
                          ),
                          validator: (value) =>
                              value?.isEmpty ?? true ? 'Required' : null,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: TextFormField(
                          controller: _stateController,
                          decoration: const InputDecoration(
                            labelText: 'State',
                            border: OutlineInputBorder(),
                          ),
                          validator: (value) =>
                              value?.isEmpty ?? true ? 'Required' : null,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  const Text(
                    'Objective',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Select a trade and choose from pre-approved objective starters, or write your own.',
                    style: TextStyle(fontSize: 12, color: Colors.grey),
                  ),
                  const SizedBox(height: 12),
                  Consumer<ContentMasterProvider>(
                    builder: (context, contentProvider, _) {
                      if (!contentProvider.isLoaded) {
                        return const Card(
                          child: Padding(
                            padding: EdgeInsets.all(16),
                            child: Text('Loading objective options...'),
                          ),
                        );
                      }
                      
                      final trades = contentProvider.getAvailableTrades();
                      
                      return Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          if (trades.isNotEmpty) ...[
                            DropdownButtonFormField<String>(
                              value: _selectedTrade,
                              decoration: const InputDecoration(
                                labelText: 'Select Trade (Optional)',
                                border: OutlineInputBorder(),
                                prefixIcon: Icon(Icons.construction),
                              ),
                              items: [
                                const DropdownMenuItem(
                                  value: null,
                                  child: Text('-- Select a trade --'),
                                ),
                                ...trades.map((trade) => DropdownMenuItem(
                                      value: trade,
                                      child: Text(trade),
                                    )),
                              ],
                              onChanged: (value) {
                                setState(() {
                                  _selectedTrade = value;
                                  _selectedObjective = null;
                                  _objectiveController.clear();
                                });
                              },
                            ),
                            const SizedBox(height: 12),
                          ],
                          if (_selectedTrade != null) ...[
                            DropdownButtonFormField<String>(
                              value: _selectedObjective,
                              decoration: const InputDecoration(
                                labelText: 'Choose Objective Starter',
                                border: OutlineInputBorder(),
                                prefixIcon: Icon(Icons.lightbulb_outline),
                              ),
                              items: _buildObjectiveDropdownItems(contentProvider),
                              onChanged: (value) {
                                setState(() {
                                  _selectedObjective = value;
                                  _objectiveController.text = value ?? '';
                                });
                              },
                            ),
                            const SizedBox(height: 12),
                          ],
                          TextFormField(
                            controller: _objectiveController,
                            decoration: InputDecoration(
                              labelText: _selectedTrade == null 
                                  ? 'Write Your Own Objective (Optional)'
                                  : 'Edit Objective (Optional)',
                              hintText: _selectedTrade == null
                                  ? 'Seeking electrical apprenticeship to apply OSHA-10 training...'
                                  : 'Customize the selected objective...',
                              border: const OutlineInputBorder(),
                            ),
                            maxLines: 3,
                          ),
                        ],
                      );
                    },
                  ),
                  const SizedBox(height: 24),
                  const Text(
                    'Work Experience & Measurable Bullets',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  const Card(
                    color: Colors.blue50,
                    child: Padding(
                      padding: EdgeInsets.all(12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Evidence-First Template:',
                            style: TextStyle(fontWeight: FontWeight.bold),
                          ),
                          SizedBox(height: 4),
                          Text(
                            'Action + Quantity/Tool/Spec + Safety/Quality + Verification',
                            style: TextStyle(fontSize: 12),
                          ),
                          SizedBox(height: 8),
                          Text(
                            'Example: "Staged and labeled 120+ devices; matched counts to plan sheets; maintained clear aisles and PPE."',
                            style: TextStyle(fontSize: 12, fontStyle: FontStyle.italic),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  if (resumeProvider.currentResume != null) ...[
                    ...resumeProvider.currentResume!.workHistory
                        .asMap()
                        .entries
                        .map((entry) {
                      final index = entry.key;
                      final work = entry.value;
                      return _buildWorkExperienceCard(
                        context,
                        work,
                        index,
                        resumeProvider,
                      );
                    }),
                  ],
                  const SizedBox(height: 16),
                  ElevatedButton.icon(
                    onPressed: () => _addMeasurableBullet(context),
                    icon: const Icon(Icons.add),
                    label: const Text('Add Measurable Bullet'),
                  ),
                  const SizedBox(height: 24),
                  const Text(
                    'Skills',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  const SkillsSelector(),
                  const SizedBox(height: 32),
                  ElevatedButton(
                    onPressed: () => _saveResume(context, resumeProvider),
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 16),
                    ),
                    child: const Text(
                      'Save Resume',
                      style: TextStyle(fontSize: 16),
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
  
  List<DropdownMenuItem<String>> _buildObjectiveDropdownItems(
    ContentMasterProvider contentProvider,
  ) {
    if (_selectedTrade == null) return [];
    
    final objectives = contentProvider.getObjectivesForTrade(_selectedTrade!);
    if (objectives == null) return [];
    
    final items = <DropdownMenuItem<String>>[
      const DropdownMenuItem(
        value: null,
        child: Text('-- Choose an objective --'),
      ),
    ];
    
    // Add apprenticeship objectives
    if (objectives.apprenticeshipObjectives.isNotEmpty) {
      items.add(const DropdownMenuItem(
        enabled: false,
        value: null,
        child: Text(
          'Apprenticeship Objectives:',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
        ),
      ));
      
      for (final objective in objectives.apprenticeshipObjectives) {
        items.add(DropdownMenuItem(
          value: objective,
          child: Text(
            objective.length > 60 ? '${objective.substring(0, 60)}...' : objective,
            style: const TextStyle(fontSize: 12),
          ),
        ));
      }
    }
    
    // Add job objectives
    if (objectives.jobObjectives.isNotEmpty) {
      items.add(const DropdownMenuItem(
        enabled: false,
        value: null,
        child: Text(
          'Job Objectives:',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
        ),
      ));
      
      for (final objective in objectives.jobObjectives) {
        items.add(DropdownMenuItem(
          value: objective,
          child: Text(
            objective.length > 60 ? '${objective.substring(0, 60)}...' : objective,
            style: const TextStyle(fontSize: 12),
          ),
        ));
      }
    }
    
    return items;
  }

  Widget _buildWorkExperienceCard(
    BuildContext context,
    WorkExperience work,
    int index,
    ResumeProvider provider,
  ) {
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              work.role,
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            Text('${work.company} - ${work.location}'),
            Text('${work.startDate} - ${work.endDate}'),
            const Divider(height: 24),
            const Text(
              'Measurable Bullets:',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            ...work.bullets.map((bullet) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('• '),
                      Expanded(child: Text(bullet.fullText)),
                    ],
                  ),
                )),
          ],
        ),
      ),
    );
  }

  void _addMeasurableBullet(BuildContext context) {
    showDialog(
      context: context,
      builder: (_) => const MeasurableBulletForm(),
    );
  }

  void _saveResume(BuildContext context, ResumeProvider provider) {
    if (!_formKey.currentState!.validate()) return;

    final resume = Resume(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      name: _nameController.text,
      email: _emailController.text,
      phone: _phoneController.text,
      city: _cityController.text,
      state: _stateController.text,
      objective: _objectiveController.text,
      workHistory: provider.currentResume?.workHistory ?? [],
      education: provider.currentResume?.education ?? [],
      certifications: provider.currentResume?.certifications ?? [],
      skills: provider.currentResume?.skills ?? SkillSet(),
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
    );

    provider.createResume(resume);
    
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Resume saved successfully!')),
    );
  }
}
