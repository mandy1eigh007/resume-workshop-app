# CONTENT_MASTER.md Integration

This document describes the integration of CONTENT_MASTER.md into the Flutter mobile app for dynamic content loading.

## Overview

The app now loads trade-specific objectives, role bullets, skills, certifications, credential badges, and artifact templates from CONTENT_MASTER.md at runtime, making it easy to update content without code changes.

## Components

### 1. Models (`lib/models/content_master.dart`)

- **ContentMaster**: Main container for all parsed content
- **TradeObjectives**: Trade-specific apprenticeship and job objectives
- **SkillsCanon**: Three-bucket skill categories (Transferable, Job-Specific, Self-Management)
- **CredentialBadge**: Micro-credentials with resume phrases and proof requirements
- **ArtifactTemplate**: Templates for evidence tracking

### 2. Service (`lib/services/content_master_service.dart`)

**ContentMasterService** parses CONTENT_MASTER.md sections:

- **Section A**: Objective Starters Bank (10 per trade: 5 apprenticeship, 5 job)
- **Section B**: Role → Bullet Bank (duty bullets per role)
- **Section C**: Skills Canon (Transferable, Job-Specific, Self-Management)
- **Section D**: Certification Normalization Table
- **Section E**: Credential Micro-Badges Library (per trade)
- **Section G**: Proof Artifact Templates

### 3. Provider (`lib/providers/content_master_provider.dart`)

**ContentMasterProvider** manages content state:

- Loads content on app initialization
- Provides error handling and fallback to empty content
- Exposes methods to query content by trade, role, category
- Notifies listeners of loading state and errors

### 4. UI Integration

#### Resume Generation Screen
- Trade selector dropdown populated from CONTENT_MASTER.md
- Objective dropdown showing apprenticeship/job objectives for selected trade
- Editable objective field for customization

#### Skills Selector Widget
- Dynamic skill categories from Skills Canon
- Dropdown to filter by Transferable, Job-Specific, or Self-Management
- Skills loaded from CONTENT_MASTER.md instead of hardcoded

#### Artifact Upload Screen
- Shows artifact templates from CONTENT_MASTER.md
- Horizontal scrollable list of templates with field counts
- Helps users understand required evidence structure

#### Home Screen
- Loading indicator while parsing CONTENT_MASTER.md
- Status card showing loaded content counts (trades, skills, certifications)
- Error message if parsing fails (with fallback)

## Error Handling

1. **Asset Loading Failure**: Returns `ContentMaster.empty()` with error message
2. **Parsing Errors**: Caught and logged, empty collections returned for failed sections
3. **Fallback Mechanism**: App remains functional even if content fails to load
4. **User Notification**: Home screen displays loading status and errors

## Usage Examples

### Get objectives for a trade:
```dart
final contentProvider = Provider.of<ContentMasterProvider>(context);
final objectives = contentProvider.getObjectivesForTrade('Electrician – Inside (01)');
print(objectives?.apprenticeshipObjectives.first);
```

### Get all skills:
```dart
final allSkills = contentProvider.getAllSkills();
final transferableOnly = contentProvider.getTransferableSkills();
```

### Get artifact templates:
```dart
final templates = contentProvider.getArtifactTemplates();
final toolTemplate = contentProvider.getArtifactTemplateByName('Tool Control Layout');
```

## Benefits

1. **Easy Content Updates**: Edit CONTENT_MASTER.md and rebuild app
2. **Consistency**: Single source of truth for all trades
3. **Offline-First**: Content bundled in app, no API required
4. **Maintainability**: Content separated from code logic
5. **Scalability**: Easy to add new trades or update existing content

## Testing

Run tests with:
```bash
flutter test test/services/content_master_service_test.dart
```

Tests cover:
- Model creation and validation
- Empty content fallback
- Content aggregation (e.g., combining all skills)

## Future Enhancements

1. **Live Updates**: Download updated CONTENT_MASTER.md from server
2. **User Customization**: Allow users to add custom objectives/bullets
3. **Analytics**: Track which objectives and skills are most used
4. **Multi-Language**: Support content in multiple languages
5. **Version Control**: Track content version for updates

## Troubleshooting

**Issue**: Content not loading
- Check that `CONTENT_MASTER.md` is in the root directory
- Verify `pubspec.yaml` includes `../CONTENT_MASTER.md` in assets
- Run `flutter clean && flutter pub get`

**Issue**: Parse errors
- Review ContentMasterService parsing logic
- Ensure CONTENT_MASTER.md follows expected format
- Check app logs for specific parsing errors

**Issue**: Empty dropdowns
- Verify content loaded successfully (check home screen status)
- Ensure trade names match exactly between CONTENT_MASTER.md and code
- Check that sections are properly delimited with `##` headers
