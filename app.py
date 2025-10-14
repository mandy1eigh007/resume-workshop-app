# app.py — Resume + Cover Letter + Instructor Pathway Packet (no AI)
# Features:
# - Trade select (+ optional auto-discovery from your apprenticeship packet)
# - Apprenticeship vs Job mode
# - Upload job descriptions (PDF/DOCX/TXT) → conservative bullet suggestions
# - Resume via your DOCX template (docxtpl)
# - Union-neutral Objective & Cover Letter (filters remove disallowed terms)
# - Instructor Pathway Packet = FULL TEXT of selected pathway docs (no summaries)

from __future__ import annotations
import io, os, re, csv, datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

import pandas as pd
import streamlit as st
from docxtpl import DocxTemplate
from pypdf import PdfReader
from docx import Document as DocxWriter  # for building cover letter & pathway packet
from docx.shared import Pt

# ─────────────────────────────────────────────────────────
# Page
# ─────────────────────────────────────────────────────────
st.set_page_config(page_title="Resume & Cover Letter Workshop", layout="wide")

# ─────────────────────────────────────────────────────────
# One-page & content guardrails
# ─────────────────────────────────────────────────────────
MAX_SUMMARY_CHARS = 450
MAX_SKILLS = 12
MAX_CERTS = 6
MAX_JOBS = 3
MAX_BULLETS_PER_JOB = 4
MAX_SCHOOLS = 2

# Block union/non-union & sub-trade silo in objectives/letters
BANNED_TERMS = [
    r"\bunion\b", r"\bnon[-\s]?union\b", r"\bibew\b", r"\blocal\s*\d+\b",
    r"\binside\s+wire(man|men)?\b", r"\bresidential\b", r"\blow[-\s]?voltage\b",
    r"\bsound\s+and\s+communication(s)?\b"
]
BANNED_RE = re.compile("|".join(BANNED_TERMS), re.I)

def strip_banned(text: str) -> str:
    return BANNED_RE.sub("", text or "").strip()

# ─────────────────────────────────────────────────────────
# Canonical skills + normalization
# ─────────────────────────────────────────────────────────
SKILL_CANON = [
    "Problem-solving","Critical thinking","Attention to detail","Time management",
    "Teamwork & collaboration","Adaptability & willingness to learn","Safety awareness",
    "Conflict resolution","Customer service","Leadership","Reading blueprints & specs",
    "Hand & power tools","Materials handling (wood/concrete/metal)",
    "Operating machinery (e.g., forklifts)","Trades math & measurement",
    "Regulatory compliance","Physical stamina & dexterity",
]
_SKILL_SYNONYMS = {
    "problem solving":"Problem-solving","problem-solving":"Problem-solving",
    "critical-thinking":"Critical thinking","attention to details":"Attention to detail",
    "time-management":"Time management","teamwork":"Teamwork & collaboration",
    "collaboration":"Teamwork & collaboration","adaptability":"Adaptability & willingness to learn",
    "willingness to learn":"Adaptability & willingness to learn","safety":"Safety awareness",
    "customer service skills":"Customer service","leadership skills":"Leadership",
    "blueprints":"Reading blueprints & specs","tools":"Hand & power tools",
    "machinery":"Operating machinery (e.g., forklifts)","math":"Trades math & measurement",
    "measurements":"Trades math & measurement","compliance":"Regulatory compliance",
    "stamina":"Physical stamina & dexterity",
}
def normalize_skill_label(s: str) -> str:
    base = (s or "").strip()
    key = re.sub(r"\s+"," ",base.lower())
    mapped = _SKILL_SYNONYMS.get(key)
    if mapped: return mapped
    return re.sub(r"\s+"," ",base).strip().title()

# ─────────────────────────────────────────────────────────
# Text cleanup
# ─────────────────────────────────────────────────────────
FILLER_LEADS = re.compile(r"^\s*(responsible for|duties included|tasked with|in charge of)\s*:?\s*", re.I)
MULTISPACE = re.compile(r"\s+")
PHONE_DIGITS = re.compile(r"\D+")

