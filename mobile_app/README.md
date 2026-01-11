# Resume Workshop Mobile App

A Flutter mobile application for the Seattle Tri-County Construction Resume & Pathway Workshop, optimized for mobile workshops in King, Pierce, and Snohomish counties.

## Features

### 1. Resume Generation with Measurable Bullets
- **Evidence-First Approach**: Uses template: `Action + Quantity/Tool/Spec + Safety/Quality + Verification`
- **Example**: "Staged and labeled 120+ devices; matched counts to plan sheets; maintained clear aisles and PPE."
- **Auto-Validation**: Prompts for quantifiable metrics and evidence

### 2. Skills Inference
- **Suggested Skills**: Extracted from resume text
- **Inferred Skills**: Automatically derived from measurable bullets
- **Quick-Add Skills**: Canon skills organized by trade (Electrical, Pipe Trades, Power Line, etc.)
- **Deduplication**: Skills are automatically deduplicated across all categories

### 3. Artifact Uploads
- **File Support**: Upload PDFs, DOCX, images, certificates
- **Camera Integration**: Take photos directly from the app
- **Privacy Guidelines**: Clear warnings against including faces in photos
- **Audit Trail**: Complete tracking of who uploaded what and when

### 4. Stand-Out Pathway Packet Assembly
- **Trade-Specific Sections**: Electrical, Pipe Trades/HVAC-R, Outside Power, Power Line Clearance Tree Trimmer, and more
- **Program Reality Checks**: Real expectations for each apprenticeship program
- **Stand-Out Moves**: Specific actions to improve selection odds
- **Student Reflections**: Guided reflection prompts
- **Evidence Integration**: Automatically includes uploaded artifacts

### 5. Quick Win Prioritization (≤2 weeks)
- **Time-Bounded**: All Quick Wins must have deadlines ≤2 weeks from creation
- **Categories**: Certification, Documentation, Networking, Skill Building, Application
- **Priority Levels**: High, Medium, Low
- **Progress Tracking**: Mark as Not Started, In Progress, Completed, or Blocked
- **Overdue Alerts**: Visual indicators for overdue items

### 6. Progress Tracking
- **Interview Tracker**: Record interviews with companies, dates, types, and outcomes
- **Rank Movement**: Track apprenticeship program rankings over time
- **Application Status**: Monitor status of multiple applications
- **Visual Dashboard**: See progress at a glance with statistics and charts

### 7. Evidence-First Defaults
- **Measurable Prompts**: All forms guide users to provide quantifiable evidence
- **Template Examples**: Built-in examples show proper formatting
- **Validation**: Forms reject vague or non-measurable entries

### 8. Seattle Tri-County Optimization
- **Offline-First**: Works without internet connection for mobile workshops
- **Neutral Language**: Automatically filters union/non-union terminology
- **Local Focus**: Content optimized for King, Pierce, and Snohomish counties
- **Trade-Specific**: Covers all major construction trades in the region

## Installation

### Prerequisites
- Flutter SDK 3.0.0 or higher
- Dart SDK 3.0.0 or higher
- Android Studio / Xcode for mobile development

### Setup

1. **Clone the repository**
   ```bash
   cd mobile_app
   ```

2. **Install dependencies**
   ```bash
   flutter pub get
   ```

3. **Run the app**
   ```bash
   # For Android
   flutter run

   # For iOS (requires Mac with Xcode)
   flutter run
   ```

## Project Structure

```
mobile_app/
├── lib/
│   ├── main.dart                 # App entry point
│   ├── models/                   # Data models
│   │   ├── resume.dart
│   │   ├── artifact.dart
│   │   ├── pathway_packet.dart
│   │   ├── quick_win.dart
│   │   └── progress.dart
│   ├── providers/                # State management
│   │   ├── resume_provider.dart
│   │   ├── artifact_provider.dart
│   │   ├── quick_win_provider.dart
│   │   └── progress_provider.dart
│   ├── screens/                  # UI screens
│   │   ├── home_screen.dart
│   │   ├── resume_generation_screen.dart
│   │   ├── artifact_upload_screen.dart
│   │   ├── pathway_packet_screen.dart
│   │   ├── quick_wins_screen.dart
│   │   └── progress_tracking_screen.dart
│   ├── widgets/                  # Reusable widgets
│   │   ├── measurable_bullet_form.dart
│   │   ├── skills_selector.dart
│   │   └── quick_win_form.dart
│   ├── services/                 # Business logic
│   │   └── storage_service.dart
│   └── utils/                    # Utilities
│       ├── skills_inference.dart
│       └── neutral_language_filter.dart
├── assets/                       # Static assets
│   ├── images/
│   ├── data/
│   └── templates/
├── android/                      # Android configuration
├── ios/                          # iOS configuration
├── test/                         # Tests
└── pubspec.yaml                  # Dependencies
```

