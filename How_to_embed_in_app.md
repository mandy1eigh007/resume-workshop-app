# How to Embed in App

## Overview

This guide explains how to integrate the content libraries into the resume workshop application.

## Content Files to Load

### JSON Files
* `Objective_Starters_Bank.json` — Objective starters by trade
* `Skills_Canon.json` — Three skill buckets
* `Resume_Context_Schema.json` — Schema for validation

### CSV Files
* `Certification_Normalization.csv` — Normalized certification names
* `Objective_Starters_By_Trade.csv` — Alternative objective format
* `Detected_Roles_Index.csv` — Roles the app can detect
* `Artifact_Tracker_Template.csv` — Template for artifact tracking
* `Mobility_Plan_Sources_Template.csv` — Template for mobility sources
* `Social_Intel_Queue_Template.csv` — Template for social intel

### Markdown Files
* `Role_Bullets_Master.md` — Bullet points by detected role
* `Credential_MicroBadges_Library.md` — Micro-badges by trade
* `Prep_Metrics_Library.md` — Named drills and recording specs
* `Proof_Artifact_Templates.md` — Artifact field templates
* `Cross_Trade_Entry_Tests_Appendix.md` — Entry test information
* `Resume_Field_Hints.md` — Field-level guidance

### Text Files
* `Trade_List.txt` — All supported trades
* `One_Page_Resume_Layout.txt` — Layout constraints

## Integration Points

### 1. Resume Form Auto-Fill

**When parsing uploaded resume:**
1. Extract text from PDF/DOCX/TXT
2. Detect roles using `Detected_Roles_Index.csv`
3. Load corresponding bullets from `Role_Bullets_Master.md`
4. Present bullets as clickable options
5. When bullet selected, infer related skills from `Skills_Canon.json`

### 2. Objective Selection

**Display trade-specific objectives:**
1. User selects trade from `Trade_List.txt`
2. User selects type: Apprenticeship or Job
3. Load objectives from `Objective_Starters_Bank.json` using trade and type
4. Display as selectable list
5. Allow optional editing while maintaining neutral tone

### 3. Skills Auto-Inference

**When user selects role bullets:**
1. Parse selected bullet for keywords
2. Match keywords to skills in `Skills_Canon.json`
3. Suggest skills across all three buckets
4. Enforce ≤12 total skills constraint
5. Allow manual override

### 4. Certification Normalization

**When user enters certifications:**
1. Check input against `Certification_Normalization.csv`
2. Auto-correct to normalized resume phrase
3. Display notes (e.g., expiry info) as hints
4. Store original + normalized version

### 5. Pathway Packet Generation

**When generating instructor packet:**
1. Load trade section from `Stand_Out_Playbook_Master.docx`
2. Append micro-badges from `Credential_MicroBadges_Library.md` for selected trade
3. Add entry test content from `Cross_Trade_Entry_Tests_Appendix.md`
4. Include artifact tracker from `Artifact_Tracker_Template.csv`
5. Add mobility plan template from `Mobility_Plan_Sources_Template.csv`
6. Include social intel queue from `Social_Intel_Queue_Template.csv`
7. Add checklists from `Packet_Checklists_Blank.md`

### 6. Field Hints

**Display contextual guidance:**
1. Load hints from `Resume_Field_Hints.md`
2. Show appropriate hint based on current field
3. Display as tooltip or help text
4. Include examples where applicable

### 7. Validation

**Enforce constraints:**
1. Validate resume structure against `Resume_Context_Schema.json`
2. Check layout constraints from `One_Page_Resume_Layout.txt`
3. Enforce bullet word count ≤24 words
4. Enforce 3–4 bullets per experience
5. Enforce ≤12 total skills
6. Enforce ≤3 experience entries
7. Validate no forbidden terms (union/non-union references)

## Code Examples

### Loading JSON Files (Python)

```python
import json

# Load objective starters
with open('Objective_Starters_Bank.json', 'r') as f:
    objectives = json.load(f)

# Get objectives for a specific trade
trade = "Carpenter (General)"
apprenticeship_objectives = objectives[trade]["Apprenticeship"]
job_objectives = objectives[trade]["Job"]

# Load skills canon
with open('Skills_Canon.json', 'r') as f:
    skills = json.load(f)

transferable_skills = skills["Transferable"]
job_specific_skills = skills["Job-Specific"]
self_management_skills = skills["Self-Management"]
```

### Loading CSV Files (Python)

```python
import pandas as pd

# Load certification normalization
certs = pd.read_csv('Certification_Normalization.csv')

# Normalize a certification
def normalize_cert(input_cert):
    match = certs[certs['Certification'].str.lower() == input_cert.lower()]
    if not match.empty:
        return match.iloc[0]['Resume_Phrase']
    return input_cert

# Load detected roles
roles = pd.read_csv('Detected_Roles_Index.csv')
```

### Parsing Markdown for Role Bullets (Python)

```python
import re

def load_role_bullets(role_name):
    with open('Role_Bullets_Master.md', 'r') as f:
        content = f.read()
    
    # Find role section
    pattern = rf'## {re.escape(role_name)}\n\n((?:\* .+\n)+)'
    match = re.search(pattern, content)
    
    if match:
        bullets_text = match.group(1)
        bullets = re.findall(r'\* (.+)', bullets_text)
        return bullets
    return []

# Example usage
carpenter_bullets = load_role_bullets("Carpenter Helper")
```

### Schema Validation (Python)

```python
import json
import jsonschema

# Load schema
with open('Resume_Context_Schema.json', 'r') as f:
    schema = json.load(f)

# Validate resume data
def validate_resume(resume_data):
    try:
        jsonschema.validate(instance=resume_data, schema=schema)
        return True, None
    except jsonschema.exceptions.ValidationError as e:
        return False, str(e)

# Example resume data
resume = {
    "header": {
        "name": "John Doe",
        "city": "Seattle",
        "state": "WA",
        "phone": "206-555-1234",
        "email": "john@example.com"
    },
    "objective": {
        "text": "Seeking structured training in carpentry...",
        "trade": "Carpenter (General)",
        "type": "Apprenticeship"
    },
    "experience": [],
    "skills": {
        "transferable": ["Problem Solving", "Time Management"],
        "job_specific": ["Hand & Power Tools", "Measuring & Layout"],
        "self_management": ["Initiative", "Willingness to Learn"]
    }
}

is_valid, error = validate_resume(resume)
```

## Best Practices

1. **Cache content files** — Load once at startup, reload only when updated
2. **Validate all inputs** — Use schema validation before generating documents
3. **Preserve neutral tone** — Warn if user edits introduce forbidden terms
4. **Track skill count** — Display counter (e.g., "8/12 skills selected")
5. **Word count enforcement** — Auto-truncate or warn when bullets exceed 24 words
6. **Evidence-ready language** — Suggest measured phrasing when user enters vague bullets
7. **Artifact linking** — Allow file uploads and associate with tracker entries

## Error Handling

* **Missing trade:** Fall back to generic objectives or prompt user to select valid trade
* **Invalid role detection:** Allow manual role selection from `Detected_Roles_Index.csv`
* **Schema validation failure:** Show specific field errors with guidance
* **File not found:** Display clear error with path and expected location

## Testing

1. Test with all 26 trades in `Trade_List.txt`
2. Test all 20 detected roles in `Detected_Roles_Index.csv`
3. Validate all objectives meet ≤200 character limit
4. Validate all role bullets meet ≤24 word limit
5. Test schema validation with valid and invalid inputs
6. Test certification normalization with all 6 cert types