def norm_ws(s: str) -> str:
    s = (s or "").strip()
    return MULTISPACE.sub(" ", s)

def cap_first(s: str) -> str:
    s = norm_ws(s)
    return s[:1].upper()+s[1:] if s else s

def clean_bullet(s: str) -> str:
    s = norm_ws(s)
    s = FILLER_LEADS.sub("", s)
    s = re.sub(r"\.+$","", s)
    s = cap_first(s)
    words = s.split()
    return " ".join(words[:20]) if len(words)>20 else s

def clean_phone(s: str) -> str:
    digits = PHONE_DIGITS.sub("", s or "")
    if len(digits)==11 and digits.startswith("1"): digits = digits[1:]
    if len(digits)==10: return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return norm_ws(s or "")

def clean_email(s: str) -> str:
    return (s or "").strip().lower()

def split_list(raw: str) -> List[str]:
    if not raw: return []
    parts = [p.strip() for p in re.split(r"[,\n;]+", raw)]
    return [p for p in parts if p]

def parse_dates(raw: str) -> tuple[str,str]:
    raw = norm_ws(raw)
    if "–" in raw or "-" in raw:
        sep = "–" if "–" in raw else "-"
        bits = [b.strip() for b in raw.split(sep,1)]
        if len(bits)==2: return bits[0], bits[1]
    return (raw,"") if raw else ("","")

# ─────────────────────────────────────────────────────────
# Trade profiles & bullet suggestions (entry-level, conservative)
# ─────────────────────────────────────────────────────────
MASTER_TRADES = [
    "Electrician","Carpenter","Plumber","Laborer","HVAC","Concrete","Roofing",
    "Drywall","Ironworker","Elevator Mechanic","Cement Mason","Bricklayer",
    "Painter","Glazier","Pile Driver","Sheet Metal","Operating Engineer",
    "Lineworker","Tree Trimmer","General"
]

TRADE_SKILL_SUGGEST = {
    "Electrician": ["Hand & power tools","Reading blueprints & specs","Safety awareness","Trades math & measurement"],
    "Carpenter": ["Hand & power tools","Reading blueprints & specs","Attention to detail","Materials handling (wood/concrete/metal)"],
    "Plumber": ["Hand & power tools","Safety awareness","Trades math & measurement","Teamwork & collaboration"],
    "Laborer": ["Materials handling (wood/concrete/metal)","Safety awareness","Operating machinery (e.g., forklifts)","Physical stamina & dexterity"],
    "HVAC": ["Hand & power tools","Reading blueprints & specs","Safety awareness","Trades math & measurement"],
    "Concrete": ["Materials handling (wood/concrete/metal)","Hand & power tools","Teamwork & collaboration","Physical stamina & dexterity"],
    "Roofing": ["Safety awareness","Hand & power tools","Attention to detail","Physical stamina & dexterity"],
    "Drywall": ["Hand & power tools","Attention to detail","Materials handling (wood/concrete/metal)","Teamwork & collaboration"],
    "Ironworker": ["Safety awareness","Rigging basics","Hand & power tools","Working at heights"],
    "Elevator Mechanic": ["Mechanical aptitude","Basic electrical","Tool proficiency","Safety awareness"],
    "Cement Mason": ["Concrete basics","Tool proficiency","Safety awareness","Teamwork & collaboration"],
    "Bricklayer": ["Attention to detail","Tool proficiency","Blueprint reading","Safety awareness"],
    "Lineworker": ["Working at heights","Rigging basics","Basic electrical","Safety awareness"],
    "Tree Trimmer": ["Rigging & ropes","Working at heights","Chainsaw safety","Teamwork & communication"],
    "General": ["Safety awareness","Teamwork & collaboration","Time management","Problem-solving"],
}

