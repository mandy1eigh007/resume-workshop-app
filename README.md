# Seattle Tri-County Construction — Resume & Pathway Packet

A single-file Streamlit app that:
- Parses uploaded resumes (PDF/DOCX/TXT/URLs) and **autofills** a construction-facing resume form.
- Maps **detected past roles** to duty **bullets** from `Job_History_Master.docx`. Clicking bullets also **infers skills**.
- Exports a **DOCX resume** via `docxtpl` using `resume_app_template.docx`.
- Generates a **Cover Letter** (DOCX) with crew-forward, measurable language.
- Builds an **Instructor Pathway Packet** (DOCX) embedding student reflections, full text of uploads, and the selected trade’s section from `Stand_Out_Playbook_Master.docx`.

## Repo layout
