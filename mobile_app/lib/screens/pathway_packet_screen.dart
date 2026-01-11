import 'package:flutter/material.dart';
import '../models/pathway_packet.dart';

class PathwayPacketScreen extends StatefulWidget {
  const PathwayPacketScreen({super.key});

  @override
  State<PathwayPacketScreen> createState() => _PathwayPacketScreenState();
}

class _PathwayPacketScreenState extends State<PathwayPacketScreen> {
  Trade _selectedTrade = Trade.electrical;
  final _studentNameController = TextEditingController();
  final List<TextEditingController> _reflectionControllers = [
    TextEditingController(),
  ];

  @override
  void dispose() {
    _studentNameController.dispose();
    for (final controller in _reflectionControllers) {
      controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Stand-Out Pathway Packet'),
        subtitle: const Text('Trade-Specific Guidance'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Card(
              color: Colors.blue50,
              child: Padding(
                padding: EdgeInsets.all(12),
                child: Text(
                  'Build your pathway packet with trade-specific sections and evidence-based content for apprenticeship programs.',
                  style: TextStyle(fontSize: 14),
                ),
              ),
            ),
            const SizedBox(height: 24),
            const Text(
              'Student Information',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            TextFormField(
              controller: _studentNameController,
              decoration: const InputDecoration(
                labelText: 'Student Name',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.person),
              ),
            ),
            const SizedBox(height: 24),
            const Text(
              'Select Your Trade',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<Trade>(
              value: _selectedTrade,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.work),
              ),
              items: Trade.values.map((trade) {
                return DropdownMenuItem(
                  value: trade,
                  child: Text(trade.displayName),
                );
              }).toList(),
              onChanged: (value) {
                setState(() {
                  _selectedTrade = value!;
                });
              },
            ),
            const SizedBox(height: 24),
            const Text(
              'Program Reality Check',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Text(_selectedTrade.programRealityCheck),
              ),
            ),
            const SizedBox(height: 24),
            const Text(
              'Stand-Out Moves for This Trade',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            ..._selectedTrade.standOutMoves.map((move) => Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    leading: const Icon(Icons.star, color: Colors.orange),
                    title: Text(move),
                  ),
                )),
            const SizedBox(height: 24),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Student Reflections',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                IconButton(
                  onPressed: _addReflectionField,
                  icon: const Icon(Icons.add_circle),
                  tooltip: 'Add another reflection',
                ),
              ],
            ),
            const SizedBox(height: 8),
            ..._reflectionControllers.asMap().entries.map((entry) {
              final index = entry.key;
              final controller = entry.value;
              return Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: TextFormField(
                  controller: controller,
                  decoration: InputDecoration(
                    labelText: 'Reflection ${index + 1}',
                    hintText: 'Describe a specific experience or learning...',
                    border: const OutlineInputBorder(),
                    suffixIcon: _reflectionControllers.length > 1
                        ? IconButton(
                            onPressed: () => _removeReflectionField(index),
                            icon: const Icon(Icons.remove_circle),
                          )
                        : null,
                  ),
                  maxLines: 4,
                ),
              );
            }),
            const SizedBox(height: 32),
            ElevatedButton.icon(
              onPressed: _savePathwayPacket,
              icon: const Icon(Icons.save),
              label: const Text('Save Pathway Packet'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: _exportPathwayPacket,
              icon: const Icon(Icons.download),
              label: const Text('Export to PDF'),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _addReflectionField() {
    setState(() {
      _reflectionControllers.add(TextEditingController());
    });
  }

  void _removeReflectionField(int index) {
    setState(() {
      _reflectionControllers[index].dispose();
      _reflectionControllers.removeAt(index);
    });
  }

  void _savePathwayPacket() {
    if (_studentNameController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter student name')),
      );
      return;
    }

    // TODO: Implement actual save logic with provider
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Pathway packet saved successfully!')),
    );
  }

  void _exportPathwayPacket() {
    // TODO: Implement PDF export
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('PDF export coming soon...')),
    );
  }
}
