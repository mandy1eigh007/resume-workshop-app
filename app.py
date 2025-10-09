# app.py — Resume Workshop → One-Page DOCX (no AI, rule-based polish only)
# Front-facing UI is the workshop intake. We fill YOUR DOCX template (docxtpl).
# Style/headers/fonts/colors come 100% from your template.

from __future__ import annotations
import io, os, re
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate

st.set_page_config(page_title="Resume Workshop → One-Page DOCX", page_icon=None, layout="wide")

# ── One-page guardrails (tune if needed)
MAX_SUMMARY_CHARS = 450
MAX_SKILLS = 12
MAX_CERTS = 6
MAX_JOBS = 3
MAX_BULLETS_PER_JOB = 4
MAX_SCHOOLS = 2

# ── Rule-based cleanup (no AI)
FILLER_LEADS = re.compile(r"^\s*(responsible for|duties included|tasked with|in charge of)\s*:?\s*", re.I)
MULTISPACE = re.compile(r"\s+")
PHONE_DIGITS = re.compile(r"\D+")

def norm_ws(s: str) -> str:
    s = (s or "").strip()
    s = MULTISPACE.sub(" ", s)
    return s

def sentence_case(s: str) -> str:
    s = norm_ws(s)
    if not s: return s
    return s[0].upper() + s[1:]

def clean_bullet(s: str) -> str:
    s = norm_ws(s)
    s = FILLER_LEADS.sub("", s)           # drop “responsible for …”
    s = re.sub(r"\.+$", "", s)            # drop trailing periods
    if s: s = s[0].upper() + s[1:]        # cap first letter
    words = s.split()
    if len(words) > 20:                   # keep bullets tight
        s = " ".join(words[:20])
    return s

