# Seattle Tri-County Construction — Resume & Pathway Packet

A single-file Streamlit app that:
- Parses uploaded resumes (PDF/DOCX/TXT/URLs) and **autofills** a construction-facing resume form.
- Maps **detected past roles** to duty **bullets** from `Job_History_Master.docx`. Clicking bullets also **infers skills**.
- Exports a **DOCX resume** via `docxtpl` using `resume_app_template.docx`.
- Generates a **Cover Letter** (DOCX) with crew-forward, measurable language.
- Builds an **Instructor Pathway Packet** (DOCX) embedding student reflections, full text of uploads, and the selected trade’s section from `Stand_Out_Playbook_Master.docx`.

## Quick Start

### Installation

1. Ensure Python 3.11+ is installed
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the App

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

### Verification

To verify everything is working correctly, run the verification test suite:

```bash
python3 test_verification.py
```

This will test:
- ✓ All Python dependencies are installed
- ✓ Required data files are present
- ✓ Text parsing functions work correctly
- ✓ Job Master DOCX parsing works
- ✓ Document generation (Resume, Cover Letter, Pathway Packet) works
- ✓ Utility functions work correctly

## Repo layout