TRADE_PROFILE = {
    "Electrician": {"keywords": {"wire":"Pulled wire and organized materials under supervision",
                                 "conduit":"Assisted with conduit measurements and layout",
                                 "panel":"Maintained clean work area and accounted for fixtures and hardware",
                                 "multimeter":"Assisted with basic checks under direction; prioritized safety"}},
    "Ironworker": {"keywords": {"steel":"Handled materials and supported rigging tasks as directed",
                                "rebar":"Assisted with rebar placement and site prep",
                                "beam":"Maintained safe work zones; used fall protection per instruction"}},
    "Elevator Mechanic": {"keywords": {"elevator":"Assisted with equipment staging and fastener prep",
                                       "hoist":"Supported hoisting/rigging tasks per direction",
                                       "control":"Maintained clean work areas; followed LOTO/PPE guidance"}},
    "Plumber": {"keywords": {"pipe":"Assisted with pipe cutting, fitting, and material staging",
                             "fixture":"Staged fixtures and maintained inventory organization"}},
    "Concrete": {"keywords": {"pour":"Supported pours; used proper tools and cleanup procedures",
                              "form":"Assisted with form setup/strip; verified measurements"}},
    "Drywall": {"keywords": {"tape":"Assisted with taping/sanding; kept tools organized",
                             "panel":"Staged and transported panels safely with spotter"}},
    "General": {"keywords": {"clean":"Maintained clean work zones and followed safety procedures",
                             "inventory":"Tracked basic materials and tools; reported shortages promptly"}}
}

# ─────────────────────────────────────────────────────────
# Prior-industry translator (optional CSV, no AI)
# ─────────────────────────────────────────────────────────
def load_mapping(default_path: str = "career_to_construction.csv"):
    rows=[]
    if os.path.exists(default_path):
        with open(default_path, newline="", encoding="utf-8") as f:
            rows += list(csv.DictReader(f))
    up = st.sidebar.file_uploader("Upload translation CSV (industry,keyword,replace_with,note)", type=["csv"])
    if up is not None:
        rows = list(csv.DictReader(io.StringIO(up.getvalue().decode("utf-8"))))
    out=[]
    for r in rows:
        out.append({
            "industry": (r.get("industry") or "").strip().lower(),
            "keyword": (r.get("keyword") or "").strip().lower(),
            "replace_with": (r.get("replace_with") or "").strip(),
            "note": (r.get("note") or "").strip(),
        })
    return out

def translate_line(s: str, mapping: List[Dict[str,str]], industry: str):
    base = (s or "").strip()
    if not base or not mapping: return base
    ind = (industry or "general").lower()
    cands = [r for r in mapping if r["keyword"] and (r["industry"] in ("general", ind))]
    low = base.lower()
    for r in cands:
        if r["keyword"] in low:
            repl = r["replace_with"] or base
            return base.replace(r["keyword"], repl) if r["keyword"] in base else repl
    return base

def translate_bullets(lines: List[str], mapping: List[Dict[str,str]], industry: str):
    out=[]
    for b in lines:
        out.append(clean_bullet(translate_line(b, mapping, industry)))
    return out

def translate_skills(skills: List[str], mapping: List[Dict[str,str]], industry: str):
    out=[]
    for s in skills:
        out.append(norm_ws(translate_line(s, mapping, industry)))
    seen=set(); dedup=[]
    for x in out:
        k=x.lower()
        if k in seen: continue
        seen.add(k); dedup.append(x)
    return dedup[:MAX_SKILLS]

# ─────────────────────────────────────────────────────────
# Upload text extraction
# ─────────────────────────────────────────────────────────
def extract_text_from_pdf(file) -> str:
    try:
        reader = PdfReader(file)
        chunks=[]
        for p in reader.pages:
            txt = p.extract_text() or ""
            chunks.append(txt)
        return "\n".join(chunks)
    except Exception:
        return ""

def extract_text_from_docx(file) -> str:
    try:
        from docx import Document as DocxReader
        doc = DocxReader(file)
        return "\n".join([p.text for p in doc.paragraphs])
    except Exception:
        return ""

def extract_text_generic(upload) -> str:
    name = upload.name.lower()
    if name.endswith(".pdf"): return extract_text_from_pdf(upload)
    if name.endswith(".docx"): return extract_text_from_docx(upload)
    try:
        return upload.getvalue().decode("utf-8", errors="ignore")
    except Exception:
        return ""

