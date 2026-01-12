# How to Embed Content Files in the App

**Purpose:** Integration guide for developers embedding content files into app workflows.

**Audience:** Developers working on the Streamlit app (Python) or Flutter mobile app.

---

## Overview

The app uses a content-driven architecture where trade-specific data (objectives, bullets, skills, certifications, credentials, etc.) is stored in separate content files rather than hardcoded in the application. This enables:

* **Single source of truth:** Update content without changing code
* **Offline-first:** Bundle content files in the app for offline access
* **Easy maintenance:** Instructors and content managers can update files
* **Scalability:** Add new trades or content without app changes

---

## Content File Locations

All content files should be placed in a central directory within the app structure.

**Recommended directory structure:**

```
/resume-workshop-app
  /data
    README_Content_Spec.md
    Resume_Context_Schema.json
    Objective_Starters_Bank.json
    Role_Bullets_Master.md
    Skills_Canon.json
    Certification_Normalization.csv
    Credential_MicroBadges_Library.md
    Prep_Metrics_Library.md
    Proof_Artifact_Templates.md
    Artifact_Tracker_Template.csv
    Mobility_Plan_Sources_Template.csv
    Social_Intel_Queue_Template.csv
    Cross_Trade_Entry_Tests_Appendix.md
    Pathway_Packet_Structure.md
    How_to_embed_in_app.md
    Objective_Starters_By_Trade.csv
    One_Page_Resume_Layout.txt
    Trade_List.txt
    Detected_Roles_Index.csv
    Resume_Field_Hints.md
    Packet_Checklists_Blank.md
    CONTENT_MASTER.md
```

---

## Loading Content Files

### Python/Streamlit App

**JSON Files:**

```python
import json

def load_objectives():
    with open('data/Objective_Starters_Bank.json', 'r', encoding='utf-8') as f:
        return json.load(f)

objectives = load_objectives()
trades = list(objectives['objectiveStarters'].keys())
```

**CSV Files:**

```python
import pandas as pd

def load_certifications():
    return pd.read_csv('data/Certification_Normalization.csv')

cert_df = load_certifications()
```

**Markdown Files:**

```python
def load_markdown(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

role_bullets = load_markdown('data/Role_Bullets_Master.md')
```

**Text Files:**

```python
def load_trade_list():
    with open('data/Trade_List.txt', 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

trades = load_trade_list()
```

---

### Flutter Mobile App

**JSON Files:**

```dart
import 'dart:convert';
import 'package:flutter/services.dart';

Future<Map<String, dynamic>> loadObjectives() async {
  final String response = await rootBundle.loadString('assets/data/Objective_Starters_Bank.json');
  return json.decode(response);
}
```

**CSV Files:**

```dart
import 'package:csv/csv.dart';

Future<List<List<dynamic>>> loadCertifications() async {
  final String response = await rootBundle.loadString('assets/data/Certification_Normalization.csv');
  return const CsvToListConverter().convert(response);
}
```

**Markdown Files:**

```dart
Future<String> loadMarkdown(String filepath) async {
  return await rootBundle.loadString(filepath);
}
```

**Note:** Don't forget to add content files to `pubspec.yaml` under assets:

```yaml
flutter:
  assets:
    - assets/data/Objective_Starters_Bank.json
    - assets/data/Skills_Canon.json
    - assets/data/Certification_Normalization.csv
    - assets/data/Role_Bullets_Master.md
    # ... add all content files
```

---

## Parsing and Using Content

### Objectives (Objective_Starters_Bank.json)

**Structure:**
```json
{
  "objectiveStarters": {
    "Trade Name": {
      "apprenticeship": ["objective1", "objective2", ...],
      "job": ["objective1", "objective2", ...]
    }
  }
}
```

**Usage:**
* Populate trade selector dropdown
* Filter by apprenticeship vs. job category
* Display objectives in a dropdown for selection
* Allow text editing after selection

---

### Skills (Skills_Canon.json)

**Structure:**
```json
{
  "skillsCanon": {
    "transferable": ["skill1", "skill2", ...],
    "jobSpecific": ["skill1", "skill2", ...],
    "selfManagement": ["skill1", "skill2", ...]
  },
  "metadata": {
    "maxSkillsPerResume": 12
  }
}
```

**Usage:**
* Display skills grouped by category
* Use filter chips or checkboxes for selection
* Enforce maximum of 12 total skills
* Show live count of selected skills

---

