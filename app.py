# app.py — Resume Workshop & Pathways (Seattle Tri-County)
# Streamlit single-file app. No APIs. Browser-only. Python 3.11.
# This build:
# - Uses Job_History_Master.docx (Heading 1 = role; bullet paragraphs = duties)
# - Removes "difference" section; straight resume building
# - Autofills header (Name/Phone/Email/City/State) from uploaded text
# - Objective = recommendations only; student types final
# - Skills auto-suggested from uploaded text + selected role bullets
# - Work Experience: detect roles, select roles, click bullets → insert into Job 1/2/3 duties
# - Neutral language preserved

from __future__ import annotations
import io, os, re, csv, datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple

import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
from docx import Document as DocxWriter
from docx.shared import Pt
from pypdf import PdfReader
import requests

# Optional PDF fallback if present (no error if missing)
try:
    from pdfminer.high_level import extract_text as pdfminer_extract_text
except Exception:
    pdfminer_extract_text = None

st.set_page_config(page_title="Resume Workshop & Pathways", layout="wide")

# ─────────────────────────────────────────────────────────
# Constants / regex
# ─────────────────────────────────────────────────────────
MAX_SUMMARY_CHARS = 450
MAX_SKILLS = 12
MAX_CERTS = 8
MAX_JOBS = 3
MAX_BULLETS_PER_JOB = 4
MAX_SCHOOLS = 2

UNION_BANS = [
    r"\bunion\b", r"\bnon[-\s]?union\b", r"\bibew\b", r"\blocal\s*\d+\b",
    r"\binside\s*wire(man|men)?\b", r"\blow[-\s]?voltage\b", r"\bsound\s+and\s+communication(s)?\b",
    r"\bneca\b", r"\bopen[-\s]?shop\b"
]
BANNED_RE = re.compile("|".join(UNION_BANS), re.I)
FILLER_LEADS = re.compile(r"^\s*(responsible for|duties included|tasked with|in charge of)\s*:?\s*", re.I)
MULTISPACE = re.compile(r"\s+")
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(\+?1[\s\-\.])?\(?\d{3}\)?[\s\-\.]?\d{3}[\s\-\.]?\d{4}")
PHONE_DIGITS = re.compile(r"\D+")
CITY_STATE_RE = re.compile(r"\b([A-Za-z .'-]{2,}),\s*([A-Za-z]{2})\b")
DATE_RANGE_RE = re.compile(
    r"(?P<start>(?:\d{4}|\w{3,9}\s+\d{4}))\s*(?:–|-|to|until|through)\s*(?P<end>(?:Present|Current|\d{4}|\w{3,9}\s+\d{4}))",
    re.I
)

# ─────────────────────────────────────────────────────────
# Basic cleaners
# ─────────────────────────────────────────────────────────
def strip_banned(text: str) -> str:
    return BANNED_RE.sub("", text or "").strip()

def norm_ws(s: str) -> str:
    s = (s or "").strip()
    return MULTISPACE.sub(" ", s)

def cap_first(s: str) -> str:
    s = norm_ws(s)
    return s[:1].upper()+s[1:] if s else s

def clean_phone(s: str) -> str:
    digits = PHONE_DIGITS.sub("", s or "")
    if len(digits)==11 and digits.startswith("1"): digits = digits[1:]
    if len(digits)==10: return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return norm_ws(s or "")

def clean_email(s: str) -> str:
    return (s or "").strip().lower()

def clean_bullet(s: str) -> str:
    s = norm_ws(s)
    s = re.sub(r"^[•\-\u2022]+\s*", "", s)
    s = FILLER_LEADS.sub("", s)
    s = re.sub(r"\.+$","", s)
    s = cap_first(s)
    words = s.split()
    return " ".join(words[:24]) if len(words)>24 else s

def split_list(raw: str) -> List[str]:
    if not raw: return []
    parts = [p.strip(" •\t") for p in re.split(r"[,\n;•]+", raw)]
    return [p for p in parts if p]

def parse_dates(raw: str) -> tuple[str,str]:
    raw = norm_ws(raw)
    m = DATE_RANGE_RE.search(raw)
    if m: return (m.group("start"), m.group("end"))
    if "–" in raw or "-" in raw:
        sep = "–" if "–" in raw else "-"
        bits = [b.strip() for b in raw.split(sep,1)]
        if len(bits)==2: return bits[0], bits[1]
    return (raw,"") if raw else ("","")

# ─────────────────────────────────────────────────────────
# File text extraction & public URL fetch
# ─────────────────────────────────────────────────────────
def extract_text_from_pdf(file) -> str:
    try:
        reader = PdfReader(file); chunks=[]
        for p in reader.pages:
            txt = p.extract_text() or ""
            chunks.append(txt)
        text = "\n".join(chunks)
        if text.strip(): return text
    except Exception:
        pass
    if pdfminer_extract_text is not None:
        try:
            if hasattr(file, "getvalue"):
                bio = io.BytesIO(file.getvalue())
            else:
                file.seek(0); bio = file
            text = pdfminer_extract_text(bio) or ""
            return text
        except Exception:
            return ""
    return ""

def extract_text_from_docx(file) -> str:
    try:
        from docx import Document as DocxReader
        doc = DocxReader(file)
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception:
        return ""

def extract_text_generic(upload) -> str:
    name = getattr(upload, "name", "").lower()
    if name.endswith(".pdf"): return extract_text_from_pdf(upload)
    if name.endswith(".docx"): return extract_text_from_docx(upload)
    try:
        return upload.getvalue().decode("utf-8", errors="ignore")
    except Exception:
        return ""

