import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/quick_win.dart';
import '../providers/quick_win_provider.dart';

class QuickWinForm extends StatefulWidget {
  const QuickWinForm({super.key});

  @override
  State<QuickWinForm> createState() => _QuickWinFormState();
}

class _QuickWinFormState extends State<QuickWinForm> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _descriptionController = TextEditingController();
  final List<TextEditingController> _stepControllers = [TextEditingController()];
  
  QuickWinCategory _category = QuickWinCategory.certification;
  QuickWinPriority _priority = QuickWinPriority.medium;
  DateTime _deadline = DateTime.now().add(const Duration(days: 7));

  @override
  void dispose() {
    _titleController.dispose();
    _descriptionController.dispose();
    for (final controller in _stepControllers) {
      controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Add Quick Win'),
      content: SingleChildScrollView(
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Card(
                color: Colors.purple50,
                child: Padding(
                  padding: EdgeInsets.all(8),
                  child: Text(
                    'Quick Wins are actions you can complete within 2 weeks',
                    style: TextStyle(fontSize: 11),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _titleController,
                decoration: const InputDecoration(
                  labelText: 'Title',
                  hintText: 'Get OSHA-10 card',
                  border: OutlineInputBorder(),
                ),
                validator: (value) => 
                    value?.isEmpty ?? true ? 'Required' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _descriptionController,
                decoration: const InputDecoration(
                  labelText: 'Description',
                  border: OutlineInputBorder(),
                ),
                maxLines: 2,
                validator: (value) => 
                    value?.isEmpty ?? true ? 'Required' : null,
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<QuickWinCategory>(
                value: _category,
                decoration: const InputDecoration(
                  labelText: 'Category',
                  border: OutlineInputBorder(),
                ),
                items: QuickWinCategory.values.map((cat) {
                  return DropdownMenuItem(
                    value: cat,
                    child: Text(cat.name),
                  );
                }).toList(),
                onChanged: (value) {
                  setState(() {
                    _category = value!;
                  });
                },
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<QuickWinPriority>(
                value: _priority,
                decoration: const InputDecoration(
                  labelText: 'Priority',
                  border: OutlineInputBorder(),
                ),
                items: QuickWinPriority.values.map((priority) {
                  return DropdownMenuItem(
                    value: priority,
                    child: Text(priority.name.toUpperCase()),
                  );
                }).toList(),
                onChanged: (value) {
                  setState(() {
                    _priority = value!;
                  });
                },
              ),
              const SizedBox(height: 12),
              ListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Deadline'),
                subtitle: Text(
                  _deadline.toString().split(' ')[0],
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                trailing: IconButton(
                  icon: const Icon(Icons.calendar_today),
                  onPressed: () => _selectDeadline(),
                ),
              ),
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('Action Steps:', style: TextStyle(fontWeight: FontWeight.bold)),
                  IconButton(
                    onPressed: _addStepField,
                    icon: const Icon(Icons.add_circle, size: 20),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              ..._stepControllers.asMap().entries.map((entry) {
                final index = entry.key;
                final controller = entry.value;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: TextFormField(
                    controller: controller,
                    decoration: InputDecoration(
                      labelText: 'Step ${index + 1}',
                      border: const OutlineInputBorder(),
                      suffixIcon: _stepControllers.length > 1
                          ? IconButton(
                              onPressed: () => _removeStepField(index),
                              icon: const Icon(Icons.remove_circle, size: 20),
                            )
                          : null,
                    ),
                    validator: (value) => 
                        value?.isEmpty ?? true ? 'Required' : null,
                  ),
                );
              }),
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
          onPressed: () => _saveQuickWin(context),
          child: const Text('Save'),
        ),
      ],
    );
  }

  void _addStepField() {
    setState(() {
      _stepControllers.add(TextEditingController());
    });
  }

  void _removeStepField(int index) {
    setState(() {
      _stepControllers[index].dispose();
      _stepControllers.removeAt(index);
    });
  }

  Future<void> _selectDeadline() async {
    final now = DateTime.now();
    final twoWeeksFromNow = now.add(const Duration(days: 14));
    
    final picked = await showDatePicker(
      context: context,
      initialDate: _deadline,
      firstDate: now,
      lastDate: twoWeeksFromNow,
      helpText: 'Select deadline (max 2 weeks)',
    );
    
    if (picked != null) {
      setState(() {
        _deadline = picked;
      });
    }
  }

  void _saveQuickWin(BuildContext context) {
    if (!_formKey.currentState!.validate()) return;

    final quickWin = QuickWin(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      title: _titleController.text,
      description: _descriptionController.text,
      category: _category,
      priority: _priority,
      deadline: _deadline,
      status: QuickWinStatus.notStarted,
      actionSteps: _stepControllers.map((c) => c.text).toList(),
      createdAt: DateTime.now(),
    );

    Provider.of<QuickWinProvider>(context, listen: false).addQuickWin(quickWin);
    
    Navigator.pop(context);
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Quick Win added successfully!')),
    );
  }
}