### Certifications (Certification_Normalization.csv)

**Structure:**
```
VariantInput,NormalizedResumeName,Notes
```

**Usage:**
* Map user-entered certification names to standardized resume names
* Use fuzzy matching or autocomplete to suggest normalized names
* Display notes (e.g., expiration info) where applicable

---

### Role Bullets (Role_Bullets_Master.md)

**Structure:**
* Markdown with `## Role Name` headers
* Bullets under each role (≤24 words each)

**Parsing Strategy:**
* Split by `## ` to identify roles
* Extract bullets under each role
* Present as suggestions when a role is detected

**Usage:**
* Detect role from work history
* Suggest relevant bullets
* Allow user to select or edit bullets

---

### Credentials (Credential_MicroBadges_Library.md)

**Structure:**
* Markdown with `## Trade Name` headers
* Credential entries with **Resume:** and **Proof:** sub-sections

**Parsing Strategy:**
* Split by `## ` to identify trades
* Extract credential name, resume phrase, and proof requirement
* Store in structured format (dict or object)

**Usage:**
* Filter credentials by selected trade
* Display credential options with resume phrases
* Guide students on required proof artifacts

---

### Templates (CSV and Markdown)

**CSV Templates:**
* Load as-is for user to fill out
* Can be exported or embedded in pathway packet

**Markdown Templates:**
* Parse sections by headers
* Display as fillable forms or checklists
* Export as part of pathway packet

---

## Data Validation

**JSON Schema:**
Use `Resume_Context_Schema.json` to validate resume data structure before export.

**Python:**
```python
import jsonschema

def validate_resume(resume_data):
    with open('data/Resume_Context_Schema.json', 'r') as f:
        schema = json.load(f)
    jsonschema.validate(instance=resume_data, schema=schema)
```

**Flutter:**
Use a JSON schema validator package to validate data.

---

## Content Updates

**Process for updating content:**

1. **Edit content files** in `/data` directory
2. **Test parsing** with app to ensure no errors
3. **Validate structure** (JSON/CSV format, markdown headers)
4. **Commit changes** to version control
5. **Deploy updated app** (if bundled) or update file server (if remote)

**No code changes required** unless structure of files changes significantly.

---

## Error Handling

**Best Practices:**

* **Graceful degradation:** If a content file fails to load, use fallback defaults
* **User feedback:** Show loading states and error messages
* **Validation:** Check file format and structure on load
* **Logging:** Log parsing errors for debugging

**Example (Python):**
```python
def load_objectives_safe():
    try:
        return load_objectives()
    except Exception as e:
        print(f"Error loading objectives: {e}")
        return {"objectiveStarters": {}}
```

---

## Performance Considerations

* **Cache parsed content:** Don't re-parse files on every page load
* **Lazy loading:** Load content only when needed (e.g., when user selects a trade)
* **Minimize file size:** Keep content files focused and well-structured

---

## Testing

**Unit Tests:**
* Test parsing functions for each file type
* Validate that all expected trades/roles/skills are present
* Test edge cases (empty files, malformed data)

**Integration Tests:**
* Test full workflow from content load to export
* Verify data populates UI correctly
* Test with different trade selections

---

## Summary

| File Type | Format | Parsing Method | Primary Use |
|-----------|--------|----------------|-------------|
| Objective_Starters_Bank.json | JSON | json.load() | Trade objectives |
| Skills_Canon.json | JSON | json.load() | Skills selection |
| Certification_Normalization.csv | CSV | pd.read_csv() or CSV parser | Cert mapping |
| Role_Bullets_Master.md | Markdown | Text split by headers | Bullet suggestions |
| Credential_MicroBadges_Library.md | Markdown | Text split by headers | Credential guidance |
| Prep_Metrics_Library.md | Markdown | Text split by headers | Drill tracking |
| Proof_Artifact_Templates.md | Markdown | Text extraction | Printable templates |
| Artifact_Tracker_Template.csv | CSV | Load as-is | Student tracking |
| Mobility_Plan_Sources_Template.csv | CSV | Load as-is | Application planning |
| Social_Intel_Queue_Template.csv | CSV | Load as-is | Instructor curation |
| Trade_List.txt | Plain text | Line-split | Trade list |
| One_Page_Resume_Layout.txt | Plain text | Text load | Layout reference |

---

## Questions?

Refer to `README_Content_Spec.md` for content structure details or contact the development team.

**End of Integration Guide**
