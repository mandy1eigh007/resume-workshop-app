# app.py — Seattle Tri-County Construction Resume & Pathway Packet
# Python 3.11 • Streamlit single-file app • No external APIs at runtime
# Libraries: streamlit, pandas, docxtpl, python-docx, pypdf, pdfminer.six, requests
# ------------------------------------------------------------------------------
from __future__ import annotations

import io
import os
import re
import json
import time
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Tuple, Optional

import streamlit as st
import pandas as pd

from docxtpl import DocxTemplate
from docx import Document as DocxReader
from docx import Document as DocxWriter
from docx.shared import Pt
from pypdf import PdfReader
import requests

# Optional, better PDF text extraction (text PDFs)
try:
    from pdfminer.high_level import extract_text as pdfminer_extract_text
except Exception:
    pdfminer_extract_text = None

# ------------------------------------------------------------------------------
# Page config
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Seattle Construction — Resume & Pathways",
    layout="wide",
)

# ------------------------------------------------------------------------------
# Constants / Config
# ------------------------------------------------------------------------------
APP_TITLE = "Seattle Tri-County — Construction Resume & Pathway Packet"

MASTER_JOB_DOC = "Job_History_Master.docx"
MASTER_PLAYBOOK_DOC = "Stand_Out_Playbook_Master.docx"
MASTER_SKILLS_DOC = "Transferable_Skills_to_Construction.docx"
RESUME_TEMPLATE_DOC = "resume_app_template.docx"

MAX_SUMMARY_CHARS = 450
MAX_SKILLS = 12
MAX_CERTS = 8
MAX_JOBS = 3
MAX_BULLETS_PER_JOB = 4
MAX_SCHOOLS = 2
ALT_BULLETS_PER_ROLE = 6

TRADE_TAXONOMY = [
    "Boilermaker",
    "Bricklayer / BAC Allied (Brick/Tile/Terrazzo/Marble/PCC)",
    "Carpenter (General)",
    "Carpenter – Interior Systems",
    "Millwright",
    "Pile Driver",
    "Cement Mason",
    "Drywall Finisher",
    "Electrician – Inside (01)",
    "Electrician – Limited Energy (06)",
    "Electrician – Residential (02)",
    "Elevator Constructor",
    "Floor Layer",
    "Glazier",
    "Heat & Frost Insulator",
    "Ironworker",
    "Laborer",
    "Operating Engineer",
    "Painter",
    "Plasterer",
    "Plumber / Steamfitter / HVAC-R",
    "Roofer",
    "Sheet Metal",
    "Sprinkler Fitter",
    "High Voltage – Outside Lineman",
    "Power Line Clearance Tree Trimmer",
]

# Regex (compiled once)
UNION_BANS = [
    r"\bunion\b", r"\bnon[-\s]?union\b", r"\bibew\b", r"\blocal\s*\d+\b",
    r"\binside\s*wire(man|men)?\b", r"\blow[-\s]?voltage\b", r"\bsound\s+and\s+communication(s)?\b",
    r"\bneca\b", r"\bopen[-\s]?shop\b"
]
BANNED_RE = re.compile("|".join(UNION_BANS), re.I)
FILLER_LEADS = re.compile(r"^\s*(responsible for|duties included|tasked with|in charge of)\s*:?\s*", re.I)
MULTISPACE = re.compile(r"\s+")
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(\+?1[\s\-\.]?)?\(?\d{3}\)?[\s\-\.]?\d{3}[\s\-\.]?\d{4}")
PHONE_DIGITS = re.compile(r"\D+")
CITY_STATE_RE = re.compile(r"\b([A-Za-z .'-]{2,}),\s*([A-Za-z]{2})\b")
SECTION_HEADERS = re.compile(
    r"^(objective|summary|professional summary|skills|core competencies|experience|work history|"
    r"employment|education|certifications|certificates|references|contact|profile|qualifications|"
    r"career|background|achievements|accomplishments|projects|volunteer|activities|interests|"
    r"technical skills|languages|awards|honors|publications|training|licenses|memberships)$",
    re.I
)

# ------------------------------------------------------------------------------
# Utility + cleaners
# ------------------------------------------------------------------------------
def strip_banned(text: str) -> str:
    return BANNED_RE.sub("", text or "").strip()

def norm_ws(s: str) -> str:
    if not s: return ""
    return MULTISPACE.sub(" ", s.strip())

def cap_first(s: str) -> str:
    s = norm_ws(s)
    return s[:1].upper() + s[1:] if s else s

