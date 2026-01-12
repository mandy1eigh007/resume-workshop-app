import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/resume_provider.dart';
import '../providers/content_master_provider.dart';
import '../utils/skills_inference.dart';

class SkillsSelector extends StatefulWidget {
  const SkillsSelector({super.key});

  @override
  State<SkillsSelector> createState() => _SkillsSelectorState();
}

class _SkillsSelectorState extends State<SkillsSelector> {
  String _selectedCategory = 'All Skills';

  @override
  Widget build(BuildContext context) {
    return Consumer2<ResumeProvider, ContentMasterProvider>(
      builder: (context, resumeProvider, contentProvider, _) {
        final skills = resumeProvider.currentResume?.skills;
        
        // Get skills from ContentMasterProvider or fallback to inference
        final allSkills = contentProvider.isLoaded 
            ? contentProvider.getAllSkills()
            : SkillsInference.getCanonSkillsByTrade('GENERAL');
        
        final transferableSkills = contentProvider.isLoaded
            ? contentProvider.getTransferableSkills()
            : [];
        
        final jobSpecificSkills = contentProvider.isLoaded
            ? contentProvider.getJobSpecificSkills()
            : [];
        
        final selfManagementSkills = contentProvider.isLoaded
            ? contentProvider.getSelfManagementSkills()
            : [];
        
        // Determine which skills to display
        List<String> displaySkills;
        switch (_selectedCategory) {
          case 'Transferable':
            displaySkills = transferableSkills;
            break;
          case 'Job-Specific':
            displaySkills = jobSpecificSkills;
            break;
          case 'Self-Management':
            displaySkills = selfManagementSkills;
            break;
          default:
            displaySkills = allSkills;
        }

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

                // Quick-Add Skills (canon from CONTENT_MASTER.md)
                const Text(
                  'Quick-Add (select from canon):',
                  style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                if (contentProvider.isLoaded) ...[
                  DropdownButtonFormField<String>(
                    value: _selectedCategory,
                    decoration: const InputDecoration(
                      labelText: 'Skill Category',
                      border: OutlineInputBorder(),
                      contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    ),
                    items: const [
                      DropdownMenuItem(value: 'All Skills', child: Text('All Skills')),
                      DropdownMenuItem(value: 'Transferable', child: Text('Transferable')),
                      DropdownMenuItem(value: 'Job-Specific', child: Text('Job-Specific')),
                      DropdownMenuItem(value: 'Self-Management', child: Text('Self-Management')),
                    ],
                    onChanged: (value) {
                      setState(() {
                        _selectedCategory = value!;
                      });
                    },
                  ),
                  const SizedBox(height: 12),
                  if (displaySkills.isNotEmpty)
                    Wrap(
                      spacing: 8,
                      runSpacing: 4,
                      children: displaySkills.map((skill) {
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
                    )
                  else
                    const Text(
                      'No skills available in this category.',
                      style: TextStyle(fontSize: 12, color: Colors.grey),
                    ),
                ] else ...[
                  const CircularProgressIndicator(),
                  const SizedBox(height: 8),
                  const Text(
                    'Loading skills from CONTENT_MASTER.md...',
                    style: TextStyle(fontSize: 12, color: Colors.grey),
                  ),
                ],

                const SizedBox(height: 16),
                const Divider(),
                const SizedBox(height: 8),

                // Summary
                Text(
                  'Total Skills Selected: ${skills?.all.length ?? 0}',
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 4),
                const Text(
                  'Maximum 12 skills recommended. Skills are deduplicated across all categories.',
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
