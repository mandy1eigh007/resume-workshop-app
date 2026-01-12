# README — Content Specification

## Purpose

This README describes the structure and purpose of all content files in this repository. These files contain the data and templates needed to power the resume workshop application.

## File Inventory

### Core Content Files

#### JSON Files

**Objective_Starters_Bank.json**
* Purpose: Trade-specific objective starters for resumes
* Structure: Nested object with trade → type (Apprenticeship/Job) → array of objectives
* Usage: Display as selectable options based on user's chosen trade
* Constraints: Each objective ≤200 characters, neutral tone, evidence-ready

**Skills_Canon.json**
* Purpose: Three-bucket skill taxonomy (Transferable, Job-Specific, Self-Management)
* Structure: Object with three arrays
* Usage: Skill selection with ≤12 total constraint
* Auto-inference: Parse selected role bullets to suggest relevant skills

**Resume_Context_Schema.json**
* Purpose: JSON schema for validating resume structure
* Structure: JSON Schema Draft 07 format
* Usage: Validate resume data before document generation
* Enforces: One-page constraints, bullet counts, skill limits

#### CSV Files

**Certification_Normalization.csv**
* Purpose: Normalize certification names to standard resume phrasing
* Columns: Certification, Resume_Phrase, Notes
* Usage: Auto-correct user input to normalized form
* Count: 6 certifications (OSHA 10/30, WA Flagger, Forklift, CPR/First Aid, EPA 608)

**Objective_Starters_By_Trade.csv**
* Purpose: Alternative flat structure for objectives
* Columns: Trade, Type, Objective
* Usage: Same as JSON version, different format for different use cases
* Count: 26 trades × 10 objectives = 260 rows

**Detected_Roles_Index.csv**
* Purpose: Roles the app can detect from uploaded resumes
* Columns: Role, Category, Bullet_Count
* Usage: Role detection and bullet mapping
* Count: 20 detectable roles

**Artifact_Tracker_Template.csv**
* Purpose: Template for tracking proof artifacts
* Columns: Item, Source_Provider, Date_Obtained, Expiry_Date, File_Link, Verifier_Name, Notes
* Usage: Embedded in pathway packet for student use

**Mobility_Plan_Sources_Template.csv**
* Purpose: Template for multi-state application sources
* Columns: Trade_Tag, Source_Name, URL, Refresh_Cadence, Notes, Status
* Usage: Staff populate with legitimate calendars and portals

**Social_Intel_Queue_Template.csv**
* Purpose: Template for trade-specific insights queue
* Columns: Trade_Tag, Link, Date_Added, Insight_1_2_Lines, How_to_Evidence, Status
* Usage: Staff populate with practical insights and evidence guidance

#### Markdown Files

**Role_Bullets_Master.md**
* Purpose: Duty bullets for detected roles
* Structure: Heading per role, bulleted list of measured bullets
* Usage: User selects detected role → bullets displayed as clickable options
* Constraints: ≤24 words per bullet, measurable/evidence-ready
* Count: 20 roles, 4 bullets each

**Credential_MicroBadges_Library.md**
* Purpose: Trade-specific micro-badges with resume phrasing and proof requirements
* Structure: Heading per trade, sub-heading per credential, resume phrase + proof type
* Usage: Embedded in pathway packet for selected trade
* Count: 26 trades, 2+ credentials each

**Prep_Metrics_Library.md**
* Purpose: Named drills and recording specifications
* Structure: Heading per drill, recording fields listed
* Usage: Guide students on how to document practice drills
* Count: 10 named drills

**Proof_Artifact_Templates.md**
* Purpose: Field templates for different artifact types
* Structure: Heading per template type, field list
* Usage: Printable templates for students to complete
* Count: 6 template types (checklists, logs, read-throughs)

**Cross_Trade_Entry_Tests_Appendix.md**
* Purpose: Entry test/physical requirements and prep resources
* Structure: Heading per test bucket, metrics and prep resources
* Usage: Embedded in pathway packet based on trade requirements
* Count: 4 test buckets (Electrical Aptitude, Mechanical Reasoning, Physical Capability, Climb)

**Pathway_Packet_Structure.md**
* Purpose: Documentation of pathway packet structure
* Structure: Outline of existing + appended sections
* Usage: Reference for developers/instructors
* Not embedded: Documentation only