class NamedBytesIO(io.BytesIO):
    def __init__(self, data: bytes, name: str):
        super().__init__(data)
        self.name = name

def _drive_direct(url: str) -> str:
    m = re.search(r"/d/([a-zA-Z0-9_-]+)", url) or re.search(r"[?&]id=([a-zA-Z0-9_-]+)", url)
    if m:
        file_id = m.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url

def fetch_url_to_named_bytes(url: str, fallback_name: str = "downloaded_file") -> NamedBytesIO | None:
    try:
        u = _drive_direct(url.strip())
        r = requests.get(u, timeout=30)
        r.raise_for_status()
        name = (url.split("?")[0].rstrip("/").split("/")[-1] or fallback_name)
        if "." not in name:
            ct = r.headers.get("content-type","").lower()
            if "pdf" in ct: name += ".pdf"
            elif "word" in ct or "officedocument" in ct: name += ".docx"
            else: name += ".txt"
        return NamedBytesIO(r.content, name)
    except Exception:
        return None

# ─────────────────────────────────────────────────────────
# Skills canon & mining
# ─────────────────────────────────────────────────────────
SKILL_CANON = [
    "Problem-solving","Critical thinking","Attention to detail","Time management",
    "Teamwork & collaboration","Adaptability & willingness to learn","Safety awareness",
    "Conflict resolution","Customer service","Leadership","Reading blueprints & specs",
    "Hand & power tools","Materials handling (wood/concrete/metal)","Operating machinery",
    "Trades math & measurement","Regulatory compliance","Physical stamina & dexterity"
]
_SKILL_SYNONYMS = {
    "problem solving":"Problem-solving","problem-solving":"Problem-solving",
    "critical-thinking":"Critical thinking","attention to details":"Attention to detail",
    "time-management":"Time management","teamwork":"Teamwork & collaboration",
    "collaboration":"Teamwork & collaboration","adaptability":"Adaptability & willingness to learn",
    "willingness to learn":"Adaptability & willingness to learn","safety":"Safety awareness",
    "customer service skills":"Customer service","leadership skills":"Leadership",
    "blueprints":"Reading blueprints & specs","tools":"Hand & power tools",
    "machinery":"Operating machinery","math":"Trades math & measurement",
    "measurements":"Trades math & measurement","compliance":"Regulatory compliance",
    "stamina":"Physical stamina & dexterity","forklift":"Operating machinery",
}
TRANSFERABLE_KEYWORDS = {
    "problem": "Problem-solving", "solve": "Problem-solving", "troubleshoot": "Problem-solving",
    "analyz": "Critical thinking", "priorit": "Time management", "deadline": "Time management",
    "detail": "Attention to detail", "team": "Teamwork & collaboration", "collabor": "Teamwork & collaboration",
    "adapt": "Adaptability & willingness to learn", "learn": "Adaptability & willingness to learn",
    "safety": "Safety awareness", "osha": "Safety awareness", "customer": "Customer service",
    "lead": "Leadership", "blueprint": "Reading blueprints & specs", "spec": "Reading blueprints & specs",
    "tool": "Hand & power tools", "drill": "Hand & power tools", "saw": "Hand & power tools",
    "forklift": "Operating machinery", "material": "Materials handling (wood/concrete/metal)",
    "machin": "Operating machinery", "math": "Trades math & measurement", "measure": "Trades math & measurement",
    "code": "Regulatory compliance", "permit": "Regulatory compliance", "compliance": "Regulatory compliance",
    "stamina": "Physical stamina & dexterity", "lift": "Physical stamina & dexterity",
}

def normalize_skill_label(s: str) -> str:
    base = (s or "").strip()
    key = re.sub(r"\s+"," ",base.lower())
    mapped = _SKILL_SYNONYMS.get(key)
    if mapped: return mapped
    return re.sub(r"\s+"," ",base).strip().title()

def suggest_transferable_skills_from_text(text: str) -> List[str]:
    hits = {}
    low = (text or "").lower()
    for kw, skill in TRANSFERABLE_KEYWORDS.items():
        if kw in low:
            hits[skill] = hits.get(skill, 0) + 1
    ordered = [s for s,_ in sorted(hits.items(), key=lambda kv: -kv[1])]
    canon_order = [s for s in SKILL_CANON if s in ordered]
    return canon_order[:8]

def categorize_skills(skills: List[str]) -> Dict[str, List[str]]:
    out = {"Transferable": [], "Job-Specific": [], "Self-Management": []}
    seen=set()
    for s in skills:
        lab = normalize_skill_label(s)
        if not lab: continue
        if lab.lower() in seen: continue
        seen.add(lab.lower())
        # light heuristic to place
        if lab in {"Reading blueprints & specs","Hand & power tools","Operating machinery","Materials handling (wood/concrete/metal)","Trades math & measurement","Regulatory compliance","Safety awareness"}:
            cat="Job-Specific"
        elif lab in {"Leadership","Adaptability & willingness to learn","Physical stamina & dexterity"}:
            cat="Self-Management"
        else:
            cat="Transferable"
        out[cat].append(lab)
    return out

