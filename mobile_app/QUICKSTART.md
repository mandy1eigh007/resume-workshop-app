# Quick Start Guide - Flutter Mobile App

## For Workshop Instructors

### What is this app?

The Resume Workshop Mobile App helps construction pre-apprentices build evidence-based resumes and pathway packets optimized for Seattle tri-county apprenticeship programs.

### Key Features for Students

1. **Resume Builder**: Create resumes with measurable bullet points
2. **Skills Tracker**: Auto-detect skills from work experience
3. **Evidence Upload**: Take photos and upload certificates
4. **Pathway Packet**: Build trade-specific application packets
5. **Quick Wins**: Track 2-week action items
6. **Progress**: Monitor interviews and program rankings

### Workshop Use Cases

#### Scenario 1: New Student Starting Resume
1. Open app → Resume Builder
2. Fill in personal info (name, email, phone, city)
3. Add work experience
4. Use "Add Measurable Bullet" for each job duty
5. Skills are automatically inferred
6. Save and export

#### Scenario 2: Uploading Evidence
1. Open app → Upload Evidence
2. Choose "Take Photo" for work samples (NO FACES!)
3. Or choose "Upload File" for certificates
4. Each upload is tracked with audit trail

#### Scenario 3: Building Pathway Packet
1. Open app → Pathway Packet
2. Enter student name
3. Select trade (Electrical, Pipe, etc.)
4. View trade-specific guidance
5. Add reflections
6. Export to PDF (coming soon)

#### Scenario 4: Setting Quick Wins
1. Open app → Quick Wins
2. Tap "Add Quick Win"
3. Set title (e.g., "Get OSHA-10")
4. Choose deadline (max 2 weeks!)
5. Add action steps
6. Track progress

### Important Reminders

⚠️ **No Faces in Photos**: Privacy policy requires no identifiable faces
⚠️ **Neutral Language**: App automatically filters union/non-union terms
⚠️ **Evidence-First**: All bullets must have numbers and specifics
⚠️ **Quick Wins ≤2 weeks**: Deadlines must be achievable

### Evidence-First Template

Students should follow this pattern for all bullet points:

```
[Action] + [Quantity/Tool/Spec] + [Safety/Quality] + [Verification]
```

**Examples:**
- ✅ "Staged and labeled 120+ devices; matched counts to plan sheets; maintained clear aisles and PPE."
- ✅ "Cut and set 30+ ft of conduit per mark; verified offsets with level; QC'd by lead before pull."
- ❌ "Helped with electrical work" (Too vague!)

### Trades Covered

The app includes specialized content for:
1. Electrical (Inside, Residential, Limited Energy)
2. Pipe Trades / HVAC-R
3. Outside Power
4. Power Line Clearance Tree Trimmer
5. Carpentry
6. Ironworkers
7. Laborers
8. Operating Engineers
9. Sheet Metal

---

## For Developers

### Prerequisites

- Flutter SDK 3.0.0+
- Dart 3.0.0+
- Android Studio (for Android)
- Xcode (for iOS, Mac only)

### Quick Setup

```bash
# Navigate to mobile app directory
cd mobile_app

# Install dependencies
flutter pub get

# Run on connected device/emulator
flutter run

# Run tests
flutter test
```

### Project Structure

```
lib/
├── main.dart              # Entry point
├── models/                # Data models (6 files)
├── providers/             # State management (4 files)
├── screens/               # UI screens (6 files)
├── widgets/               # Reusable widgets (3 files)
├── services/              # Business logic (1 file)
└── utils/                 # Utilities (2 files)
```

### Key Files to Understand

1. **main.dart**: App initialization and provider setup
2. **models/resume.dart**: Core resume model with MeasurableBullet
3. **utils/skills_inference.dart**: Skill detection logic
4. **utils/neutral_language_filter.dart**: Union/non-union filtering
5. **services/storage_service.dart**: Local data persistence

### State Management

Using **Provider** pattern:
```dart
// Access provider
final resumeProvider = Provider.of<ResumeProvider>(context);

// Update state
await resumeProvider.createResume(resume);

// Listen to changes
Consumer<ResumeProvider>(
  builder: (context, provider, _) {
    return Text(provider.currentResume?.name ?? '');
  },
)
```

