# app.py — Resume Workshop → One-Page DOCX (no AI)
# Front-facing UI mirrors your workshop. Rule-based cleanup. Outputs:
# - DOCX using your template (docxtpl)
# - CSV snapshot of the student's intake

from __future__ import annotations
import io, os, re, csv
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

import streamlit as st
from docxtpl import DocxTemplate

st.set_page_config(page_title="Resume Workshop → One-Page DOCX", page_icon=None, layout="wide")

# ── One-page guardrails (tune if needed)
MAX_SUMMARY_CHARS = 450
MAX_SKILLS = 12
MAX_CERTS = 6
MAX_JOBS = 3
MAX_BULLETS_PER_JOB = 4
MAX_SCHOOLS = 2

# ── Cleanup (no AI)
FILLER_LEADS = re.compile(r"^\s*(responsible for|duties included|tasked with|in charge of)\s*:?\s*", re.I)
MULTISPACE = re.compile(r"\s+")
PHONE_DIGITS = re.compile(r"\D+")

def norm_ws(s: str) -> str:
    s = (s or "").strip()
    s = MULTISPACE.sub(" ", s)
    return s

def cap_first(s: str) -> str:
    s = norm_ws(s)
    return s[:1].upper() + s[1:] if s else s

def clean_bullet(s: str) -> str:
    s = norm_ws(s)
    s = FILLER_LEADS.sub("", s)
    s = re.sub(r"\.+$", "", s)
    s = cap_first(s)
    words = s.split()
    return " ".join(words[:20]) if len(words) > 20 else s

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

def parse_dates(raw: str) -> tuple[str, str]:
    raw = norm_ws(raw)
    if "–" in raw or "-" in raw:
        sep = "–" if "–" in raw else "-"
        bits = [b.strip() for b in raw.split(sep, 1)]
        if len(bits) == 2:
            return bits[0], bits[1]
    return (raw, "") if raw else ("", "")

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
    details: str = ""  # City/State or notes

# ── Build context for docxtpl (keys match your template)
def build_context(form: Dict[str, Any]) -> Dict[str, Any]:
    # Contact
    Name  = cap_first(form["Name"])
    City  = cap_first(form["City"])
    State = (form["State"] or "").strip().upper()
    phone = clean_phone(form["Phone"])
    email = clean_email(form["Email"])

    # Objective → final box
    summary = norm_ws(form["Objective_Final"])[:MAX_SUMMARY_CHARS]

    # Skills (merge 3 lists)
    skills_all = []
    for raw in (form["Skills_Transferable"], form["Skills_JobSpecific"], form["Skills_SelfManagement"]):
        skills_all += split_list(raw)
    skills = [norm_ws(s) for s in skills_all][:MAX_SKILLS]

    # Certifications
    certs = [norm_ws(c) for c in split_list(form["Certifications"] )][:MAX_CERTS]

    # Experience (up to 3)
    jobs: List[Job] = []
    for idx in range(1, 4):
        company = form.get(f"Job{idx}_Company","")
        cityst  = form.get(f"Job{idx}_CityState","")
        dates   = form.get(f"Job{idx}_Dates","")
        title   = form.get(f"Job{idx}_Title","")
        duties  = form.get(f"Job{idx}_Duties","")
        if not any([company, title, duties]):
            continue
        start, end = parse_dates(dates)
        j = Job(
            company=cap_first(company),
            role=cap_first(title),
            city=cap_first(cityst),
            start=norm_ws(start),
            end=norm_ws(end),
            bullets=[b for b in duties.splitlines() if b.strip()]
        )
        j.trim(MAX_BULLETS_PER_JOB)
        jobs.append(j)
    jobs = jobs[:MAX_JOBS]

    # Education (up to 2)
    schools: List[School] = []
    for idx in range(1, 2+1):
        sch   = form.get(f"Edu{idx}_School","")
        citys = form.get(f"Edu{idx}_CityState","")
        dates = form.get(f"Edu{idx}_Dates","")
        cred  = form.get(f"Edu{idx}_Credential","")
        if not any([sch, cred, dates, citys]):
            continue
        year = norm_ws(dates)
        details = cap_first(citys) if citys else ""
        schools.append(School(
            school=cap_first(sch),
            credential=cap_first(cred),
            year=year,
            details=details
        ))
    schools = schools[:MAX_SCHOOLS]

    # Optional sections → lightly appended to summary tail
    other_work = norm_ws(form.get("Other_Work",""))
    volunteer  = norm_ws(form.get("Volunteer",""))
    tail_bits = []
    if other_work: tail_bits.append(f"Other work: {other_work}")
    if volunteer:  tail_bits.append(f"Volunteer: {volunteer}")
    if tail_bits:
        add = "  •  ".join(tail_bits)
        summary = (summary + " " + add).strip()
        summary = summary[:MAX_SUMMARY_CHARS]

    # Final context → match your template tokens (including spaced variants)
    ctx = {
        "Name": Name,
        " City": City,  "City": City,
        " State": State,"State": State,
        "phone": phone,
        "email": email,
        "summary": summary,
        "skills": skills,
        "certs": certs,
        "jobs": [asdict(j) for j in jobs if any([j.company, j.role, j.bullets])],
        "schools": [asdict(s) for s in schools if any([s.school, s.credential, s.year, s.details])],
    }
    return ctx