# ─────────────────────────────────────────────────────────
# Trade taxonomy
# ─────────────────────────────────────────────────────────
TRADE_TAXONOMY = [
    "Boilermaker (Local 104, 502)",
    "Bricklayer / BAC Allied (Brick/Tile/Terrazzo/Marble/PCC)",
    "Carpenter (General)",
    "Carpenter – Interior Systems",
    "Millwright",
    "Pile Driver",
    "Cement Mason (OPCMIA 528)",
    "Drywall Finisher (IUPAT)",
    "Electrician – Inside (01)",
    "Electrician – Limited Energy (06)",
    "Electrician – Residential (02)",
    "Elevator Constructor (IUEC/NEIEP)",
    "Floor Layer (IUPAT)",
    "Glazier (IUPAT 188)",
    "Heat & Frost Insulator (Local 7)",
    "Ironworker (Local 86)",
    "Laborer (LIUNA 242/252/292)",
    "Operating Engineer (IUOE 302/612)",
    "Painter (IUPAT DC5)",
    "Plasterer (OPCMIA 528)",
    "Plumber / Steamfitter / HVAC-R (UA 32 / UA 26)",
    "Roofer (Local 54/153)",
    "Sheet Metal (SMART 66)",
    "Sprinkler Fitter (UA 699)",
    "High Voltage – Outside Lineman (NW Line JATC)",
    "Power Line Clearance Tree Trimmer (NW Line JATC)",
]

# ─────────────────────────────────────────────────────────
# Parse Job_History_Master.docx
# ─────────────────────────────────────────────────────────
def read_job_master() -> Dict[str, List[str]]:
    # Try sidebar upload first; else repo root file
    if "job_master_bytes" in st.session_state:
        raw = st.session_state["job_master_bytes"]
        doc = DocxWriter(io.BytesIO(raw))
    else:
        path = "Job_History_Master.docx"
        if not os.path.exists(path):
            return {}
        doc = DocxWriter(path)
    roles: Dict[str,List[str]] = {}
    cur = None
    for p in doc.paragraphs:
        style = (p.style.name or "").lower() if p.style else ""
        text = (p.text or "").strip()
        if not text:
            continue
        if "heading 1" in style:
            cur = text
            roles.setdefault(cur, [])
            continue
        # treat list bullet or plain text under a role as a bullet
        if cur:
            roles[cur].append(clean_bullet(text))
    # Dedup and clamp
    for k,v in roles.items():
        dedup=[]; seen=set()
        for b in v:
            key=b.lower()
            if key in seen: continue
            seen.add(key); dedup.append(b)
        roles[k]=dedup[:12]
    return roles

# Skill suggestions derived from chosen bullets (simple keyword map)
BULLET_SKILL_HINTS = [
    (re.compile(r"\b(anchor|bolt|rig|signal|bucket|harness|tie[-\s]?off|drop zone)\b", re.I), "Safety awareness"),
    (re.compile(r"\b(clean|organize|stage|restock|housekeep|walkway)\b", re.I), "Attention to detail"),
    (re.compile(r"\b(pallet|forklift|lift|jack|rig|hoist|carry|load|unload)\b", re.I), "Materials handling (wood/concrete/metal)"),
    (re.compile(r"\b(conduit|measure|layout|prints?|drawings?)\b", re.I), "Reading blueprints & specs"),
    (re.compile(r"\b(grinder|drill|saw|snips|hand tools|power tools)\b", re.I), "Hand & power tools"),
    (re.compile(r"\b(ppa|ppe|osha|lockout|tagout|loto|hazard|spill)\b", re.I), "Regulatory compliance"),
    (re.compile(r"\b(count|verify|qc|inspect|torque)\b", re.I), "Critical thinking"),
    (re.compile(r"\b(rush|deadlines?|targets?|production|pace)\b", re.I), "Time management"),
    (re.compile(r"\b(team|crew|assist|support|communicat)\b", re.I), "Teamwork & collaboration"),
    (re.compile(r"\b(climb|lift|carry|physical)\b", re.I), "Physical stamina & dexterity"),
]

def skills_from_bullets(bullets: List[str]) -> List[str]:
    hits=set()
    for b in bullets:
        for rx, skill in BULLET_SKILL_HINTS:
            if rx.search(b):
                hits.add(skill)
    return list(hits)

# Role detection from uploaded text (naive keyword match)
def detect_roles_from_text(text: str, all_roles: List[str]) -> List[str]:
    low = (text or "").lower()
    found=[]
    for r in all_roles:
        k=r.lower()
        # break to simple triggers (line cook → "line cook"; warehouse associate → "warehouse")
        tokens = [w for w in re.split(r"[^a-z0-9]+", k) if len(w)>=4]
        if any(t in low for t in tokens):
            found.append(r)
    # dedup, keep order of appearance in all_roles
    seen=set(); out=[]
    for r in all_roles:
        if r in found and r not in seen:
            seen.add(r); out.append(r)
    return out[:10]

# ─────────────────────────────────────────────────────────
# Parsing helpers (header/jobs/edu/certs)
# ─────────────────────────────────────────────────────────
def parse_header(text: str) -> Dict[str,str]:
    name = ""; email = ""; phone = ""; city = ""; state = ""
    m = EMAIL_RE.search(text or "");  email = m.group(0) if m else ""
    m = PHONE_RE.search(text or "");  phone = m.group(0) if m else ""
    # Try to find a top contact block
    top = "\n".join([l.strip() for l in (text or "").splitlines()[:18] if l.strip()])
    sep_line = re.sub(r"[•·–—\-•]+", "|", top)
    for candidate in sep_line.split("\n"):
        if "@" in candidate or re.search(r"\d{3}.*\d{4}", candidate):
            parts = [p.strip() for p in re.split(r"\|", candidate) if p.strip()]
            for p in parts:
                if EMAIL_RE.search(p) or PHONE_RE.search(p):
                    continue
                mcs = CITY_STATE_RE.search(p)
                if mcs:
                    city, state = mcs.group(1), mcs.group(2).upper()
                    continue
                if 2 <= len(p.split()) <= 4 and not re.search(r"\d", p):
                    caps = sum(w[:1].isupper() for w in p.split())
                    if caps >= 2:
                        name = p
                        break
    if not name:
        for l in [l.strip() for l in (text or "").splitlines()[:15]]:
            if EMAIL_RE.search(l) or PHONE_RE.search(l):
                continue
            if any(h in l.lower() for h in ["objective","summary","skills","experience","education"]):
                continue
            if 2 <= len(l.split()) <= 4 and all(w and w[0].isalpha() for w in l.split()):
                tokens = l.split()
                if sum(t[:1].isupper() for t in tokens) >= 2:
                    name = l
                    break
    if not city or not state:
        m2 = CITY_STATE_RE.search(text or "")
        if m2:
            city, state = m2.group(1), m2.group(2).upper()
    return {"Name": cap_first(name), "Email": clean_email(email), "Phone": clean_phone(phone),
            "City": cap_first(city), "State": (state or "").strip()}

