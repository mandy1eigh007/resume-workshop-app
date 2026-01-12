# Content Specification for Resume Workshop App

## Overview
This document describes the structure, format, and purpose of all content files used in the Seattle Tri-County Construction Resume & Pathway Packet application.

## File Inventory

### Core Content Files

1. **CONTENT_MASTER.md** - The comprehensive master content document containing all trade-specific guidance, objectives, bullets, skills, and artifact templates.

2. **Resume_Context_Schema.json** - JSON schema defining the structure of resume data.

3. **Objective_Starters_Bank.json** - JSON-formatted objectives organized by trade (apprenticeship and job).

4. **Objective_Starters_By_Trade.csv** - CSV format of objectives for easy filtering and import.

5. **Role_Bullets_Master.md** - Markdown document with duty bullets per detected role (≤24 words, measured/evidence-ready).

6. **Skills_Canon.json** - JSON file with skills organized into three buckets: Transferable, Job-Specific, and Self-Management.

7. **Certification_Normalization.csv** - CSV mapping various certification names to standardized resume phrases.

8. **Credential_MicroBadges_Library.md** - Trade-specific micro-credentials with resume phrases and proof artifact requirements.

9. **Prep_Metrics_Library.md** - Named drills and how they're recorded (timed carry, conduit bending, etc.).

10. **Proof_Artifact_Templates.md** - Text templates for checklists, logs, and verification forms.

### Tracking Templates

11. **Artifact_Tracker_Template.csv** - Blank CSV template for tracking proof artifacts (Item, Source, Date, Expiry, File/Link, Verifier, Notes).

12. **Mobility_Plan_Sources_Template.csv** - Template for logging multi-state application sources and calendars.

13. **Social_Intel_Queue_Template.csv** - Template for tracking trade-specific insights and evidence requirements.

### Supporting Documents

14. **Cross_Trade_Entry_Tests_Appendix.md** - Summary of entry tests, physicals, and prep resources across trades.

15. **Pathway_Packet_Structure.md** - Document describing the structure and sections of the Pathway Packet output.

16. **How_to_embed_in_app.md** - Integration guide for embedding content files into app workflows.

17. **Stand_Out_Playbook_Master_APPEND_ONLY_Scaffold.md** - Scaffold structure for the trade-specific Stand-Out Playbook with append-only "Do Next" sections.

18. **One_Page_Resume_Layout.txt** - Plain text layout showing the exact structure of a one-page resume.

19. **Trade_List.txt** - Simple line-separated list of all supported trades.

20. **Detected_Roles_Index.csv** - Index mapping common job titles to standardized role names used in bullet bank.

21. **Resume_Field_Hints.md** - Guidance and hints for filling out each resume field (Objective, Experience, Skills, Certifications, Education).

22. **Packet_Checklists_Blank.md** - Blank checklists for 0-2 weeks, 2-6 weeks, and 6-12 weeks action items.

## Content Principles

### Evidence Doctrine
"If you can't attach it (card, score, log, checklist, sign-off, face-free photo), it's weak."

### Neutrality Guardrails
- Forbidden terms: "union," "non-union," local numbers in objectives
- Use neutral, factual, crew-useful language
- No sub-trade labels in objectives

### Measurement Standard
- Bullets: ≤24 words, with measured/evidence-ready phrasing
- Resume: One page, ≤12 total skills, 3-4 measured bullets per job
- Objectives: Neutral wording, chosen from starter bank or edited by student

### Privacy Requirements
- Photos must exclude faces and sensitive site identifiers
- No personal data in templates
- Permission documented when identifiable content is necessary

## Data Formats

### JSON Files
- Use consistent structure with clear hierarchies
- Include validation-friendly field names
- Support both apprenticeship and job categories where applicable

### CSV Files
- Include header row
- Use consistent column ordering
- Quote fields containing commas or newlines
- UTF-8 encoding

### Markdown Files
- Use consistent heading hierarchy
- Include clear section markers
- Format bullets consistently
- Maintain ≤24 word limit for duty bullets

### Plain Text Files
- UTF-8 encoding
- Line-separated for list files
- Clear structure for layout templates

## Integration Notes

All content files are designed to:
1. Support offline-first architecture (bundled in app)
2. Enable dynamic loading without code changes
3. Maintain a single source of truth for trade-specific content
4. Allow easy updates by instructors and content managers
5. Support validation and verification workflows

## Versioning
Content files should be versioned alongside the application. Breaking changes to structure require corresponding app updates.

## Contact
For questions about content structure or updates, refer to How_to_embed_in_app.md.