# ─────────────────────────────────────────────────────────
# Bullet suggestions from JD text
# ─────────────────────────────────────────────────────────
def suggest_bullets_from_text(text: str, trade: str) -> List[str]:
    low = (text or "").lower()
    profile = TRADE_PROFILE.get(trade, TRADE_PROFILE["General"])
    out=[]
    for kw, stub in profile["keywords"].items():
        if kw in low:
            out.append(stub)
    if not out and low.strip():
        out = [
            "Maintained clean work zones and followed safety procedures",
            "Handled materials and supported crew tasks as directed",
        ]
    seen=set(); dedup=[]
    for b in out:
        if b.lower() in seen: continue
        seen.add(b.lower()); dedup.append(clean_bullet(b))
    return dedup[:MAX_BULLETS_PER_JOB]

# ─────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────
@dataclass
class Job:
    company:str=""; role:str=""; city:str=""; start:str=""; end:str=""; bullets:List[str]=None
    def trim(self,k:int):
        bs=[clean_bullet(b) for b in (self.bullets or []) if b.strip()]
        self.bullets = bs[:k]

@dataclass
class School:
    school:str=""; credential:str=""; year:str=""; details:str=""

# ─────────────────────────────────────────────────────────
# Build resume context for template
# ─────────────────────────────────────────────────────────
def build_resume_context(form: Dict[str,Any], mapping: List[Dict[str,str]], prior_industry:str, trade:str) -> Dict[str,Any]:
    Name=cap_first(form["Name"]); City=cap_first(form["City"]); State=(form["State"] or "").strip().upper()
    phone=clean_phone(form["Phone"]); email=clean_email(form["Email"])
    summary = strip_banned(norm_ws(form["Objective_Final"]))[:MAX_SUMMARY_CHARS]

    skills_all=[]
    for raw in (form["Skills_Transferable"], form["Skills_JobSpecific"], form["Skills_SelfManagement"]):
        skills_all += split_list(raw)

    seen=set(); skills_norm=[]
    for s in skills_all:
        lab=normalize_skill_label(norm_ws(s))
        if lab and lab.lower() not in seen:
            seen.add(lab.lower()); skills_norm.append(lab)

    for s in TRADE_SKILL_SUGGEST.get(trade, []):
        if s.lower() not in seen:
            seen.add(s.lower()); skills_norm.append(s)

    skills = translate_skills(skills_norm, mapping, prior_industry)

    certs = [norm_ws(c) for c in split_list(form["Certifications"] )][:MAX_CERTS]

    jobs=[]
    for idx in range(1, MAX_JOBS+1):
        company=form.get(f"Job{idx}_Company",""); cityst=form.get(f"Job{idx}_CityState","")
        dates=form.get(f"Job{idx}_Dates",""); title=form.get(f"Job{idx}_Title",""); duties=form.get(f"Job{idx}_Duties","")
        if not any([company, title, duties]): continue
        s,e = parse_dates(dates)
        raw_b = [b for b in (duties or "").splitlines() if b.strip()]
        trans_b = translate_bullets(raw_b, mapping, prior_industry)
        j = Job(company=cap_first(company), role=cap_first(title), city=cap_first(cityst),
                start=norm_ws(s), end=norm_ws(e), bullets=trans_b)
        j.trim(MAX_BULLETS_PER_JOB); jobs.append(j)
    jobs = jobs[:MAX_JOBS]

    schools=[]
    for idx in range(1, MAX_SCHOOLS+1):
        sch=form.get(f"Edu{idx}_School",""); cs=form.get(f"Edu{idx}_CityState",""); d=form.get(f"Edu{idx}_Dates",""); cr=form.get(f"Edu{idx}_Credential","")
        if not any([sch,cr,d,cs]): continue
        schools.append(School(school=cap_first(sch), credential=cap_first(cr), year=norm_ws(d), details=cap_first(cs) if cs else ""))

    other_work = norm_ws(form.get("Other_Work",""))
    volunteer  = norm_ws(form.get("Volunteer",""))
    tail=[]
    if other_work: tail.append(f"Other work: {other_work}")
    if volunteer:  tail.append(f"Volunteer: {volunteer}")
    if tail:
        add="  •  ".join(tail)
        summary = (summary + " " + add).strip()[:MAX_SUMMARY_CHARS]

    return {
        "Name": Name, " City": City, "City": City, " State": State, "State": State,
        "phone": phone, "email": email, "summary": summary,
        "skills": skills[:MAX_SKILLS],
        "certs": certs,
        "jobs": [asdict(j) for j in jobs if any([j.company,j.role,j.bullets])],
        "schools": [asdict(s) for s in schools if any([s.school,s.credential,s.year,s.details])],
    }