def clean_phone(s: str) -> str:
    digits = PHONE_DIGITS.sub("", s or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return norm_ws(s or "")

def clean_email(s: str) -> str:
    return (s or "").strip().lower()

def clean_bullet(s: str) -> str:
    s = norm_ws(s)
    s = re.sub(r"^[•\-\u2022]+\s*", "", s)
    s = FILLER_LEADS.sub("", s)
    s = re.sub(r"\.+$", "", s)
    s = cap_first(s)
    words = s.split()
    return " ".join(words[:24]) if len(words) > 24 else s

def split_list(raw: str) -> List[str]:
    if not raw: return []
    parts = [p.strip(" •\t") for p in re.split(r"[,\n;•]+", raw)]
    return [p for p in parts if p]

# ------------------------------------------------------------------------------
# File text extraction (PDF/DOCX/TXT/URL)
# ------------------------------------------------------------------------------
def extract_text_from_pdf(file) -> str:
    # Try pdfminer first (text PDFs)
    try:
        if pdfminer_extract_text is not None:
            if hasattr(file, "getvalue"):
                bio = io.BytesIO(file.getvalue())
            else:
                try: file.seek(0)
                except Exception: pass
                bio = io.BytesIO(file.read())
            bio.seek(0)
            txt = pdfminer_extract_text(bio) or ""
            if txt.strip():
                return txt
    except Exception:
        pass

    # Fallback: pypdf
    try:
        try: file.seek(0)
        except Exception: pass
        reader = PdfReader(file)
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception:
        return ""

def extract_text_from_docx(file) -> str:
    try:
        doc = DocxReader(file)
        parts = []
        for p in doc.paragraphs:
            if p.text.strip():
                parts.append(p.text)
        for tbl in doc.tables:
            for row in tbl.rows:
                cells = [c.text.strip() for c in row.cells if c.text.strip()]
                if cells:
                    parts.append(" | ".join(cells))
        return "\n".join(parts)
    except Exception:
        return ""

def extract_text_generic(upload) -> str:
    name = getattr(upload, "name", "").lower()
    if name.endswith(".pdf"):
        return extract_text_from_pdf(upload)
    if name.endswith(".docx"):
        return extract_text_from_docx(upload)
    # txt or other
    try:
        return upload.getvalue().decode("utf-8", errors="ignore")
    except Exception:
        return ""

def _drive_direct(url: str) -> str:
    m = re.search(r"/d/([a-zA-Z0-9_-]+)", url) or re.search(r"[?&]id=([a-zA-Z0-9_-]+)", url)
    if m:
        file_id = m.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url

def fetch_url_to_bytes(url: str) -> Optional[io.BytesIO]:
    try:
        u = _drive_direct(url.strip())
        r = requests.get(u, timeout=30)
        r.raise_for_status()
        return io.BytesIO(r.content)
    except Exception:
        return None

# ------------------------------------------------------------------------------
# Skill canon + inference
# ------------------------------------------------------------------------------
SKILL_CANON = [
    "Problem-solving","Critical thinking","Attention to detail","Time management",
    "Teamwork & collaboration","Adaptability & willingness to learn","Safety awareness",
    "Conflict resolution","Customer service","Leadership","Reading blueprints & specs",
    "Hand & power tools","Materials handling (wood/concrete/metal)","Operating machinery",
    "Trades math & measurement","Regulatory compliance","Physical stamina & dexterity",
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
    "problem": "Problem-solving","solve": "Problem-solving","troubleshoot": "Problem-solving",
    "analyz": "Critical thinking","priorit": "Time management","deadline": "Time management",
    "detail": "Attention to detail","team": "Teamwork & collaboration","collabor": "Teamwork & collaboration",
    "adapt": "Adaptability & willingness to learn","learn": "Adaptability & willingness to learn",
    "safety": "Safety awareness","osha": "Safety awareness","customer": "Customer service",
    "lead": "Leadership","blueprint": "Reading blueprints & specs","spec": "Reading blueprints & specs",
    "tool": "Hand & power tools","drill": "Hand & power tools","saw": "Hand & power tools",
    "forklift": "Operating machinery","material": "Materials handling (wood/concrete/metal)",
    "machin": "Operating machinery","math": "Trades math & measurement","measure": "Trades math & measurement",
    "code": "Regulatory compliance","permit": "Regulatory compliance","compliance": "Regulatory compliance",
    "stamina": "Physical stamina & dexterity","lift": "Physical stamina & dexterity",
}

BULLET_SKILL_HINTS = [
    (re.compile(r"\b(clean|organize|stage|restock|housekeep|walkway|sweep|debris)\b", re.I), "Attention to detail"),
    (re.compile(r"\b(pallet|forklift|lift|jack|rig|hoist|carry|load|unload|stack)\b", re.I), "Materials handling (wood/concrete/metal)"),
    (re.compile(r"\b(conduit|measure|layout|prints?|drawings?)\b", re.I), "Reading blueprints & specs"),
    (re.compile(r"\b(grinder|drill|saw|snips|hand tools|power tools|torch)\b", re.I), "Hand & power tools"),
    (re.compile(r"\b(ppe|osha|lockout|tagout|loto|hazard|spill|permit)\b", re.I), "Regulatory compliance"),
    (re.compile(r"\b(count|verify|inspect|qc|torque|measure)\b", re.I), "Critical thinking"),
    (re.compile(r"\b(rush|deadline|targets?|production|pace)\b", re.I), "Time management"),
    (re.compile(r"\b(team|crew|assist|support|communicat)\b", re.I), "Teamwork & collaboration"),
    (re.compile(r"\b(climb|lift|carry|physical|stamina)\b", re.I), "Physical stamina & dexterity"),
]

def normalize_skill_label(s: str) -> str:
    if not s: return ""
    base = (s or "").strip()
    key = re.sub(r"\s+"," ",base.lower())
    mapped = _SKILL_SYNONYMS.get(key)
    if mapped: return mapped
    return re.sub(r"\s+"," ",base).strip().title()

def suggest_transferable_skills_from_text(text: str) -> List[str]:
    if not text: return []
    hits: Dict[str,int] = {}
    low = text.lower()
    for kw, skill in TRANSFERABLE_KEYWORDS.items():
        if kw in low:
            hits[skill] = hits.get(skill, 0) + 1
    ordered = [k for k,_ in sorted(hits.items(), key=lambda kv: -kv[1])]
    canon_order = [s for s in SKILL_CANON if s in ordered]
    return canon_order[:8]

def skills_from_bullets(bullets: List[str]) -> List[str]:
    hits=set()
    for b in bullets:
        for rx, skill in BULLET_SKILL_HINTS:
            if rx.search(b):
                hits.add(skill)
    return list(hits)

def categorize_skills(skills: List[str]) -> Dict[str, List[str]]:
    out = {"Transferable": [], "Job-Specific": [], "Self-Management": []}
    seen=set()
    job_specific = {
        "Reading blueprints & specs","Hand & power tools","Operating machinery",
        "Materials handling (wood/concrete/metal)","Trades math & measurement",
        "Regulatory compliance","Safety awareness",
    }
    self_mgmt = {"Leadership","Adaptability & willingness to learn","Physical stamina & dexterity"}
    for s in skills:
        lab = normalize_skill_label(s)
        if not lab: continue
        if lab.lower() in seen: continue
        seen.add(lab.lower())
        if lab in job_specific:
            out["Job-Specific"].append(lab)
        elif lab in self_mgmt:
            out["Self-Management"].append(lab)
        else:
            out["Transferable"].append(lab)
    return out

# ------------------------------------------------------------------------------
# Role aliases & detection
# ------------------------------------------------------------------------------
ROLE_ALIASES = {
    "Line Cook": ["line cook","cook","kitchen"],
    "Prep Cook": ["prep cook","prep"],
    "Server": ["server","waiter","waitress","front of house","foh"],
    "Dishwasher": ["dishwasher","dishes"],
    "Barista": ["barista","coffee"],
    "Cashier": ["cashier","till","pos"],
    "Retail Associate": ["retail associate","retail","sales associate"],
    "Stocker": ["stocker","stocking","stock clerk"],
    "Warehouse Associate": ["warehouse associate","warehouse","whse"],
    "Order Selector": ["order selector","selector","order picker","picker"],
    "Shipping & Receiving": ["shipping","receiving","ship","receive"],
    "Material Handler": ["material handler","materials","handler"],
    "Forklift Operator (trainee/experience)": ["forklift","lift truck","fork truck"],
    "Delivery Driver (Non-CDL)": ["delivery driver","driver","courier"],
    "Mover": ["mover","moving"],
    "Janitor": ["janitor","custodian"],
    "Custodian": ["custodian","janitor"],
    "Housekeeper": ["housekeeper","housekeeping","room attendant"],
    "Security Guard": ["security","guard"],
    "Landscaper/Groundskeeper": ["landscaper","grounds","groundskeeper","mowing"],
    "Construction Laborer (general)": ["construction laborer","laborer","construction"],
    "Demolition Laborer": ["demolition","demo"],
    "Traffic Control/Flagger": ["flagger","traffic control"],
    "Tool Room Attendant": ["tool room","tool attendant","toolroom"],
    "Parts Counter": ["parts counter","parts"],
    "Facilities Porter": ["porter","facilities porter"],
    "Event Setup Crew/Stagehand": ["stagehand","event setup","av crew"],
    "Maintenance Helper": ["maintenance helper","maintenance"],
    "Painter Helper": ["painter helper","paint prep","painter"],
    "Drywall/Lather Helper": ["drywall","lather","sheetrock"],
    "Flooring Helper": ["flooring helper","flooring"],
    "Concrete Laborer": ["concrete laborer","concrete"],
    "Mason Tender": ["mason tender","masonry helper","masonry"],
    "Carpenter Helper": ["carpenter helper","carpenter","framing"],
    "Roofer Helper": ["roofer","roofing"],
    "HVAC Helper": ["hvac helper","hvac"],
    "Electrical Helper": ["electrical helper","electrician helper","electrical"],
    "Plumbing Helper": ["plumbing helper","plumbing","plumber helper"],
    "Sheet Metal Helper": ["sheet metal helper","sheet metal"],
    "Ironworker Helper": ["ironworker helper","ironworker"],
    "Glazier Helper": ["glazier","glazier helper","glass"],
    "Welder/Fabrication Helper": ["welder","fabrication","fab"],
    "Grounds/Right-of-Way Helper": ["right of way","row","grounds"],
    "Warehouse Clerk": ["warehouse clerk","inventory clerk"],
    "Assembler (Light Manufacturing)": ["assembler","assembly","light manufacturing"],
    "Kitchen Helper": ["kitchen helper","kitchen"],
    "Busser": ["busser","bussing"],
    "Host": ["host","hostess"],
    "Recycling Sorter": ["recycling sorter","recycling"],
    "Delivery Helper": ["delivery helper","helper"],
    "General Laborer": ["general laborer","general labor","labor"],
}

_ROLE_PATTERNS = {}
for role, terms in ROLE_ALIASES.items():
    _ROLE_PATTERNS[role] = [re.compile(rf"\b{re.escape(t)}\b", re.I) for t in terms]

def detect_roles_from_text(text: str, all_roles: List[str]) -> List[str]:
    if not text: return []
    low = text.lower()
    found=set()
    for r in all_roles:
        patterns = _ROLE_PATTERNS.get(r, [re.compile(rf"\b{re.escape(r.lower())}\b", re.I)])
        if any(p.search(low) for p in patterns):
            found.add(r)
    return [r for r in all_roles if r in found][:12]

# ------------------------------------------------------------------------------
# Header / Education parsing
# ------------------------------------------------------------------------------
def _likely_name(lines: List[str]) -> str:
    best = ""
    best_score = -1.0
    skip_words = {"address","phone","email","street","avenue","road","city","state","zip","resume","curriculum","vitae"}
    for i, l in enumerate(lines[:20]):
        s = l.strip()
        if not s: continue
        if EMAIL_RE.search(s) or PHONE_RE.search(s): continue
        if SECTION_HEADERS.match(s): continue
        if re.search(r"(objective|summary|skills|experience|education|cert|resume|cv|curriculum)", s, re.I): continue
        words = [w for w in re.split(r"\s+", s) if w]
        if not (2 <= len(words) <= 4): continue
        if any(re.search(r"\d", w) for w in words): continue
        if any(w.lower() in skip_words for w in words): continue
        caps = sum(1 for w in words if w[:1].isalpha() and w[:1].isupper())
        score = caps / max(1,len(words)) + (20 - i) * 0.01
        if score > best_score:
            best_score = score
            best = s
    return best

def parse_header(text: str) -> Dict[str,str]:
    name = ""
    email = ""
    phone = ""
    city = ""
    state = ""
    m = EMAIL_RE.search(text or "")
    email = m.group(0) if m else ""
    m = PHONE_RE.search(text or "")
    phone = m.group(0) if m else ""
    lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
    m2 = CITY_STATE_RE.search("\n".join(lines[:30]))
    if m2:
        city, state = m2.group(1), m2.group(2).upper()
    name = _likely_name(lines)
    return {
        "Name": cap_first(name),
        "Email": clean_email(email),
        "Phone": clean_phone(phone),
        "City": cap_first(city),
        "State": (state or "").strip(),
    }

def parse_education(text: str) -> List[Dict[str,str]]:
    out=[]
    lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
    EDU_KEYWORDS = re.compile(r"(high school|ged|college|university|program|certificate|diploma|academy|institute|school of)", re.I)
    YEAR_PATTERN = re.compile(r"\b(20\d{2}|19\d{2})\b")
    i=0
    while i < len(lines) and len(out) < MAX_SCHOOLS:
        l = lines[i]
        if EDU_KEYWORDS.search(l):
            school = cap_first(l)
            cred=""; year=""; details=""
            for la in lines[i+1:i+7]:
                if not year and YEAR_PATTERN.search(la):
                    year = YEAR_PATTERN.search(la).group(0)
                mcs = CITY_STATE_RE.search(la)
                if mcs and not details:
                    details = f"{cap_first(mcs.group(1))}, {mcs.group(2).upper()}"
                if not cred:
                    if any(x in la.lower() for x in ["diploma","degree","certificate","ged","program","apprentice","associate","bachelor","master"]):
                        cred = cap_first(la.strip())
            out.append({"school":school,"credential":cred,"year":year,"details":details})
        i += 1
    return out[:MAX_SCHOOLS]

# ------------------------------------------------------------------------------
# Cert normalization
# ------------------------------------------------------------------------------
CERT_MAP = {
    "osha 10": "OSHA Outreach 10-Hour (Construction)",
    "osha-10": "OSHA Outreach 10-Hour (Construction)",
    "osha10": "OSHA Outreach 10-Hour (Construction)",
    "osha": "OSHA Outreach 10-Hour (Construction)",
    "osha 30": "OSHA Outreach 30-Hour (Construction)",
    "osha-30": "OSHA Outreach 30-Hour (Construction)",
    "osha30": "OSHA Outreach 30-Hour (Construction)",
    "flagger": "WA Flagger (expires 3 years from issuance)",
    "wa flagger": "WA Flagger (expires 3 years from issuance)",
    "forklift": "Forklift — employer evaluation on hire",
    "fork lift": "Forklift — employer evaluation on hire",
    "cpr": "CPR",
    "first aid": "First Aid",
    "firstaid": "First Aid",
    "aerial lift": "Aerial Lift",
    "confined space": "Confined Space",
    "traffic control": "Traffic Control",
    "epa 608": "EPA Section 608 (Type I/II/III/Universal)",
    "section 608": "EPA Section 608 (Type I/II/III/Universal)",
}

_CERT_PATTERNS = {k: re.compile(rf"\b{re.escape(k)}\b", re.I) for k in CERT_MAP.keys()}

def parse_certs(text: str) -> List[str]:
    if not text: return []
    low = text.lower()
    out=set()
    for k,pattern in _CERT_PATTERNS.items():
        if pattern.search(low):
            out.add(CERT_MAP[k])
    return sorted(out)

# ------------------------------------------------------------------------------
# Job Master + Playbook readers
# ------------------------------------------------------------------------------
@st.cache_data
def cached_read_job_master(path: str) -> Dict[str, List[str]]:
    if not os.path.exists(path): return {}
    doc = DocxReader(path)
    roles: Dict[str,List[str]] = {}
    cur=None
    for p in doc.paragraphs:
        style = (p.style.name or "").lower() if p.style else ""
        text = (p.text or "").strip()
        if not text: continue
        if "heading 1" in style:
            cur = text
            roles.setdefault(cur, [])
            continue
        if cur:
            roles[cur].append(clean_bullet(text))
    # Dedup + clamp
    for k,v in roles.items():
        seen=set(); dedup=[]
        for b in v:
            key=b.lower()
            if key in seen: continue
            seen.add(key); dedup.append(b)
        roles[k]=dedup[:20]
    return roles

@st.cache_data
def cached_extract_playbook_section(path: str, trade_label: str) -> str:
    if not os.path.exists(path): return ""
    doc = DocxReader(path)
    # Collect paragraphs from the requested Heading 1 until next Heading 1
    out_lines=[]
    active=False
    for p in doc.paragraphs:
        style = (p.style.name or "").lower() if p.style else ""
        text = p.text or ""
        if "heading 1" in style:
            if active: break
            if text.strip() == trade_label.strip():
                active = True
                out_lines.append(text.strip())
                continue
        if active:
            out_lines.append(text)
    return "\n".join(out_lines).strip()

# ------------------------------------------------------------------------------
# Resume context classes
# ------------------------------------------------------------------------------
@dataclass
class Job:
    company: str = ""
    role: str = ""
    city: str = ""
    start: str = ""
    end: str = ""
    bullets: List[str] = field(default_factory=list)

    def trim(self, max_bullets: int):
        bs = [clean_bullet(b) for b in (self.bullets or []) if str(b).strip()]
        self.bullets = bs[:max_bullets]

@dataclass
class School:
    school: str = ""
    credential: str = ""
    year: str = ""
    details: str = ""

# ------------------------------------------------------------------------------
# Objective starters
# ------------------------------------------------------------------------------
def objective_starters(trade_label: str, path_choice: str) -> List[str]:
    t = trade_label
    if path_choice == "Apprenticeship":
        return [
            f"Apprenticeship track — {t}: Ready to contribute on day one with safe pace, tool control, and measured work while advancing my trade knowledge.",
            f"Seeking {t} apprenticeship: bring consistent attendance, clean safety habits (PPE/LOTO vocabulary), and steady production under supervision.",
            f"Targeting {t} apprenticeship to grow skills in prints, layout, and materials handling; document work with counts, dimensions, and sign-offs.",
            f"Applying to {t} apprenticeship with verified OSHA-10, flagger, and recent practice logs; eager to learn and execute per spec.",
            f"Motivated to train in {t} with reliability, safety, and proof-driven work (checklists, measurements, torque) supporting the crew.",
        ]
    else:
        return [
            f"{t} — Immediate-hire objective: add value with safe production, tool control, and measured results while learning site standards.",
            f"{t} — Ready to work: bring OSHA-10, reliable attendance, and experience following instructions with documented counts and QC checks.",
            f"{t} — Focus on pace and safety: follow prints and directions, maintain clean work area, and log completed tasks each shift.",
            f"{t} — Contribute on material handling, setup, and verified measurements; support crew with consistent communication.",
            f"{t} — Produce safely with measurable output and supervisor sign-offs; build skills in layout, tools, and equipment.",
        ]

# ------------------------------------------------------------------------------
# UI — Header
# ------------------------------------------------------------------------------
st.title(APP_TITLE)
st.caption("Neutral language • Measurable evidence • Seattle tri-county focus")

# Upload panel
with st.sidebar:
    st.subheader("Uploads")
    uploaded = st.file_uploader(
        "Upload resume(s) or supporting files (PDF/DOCX/TXT). You can add multiple.",
        type=["pdf","docx","txt"], accept_multiple_files=True
    )
    url_input = st.text_input("...or paste a public URL (Google Drive/Direct/etc.)", "")
    fetched_bytes = None
    if url_input.strip():
        fetched_bytes = fetch_url_to_bytes(url_input.strip())
        if fetched_bytes is None:
            st.warning("Could not fetch the URL. Make sure it's publicly accessible.")
    st.markdown("---")
    trade_label = st.selectbox("Target trade", TRADE_TAXONOMY, index=TRADE_TAXONOMY.index("Laborer"))
    path_choice = st.radio("Path", ["Apprenticeship","Job"], index=0)
    st.markdown("---")
    st.subheader("Instructor Packet")
    student_reflections = st.text_area(
        "Student reflections to embed (optional)",
        help="These will appear at the front of the Instructor Pathway Packet."
    )

# Combine text from uploads
texts=[]
if uploaded:
    for up in uploaded:
        texts.append(extract_text_generic(up))
if fetched_bytes:
    # crude type guess: try pdf then docx then txt decode
    content = extract_text_from_pdf(fetched_bytes) or extract_text_from_docx(fetched_bytes)
    if not content:
        try:
            content = fetched_bytes.getvalue().decode("utf-8", errors="ignore")
        except Exception:
            content = ""
    texts.append(content)

raw_text = "\n\n".join([t for t in texts if t])

# Parse header/certs/education/roles/skills
parsed_header = parse_header(raw_text) if raw_text else {"Name":"","Email":"","Phone":"","City":"","State":""}
parsed_certs = parse_certs(raw_text)
parsed_schools = parse_education(raw_text)
transferable_suggestions = suggest_transferable_skills_from_text(raw_text)
job_master = cached_read_job_master(MASTER_JOB_DOC)
available_roles = list(job_master.keys()) if job_master else list(ROLE_ALIASES.keys())
detected_roles = detect_roles_from_text(raw_text, available_roles) if raw_text else []

# ------------------------------------------------------------------------------
# Autofill Debug (expander)
# ------------------------------------------------------------------------------
with st.expander("Autofill Debug (parser snapshot)"):
    st.json({
        "Header": parsed_header,
        "Detected roles": detected_roles,
        "Suggested transferable": transferable_suggestions,
        "Certs (normalized)": parsed_certs,
        "Schools": parsed_schools,
    })

# ------------------------------------------------------------------------------
# Form — Header
# ------------------------------------------------------------------------------
st.subheader("Header")
colA,colB,colC = st.columns([2,1.2,1.2])
with colA:
    name = st.text_input("Name", parsed_header.get("Name",""))
with colB:
    phone = st.text_input("Phone", parsed_header.get("Phone",""))
with colC:
    email = st.text_input("Email", parsed_header.get("Email",""))

colD,colE = st.columns([1.6,0.4])
with colD:
    city = st.text_input("City", parsed_header.get("City",""))
with colE:
    state = st.text_input("State (2-letter)", parsed_header.get("State",""))

# ------------------------------------------------------------------------------
# Objective (starters; not finalized)
# ------------------------------------------------------------------------------
st.subheader("Objective")
st.caption("You’ll edit/choose one. These are just starters — neutral, measurable, no union/non-union phrasing.")
start_apprentice = objective_starters(trade_label, "Apprenticeship")
start_job = objective_starters(trade_label, "Job")
col1,col2 = st.columns(2)
with col1:
    st.markdown("**Apprenticeship starters**")
    for s in start_apprentice:
        st.code(s)
with col2:
    st.markdown("**Job starters**")
    for s in start_job:
        st.code(s)
summary = st.text_area(
    "Type your objective (1–2 sentences).",
    max_chars=MAX_SUMMARY_CHARS,
    placeholder="State the goal (apprenticeship or job), the trade, and what you bring (safety, pace, reliability)."
)

# ------------------------------------------------------------------------------
# Skills
# ------------------------------------------------------------------------------
st.subheader("Skills")
st.caption("Click suggestions to add — edit freely. Keep total ≤ 12.")
colT, colJ, colS = st.columns(3)
with colT:
    transfer_in = st.text_area("Transferable (comma/newline)", value=", ".join(transferable_suggestions))
with colJ:
    job_specific_in = st.text_area("Job-Specific (comma/newline)", value="")
with colS:
    self_mgmt_in = st.text_area("Self-Management (comma/newline)", value="")

def gather_skills() -> List[str]:
    ts = split_list(transfer_in)
    js = split_list(job_specific_in)
    sm = split_list(self_mgmt_in)
    all_s = [normalize_skill_label(s) for s in (ts+js+sm)]
    out=[]; seen=set()
    for s in all_s:
        if not s: continue
        if s.lower() in seen: continue
        seen.add(s.lower()); out.append(s)
    return out[:MAX_SKILLS]

# ------------------------------------------------------------------------------
# Detected / Available roles → click to insert bullets
# ------------------------------------------------------------------------------
st.subheader("Work Experience — Role-linked duty bullets")
role_panel = st.container()
with role_panel:
    rcol1, rcol2 = st.columns(2)
    with rcol1:
        st.markdown("**Detected roles:**")
        if detected_roles:
            st.write(", ".join(detected_roles))
        else:
            st.write("—")
    with rcol2:
        st.markdown("**Available roles (from Job_History_Master):**")
        st.write(", ".join(available_roles[:20]) + ("..." if len(available_roles) > 20 else ""))

# Three job slots
job_slots: List[Job] = [Job(), Job(), Job()]

def role_insert_ui(slot_index: int):
    st.caption("Pick a role to load bullets (click to add to this job).")
    role_choice = st.selectbox(f"Role for Job {slot_index+1}", options=["—"] + available_roles, key=f"role_{slot_index}")
    if role_choice != "—" and job_master.get(role_choice):
        st.markdown(f"*Bullets for **{role_choice}*** — click to insert:")
        bullets = job_master[role_choice]
        # Show main list + alternates panel
        for i, b in enumerate(bullets[:10]):
            if st.button(f"➕ {b}", key=f"add_b_{slot_index}_{i}"):
                job_slots[slot_index].bullets.append(clean_bullet(b))
                # Skills inference on insert
                inferred = skills_from_bullets([b])
                if inferred:
                    merged = gather_skills() + inferred
                    # Put back into text areas (respect categories best-effort)
                    cats = categorize_skills(merged)
                    # rewrite text areas
                    st.session_state[f"skills_transfer_{slot_index}"] = ", ".join(cats["Transferable"])
                    st.session_state[f"skills_job_{slot_index}"] = ", ".join(cats["Job-Specific"])
                    st.session_state[f"skills_self_{slot_index}"] = ", ".join(cats["Self-Management"])

# Work experience inputs
st.caption("Enter Job info (Company/Title/City/Dates) and click bullets above to insert; edit freely. 3–4 bullets per job.")
for idx in range(3):
    st.markdown(f"**Job {idx+1}**")
    c1,c2,c3,c4 = st.columns([1.6,1.2,1.2,1.2])
    job_slots[idx].company = c1.text_input("Company", key=f"j_company_{idx}")
    job_slots[idx].role = c2.text_input("Title", key=f"j_role_{idx}")
    job_slots[idx].city = c3.text_input("City, ST", key=f"j_city_{idx}")
    col_dates = c4
    d1,d2 = col_dates.columns(2)
    job_slots[idx].start = d1.text_input("Start", key=f"j_start_{idx}")
    job_slots[idx].end = d2.text_input("End", key=f"j_end_{idx}")
    # Role → insert bullets
    role_insert_ui(idx)
    job_slots[idx].bullets = split_list(st.text_area("Bullets (one per line)", value="\n".join(job_slots[idx].bullets), key=f"j_bullets_{idx}"))
    job_slots[idx].trim(MAX_BULLETS_PER_JOB)
    st.markdown("---")

# ------------------------------------------------------------------------------
# Certifications
# ------------------------------------------------------------------------------
st.subheader("Certifications")
st.caption("Exact labels will be normalized. Forklift = employer evaluation on hire (pre-hire classes are prep only).")
cert_suggestions = sorted(set(parsed_certs) | {"OSHA Outreach 10-Hour (Construction)","WA Flagger (expires 3 years from issuance)","Forklift — employer evaluation on hire","CPR","First Aid"})
certs_in = st.text_area("Certifications (comma/newline)", value=", ".join(cert_suggestions))

# ------------------------------------------------------------------------------
# Education
# ------------------------------------------------------------------------------
st.subheader("Education")
ed1, ed2 = st.columns(2)
schools: List[School] = []
for i, col in enumerate([ed1, ed2]):
    with col:
        st.markdown(f"**School {i+1}**")
        school = st.text_input("School", value=(parsed_schools[i]["school"] if i < len(parsed_schools) else ""), key=f"s_school_{i}")
        cred = st.text_input("Credential", value=(parsed_schools[i]["credential"] if i < len(parsed_schools) else ""), key=f"s_cred_{i}")
        year = st.text_input("Year", value=(parsed_schools[i]["year"] if i < len(parsed_schools) else ""), key=f"s_year_{i}")
        details = st.text_input("Details (city/state etc.)", value=(parsed_schools[i]["details"] if i < len(parsed_schools) else ""), key=f"s_det_{i}")
        if any([school,cred,year,details]):
            schools.append(School(school=school, credential=cred, year=year, details=details))

# ------------------------------------------------------------------------------
# Build resume context
# ------------------------------------------------------------------------------
def build_resume_context() -> Dict[str,Any]:
    all_sk = gather_skills()
    # Dedup & clamp
    dedup=[]; seen=set()
    for s in all_sk:
        if s.lower() in seen: continue
        seen.add(s.lower()); dedup.append(s)
    dedup = dedup[:MAX_SKILLS]

    # Cert dedupe & normalize exact labels
    certs = []
    for c in split_list(certs_in):
        lab = c.strip()
        low = lab.lower()
        norm = None
        for k,v in CERT_MAP.items():
            if re.search(rf"\b{re.escape(k)}\b", low): norm = v; break
        certs.append(norm or lab)
    certs = sorted(set(certs))[:MAX_CERTS]

    jobs = []
    for j in job_slots:
        if not any([j.company, j.role, j.city, j.start, j.end, j.bullets]):
            continue
        jobs.append({
            "company": j.company.strip(),
            "role": j.role.strip(),
            "city": j.city.strip(),
            "start": j.start.strip(),
            "end": j.end.strip(),
            "bullets": [clean_bullet(b) for b in j.bullets if b.strip()][:MAX_BULLETS_PER_JOB],
        })
        if len(jobs) == MAX_JOBS:
            break

    schools_ctx = [asdict(s) for s in schools][:MAX_SCHOOLS]

    ctx = {
        "Name": name.strip(),
        "City": city.strip(),
        "State": state.strip(),
        "phone": phone.strip(),
        "email": email.strip(),
        "summary": strip_banned(summary.strip()),
        "skills": dedup,
        "certs": certs,
        "jobs": jobs,
        "schools": schools_ctx,
        "trade_label": trade_label,
    }
    return ctx

# ------------------------------------------------------------------------------
# Exports: Resume (docxtpl), Cover Letter, Instructor Packet
# ------------------------------------------------------------------------------
def export_resume_docx(ctx: Dict[str,Any]) -> bytes:
    if not os.path.exists(RESUME_TEMPLATE_DOC):
        raise FileNotFoundError(f"Missing {RESUME_TEMPLATE_DOC} in repo root.")
    tpl = DocxTemplate(RESUME_TEMPLATE_DOC)
    tpl.render(ctx)
    bio = io.BytesIO()
    tpl.save(bio)
    return bio.getvalue()

def export_cover_letter_docx(ctx: Dict[str,Any], path_choice: str) -> bytes:
    doc = DocxWriter()
    p = doc.add_paragraph()
    run = p.add_run(ctx.get("Name",""))
    run.bold = True
    run.font.size = Pt(12)
    doc.add_paragraph(f"{ctx.get('City','')}, {ctx.get('State','')}")
    doc.add_paragraph(f"{ctx.get('phone','')} • {ctx.get('email','')}")

    doc.add_paragraph("")  # space
    body = []

    if path_choice == "Apprenticeship":
        body.append(f"I’m applying for {ctx.get('trade_label','the trade')} apprenticeship. I come with OSHA Outreach 10-Hour (Construction), reliable attendance, and practice logging measured work (counts, dimensions, torque) under supervision.")
        body.append("I work safely around people and equipment, follow instructions, and keep my area clean. I note specifications from prints or leads, check measurements, and ask questions early to avoid rework.")
        body.append("I can contribute on day one with materials handling, setup, and verifiable tasks, while continuing to learn prints, layout, and tool control. I keep proof of work via checklists and sign-offs.")
    else:
        body.append(f"I’m seeking an immediate-hire role in {ctx.get('trade_label','the trade')}. I bring safe pace, tool control, and measurable output. I follow instructions and document work with counts and QC checks.")
        body.append("I show up ready, use PPE correctly, maintain housekeeping, and communicate changes quickly. I’m comfortable with materials handling, staging, and basic tool use under supervision.")
        body.append("I will support the crew by executing assigned tasks reliably and capturing proof of completion (readings, photos without faces, and supervisor sign-off).")

    for para in body:
        doc.add_paragraph(para)

    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

def export_instructor_packet_docx(ctx: Dict[str,Any], reflections: str, upload_texts: List[str]) -> bytes:
    if not os.path.exists(MASTER_PLAYBOOK_DOC):
        raise FileNotFoundError(f"Missing {MASTER_PLAYBOOK_DOC} in repo root.")
    section_text = cached_extract_playbook_section(MASTER_PLAYBOOK_DOC, ctx.get("trade_label","")) or "(Playbook section not found.)"

    doc = DocxWriter()
    title = doc.add_paragraph()
    r = title.add_run("Instructor Pathway Packet")
    r.bold = True; r.font.size = Pt(16)

    doc.add_paragraph("")
    doc.add_paragraph(f"Student: {ctx.get('Name','')}  •  {ctx.get('City','')}, {ctx.get('State','')}  •  {ctx.get('phone','')}  •  {ctx.get('email','')}")
    doc.add_paragraph(f"Target: {ctx.get('trade_label','')}  •  Path: {path_choice}")

    if reflections.strip():
        doc.add_paragraph("")
        ph = doc.add_paragraph()
        ph.add_run("Student Reflections").bold = True
        for line in reflections.splitlines():
            doc.add_paragraph(line)

    doc.add_paragraph("")
    ph2 = doc.add_paragraph()
    ph2.add_run("Stand-Out Playbook — Selected Trade").bold = True
    for line in section_text.splitlines():
        doc.add_paragraph(line)

    if upload_texts:
        doc.add_paragraph("")
        ph3 = doc.add_paragraph()
        ph3.add_run("Full Text of Uploaded Docs").bold = True
        for i, txt in enumerate(upload_texts, start=1):
            doc.add_paragraph("")
            doc.add_paragraph(f"— Upload {i} —")
            for line in (txt or "").splitlines():
                if line.strip():
                    doc.add_paragraph(line)

    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

# ------------------------------------------------------------------------------
# Actions
# ------------------------------------------------------------------------------
st.subheader("Generate")
ctx_preview = build_resume_context()

cols = st.columns(3)
with cols[0]:
    if st.button("Generate Resume (DOCX)"):
        try:
            b = export_resume_docx(ctx_preview)
            st.download_button("Download Resume.docx", data=b, file_name="Resume.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        except Exception as e:
            st.error(f"Resume export failed: {e}")

with cols[1]:
    if st.button("Generate Cover Letter (DOCX)"):
        try:
            b = export_cover_letter_docx(ctx_preview, path_choice)
            st.download_button("Download Cover_Letter.docx", data=b, file_name="Cover_Letter.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        except Exception as e:
            st.error(f"Cover letter export failed: {e}")

with cols[2]:
    if st.button("Generate Instructor Packet (DOCX)"):
        try:
            b = export_instructor_packet_docx(ctx_preview, student_reflections, [t for t in texts if t])
            st.download_button("Download Instructor_Packet.docx", data=b, file_name="Instructor_Packet.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        except Exception as e:
            st.error(f"Packet export failed: {e}")

# Final context preview (for docxtpl)
st.subheader("Resume context (docxtpl JSON)")
st.code(json.dumps(ctx_preview, indent=2))

st.caption("Guardrails: neutral language • evidence beats adjectives • never invent employers/dates • mark uncertain claims as (suggested)")
