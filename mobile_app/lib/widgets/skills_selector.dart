import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/resume_provider.dart';
import '../utils/skills_inference.dart';

class SkillsSelector extends StatefulWidget {
  const SkillsSelector({super.key});

  @override
  State<SkillsSelector> createState() => _SkillsSelectorState();
}

class _SkillsSelectorState extends State<SkillsSelector> {
  String _selectedTrade = 'ELECTRICAL';

  @override
  Widget build(BuildContext context) {
    return Consumer<ResumeProvider>(
      builder: (context, resumeProvider, _) {
        final skills = resumeProvider.currentResume?.skills;
        final canonSkills = SkillsInference.getCanonSkillsByTrade(_selectedTrade);

        return Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Text(
                      'Skills Categories',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                    const Spacer(),
                    TextButton.icon(
                      onPressed: () {
                        resumeProvider.inferSkillsFromBullets();
                      },
                      icon: const Icon(Icons.auto_awesome, size: 16),
                      label: const Text('Auto-Infer'),
                    ),
                  ],
                ),
                const SizedBox(height: 16),

                // Suggested Skills (from text)
                if (skills?.suggested.isNotEmpty ?? false) ...[
                  const Text(
                    'Suggested (from resume text):',
                    style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 4,
                    children: skills!.suggested.map((skill) => Chip(
                      label: Text(skill, style: const TextStyle(fontSize: 12)),
                      backgroundColor: Colors.blue[100],
                      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    )).toList(),
                  ),
                  const SizedBox(height: 16),
                ],

                // Inferred Skills (from bullets)
                if (skills?.inferred.isNotEmpty ?? false) ...[
                  const Text(
                    'Inferred (from measurable bullets):',
                    style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 4,
                    children: skills!.inferred.map((skill) => Chip(
                      label: Text(skill, style: const TextStyle(fontSize: 12)),
                      backgroundColor: Colors.green[100],
                      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    )).toList(),
                  ),
                  const SizedBox(height: 16),
                ],

                // Quick-Add Skills (canon)
                const Text(
                  'Quick-Add (select from canon):',
                  style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                DropdownButtonFormField<String>(
                  value: _selectedTrade,
                  decoration: const InputDecoration(
                    labelText: 'Trade',
                    border: OutlineInputBorder(),
                    contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  ),
                  items: const [
                    DropdownMenuItem(value: 'ELECTRICAL', child: Text('Electrical')),
                    DropdownMenuItem(value: 'PIPE TRADES', child: Text('Pipe Trades/HVAC')),
                    DropdownMenuItem(value: 'POWER LINE', child: Text('Power Line')),
                    DropdownMenuItem(value: 'GENERAL', child: Text('General Construction')),
                  ],
                  onChanged: (value) {
                    setState(() {
                      _selectedTrade = value!;
                    });
                  },
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 4,
                  children: canonSkills.map((skill) {
                    final isSelected = skills?.quickAdd.contains(skill) ?? false;
                    return FilterChip(
                      label: Text(skill, style: const TextStyle(fontSize: 12)),
                      selected: isSelected,
                      onSelected: (selected) {
                        if (selected) {
                          resumeProvider.addQuickAddSkill(skill);
                        }
                      },
                      backgroundColor: Colors.orange[50],
                      selectedColor: Colors.orange[200],
                      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    );
                  }).toList(),
                ),

                const SizedBox(height: 16),
                const Divider(),
                const SizedBox(height: 8),

                // Summary
                Text(
                  'Total Skills: ${skills?.all.length ?? 0}',
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 4),
                const Text(
                  'Skills are deduplicated across all categories.',
                  style: TextStyle(fontSize: 11, color: Colors.grey),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