def render_docx(template_bytes: bytes, context: Dict[str, Any]) -> bytes:
    tpl = DocxTemplate(io.BytesIO(template_bytes))
    tpl.render(context)
    out = io.BytesIO()
    tpl.save(out)
    out.seek(0)
    return out.getvalue()

def intake_to_csv_bytes(form: Dict[str, Any]) -> bytes:
    # simple one-row CSV so you can keep a local record per student
    fields = list(form.keys())
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(fields)
    w.writerow([form[k] for k in fields])
    return buf.getvalue().encode("utf-8")

# ── Sidebar — template
with st.sidebar:
    st.header("Template")
    st.caption("Loads resume_app_template.docx from the repo by default. You can upload a different DOCX.")
    tpl_bytes = None
    if os.path.exists("resume_app_template.docx"):
        with open("resume_app_template.docx","rb") as f:
            tpl_bytes = f.read()
    upl = st.file_uploader("Upload DOCX template (optional)", type=["docx"])
    if upl is not None:
        tpl_bytes = upl.read()

# ── Main — WORKSHOP INTAKE (labels mirror the packet)
st.markdown("# Resume Workshop → One-Page DOCX")

with st.form("workshop"):
    # 2. Header (Contact)
    st.subheader("2) Your Header (Contact Information)")
    c1, c2 = st.columns(2)
    with c1:
        Name = st.text_input("Name:", "")
        City = st.text_input("City:", "")
        State = st.text_input("State (2-letter):", "")
    with c2:
        Phone = st.text_input("Phone:", "")
        Email = st.text_input("Email:", "")

    # 3. Writing Your Objective
    st.subheader("3) Writing Your Objective")
    st.caption("Answer the prompts, then write a 1–2 sentence objective.")
    Obj_Seeking = st.text_input("What job or apprenticeship are you seeking?", "")
    Obj_Quality = st.text_input("One skill or quality to highlight:", "")
    Objective_Final = st.text_area("Write your final objective here (1–2 sentences):", "")

    # 4. Your Skills Section
    st.subheader("4) Your Skills Section")
    Skills_Transferable = st.text_area("Transferable Skills (at least five):", "")
    Skills_JobSpecific = st.text_area("Job-Specific Skills (at least five):", "")
    Skills_SelfManagement = st.text_area("Self-Management Skills (at least five):", "")

    # 5. Work Experience – Job 1..3
    st.subheader("5) Work Experience")
    job_blocks = []
    for idx in range(1, 4):
        st.markdown(f"**Job {idx}**")
        j1, j2 = st.columns(2)
        with j1:
            JobCompany = st.text_input(f"Job {idx} – Company:", key=f"J{idx}c")
            JobCitySt  = st.text_input(f"Job {idx} – City/State:", key=f"J{idx}cs")
            JobDates   = st.text_input(f"Job {idx} – Dates (e.g., 2023-06 – 2024-05 or Present):", key=f"J{idx}d")
        with j2:
            JobTitle   = st.text_input(f"Job {idx} – Title:", key=f"J{idx}t")
            JobDuties  = st.text_area(f"Job {idx} – Duties/Accomplishments (1–4 bullets, one per line):", key=f"J{idx}du")
        job_blocks.append((JobCompany, JobCitySt, JobDates, JobTitle, JobDuties))

    # 6. Certifications
    st.subheader("6) Certifications")
    Certifications = st.text_area("List certifications (comma or newline). If none, write 'None yet' or planned:", "OSHA-10")

    # 7. Education
    st.subheader("7) Education")
    edu_blocks = []
    for idx in range(1, 3):
        st.markdown(f"**School/Program {idx}**")
        ESchool = st.text_input(f"School/Program {idx}:", key=f"E{idx}s")
        ECitySt = st.text_input(f"City/State {idx}:", key=f"E{idx}cs")
        EDates  = st.text_input(f"Dates {idx}:", key=f"E{idx}d")
        ECred   = st.text_input(f"Certificate/Diploma {idx}:", key=f"E{idx}c")
        edu_blocks.append((ESchool, ECitySt, EDates, ECred))

    # 8. Optional Sections
    st.subheader("8) Optional Sections")
    Other_Work = st.text_area("Other Work Experience (optional):", "")
    Volunteer  = st.text_area("Volunteer Experience (optional):", "")

    submitted = st.form_submit_button("Generate One-Page Resume (DOCX)", type="primary")