def render_docx_with_template(template_bytes: bytes, context: Dict[str,Any]) -> bytes:
    tpl = DocxTemplate(io.BytesIO(template_bytes))
    tpl.render(context)
    out = io.BytesIO(); tpl.save(out); out.seek(0)
    return out.getvalue()

# ─────────────────────────────────────────────────────────
# Cover letter (built with python-docx so no extra template needed)
# ─────────────────────────────────────────────────────────
def build_cover_letter_docx(data: Dict[str,str]) -> bytes:
    # sanitize user text against banned terms
    role = strip_banned(data.get("role",""))
    company = strip_banned(data.get("company",""))
    body_strength = strip_banned(data.get("strength",""))
    trade = strip_banned(data.get("trade",""))
    app_type = (data.get("application_type","Apprenticeship") or "Apprenticeship").strip()

    doc = DocxWriter()
    styles = doc.styles['Normal']
    styles.font.name = 'Calibri'
    styles.font.size = Pt(11)

    # Header-ish block
    doc.add_paragraph(f"{data.get('name','')}")
    doc.add_paragraph(f"{data.get('city','')}, {data.get('state','')}")
    contact = ", ".join([x for x in [data.get('phone',''), data.get('email','')] if x])
    if contact: doc.add_paragraph(contact)
    doc.add_paragraph("")  # spacer

    # Date & recipient
    today = datetime.date.today().strftime("%B %d, %Y")
    doc.add_paragraph(today)
    if company: doc.add_paragraph(company)
    if data.get("location"): doc.add_paragraph(data["location"])
    doc.add_paragraph("")

    # Greeting
    doc.add_paragraph("Dear Hiring Committee,")

    # Body (neutral to union / sub-trade)
    p1 = doc.add_paragraph()
    p1.add_run(
        f"I’m applying for a {role} {('apprenticeship' if app_type=='Apprenticeship' else 'position')} "
        f"in the {trade} scope. I bring reliability, safety awareness, and hands-on readiness to contribute on day one."
    )

    p2 = doc.add_paragraph()
    p2.add_run(
        "My background includes construction-site experience, tool proficiency, and teamwork under real schedules. "
        "I’m punctual, coachable, and committed to quality and safe production."
    )

    if body_strength:
        doc.add_paragraph("Highlights:")
        for line in split_list(body_strength):
            doc.add_paragraph(f"• {line}", style=None)

    p3 = doc.add_paragraph()
    p3.add_run(
        "Thank you for your consideration. I’m ready to support your crew and learn the trade the right way."
    )

    doc.add_paragraph("")
    doc.add_paragraph(f"Sincerely,")
    doc.add_paragraph(data.get("name",""))

    bio = io.BytesIO(); doc.save(bio); bio.seek(0)
    return bio.getvalue()

# ─────────────────────────────────────────────────────────
# Instructor Pathway Packet (FULL TEXT — no summaries)
# ─────────────────────────────────────────────────────────
def choose_relevant_pathway_files(trade: str, uploads: List[Any]) -> List[Any]:
    """
    Select files whose names hint at the chosen trade. Always include any general packet.
    """
    name_hits=[]
    t = trade.lower()
    keywords = {
        "electrician": ["electric","line","tacoma power","meter","wire"],
        "ironworker": ["iron","rebar","steel"],
        "elevator mechanic": ["elevator","escalator","lift","neiep","iuec"],
        "plumber": ["plumb","pipe","roadmap"],
        "cement mason": ["cement","concrete","mason"],
        "bricklayer": ["brick","masonry","bac"],
        "lineworker": ["line jatc","lineworker","tree","powerline"],
        "tree trimmer": ["tree","clearance","power line"],
        "general": [],
    }
    kw = keywords.get(trade.lower(), [])
    for f in uploads:
        name = f.name.lower()
        if "seattle construction trades apprenticeship roadmaps" in name:  # general
            name_hits.append(f); continue
        if not kw: continue
        if any(k in name for k in kw):
            name_hits.append(f)
    # If nothing matched, include all so instructors still get everything (full text)
    return name_hits or uploads