def parse_education(text: str) -> List[Dict[str,str]]:
    out=[]
    lines = [l.strip() for l in (text or "").splitlines()]
    i=0
    while i < len(lines) and len(out) < MAX_SCHOOLS:
        l = lines[i]
        if re.search(r"(high school|ged|college|university|program|certificate|diploma)", l, re.I):
            school = cap_first(l)
            cred=""; year=""; details=""
            for la in lines[i+1:i+5]:
                if re.search(r"\b(20\d{2}|19\d{2})\b", la):
                    year = la.strip()
                mcs = CITY_STATE_RE.search(la)
                if mcs:
                    details = f"{mcs.group(1)}, {mcs.group(2).upper()}"
                if any(x in la.lower() for x in ["diploma","degree","certificate","ged","program"]) and not cred:
                    cred = cap_first(la.strip())
            out.append({"school": school, "credential": cred, "year": year, "details": details})
        i+=1
    return out[:MAX_SCHOOLS]

CERT_KEYWORDS = [
    "osha", "forklift", "flagger", "cpr", "first aid", "hazwoper",
    "twic", "nccer", "confined space", "ppe", "aerial lift", "traffic control"
]
def parse_certs(text: str) -> List[str]:
    low = (text or "").lower()
    found=set()
    for k in CERT_KEYWORDS:
        if k in low:
            if k=="osha": found.add("OSHA-10")
            elif k=="first aid": found.add("First Aid")
            elif k=="aerial lift": found.add("Aerial Lift")
            else: found.add(k.title())
    for line in (text or "").splitlines():
        if re.search(r"flagger", line, re.I): found.add("Flagger")
        if re.search(r"forklift", line, re.I): found.add("Forklift")
        if re.search(r"\bcpr\b", line, re.I): found.add("CPR")
    return sorted(found)

# ─────────────────────────────────────────────────────────
# Data classes + resume rendering
# ─────────────────────────────────────────────────────────
@dataclass
class Job:
    company:str=""; role:str=""; city:str=""; start:str=""; end:str=""; bullets:List[str]=None
    def trim(self,k:int):
        bs=[clean_bullet(b) for b in (self.bullets or []) if str(b).strip()]
        self.bullets = bs[:k]

@dataclass
class School:
    school:str=""; credential:str=""; year:str=""; details:str=""

def build_resume_context(form: Dict[str,Any], trade_label: str) -> Dict[str,Any]:
    Name=cap_first(form["Name"]); City=cap_first(form["City"]); State=(form["State"] or "").strip().upper()
    phone=clean_phone(form["Phone"]); email=clean_email(form["Email"])

    # Objective: use user's final (recommendations were shown earlier; not auto-inserted)
    summary = strip_banned(norm_ws(form.get("Objective_Final","")))[:MAX_SUMMARY_CHARS]

    # Skills
    skills_all=[]
    for raw in (form.get("Skills_Transferable",""), form.get("Skills_JobSpecific",""), form.get("Skills_SelfManagement","")):
        skills_all += split_list(raw)
    seen=set(); skills=[]
    for s in skills_all:
        lab=normalize_skill_label(norm_ws(s))
        if lab and lab.lower() not in seen:
            seen.add(lab.lower()); skills.append(lab)
    skills = skills[:MAX_SKILLS]

    certs = [norm_ws(c) for c in split_list(form.get("Certifications",""))][:MAX_CERTS]

    jobs=[]
    for idx in range(1, MAX_JOBS+1):
        company=form.get(f"Job{idx}_Company",""); cityst=form.get(f"Job{idx}_CityState","")
        dates=form.get(f"Job{idx}_Dates",""); title=form.get(f"Job{idx}_Title",""); duties=form.get(f"Job{idx}_Duties","")
        if not any([company, title, duties, dates, cityst]): continue
        s,e = parse_dates(dates)
        raw_b = [b for b in (duties or "").splitlines() if b.strip()]
        j = Job(company=cap_first(company), role=cap_first(title), city=cap_first(cityst),
                start=norm_ws(s), end=norm_ws(e), bullets=raw_b)
        j.trim(MAX_BULLETS_PER_JOB); jobs.append(j)
    jobs = jobs[:MAX_JOBS]

    schools=[]
    for idx in range(1, MAX_SCHOOLS+1):
        sch=form.get(f"Edu{idx}_School",""); cs=form.get(f"Edu{idx}_CityState",""); d=form.get(f"Edu{idx}_Dates",""); cr=form.get(f"Edu{idx}_Credential","")
        if not any([sch,cr,d,cs]): continue
        schools.append(School(school=cap_first(sch), credential=cap_first(cr), year=norm_ws(d), details=cap_first(cs) if cs else ""))

    return {
        "Name": Name, "City": City, "State": State,
        "phone": phone, "email": email, "summary": summary,
        "skills": skills,
        "certs": certs,
        "jobs": [asdict(j) for j in jobs if any([j.company,j.role,j.bullets])],
        "schools": [asdict(s) for s in schools if any([s.school,s.credential,s.year,s.details])],
        "trade_label": trade_label,
    }