### Adding a New Feature

1. **Create Model** (if needed) in `lib/models/`
2. **Create Provider** (if needed) in `lib/providers/`
3. **Create Screen** in `lib/screens/`
4. **Create Widgets** (if needed) in `lib/widgets/`
5. **Add Tests** in `test/`
6. **Update Navigation** in relevant screens

### Testing

```bash
# Run all tests
flutter test

# Run specific test
flutter test test/models/resume_test.dart

# Run with coverage
flutter test --coverage
```

### Building for Release

```bash
# Android APK
flutter build apk --release

# Android App Bundle (for Play Store)
flutter build appbundle --release

# iOS (Mac only)
flutter build ios --release
```

### Common Issues

**Issue**: Dependencies not found
```bash
# Solution
flutter clean
flutter pub get
```

**Issue**: Build fails on Android
```bash
# Solution
cd android
./gradlew clean
cd ..
flutter run
```

**Issue**: iOS build fails
```bash
# Solution
cd ios
pod install
cd ..
flutter run
```

### Adding Dependencies

1. Edit `pubspec.yaml`
2. Run `flutter pub get`
3. Import in Dart files

Example:
```yaml
dependencies:
  new_package: ^1.0.0
```

```dart
import 'package:new_package/new_package.dart';
```

### Code Style

- Follow [Effective Dart](https://dart.dev/guides/language/effective-dart)
- Use `flutter analyze` to check code quality
- Format code with `flutter format lib/`

### Debugging

**Hot Reload**: Press `r` in terminal (saves time!)
**Hot Restart**: Press `R` in terminal
**DevTools**: Run `flutter pub global activate devtools`

### Performance Tips

1. Use `const` constructors where possible
2. Avoid rebuilding widgets unnecessarily
3. Use `ListView.builder` for long lists
4. Profile with `flutter run --profile`

---

## Frequently Asked Questions

### For Instructors

**Q: Can students use this offline?**
A: Yes! All data is stored locally on the device. No internet required.

**Q: How is data saved?**
A: Data is automatically saved to the device using local storage (SharedPreferences).

**Q: Can students export their resume?**
A: PDF export is coming in Phase 2. Currently, they can view and share screenshots.

**Q: What if a student adds union/non-union language?**
A: The app automatically filters and replaces such terms with neutral alternatives.

**Q: How many Quick Wins can a student have?**
A: Unlimited, but each must have a deadline ≤2 weeks.

### For Developers

**Q: Why SharedPreferences instead of SQLite?**
A: For Phase 1, SharedPreferences provides faster development, smaller app size, and is sufficient for the data volume. Migrate to SQLite in Phase 2 if needed.

**Q: Can I add more trades?**
A: Yes! Edit `lib/models/pathway_packet.dart` and add to the `Trade` enum. Add corresponding content in the extension methods.

**Q: How do I add more skill keywords?**
A: Edit `lib/utils/skills_inference.dart` and add to the `_skillKeywords` map.

**Q: Is there a backend API?**
A: Not yet. Phase 1 is offline-first. Phase 2 will add backend integration for syncing.

**Q: How do I customize the evidence template?**
A: Edit `lib/widgets/measurable_bullet_form.dart` to change the template structure and validation.

---

## Support & Contribution

### Getting Help

1. Check the [README.md](README.md) for detailed documentation
2. Review [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for architecture
3. Ask workshop coordinator for app-specific questions

### Contributing

This app is specifically designed for Seattle Tri-County construction workshops. When contributing:

1. Maintain evidence-first philosophy
2. Ensure neutral language filtering
3. Keep Quick Wins ≤2 weeks
4. Add tests for new features
5. Update documentation

### Version History

**v1.0.0** (Jan 11, 2025)
- Initial release
- All North Star spec features
- 9 trades supported
- Offline-first architecture
- Comprehensive testing

---

## Next Steps

### For Instructors
1. Install the app on workshop devices
2. Practice with sample student data
3. Review the evidence-first template with students
4. Emphasize the "no faces" photo policy

### For Developers
1. Set up development environment
2. Run tests to verify setup
3. Review the codebase structure
4. Try making a small change and hot reloading
5. Build for your target platform

---

**Happy Building! 🚀**

For questions or issues, contact your workshop coordinator or development team.