## Key Technologies

- **Flutter**: Cross-platform mobile framework
- **Provider**: State management
- **SharedPreferences**: Local data persistence
- **file_picker**: File selection
- **image_picker**: Camera and photo library access
- **permission_handler**: Runtime permissions
- **pdf**: PDF generation for exports

## Data Storage

The app uses **SharedPreferences** for local storage, which is suitable for:
- Quick startup and lightweight data
- Offline-first mobile workshops
- No server dependencies

For production with larger datasets, consider migrating to **SQLite** using the `sqflite` package.

## Permissions

### Android
- `CAMERA`: Take photos for evidence
- `READ_EXTERNAL_STORAGE`: Access files
- `WRITE_EXTERNAL_STORAGE`: Save documents
- `INTERNET`: Future API integration

### iOS
- `NSCameraUsageDescription`: Camera access for evidence photos
- `NSPhotoLibraryUsageDescription`: Photo library access

## Evidence-First Philosophy

This app implements an **evidence-first approach** to resume building:

1. **Quantifiable Metrics**: Every bullet point must include numbers (120+ devices, 30+ ft, 20+ pallets)
2. **Tools and Specs**: Mention specific tools, materials, or specifications
3. **Safety and Quality**: Reference safety protocols, PPE, or quality checks
4. **Verification**: Note who verified the work (lead, supervisor, QC)

**Bad Example**: "Helped with electrical work"
**Good Example**: "Staged and labeled 120+ devices; matched counts to plan sheets; maintained clear aisles and PPE."

## Neutral Language

The app automatically filters union/non-union terminology to maintain neutrality:

- **Banned Terms**: union, non-union, union shop, open shop, closed shop, etc.
- **Replacements**: "union apprenticeship" → "registered apprenticeship"
- **Audit**: All text inputs are filtered before storage

## Testing

```bash
# Run all tests
flutter test

# Run specific test file
flutter test test/models/resume_test.dart
```

## Building for Release

### Android APK
```bash
flutter build apk --release
```

### iOS IPA (requires Mac)
```bash
flutter build ios --release
```

## Contributing

This app is specifically designed for Seattle Tri-County construction pre-apprentice programs. When contributing:

1. Maintain the evidence-first philosophy
2. Ensure neutral language filtering
3. Keep Quick Wins constrained to ≤2 weeks
4. Follow the measurable bullet template
5. Add tests for new features

## Trade-Specific Content

The app includes specialized content for:
- **Electrical** (Inside, Residential, Limited Energy)
- **Pipe Trades / HVAC-R** (Plumber, Steamfitter, HVAC-R)
- **Outside Power**
- **Power Line Clearance Tree Trimmer**
- **Carpentry**
- **Ironworkers**
- **Laborers**
- **Operating Engineers**
- **Sheet Metal**

Each trade has:
- Program reality checks
- Stand-out moves
- Evidence bullet templates
- Study cues

## Support

For issues or questions:
1. Check the in-app help screens
2. Review the Stand-Out Playbook content
3. Contact your workshop instructor

## License

Copyright 2025 - Seattle Tri-County Construction Resume Workshop

## Version History

### 1.0.0 (2025-01-11)
- Initial release
- Resume generation with measurable bullets
- Skills inference (Suggested, Inferred, Quick-Add)
- Artifact uploads with camera support
- Stand-Out Pathway Packet with trade-specific sections
- Quick Win prioritization (≤2 weeks)
- Progress tracking (interviews and rank movement)
- Evidence-first defaults
- Neutral language filtering
- Offline-first architecture