def render_docx_with_template(template_bytes: bytes, context: Dict[str,Any]) -> bytes:
    tpl = DocxTemplate(io.BytesIO(template_bytes))
    tpl.render(context)
    out = io.BytesIO(); tpl.save(out); out.seek(0)
    return out.getvalue()

def build_cover_letter_docx(data: Dict[str,str]) -> bytes:
    role = strip_banned(data.get("role",""))
    company = strip_banned(data.get("company",""))
    body_strength = strip_banned(data.get("strength",""))
    trade_label = strip_banned(data.get("trade_label",""))
    app_type = (data.get("application_type","Apprenticeship") or "Apprenticeship").strip()

    doc = DocxWriter()
    styles = doc.styles['Normal']; styles.font.name = 'Calibri'; styles.font.size = Pt(11)

    doc.add_paragraph(f"{data.get('name','')}")
    doc.add_paragraph(f"{data.get('city','')}, {data.get('state','')}")
    contact = ", ".join([x for x in [data.get('phone',''), data.get('email','')] if x])
    if contact: doc.add_paragraph(contact)
    doc.add_paragraph("")

    today = datetime.date.today().strftime("%B %d, %Y")
    doc.add_paragraph(today)
    if company: doc.add_paragraph(company)
    if data.get("location"): doc.add_paragraph(data["location"])
    doc.add_paragraph("")
    doc.add_paragraph("Dear Hiring Committee,")

    p1 = doc.add_paragraph()
    p1.add_run(
        f"I’m applying for a {role} {('apprenticeship' if app_type=='Apprenticeship' else 'position')} "
        f"in the {trade_label} scope. I bring reliability, safety awareness, and hands-on readiness."
    )
    p2 = doc.add_paragraph()
    p2.add_run(
        "My background includes tool proficiency, teamwork under real schedules, and a commitment to quality and safe production."
    )
    hi = split_list(body_strength)
    if hi:
        doc.add_paragraph("Highlights:")
        for line in hi:
            doc.add_paragraph(f"• {line}")

    doc.add_paragraph("")
    doc.add_paragraph("Thank you for your consideration. I’m ready to support your crew and learn the trade the right way.")
    doc.add_paragraph("")
    doc.add_paragraph("Sincerely,")
    doc.add_paragraph(data.get("name",""))

    bio = io.BytesIO(); doc.save(bio); bio.seek(0)
    return bio.getvalue()

def build_pathway_packet_docx(student: Dict[str,str], trade_label: str, app_type: str, sources: List[Any], reflections: Dict[str,str]) -> bytes:
    doc = DocxWriter()
    styles = doc.styles['Normal']; styles.font.name = 'Calibri'; styles.font.size = Pt(11)

    doc.add_heading("Instructor Pathway Packet", level=0)
    meta = f"Student: {student.get('name','')} | Target: {trade_label} | Application type: {app_type}"
    doc.add_paragraph(meta); doc.add_paragraph("")

    doc.add_heading("Workshop Reflections", level=1)
    for k,v in reflections.items():
        doc.add_paragraph(k+":")
        for line in (v or "").splitlines():
            doc.add_paragraph(line)

    for upl in sources or []:
        doc.add_page_break()
        doc.add_heading(getattr(upl,"name","(file)"), level=1)
        text = extract_text_generic(upl)
        if text.strip():
            for line in text.splitlines():
                doc.add_paragraph(line)
        else:
            doc.add_paragraph("[Text could not be extracted from this file.]")

    out = io.BytesIO(); doc.save(out); out.seek(0)
    return out.getvalue()

# ─────────────────────────────────────────────────────────
# Sidebar — template + job master + extra docs
# ─────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Templates & Docs")

    tpl_bytes=None
    if os.path.exists("resume_app_template.docx"):
        with open("resume_app_template.docx","rb") as f: tpl_bytes=f.read()
    upl_tpl = st.file_uploader("Upload RESUME DOCX template (optional)", type=["docx"])
    if upl_tpl is not None:
        tpl_bytes = upl_tpl.read()

    st.markdown("---")
    st.caption("Upload Job History Master (optional override).")
    job_master_upl = st.file_uploader("Job_History_Master.docx", type=["docx"], accept_multiple_files=False)
    if job_master_upl is not None:
        st.session_state["job_master_bytes"] = job_master_upl.read()

    st.markdown("---")
    st.caption("Upload additional instructor/pathway docs (PDF/DOCX/TXT). These get embedded (full text) in the Instructor Packet.")
    pathway_uploads = st.file_uploader("Upload pathway documents", type=["pdf","docx","txt"], accept_multiple_files=True)

# ─────────────────────────────────────────────────────────
# Main — Intake (uploads/URLs/paste)
# ─────────────────────────────────────────────────────────
st.title("Resume Workshop")

st.subheader("Intake: Bring Your Stuff")
c0a, c0b = st.columns(2)
with c0a:
    prev_resume_files = st.file_uploader(
        "Previous resume (PDF/DOCX/TXT)", type=["pdf","docx","txt"], accept_multiple_files=True
    )
