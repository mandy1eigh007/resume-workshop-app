# Resume Workshop Mobile App

A Flutter mobile application for the Seattle Tri-County Construction Resume Workshop.

## Overview

This mobile app provides a user-friendly interface for:
- Uploading resumes (PDF, DOCX, TXT formats)
- Processing and analyzing resume text
- Generating construction-focused DOCX documents

## Project Structure

```
lib/
├── main.dart                          # App entry point
└── screens/
    ├── home_screen.dart              # Main navigation screen
    ├── file_upload_screen.dart       # File upload functionality
    ├── text_processing_screen.dart   # Text analysis features
    └── docx_generation_screen.dart   # Document generation
```

## Features

### Home Screen
- Clean, card-based navigation interface
- Quick access to all main features
- Construction-themed branding

### File Upload Screen
- File picker for PDF, DOCX, TXT files
- URL input for remote resume loading
- Visual feedback for file selection

### Text Processing Screen
- Resume text input and analysis
- Job role detection
- Skills inference
- Construction industry mapping

### DOCX Generation Screen
- Multiple document types:
  - Construction-focused resume
  - Cover letter
  - Instructor pathway packet
- Template-based generation
- Document preview capability

## Getting Started

### Prerequisites

- Flutter SDK (3.0.0 or higher)
- Dart SDK
- Android Studio or Xcode (for mobile development)

### Installation

1. Clone the repository
2. Navigate to the project directory
3. Install dependencies:
   ```bash
   flutter pub get
   ```

### Running the App

```bash
flutter run
```

## Dependencies

- `flutter`: Flutter SDK
- `cupertino_icons`: iOS-style icons
- `file_picker`: File selection functionality
- `path_provider`: File system access

## Development

### Adding New Features

1. Create new screens in `lib/screens/`
2. Add navigation in `home_screen.dart`
3. Update this README

### Code Style

This project uses Flutter's recommended linting rules (`flutter_lints`).

## Integration Points

The mobile app is designed to work with the existing Python backend:
- Resume parsing functionality
- Job history database (Job_History_Master.docx)
- Document templates (resume_app_template.docx)
- Stand Out Playbook sections

## Future Enhancements

- Backend API integration
- Local storage for drafts
- Offline mode support
- PDF preview
- Share functionality
- Push notifications

## License

Part of the Seattle Tri-County Construction Resume Workshop project.
