# Resume Workshop → One-Page DOCX

Streamlit app that collects **workshop answers**, applies **rule-based cleanup** (no AI), and fills a **Word (.docx) resume template** exactly as designed.

## Deploy on Streamlit Cloud
1. Repo must contain:
   - `app.py`
   - `requirements.txt`
   - `resume_app_template.docx`
2. In Streamlit Cloud: **New app** → select this repo → file: `app.py` → **Deploy**.

## Template Placeholders (in your .docx)
{{Name}}, {{ City }}, {{ State }}, {{ phone }}, {{ email }}
{{ summary }}

{% for s in skills %}• {{ s }}{% endfor %}
{% for c in certs %}• {{ c }}{% endfor %}

{% for job in jobs %}
{{ job.company }} — {{ job.role }} ({{ job.start }} – {{ job.end }})
{{ job.city }}
{% for b in job.bullets %}• {{ b }}{% endfor %}
{% endfor %}

{% for s in schools %}
{{ s.school }} — {{ s.credential }} — {{ s.year }}
{{ s.details }}
{% endfor %}

markdown
Copy code

## One-Page Limits (tune in `app.py`)
- `MAX_SUMMARY_CHARS = 450`
- `MAX_SKILLS = 12`
- `MAX_CERTS = 6`
- `MAX_JOBS = 3`
- `MAX_BULLETS_PER_JOB = 4`
- `MAX_SCHOOLS = 2`

## What the app cleans (no AI)
- Trims spaces, sentence-cases text.
- Removes filler starts (“responsible for…”, “duties included…”).
- Bullets ≤ ~20 words, strips trailing periods.
- Formats phone `(xxx) xxx-xxxx` when possible; lowercases emails.

## Troubleshooting
- **Template not found:** Ensure `resume_app_template.docx` is in repo root or upload via sidebar.
- **Placeholders not filling:** Check variable names/extra spaces in the `.docx`.
- **Over one page:** Shorten summary/bullets or adjust limits above.