with c0b:
    jd_files = st.file_uploader(
        "Job descriptions / postings (PDF/DOCX/TXT)", type=["pdf","docx","txt"], accept_multiple_files=True
    )

st.markdown("**Or import by URL (public links only: Google Drive/GCS):**")
url_list = st.text_area("One URL per line", "")
url_fetches = []
if url_list.strip():
    for i, raw in enumerate(url_list.splitlines(), start=1):
        u = raw.strip()
        if not u:
            continue
        nb = fetch_url_to_named_bytes(u, fallback_name=f"url_{i}")
        if nb is not None:
            url_fetches.append(nb)
        else:
            st.warning(f"Could not fetch: {u} (is it public?)")

st.markdown("**Or paste text directly:**")
paste_box = st.text_area("Paste any resume or job description text here", "")

def extract_multi(files) -> str:
    txt = ""
    for f in files or []:
        txt += "\n" + extract_text_generic(f)
    return txt

prev_resume_text = extract_multi(prev_resume_files)
jd_text_files = extract_multi(jd_files) + extract_multi(url_fetches)
jd_text_paste = paste_box or ""
combined_text = "\n".join([prev_resume_text, jd_text_files, jd_text_paste]).strip()

if combined_text:
    st.caption(f"Loaded text from {len(prev_resume_files or [])} resume file(s), "
               f"{len(jd_files or []) + len(url_fetches)} JD file(s)/URL(s), "
               f"and {'pasted text' if jd_text_paste else 'no pasted text'}.")
    preview = combined_text[:1000].replace("\n"," ")
    st.info(f"Preview: {preview}…")

# ─────────────────────────────────────────────────────────
# Job Master & Role Detection
# ─────────────────────────────────────────────────────────
ROLE_BULLETS = read_job_master()
ALL_ROLES = list(ROLE_BULLETS.keys())

detected_roles = detect_roles_from_text(combined_text, ALL_ROLES) if combined_text else []

# ─────────────────────────────────────────────────────────
# Autofill — header + certs + schools
# ─────────────────────────────────────────────────────────
def set_if_empty(key: str, val: str):
    if key not in st.session_state or not str(st.session_state.get(key,"")).strip():
        st.session_state[key] = val

if st.button("Auto-Fill Header/Certs/Education from Text", type="secondary", disabled=(not combined_text)):
    hdr = parse_header(combined_text)
    for k,v in {"Name":"Name","Phone":"Phone","Email":"Email","City":"City","State":"State"}.items():
        set_if_empty(v, hdr.get(k,""))

    certs = parse_certs(combined_text)
    if certs: set_if_empty("Certifications", ", ".join(sorted(certs)))

    schools = parse_education(combined_text)
    if schools:
        if len(schools) >= 1:
            set_if_empty("Edu1_School", schools[0].get("school",""))
            set_if_empty("Edu1_CityState", schools[0].get("details",""))
            set_if_empty("Edu1_Dates", schools[0].get("year",""))
            set_if_empty("Edu1_Credential", schools[0].get("credential",""))
        if len(schools) >= 2:
            set_if_empty("Edu2_School", schools[1].get("school",""))
            set_if_empty("Edu2_CityState", schools[1].get("details",""))
            set_if_empty("Edu2_Dates", schools[1].get("year",""))
            set_if_empty("Edu2_Credential", schools[1].get("credential",""))
    st.success("Autofill complete (Header / Certs / Education).")

# ─────────────────────────────────────────────────────────
# Build the Resume — UI
# ─────────────────────────────────────────────────────────
st.subheader("Header")
c1, c2 = st.columns(2)
with c1:
    Name = st.text_input("Name", key="Name")
    Phone = st.text_input("Phone", key="Phone")
    Email = st.text_input("Email", key="Email")
with c2:
    City = st.text_input("City", key="City")
    State = st.text_input("State (2-letter)", key="State")

st.subheader("Objective")
c3a, c3b = st.columns(2)
with c3a:
    application_type = st.radio("Target:", ["Apprenticeship","Job"], horizontal=True, index=0)
    trade = st.selectbox("Trade target", TRADE_TAXONOMY, index=TRADE_TAXONOMY.index("Electrician – Inside (01)"), key="SelectedTrade")
with c3b:
    wk_pitch = st.text_input("10-second pitch (optional):", st.session_state.get("Pitch",""))
    st.session_state["Pitch"] = wk_pitch

# Recommendations (student must type final)
suggest_text = []
if application_type == "Apprenticeship":
    suggest_text.append(f"Seeking entry into a registered apprenticeship in {trade}; bring safety habits, reliability, and hands-on readiness.")
else:
    suggest_text.append(f"Seeking full-time work in {trade}; ready for tool handling, safe production pace, and team support.")

suggest_text.append("Evidence over adjectives: include measurements, prints followed, tools used, and who verified (lead/foreman).")
st.info("Suggested objective starters:\n- " + "\n- ".join(suggest_text))
wk_objective_final = st.text_area("Type your objective (1–2 sentences):", st.session_state.get("Objective_Final",""))
st.session_state["Objective_Final"] = wk_objective_final

# ─────────────────────────────────────────────────────────
# Skills (auto suggestions + editable)
# ─────────────────────────────────────────────────────────
st.subheader("Skills")
suggested_from_text = suggest_transferable_skills_from_text(combined_text)
st.caption("Click suggestions to add; edit freely.")

# Suggestions panel
with st.expander("Suggested skills from uploads and selected role bullets"):
    st.write("From uploads:", ", ".join(suggested_from_text) if suggested_from_text else "(none yet)")
    # We'll fill role-bullet-driven suggestions live below