def build_pathway_packet_docx(student: Dict[str,str], trade: str, app_type: str, sources: List[Any]) -> bytes:
    """
    Create DOCX that embeds FULL TEXT from each uploaded pathway document.
    """
    doc = DocxWriter()
    styles = doc.styles['Normal']; styles.font.name = 'Calibri'; styles.font.size = Pt(11)

    doc.add_heading("Instructor Pathway Packet", level=0)
    meta = f"Student: {student.get('name','')} | Trade: {trade} | Application type: {app_type}"
    doc.add_paragraph(meta)
    doc.add_paragraph("")

    for upl in sources:
        doc.add_page_break()
        doc.add_heading(upl.name, level=1)
        text = extract_text_generic(upl)
        # Include all text, no summarization
        if text.strip():
            for line in text.splitlines():
                doc.add_paragraph(line)
        else:
            doc.add_paragraph("[Text could not be extracted from this file.]")

    out = io.BytesIO(); doc.save(out); out.seek(0)
    return out.getvalue()

# ─────────────────────────────────────────────────────────
# Sidebar — templates, mappings, pathway sources, auto trade discovery
# ─────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Templates & Options")

    # Resume template
    tpl_bytes=None
    if os.path.exists("resume_app_template.docx"):
        with open("resume_app_template.docx","rb") as f: tpl_bytes=f.read()
    upl_tpl = st.file_uploader("Upload RESUME DOCX template (optional)", type=["docx"])
    if upl_tpl is not None: tpl_bytes = upl_tpl.read()

    st.markdown("---")
    mapping = load_mapping()
    prior_industry = st.selectbox(
        "Prior industry (optional translator, no AI)",
        ["general","retail","food service","warehouse","janitorial","childcare",
         "call center","security","delivery","reception","housekeeping",
         "fitness","teaching","artist","data entry","grocery","landscaping"],
        index=0
    )

    st.markdown("---")
    st.caption("Upload pathway/source docs (PDF/DOCX/TXT). These will be embedded FULL TEXT in the Instructor Packet.")
    pathway_uploads = st.file_uploader("Upload pathway documents", type=["pdf","docx","txt"], accept_multiple_files=True)

    st.caption("Optional: upload your Apprenticeship Packet to auto-discover trades (e.g., Seattle Construction Trades packet).")
    trade_packet = st.file_uploader("Upload apprenticeship packet (PDF/DOCX)", type=["pdf","docx"])

# Auto-discover trades present in a packet (simple keyword scan)
def discover_trades(packet_upload) -> List[str]:
    text = extract_text_generic(packet_upload) if packet_upload else ""
    found=[]
    low=text.lower()
    for t in MASTER_TRADES:
        if t.lower() in low: found.append(t)
    return sorted(set(found)) if found else []

discovered = discover_trades(trade_packet)
TRADE_OPTIONS = discovered or MASTER_TRADES

# ─────────────────────────────────────────────────────────
# Main UI
# ─────────────────────────────────────────────────────────
st.markdown("# Resume & Cover Letter Workshop")

# 1) Application type & trade
st.subheader("1) Target & Trade")
colA, colB = st.columns([1,1])
with colA:
    application_type = st.radio("Are you applying for:", ["Apprenticeship","Job"], index=0, horizontal=True)
with colB:
    trade = st.selectbox("Select your trade target:", TRADE_OPTIONS, index=0)

# 2) Upload job descriptions/postings
st.subheader("2) Upload job descriptions or postings (PDF, DOCX, TXT)")
uploads = st.file_uploader("Upload one or more files", type=["pdf","docx","txt"], accept_multiple_files=True)
jd_text = ""
if uploads:
    for f in uploads:
        jd_text += "\n" + extract_text_generic(f)