**How_to_embed_in_app.md**
* Purpose: Integration guide for developers
* Structure: Integration points, code examples, best practices
* Usage: Developer reference
* Not embedded: Documentation only

**Resume_Field_Hints.md**
* Purpose: Field-level guidance for resume form fields
* Structure: Heading per field, guidelines and examples
* Usage: Display as tooltips/help text in app
* Covers: All resume fields (header, objective, experience, skills, certs, education)

**Packet_Checklists_Blank.md**
* Purpose: Blank checklist templates for three time blocks
* Structure: Week 0–2, Weeks 2–6, Weeks 6–12, Outcome Tracking
* Usage: Embedded in pathway packet for student to complete
* Format: Markdown checkboxes, fillable fields

**Stand_Out_Playbook_Master_APPEND_ONLY_Scaffold.md**
* Purpose: Scaffold showing how to append new content to existing playbook
* Structure: Marker for existing content + all new sections
* Usage: Template for pathway packet generation
* Important: Existing trade content must remain intact

#### Text Files

**Trade_List.txt**
* Purpose: Complete list of supported trades
* Format: One trade per line
* Usage: Trade selection dropdown, validation
* Count: 26 trades

**One_Page_Resume_Layout.txt**
* Purpose: Layout specification and constraints
* Format: Plain text outline
* Usage: Display constraints to user, enforce in validation
* Key constraints: 1 page, ≤12 skills, 3–4 bullets per job, ≤24 words per bullet

## Content Philosophy

### Evidence-Driven
All content emphasizes measurable, provable signals:
* Counts, weights, distances, areas
* Frequencies (per shift, per day)
* Documentation (logs, checklists, sign-offs)
* Proof artifacts (cards, scores, photos)

### Neutral Tone
Content avoids:
* Adjectives without evidence ("hard worker," "great")
* Union/non-union references
* Sub-trade labels in objectives
* Hype or exaggeration

### Seattle-First
Geographic scope:
* Primary: Seattle tri-county (King/Pierce/Snohomish)
* Secondary: Multi-state options with reciprocity notes

### Low/No-Cost Priority
Where paid options exist, public alternatives are presented:
* Open courses
* Library access
* Practice drills
* Public utility programs

## Data Integrity

### Update Protocols

**Who can update:**
* Staff instructors: All templates and libraries
* System admin: Schema and validation rules
* Students: Only their individual artifact trackers and checklists

**Version control:**
* All updates logged with date and author
* Major changes require review
* Breaking changes require app update

**Testing:**
* All trades tested (26 total)
* All roles tested (20 total)
* Schema validation tested with valid/invalid inputs
* Bullet word count verified (≤24 words)
* Objective character count verified (≤200 characters)

### Validation Rules

**Objectives:**
* ≤200 characters
* No forbidden terms
* Neutral, evidence-ready tone

**Role Bullets:**
* ≤24 words
* Measurable language
* Past tense for completed work

**Skills:**
* Total ≤12 across all buckets
* Must exist in Skills_Canon.json

**Certifications:**
* Must normalize to standard phrase
* Time-limited certs flagged with expiry tracking

## Usage in App

### Load Order
1. Load all JSON and CSV files at startup (cache)
2. Load markdown files on-demand by trade/role
3. Reload only when files change

### Integration Points
See `How_to_embed_in_app.md` for detailed integration guide covering:
* Resume auto-fill from uploaded documents
* Objective selection by trade
* Skills auto-inference from bullets
* Certification normalization
* Pathway packet generation
* Field hints display
* Schema validation

### Error Handling
* Missing trade: Fall back to generic options or prompt
* Invalid role: Allow manual selection
* Schema validation failure: Show specific field errors
* File not found: Display clear error with expected path

## Maintenance Schedule

**Monthly:**
* Review Social Intel Queue for new insights
* Update Mobility Plan Sources with new calendars
* Check certification expiry policies

**Quarterly:**
* Review role bullets for accuracy
* Update prep resource links
* Validate all external URLs

**Annually:**
* Review all trades for industry changes
* Update entry test requirements
* Review skill canon for completeness

## Support

For questions about content structure or updates:
* Technical: See `How_to_embed_in_app.md`
* Content: Refer to `CONTENT_MASTER.md`
* Structure: This file (README_Content_Spec.md)

---

**Last Updated:** [Current Date]

**Content Version:** 1.0

**Compatible App Version:** 1.0+
