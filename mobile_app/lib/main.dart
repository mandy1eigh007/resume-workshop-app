import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'screens/home_screen.dart';
import 'providers/resume_provider.dart';
import 'providers/artifact_provider.dart';
import 'providers/progress_provider.dart';
import 'providers/quick_win_provider.dart';
import 'providers/content_master_provider.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize ContentMasterProvider and load content
  final contentMasterProvider = ContentMasterProvider();
  await contentMasterProvider.loadContent();
  
  runApp(ResumeWorkshopApp(contentMasterProvider: contentMasterProvider));
}

class ResumeWorkshopApp extends StatelessWidget {
  final ContentMasterProvider contentMasterProvider;
  
  const ResumeWorkshopApp({
    super.key,
    required this.contentMasterProvider,
  });

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider.value(value: contentMasterProvider),
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