# Editable fields
Skills_Transferable = st.text_area("Transferable (comma/newline):", st.session_state.get("Skills_Transferable",""))
Skills_JobSpecific  = st.text_area("Job-Specific (comma/newline):", st.session_state.get("Skills_JobSpecific",""))
Skills_SelfManagement = st.text_area("Self-Management (comma/newline):", st.session_state.get("Skills_SelfManagement",""))

# Quick add from canon
quick_transfer = st.multiselect("Quick Add: Transferable skills", SKILL_CANON, default=suggested_from_text)
if quick_transfer:
    merged = (Skills_Transferable + (", " if Skills_Transferable.strip() else "") + ", ".join(quick_transfer))
    st.session_state["Skills_Transferable"] = merged
    Skills_Transferable = merged

# ─────────────────────────────────────────────────────────
# Work Experience — Role picker + bullets → insert into Job 1/2/3
# ─────────────────────────────────────────────────────────
st.subheader("Work Experience — Role Library")
colr1, colr2 = st.columns([1,2])

with colr1:
    st.write("Detected roles (from uploads):")
    if detected_roles:
        st.write("• " + "\n• ".join(detected_roles))
    else:
        st.write("(none detected yet)")

    chosen_roles = st.multiselect("Select roles to pull duty bullets from (you can add more):",
                                  options=ALL_ROLES,
                                  default=detected_roles[:5])

with colr2:
    target_job = st.radio("Insert bullets into:", ["Job 1","Job 2","Job 3"], horizontal=True, index=0)
    target_key = {"Job 1":"Job1_Duties","Job 2":"Job2_Duties","Job 3":"Job3_Duties"}[target_job]

    # Ensure duty fields exist
    for k in ["Job1_Duties","Job2_Duties","Job3_Duties"]:
        st.session_state.setdefault(k, "")

    role_selected = st.selectbox("Pick a role to view bullets", ["(choose)"] + chosen_roles)
    if role_selected != "(choose)":
        bullets = ROLE_BULLETS.get(role_selected, [])
        st.write("Click a bullet to insert:")
        cols = st.columns(2)
        for i, b in enumerate(bullets):
            if cols[i % 2].button("• " + b, key=f"ins_{role_selected}_{i}"):
                current = st.session_state.get(target_key, "")
                lines = [ln for ln in current.splitlines() if ln.strip()]
                if b not in lines:
                    lines.append(b)
                st.session_state[target_key] = "\n".join(lines[:MAX_BULLETS_PER_JOB])

        # Skills from chosen bullets
        suggested_from_bullets = skills_from_bullets(bullets)
        if suggested_from_bullets:
            st.caption("Skills inferred from this role’s bullets: " + ", ".join(sorted(set(suggested_from_bullets))))
            # Pre-merge to Job-Specific by default; student can move/edit
            merged_js = (st.session_state.get("Skills_JobSpecific","") + (", " if st.session_state.get("Skills_JobSpecific","").strip() else "") + ", ".join(suggested_from_bullets)).strip(", ")
            st.session_state["Skills_JobSpecific"] = merged_js

# Jobs 1–3 fields
st.subheader("Work Experience — Jobs")
def job_block(n: int):
    c1,c2 = st.columns(2)
    with c1:
        st.text_input(f"Job {n} – Company:", key=f"Job{n}_Company")
        st.text_input(f"Job {n} – Dates (e.g., 2023-06 – Present):", key=f"Job{n}_Dates")
    with c2:
        st.text_input(f"Job {n} – City/State:", key=f"Job{n}_CityState")
        st.text_input(f"Job {n} – Title:", key=f"Job{n}_Title")
    st.text_area(f"Job {n} – Duties/Accomplishments (1–4 bullets):", key=f"Job{n}_Duties", height=110)

job_block(1)
job_block(2)
job_block(3)

# ─────────────────────────────────────────────────────────
# Certifications / Education
# ─────────────────────────────────────────────────────────
st.subheader("Certifications")
Certifications = st.text_area(
    "List certifications (comma/newline). If none, write 'None yet' or what you plan to get.",
    st.session_state.get("Certifications","OSHA-10, Flagger (WA), Forklift operator (employer evaluation on hire)")
)

st.subheader("Education")
st.write("Reverse order. Include city/state, dates, and credential/diploma.")
E1s = st.text_input("School/Program 1:", key="Edu1_School"); E1cs = st.text_input("City/State 1:", key="Edu1_CityState")
E1d = st.text_input("Dates 1:", key="Edu1_Dates"); E1c = st.text_input("Certificate/Diploma 1:", key="Edu1_Credential")
E2s = st.text_input("School/Program 2:", key="Edu2_School"); E2cs = st.text_input("City/State 2:", key="Edu2_CityState")
E2d = st.text_input("Dates 2:", key="Edu2_Dates"); E2c = st.text_input("Certificate/Diploma 2:", key="Edu2_Credential")

st.markdown("**Final Checklist**")
st.markdown("""
- [ ] One page only  
- [ ] Professional font (10–12 pt)  
- [ ] Saved as PDF  
- [ ] Reviewed by peer  
- [ ] Reviewed by instructor  
""")

# ─────────────────────────────────────────────────────────
# Cover Letter (optional)
# ─────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Cover Letter (optional)")
CL_Company = st.text_input("Company/Employer:","")
CL_Role    = st.text_input("Role Title:", f"{st.session_state.get('SelectedTrade','Apprenticeship')} apprentice")
CL_Location= st.text_input("Company Location (City, State):","")
CL_Highlights = st.text_area("Optional: bullet highlights (comma/newline/• allowed):","Reliable • Safety-focused • Coachable")

