import 'package:flutter/material.dart';
import 'screens/home_screen.dart';

void main() {
  runApp(const ResumeWorkshopApp());
}

class ResumeWorkshopApp extends StatelessWidget {
  const ResumeWorkshopApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Resume Workshop',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      home: const HomeScreen(),
    );
  }
}
