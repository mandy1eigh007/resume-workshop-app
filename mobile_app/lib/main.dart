import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'screens/home_screen.dart';
import 'providers/resume_provider.dart';
import 'providers/artifact_provider.dart';
import 'providers/progress_provider.dart';
import 'providers/quick_win_provider.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ResumeWorkshopApp());
}

class ResumeWorkshopApp extends StatelessWidget {
  const ResumeWorkshopApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ResumeProvider()),
        ChangeNotifierProvider(create: (_) => ArtifactProvider()),
        ChangeNotifierProvider(create: (_) => ProgressProvider()),
        ChangeNotifierProvider(create: (_) => QuickWinProvider()),
      ],
      child: MaterialApp(
        title: 'Resume Workshop - Seattle Tri-County',
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: Colors.blue,
            brightness: Brightness.light,
          ),
          useMaterial3: true,
          appBarTheme: const AppBarTheme(
            centerTitle: true,
            elevation: 2,
          ),
        ),
        home: const HomeScreen(),
        debugShowCheckedModeBanner: false,
      ),
    );
  }
}