# ─────────────────────────────────────────────────────────
# Generate Docs
# ─────────────────────────────────────────────────────────
if st.button("Generate Resume + Cover Letter + Instructor Packet", type="primary"):
    problems=[]
    if not st.session_state.get("Name","").strip():
        problems.append("Name is required.")
    if not (st.session_state.get("Phone","").strip() or st.session_state.get("Email","").strip()):
        problems.append("At least one contact method (Phone or Email) is required.")
    if problems:
        st.error(" | ".join(problems))
        st.stop()

    # Build form dict
    trade = st.session_state.get("SelectedTrade","Electrician – Inside (01)")
    # Merge Quick Add into Transferable
    skills_transfer_final = st.session_state.get("Skills_Transferable","")
    if quick_transfer:
        skills_transfer_final = (skills_transfer_final + (", " if skills_transfer_final.strip() else "") + ", ".join(quick_transfer))

    form = {
        "Name": st.session_state.get("Name",""), "City": st.session_state.get("City",""), "State": st.session_state.get("State",""),
        "Phone": st.session_state.get("Phone",""), "Email": st.session_state.get("Email",""),
        "Objective_Final": st.session_state.get("Objective_Final",""),
        "Skills_Transferable": skills_transfer_final,
        "Skills_JobSpecific": st.session_state.get("Skills_JobSpecific",""),
        "Skills_SelfManagement": st.session_state.get("Skills_SelfManagement",""),
        "Certifications": st.session_state.get("Certifications", Certifications),
    }
    # Jobs
    for i in (1,2,3):
        form[f"Job{i}_Company"]=st.session_state.get(f"Job{i}_Company","")
        form[f"Job{i}_CityState"]=st.session_state.get(f"Job{i}_CityState","")
        form[f"Job{i}_Dates"]=st.session_state.get(f"Job{i}_Dates","")
        form[f"Job{i}_Title"]=st.session_state.get(f"Job{i}_Title","")
        form[f"Job{i}_Duties"]=st.session_state.get(f"Job{i}_Duties","")
    # Education
    for i in (1,2):
        form[f"Edu{i}_School"]=st.session_state.get(f"Edu{i}_School","")
        form[f"Edu{i}_CityState"]=st.session_state.get(f"Edu{i}_CityState","")
        form[f"Edu{i}_Dates"]=st.session_state.get(f"Edu{i}_Dates","")
        form[f"Edu{i}_Credential"]=st.session_state.get(f"Edu{i}_Credential","")

    # Resume
    if not tpl_bytes:
        st.error("Template not found. Put resume_app_template.docx in the repo or upload it in the sidebar.")
        st.stop()
    try:
        resume_ctx = build_resume_context(form, trade)
        resume_bytes = render_docx_with_template(tpl_bytes, resume_ctx)
    except Exception as e:
        st.error(f"Resume template rendering failed: {e}")
        st.stop()

    # Cover Letter
    cover_bytes = build_cover_letter_docx({
        "name": form["Name"], "city": form["City"], "state": form["State"], "phone": clean_phone(form["Phone"]), "email": clean_email(form["Email"]),
        "company": CL_Company, "role": CL_Role, "location": CL_Location,
        "trade_label": trade, "strength": CL_Highlights,
        "application_type": application_type,
    })

    # Instructor Packet (Workshop reflections + full text of docs)
    reflections = {
        "Objective (student typed)": st.session_state.get("Objective_Final",""),
        "Pitch (optional)": st.session_state.get("Pitch",""),
    }
    merged_docs_for_packet = list(pathway_uploads or []) \
                           + list(prev_resume_files or []) \
                           + list(jd_files or []) \
                           + url_fetches
    packet_bytes = build_pathway_packet_docx({"name": form["Name"]}, trade, application_type, merged_docs_for_packet, reflections)

    safe_name = (form["Name"] or "Student").replace(" ","_")
    st.download_button("Download Resume (DOCX)", data=resume_bytes,
                       file_name=f"{safe_name}_Resume.docx",
                       mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                       use_container_width=True)
    st.download_button("Download Cover Letter (DOCX)", data=cover_bytes,
                       file_name=f"{safe_name}_Cover_Letter.docx",
                       mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                       use_container_width=True)
    st.download_button("Download Instructor Pathway Packet (DOCX)", data=packet_bytes,
                       file_name=f"{safe_name}_Instructor_Pathway_Packet.docx",
                       mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                       use_container_width=True)

    # Intake CSV — fixed column order
    csv_fields = [
        "Name","City","State","Phone","Email",
        "Objective_Final",
        "Skills_Transferable","Skills_JobSpecific","Skills_SelfManagement",
        "Certifications",
        "Job1_Company","Job1_CityState","Job1_Dates","Job1_Title","Job1_Duties",
        "Job2_Company","Job2_CityState","Job2_Dates","Job2_Title","Job2_Duties",
        "Job3_Company","Job3_CityState","Job3_Dates","Job3_Title","Job3_Duties",
        "Edu1_School","Edu1_CityState","Edu1_Dates","Edu1_Credential",
        "Edu2_School","Edu2_CityState","Edu2_Dates","Edu2_Credential"
    ]
    buf=io.StringIO(); w=csv.writer(buf)
    w.writerow(csv_fields); w.writerow([form.get(k,"") for k in csv_fields])
    st.download_button("Download Intake CSV", data=buf.getvalue().encode("utf-8"),
                       file_name=f"{safe_name}_Workshop_Intake.csv", mime="text/csv",
                       use_container_width=True)
    st.success("Generated.")