# ── Build → Validate → Download
if submitted:
    # lightweight validation so you don’t hand students a blank header
    problems = []
    if not Name.strip(): problems.append("Name is required.")
    if not (Phone.strip() or Email.strip()): problems.append("At least one contact method (Phone or Email) is required.")
    if Objective_Final.strip() == "": problems.append("Objective (final) is required.")
    if problems:
        st.error(" | ".join(problems))
        st.stop()

    if not tpl_bytes:
        st.error("Template not found. Put resume_app_template.docx in the repo or upload one in the sidebar.")
        st.stop()

    # collect workshop answers
    form = {
        "Name": Name, "City": City, "State": State,
        "Phone": Phone, "Email": Email,

        "Objective_Seeking": Obj_Seeking,
        "Objective_Quality": Obj_Quality,
        "Objective_Final": Objective_Final,

        "Skills_Transferable": Skills_Transferable,
        "Skills_JobSpecific": Skills_JobSpecific,
        "Skills_SelfManagement": Skills_SelfManagement,

        "Certifications": Certifications,

        "Other_Work": Other_Work,
        "Volunteer": Volunteer,
    }

    for i, (co, cs, d, ti, du) in enumerate(job_blocks, start=1):
        form[f"Job{i}_Company"]   = co
        form[f"Job{i}_CityState"] = cs
        form[f"Job{i}_Dates"]     = d
        form[f"Job{i}_Title"]     = ti
        form[f"Job{i}_Duties"]    = du

    for i, (sch, cs, d, cr) in enumerate(edu_blocks, start=1):
        form[f"Edu{i}_School"]     = sch
        form[f"Edu{i}_CityState"]  = cs
        form[f"Edu{i}_Dates"]      = d
        form[f"Edu{i}_Credential"] = cr

    # counters (help keep to one page)
    skills_count = len(split_list(Skills_Transferable) + split_list(Skills_JobSpecific) + split_list(Skills_SelfManagement))
    certs_count  = len(split_list(Certifications))
    jobs_count   = sum(1 for i in range(1,4) if form.get(f"Job{i}_Company") or form.get(f"Job{i}_Title"))
    schools_count= sum(1 for i in range(1,3) if form.get(f"Edu{i}_School") or form.get(f"Edu{i}_Credential"))
    st.info(f"Counts → Summary: {len(Objective_Final)} chars | Skills: {skills_count} | Certs: {certs_count} | Jobs: {jobs_count} | Schools: {schools_count}")

    # render + download
    try:
        ctx = build_context(form)
        docx_bytes = render_docx(tpl_bytes, ctx)
        safe_name = (ctx.get("Name") or "Resume").replace(" ", "_")

        # DOCX
        st.download_button(
            "Download DOCX",
            data=docx_bytes,
            file_name=f"{safe_name}_Resume.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )

        # Intake CSV (one-row)
        csv_bytes = intake_to_csv_bytes(form)
        st.download_button(
            "Download Intake CSV",
            data=csv_bytes,
            file_name=f"{safe_name}_Workshop_Intake.csv",
            mime="text/csv",
            use_container_width=True
        )

        st.success("Generated from your exact template.")
        if st.button("Start new student"):
            st.experimental_rerun()

    except Exception as e:
        st.error(f"Template rendering failed: {e}")