jd_suggestions = suggest_bullets_from_text(jd_text, trade) if jd_text else []

with st.form("workshop"):
    # 3) Contact
    st.subheader("3) Contact")
    c1,c2 = st.columns(2)
    with c1:
        Name = st.text_input("Name","")
        City = st.text_input("City","")
        State = st.text_input("State (2-letter)","")
    with c2:
        Phone = st.text_input("Phone","")
        Email = st.text_input("Email","")

    # 4) Objective (union-neutral)
    st.subheader("4) Objective")
    st.caption("Neutral wording (no union/non-union, no sub-trade labels).")
    Obj_Seeking = st.text_input("Target role (e.g., Entry-level Electrician / Pre-apprentice):", f"{trade} pre-apprentice" if application_type=="Apprenticeship" else f"Entry-level {trade}")
    Obj_Quality = st.text_input("One strength to highlight (e.g., safety, reliability):","safety mindset")
    Objective_Final = st.text_area("Final objective (1–2 sentences):","I’m seeking hands-on experience as an entry-level contributor in construction, bringing a safety mindset, reliability, and readiness to learn.")

    # 5) Skills
    st.subheader("5) Skills")
    quick_transfer = st.multiselect("Quick add transferable skills:", SKILL_CANON, default=[])
    quick_trade = st.multiselect("Quick add trade-specific skills:", TRADE_SKILL_SUGGEST.get(trade, []), default=TRADE_SKILL_SUGGEST.get(trade, []))
    Skills_Transferable = st.text_area("Extra Transferable Skills (comma/newline):","")
    Skills_JobSpecific = st.text_area("Job-Specific Skills (comma/newline):","")
    Skills_SelfManagement = st.text_area("Self-Management Skills (comma/newline):","")

    # 6) Work Experience
    st.subheader("6) Work Experience (up to 3)")
    job_blocks=[]
    for idx in range(1, MAX_JOBS+1):
        st.markdown(f"**Job {idx}**")
        j1,j2 = st.columns(2)
        with j1:
            JobCompany = st.text_input(f"Job {idx} – Company:", key=f"J{idx}c")
            JobCitySt  = st.text_input(f"Job {idx} – City/State:", key=f"J{idx}cs")
            JobDates   = st.text_input(f"Job {idx} – Dates (e.g., 2023-06 – 2024-05 or Present):", key=f"J{idx}d")
        with j2:
            JobTitle   = st.text_input(f"Job {idx} – Title:", key=f"J{idx}t")
            placeholder = "One per line, e.g., Assisted with conduit layout\nUsed PPE and kept work zone clean"
            defaults = "\n".join(jd_suggestions) if (idx==1 and jd_suggestions) else ""
            JobDuties  = st.text_area(f"Job {idx} – Duties/Accomplishments (1–4 bullets):", key=f"J{idx}du", value=defaults, placeholder=placeholder)
        job_blocks.append((JobCompany, JobCitySt, JobDates, JobTitle, JobDuties))

    # 7) Certifications
    st.subheader("7) Certifications")
    Certifications = st.text_area("List certifications (comma/newline). If none, write 'None yet' or planned:","OSHA-10")

    # 8) Education
    st.subheader("8) Education (up to 2)")
    edu_blocks=[]
    for idx in range(1, MAX_SCHOOLS+1):
        st.markdown(f"**School/Program {idx}**")
        ESchool = st.text_input(f"School/Program {idx}:", key=f"E{idx}s")
        ECitySt = st.text_input(f"City/State {idx}:", key=f"E{idx}cs")
        EDates  = st.text_input(f"Dates {idx}:", key=f"E{idx}d")
        ECred   = st.text_input(f"Certificate/Diploma {idx}:", key=f"E{idx}c")
        edu_blocks.append((ESchool, ECitySt, EDates, ECred))

    # 9) Optional
    st.subheader("9) Optional")
    Other_Work = st.text_area("Other Work Experience (optional):","")
    Volunteer  = st.text_area("Volunteer Experience (optional):","")

    # 10) Cover Letter fields
    st.subheader("10) Cover Letter")
    CL_Company = st.text_input("Company/Employer (for the letter):","")
    CL_Role    = st.text_input("Role Title (for the letter):", f"{trade} Apprentice" if application_type=="Apprenticeship" else f"Entry-level {trade}")
    CL_Location= st.text_input("Company Location (City, State):","")
    CL_Highlights = st.text_area("Optional: bullet highlights (comma/newline):","Reliable • Safety-focused • Coachable")

    submitted = st.form_submit_button("Generate Resume + Cover Letter + Instructor Packet", type="primary")