def clean_phone(s: str) -> str:
    digits = PHONE_DIGITS.sub("", s or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return norm_ws(s or "")

def clean_email(s: str) -> str:
    return (s or "").strip().lower()

def split_list(raw: str) -> List[str]:
    if not raw: return []
    parts = [p.strip() for p in re.split(r"[,\n;]+", raw)]
    return [p for p in parts if p]

# ── Data classes
@dataclass
class Job:
    company: str = ""
    role: str = ""
    city: str = ""
    start: str = ""
    end: str = ""
    bullets: List[str] = None
    def trim(self, k: int):
        bs = [clean_bullet(b) for b in (self.bullets or []) if b.strip()]
        self.bullets = bs[:k]

@dataclass
class School:
    school: str = ""
    credential: str = ""
    year: str = ""
    details: str = ""

# ── Build context for docxtpl (keys match your template)
def build_context(form: Dict[str, Any]) -> Dict[str, Any]:
    # Contact
    Name  = sentence_case(form["Name"])
    City  = sentence_case(form["City"])
    State = form["State"].strip().upper()
    phone = clean_phone(form["phone"])
    email = clean_email(form["email"])

    # Summary
    summary = norm_ws(form["summary"])[:MAX_SUMMARY_CHARS]

    # Lists
    skills = [norm_ws(s) for s in split_list(form["skills_raw"])][:MAX_SKILLS]
    certs  = [norm_ws(c) for c in split_list(form["certs_raw"])][:MAX_CERTS]

    # Jobs
    jobs: List[Job] = []
    for i in range(form["job_count"]):
        bullets = [b for b in form[f"bullets_{i}"].splitlines() if b.strip()]
        j = Job(
            company=sentence_case(form[f"company_{i}"]),
            role=sentence_case(form[f"role_{i}"]),
            city=sentence_case(form[f"city_{i}"]),
            start=norm_ws(form[f"start_{i}"]),
            end=norm_ws(form[f"end_{i}"]),
            bullets=bullets
        )
        j.trim(MAX_BULLETS_PER_JOB)
        jobs.append(j)
    jobs = jobs[:MAX_JOBS]

    # Schools
    schools: List[School] = []
    for i in range(form["school_count"]):
        s = School(
            school=sentence_case(form[f"school_{i}"]),
            credential=sentence_case(form[f"cred_{i}"]),
            year=norm_ws(form[f"year_{i}"]),
            details=sentence_case(form[f"det_{i}"])
        )
        schools.append(s)
    schools = schools[:MAX_SCHOOLS]

    # Context EXACTLY for your template keys
    ctx = {
        "Name": Name,
        " City": City,        # keep spaced keys in case the template used them
        " State": State,
        "phone": phone,
        "email": email,
        "summary": summary,
        "skills": skills,
        "certs": certs,
        "jobs": [asdict(j) for j in jobs if any([j.company, j.role, j.bullets])],
        "schools": [asdict(s) for s in schools if any([s.school, s.credential])],
    }
    # Also provide non-spaced backups so it still works if you fix tokens later.
    ctx.setdefault("City", City)
    ctx.setdefault("State", State)
    return ctx

def render_docx(template_bytes: bytes, context: Dict[str, Any]) -> bytes:
    tpl = DocxTemplate(io.BytesIO(template_bytes))
    tpl.render(context)
    out = io.BytesIO()
    tpl.save(out)
    out.seek(0)
    return out.getvalue()

# ── Sidebar — template + quick help
with st.sidebar:
    st.header("Template")
    st.caption("By default this loads resume_app_template.docx from the repo. You can upload a different DOCX.")
    tpl_bytes = None
    default_path = "resume_app_template.docx"
    if os.path.exists(default_path):
        with open(default_path, "rb") as f:
            tpl_bytes = f.read()
    uploaded = st.file_uploader("Upload DOCX template (optional)", type=["docx"])
    if uploaded is not None:
        tpl_bytes = uploaded.read()

    st.markdown("---")
    st.write("**Template keys expected** (docxtpl/Jinja):")
    st.code(
        """{{Name}}, {{ City }}, {{ State }}, {{ phone }}, {{ email }}
{{ summary }}
{% for s in skills %}• {{ s }}{% endfor %}
{% for c in certs %}• {{ c }}{% endfor %}

{% for job in jobs %}
  {{ job.company }} — {{ job.role }}  ({{ job.start }} – {{ job.end }})
  {{ job.city }}
  {% for b in job.bullets %}• {{ b }}{% endfor %}
{% endfor %}

{% for s in schools %}
  {{ s.school }} — {{ s.credential }} — {{ s.year }}
  {{ s.details }}
{% endfor %}""",
        language="jinja"
    )

# ── Main — WORKSHOP INTAKE (front-facing)
st.markdown("# Resume Workshop → One-Page DOCX")

with st.form("workshop"):
    st.subheader("Contact (from sign-in sheet)")
    c1, c2 = st.columns(2)
    with c1:
        Name  = st.text_input("Student full name", "")
        City  = st.text_input("City", "")
        State = st.text_input("State (2-letter, e.g., WA)", "")
    with c2:
        phone = st.text_input("Phone (digits or any format)", "")
        email = st.text_input("Email", "")

    st.subheader("Objective (what are they aiming for?)")
    summary = st.text_area("In 3–5 short lines: role, safety mindset, strengths, availability.", "")

    st.subheader("Skills (from whiteboard activity)")
    skills_raw = st.text_area("List skills (comma or new line). Keep the best ~12.", "")

    st.subheader("Certifications (cards & training)")
    certs_raw = st.text_area("Examples: OSHA-10, Flagger, Forklift, First Aid/CPR.", "OSHA-10")

    st.subheader("Experience (jobs, volunteering, crews)")
    job_count = st.number_input("How many roles to include?", 0, MAX_JOBS, min(MAX_JOBS, 2))
    jobs_blocks: List[Dict[str, Any]] = []
    for i in range(int(job_count)):
        st.markdown(f"**Role {i+1}**")
        j1, j2 = st.columns([2,2])
        with j1:
            company = st.text_input(f"Employer/Project {i+1}", key=f"company_{i}")
            role    = st.text_input(f"Role/Title {i+1}", key=f"role_{i}")
            city_j  = st.text_input(f"City/Region {i+1}", key=f"city_{i}")
        with j2:
            start   = st.text_input(f"Start (YYYY-MM or season) {i+1}", key=f"start_{i}")
            end     = st.text_input(f"End (YYYY-MM or 'Present') {i+1}", key=f"end_{i}")
        bullets  = st.text_area(f"What did they do? (1–4 bullet lines)", key=f"bullets_{i}",
                                placeholder="E.g., Set up traffic control; Used PPE; Assisted with concrete forms")
        jobs_blocks.append({
            f"company_{i}": company, f"role_{i}": role, f"city_{i}": city_j,
            f"start_{i}": start, f"end_{i}": end, f"bullets_{i}": bullets
        })

    st.subheader("Education")
    school_count = st.number_input("How many schools/certs programs?", 0, MAX_SCHOOLS, min(MAX_SCHOOLS, 1))
    schools_blocks: List[Dict[str, Any]] = []
    for i in range(int(school_count)):
        st.markdown(f"**School/Program {i+1}**")
        e1, e2 = st.columns([2,1])
        with e1:
            school = st.text_input(f"School/Program {i+1}", key=f"school_{i}")
            cred   = st.text_input(f"Credential (Diploma/GED/Cert) {i+1}", key=f"cred_{i}")
            det    = st.text_input(f"Details (e.g., ANEW Pre-Apprenticeship)", key=f"det_{i}")
        with e2:
            year   = st.text_input(f"Year {i+1}", key=f"year_{i}")
        schools_blocks.append({f"school_{i}": school, f"cred_{i}": cred, f"det_{i}": det, f"year_{i}:": year})

    submitted = st.form_submit_button("Generate One-Page Resume (DOCX)", type="primary")

# ── Build → Download
if submitted:
    # load template
    tpl_bytes = tpl_bytes or (open("resume_app_template.docx","rb").read() if os.path.exists("resume_app_template.docx") else None)
    if not tpl_bytes:
        st.error("Template not found. Put resume_app_template.docx in the repo, or upload one in the sidebar.")
    else:
        # collect workshop answers
        form = {
            "Name": Name, "City": City, "State": State,
            "phone": phone, "email": email,
            "summary": summary,
            "skills_raw": skills_raw, "certs_raw": certs_raw,
            "job_count": int(job_count), "school_count": int(school_count),
        }
        for d in jobs_blocks: form.update(d)
        for d in schools_blocks: form.update(d)

        # quick counters (helps keep one page)
        skills_list = split_list(skills_raw)
        certs_list  = split_list(certs_raw)
        st.info(f"Counts → Summary: {len(summary)} chars | Skills: {len(skills_list)} | Certs: {len(certs_list)} | Roles: {job_count} | Schools: {school_count}")

        # render + download
        try:
            ctx = build_context(form)
            docx_bytes = render_docx(tpl_bytes, ctx)
            safe_name = (ctx.get("Name") or "Resume").replace(" ", "_")
            st.download_button(
                "Download DOCX",
                data=docx_bytes,
                file_name=f"{safe_name}_Resume.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
            st.success("Generated from your exact template.")
        except Exception as e:
            st.error(f"Template rendering failed: {e}")