# ─────────────────────────────────────────────────────────
# Build → Validate → Export
# ─────────────────────────────────────────────────────────
if submitted:
    problems=[]
    if not Name.strip(): problems.append("Name is required.")
    if not (Phone.strip() or Email.strip()): problems.append("At least one contact method (Phone or Email) is required.")
    if Objective_Final.strip()=="": problems.append("Objective (final) is required.")
    if problems:
        st.error(" | ".join(problems)); st.stop()

    # Merge quick-adds
    if quick_transfer:
        Skills_Transferable = (Skills_Transferable + (", " if Skills_Transferable.strip() else "") + ", ".join(quick_transfer))
    if quick_trade:
        Skills_JobSpecific = (Skills_JobSpecific + (", " if Skills_JobSpecific.strip() else "") + ", ".join(quick_trade))

    # Build intake dict
    form = {
        "Name": Name, "City": City, "State": State,
        "Phone": Phone, "Email": Email,
        "Objective_Seeking": Obj_Seeking, "Objective_Quality": Obj_Quality,
        "Objective_Final": Objective_Final,
        "Skills_Transferable": Skills_Transferable,
        "Skills_JobSpecific": Skills_JobSpecific,
        "Skills_SelfManagement": Skills_SelfManagement,
        "Certifications": Certifications,
        "Other_Work": Other_Work, "Volunteer": Volunteer,
    }
    for i,(co,cs,d,ti,du) in enumerate(job_blocks, start=1):
        form[f"Job{i}_Company"]=co; form[f"Job{i}_CityState"]=cs; form[f"Job{i}_Dates"]=d
        form[f"Job{i}_Title"]=ti; form[f"Job{i}_Duties"]=du
    for i,(sch,cs,d,cr) in enumerate(edu_blocks, start=1):
        form[f"Edu{i}_School"]=sch; form[f"Edu{i}_CityState"]=cs; form[f"Edu{i}_Dates"]=d; form[f"Edu{i}_Credential"]=cr

    # Counts/debug
    skills_count = len(split_list(Skills_Transferable)+split_list(Skills_JobSpecific)+split_list(Skills_SelfManagement))
    certs_count  = len(split_list(Certifications))
    jobs_count   = sum(1 for i in range(1,MAX_JOBS+1) if form.get(f"Job{i}_Company") or form.get(f"Job{i}_Title"))
    schools_count= sum(1 for i in range(1,MAX_SCHOOLS+1) if form.get(f"Edu{i}_School") or form.get(f"Edu{i}_Credential"))
    st.info(f"Counts → Summary: {len(Objective_Final)} chars | Skills: {skills_count} | Certs: {certs_count} | Jobs: {jobs_count} | Schools: {schools_count}")

    # Resume via template
    if not tpl_bytes:
        st.error("Template not found. Put resume_app_template.docx in the repo or upload it in the sidebar.")
        st.stop()

    try:
        resume_ctx = build_resume_context(form, mapping, prior_industry, trade)
        resume_bytes = render_docx_with_template(tpl_bytes, resume_ctx)
    except Exception as e:
        st.error(f"Resume template rendering failed: {e}")
        st.stop()

    # Cover letter (union-neutral)
    cover_bytes = build_cover_letter_docx({
        "name": Name, "city": City, "state": State, "phone": clean_phone(Phone), "email": clean_email(Email),
        "company": CL_Company, "role": CL_Role, "location": CL_Location,
        "trade": trade, "strength":
