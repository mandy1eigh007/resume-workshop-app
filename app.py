# app.py — Resume Workshop & Pathways (Seattle Tri-County)
# Streamlit single-file app. Browser-only. Python 3.11.
# Full build: header autofill, role→bullets from Job Master (click-to-insert),
# skills inference on insert, normalized certs, education parsing, URL imports,
# docxtpl resume rendering, cover letter, instructor packet.
# Objective is NOT auto-finalized: we provide Apprenticeship/Job starter lines.

from __future__ import annotations
import io, os, re, csv, datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple, Optional

import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
from docx import Document as DocxReader
from docx import Document as DocxWriter
from docx.shared import Pt
from pypdf import PdfReader
import requests

# Optional PDF fallback
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

# neutralize “union-ish” language in free text (we avoid generating it anyway)
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
DATE_RANGE_RE = re.compile(
    r"(?P<start>(?:\d{4}|\w{3,9}\s+\d{4}))\s*(?:–|-|to|until|through)\s*(?P<end>(?:Present|Current|\d{4}|\w{3,9}\s+\d{4}))",
    re.I
)
SECTION_HEADERS = re.compile(
    r"^(objective|summary|professional summary|skills|core competencies|experience|work history|"
    r"employment|education|certifications|certificates|references|contact|profile|qualifications|"
    r"career|background|achievements|accomplishments|projects|volunteer|activities|interests|"
    r"technical skills|languages|awards|honors|publications|training|licenses|memberships)$",
    re.I
)

# clean trade dropdown — no locals in the visible labels
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
    words = s.split()
    return " ".join(words[:24]) if len(words)>24 else s

def split_list(raw: str) -> List[str]:
    if not raw: return []
    parts = [p.strip(" •\t") for p in re.split(r"[,\n;•]+", raw)]
    return [p for p in parts if p]

def parse_dates(raw: str) -> Tuple[str,str]:
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
    # Try pdfminer first (more robust for text PDFs)
    if pdfminer_extract_text is not None:
        try:
            if hasattr(file, "getvalue"):
                bio = io.BytesIO(file.getvalue())
            else:
                try:
                    file.seek(0)
                    bio = io.BytesIO(file.read())
                except Exception:
                    bio = io.BytesIO(file.read() if hasattr(file, "read") else b"")
            bio.seek(0)
            text = pdfminer_extract_text(bio) or ""
            if text.strip():
                return text
        except Exception:
            pass
    # Fallback pypdf
    try:
        if hasattr(file, "seek"):
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
            t = p.text.strip()
            if t: parts.append(t)
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
    if name.endswith(".pdf"): return extract_text_from_pdf(upload)
    if name.endswith(".docx"): return extract_text_from_docx(upload)
    try:
        return upload.getvalue().decode("utf-8", errors="ignore")
    except Exception:
        return ""

class NamedBytesIO(io.BytesIO):
    def __init__(self, data: bytes, name: str):
        super().__init__(data); self.name = name

def _drive_direct(url: str) -> str:
    m = re.search(r"/d/([a-zA-Z0-9_-]+)", url) or re.search(r"[?&]id=([a-zA-Z0-9_-]+)", url)
    if m:
        file_id = m.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url

@st.cache_data(ttl=3600)
def fetch_url_to_named_bytes(url: str, fallback_name: str = "downloaded_file") -> Optional[NamedBytesIO]:
    try:
        u = _drive_direct(url.strip())
        r = requests.get(u, timeout=30)
        r.raise_for_status()
        base = url.split("?")[0].rstrip("/").split("/")[-1] or fallback_name
        name = base
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

def categorize_skills(skills: List[str]) -> Dict[str, List[str]]:
    out = {"Transferable": [], "Job-Specific": [], "Self-Management": []}
    seen=set()
    for s in skills:
        lab = normalize_skill_label(s)
        if not lab: continue
        if lab.lower() in seen: continue
        seen.add(lab.lower())
        if lab in {"Reading blueprints & specs","Hand & power tools","Operating machinery","Materials handling (wood/concrete/metal)","Trades math & measurement","Regulatory compliance","Safety awareness"}:
            cat="Job-Specific"
        elif lab in {"Leadership","Adaptability & willingness to learn","Physical stamina & dexterity"}:
            cat="Self-Management"
        else:
            cat="Transferable"
        out[cat].append(lab)
    return out

# ─────────────────────────────────────────────────────────
# Role→bullets mapping (Job Master) + detection
# ─────────────────────────────────────────────────────────
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
}

def detect_roles_from_text(text: str, all_roles: List[str]) -> List[str]:
    low=(text or "").lower()
    found=set()
    for r in all_roles:
        terms = ROLE_ALIASES.get(r, [r.lower()])
        for t in terms:
            if re.search(rf"\b{re.escape(t)}\b", low):
                found.add(r); break
    return [r for r in all_roles if r in found][:12]

@st.cache_data
def read_job_master_roles(raw_bytes: Optional[bytes]) -> Dict[str, List[str]]:
    """Parse Job_History_Master.docx. Heading 1 = role; subsequent paragraphs = bullets."""
    try:
        doc = DocxReader(io.BytesIO(raw_bytes)) if raw_bytes else DocxReader("Job_History_Master.docx")
    except Exception:
        return {}
    roles: Dict[str,List[str]] = {}
    cur = None
    for p in doc.paragraphs:
        style = (p.style.name or "").lower() if p.style else ""
        text = (p.text or "").strip()
        if not text: continue
        if "heading 1" in style:
            cur = text; roles.setdefault(cur, [])
            continue
        if cur:
            roles[cur].append(clean_bullet(text))
    # dedupe + clamp
    for k,v in roles.items():
        seen=set(); ded=[]
        for b in v:
            key=b.lower()
            if key in seen: continue
            seen.add(key); ded.append(b)
        roles[k]=ded[:12]
    return roles

# infer skills when bullets are inserted
BULLET_SKILL_HINTS = [
    (re.compile(r"\b(clean|organize|stage|restock|housekeep|walkway|sweep|debris)\b", re.I), ("Transferable","Attention to detail")),
    (re.compile(r"\b(pallet|forklift|lift|jack|rig|hoist|carry|load|unload|stack)\b", re.I), ("Job-Specific","Materials handling (wood/concrete/metal)")),
    (re.compile(r"\b(conduit|measure|layout|prints?|drawings?)\b", re.I), ("Job-Specific","Reading blueprints & specs")),
    (re.compile(r"\b(grinder|drill|saw|snips|hand tools|power tools|torch)\b", re.I), ("Job-Specific","Hand & power tools")),
    (re.compile(r"\b(ppe|osha|lockout|tagout|loto|hazard|spill|permit)\b", re.I), ("Job-Specific","Regulatory compliance")),
    (re.compile(r"\b(count|verify|inspect|qc|torque|measure)\b", re.I), ("Transferable","Critical thinking")),
    (re.compile(r"\b(rush|deadline|targets?|production|pace)\b", re.I), ("Transferable","Time management")),
    (re.compile(r"\b(team|crew|assist|support|communicat)\b", re.I), ("Transferable","Teamwork & collaboration")),
    (re.compile(r"\b(climb|lift|carry|physical|stamina)\b", re.I), ("Self-Management","Physical stamina & dexterity")),
]
def infer_skills_from_bullets(bullets: List[str]) -> Dict[str, List[str]]:
    cats={"Transferable":[], "Job-Specific":[], "Self-Management":[]}
    seen=set()
    for b in bullets:
        for rx,(cat,label) in BULLET_SKILL_HINTS:
            if rx.search(b):
                key=(cat,label.lower())
                if key not in seen:
                    seen.add(key); cats[cat].append(label)
    return cats

# ─────────────────────────────────────────────────────────
# Header / Education / Certs parsing
# ─────────────────────────────────────────────────────────
def _likely_name(lines: List[str]) -> str:
    best=""; best_score=-1.0
    for i,l in enumerate(lines[:20]):
        s=l.strip()
        if not s: continue
        if EMAIL_RE.search(s) or PHONE_RE.search(s): continue
        if SECTION_HEADERS.match(s): continue
        if re.search(r"(objective|summary|skills|experience|education|cert|resume|cv|curriculum)", s, re.I): continue
        words = [w for w in re.split(r"\s+", s) if w]
        if not (2 <= len(words) <= 4): continue
        if any(re.search(r"\d", w) for w in words): continue
        caps = sum(1 for w in words if w[:1].isalpha() and w[:1].isupper())
        score = caps/len(words) + (20 - i)*0.01
        if score>best_score:
            best_score=score; best=s
    return best

def parse_header(text: str) -> Dict[str,str]:
    name=""; email=""; phone=""; city=""; state=""
    m = EMAIL_RE.search(text or "");  email = m.group(0) if m else ""
    m = PHONE_RE.search(text or "");  phone = m.group(0) if m else ""
    lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
    m2 = CITY_STATE_RE.search("\n".join(lines[:30]))
    if m2: city, state = m2.group(1), m2.group(2).upper()
    name = _likely_name(lines)
    return {"Name": cap_first(name), "Email": clean_email(email), "Phone": clean_phone(phone),
            "City": cap_first(city), "State": (state or "").strip()}

def parse_education(text: str) -> List[Dict[str,str]]:
    out=[]; lines=[l.strip() for l in (text or "").splitlines() if l.strip()]
    i=0
    while i < len(lines) and len(out) < MAX_SCHOOLS:
        l = lines[i]
        if re.search(r"(high school|ged|college|university|program|certificate|diploma|academy|institute)", l, re.I):
            school = cap_first(l); cred=""; year=""; details=""
            for la in lines[i+1:i+7]:
                if re.search(r"\b(20\d{2}|19\d{2})\b", la) and not year:
                    year = la.strip()
                mcs = CITY_STATE_RE.search(la)
                if mcs and not details:
                    details = f"{mcs.group(1)}, {mcs.group(2).upper()}"
                if any(x in la.lower() for x in ["diploma","degree","certificate","ged","program","apprentice","associate","bachelor","master"]) and not cred:
                    cred = cap_first(la.strip())
            out.append({"school": school, "credential": cred, "year": year, "details": details})
        i+=1
    return out[:MAX_SCHOOLS]

CERT_MAP = {
    "osha 10": "OSHA Outreach 10-Hour (Construction)",
    "osha-10": "OSHA Outreach 10-Hour (Construction)",
    "osha10": "OSHA Outreach 10-Hour (Construction)",
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
}
CERT_PATTERNS = {k: re.compile(rf"\b{re.escape(k)}\b", re.I) for k in CERT_MAP}
def parse_certs(text: str) -> List[str]:
    low=(text or "").lower(); out=set()
    for k,rx in CERT_PATTERNS.items():
        if rx.search(low): out.add(CERT_MAP[k])
    return sorted(out)

# ─────────────────────────────────────────────────────────
# Objective starters (not final)
# ─────────────────────────────────────────────────────────
def objective_starters(trade: str) -> Dict[str, List[str]]:
    app = [
        f"Aim to enter {trade} apprenticeship—reliable day-one helper with safety habits, tool control, and documented practice hours (suggested).",
        f"Seeking {trade} apprenticeship; bring on-time pace, PPE compliance, and print-reading basics from self-study (suggested).",
        f"Ready for structured training in {trade}; will log tasks, measurements, and supervisor sign-offs to progress quickly.",
        f"Motivated to learn {trade} to standard; focus on safe production, checklist discipline, and crew support.",
        f"Pursuing {trade} apprenticeship; committed to math/prints practice and proven attendance record.",
    ]
    job = [
        f"Seeking entry-level {trade} role; can contribute on day one with safe pace, materials handling, and verified task logs.",
        f"Ready to support a {trade} crew—use tools per guidance, follow prints, and hit targets under supervision.",
        f"Immediate availability for {trade}-adjacent helper work; document counts, measurements, and QC checks.",
        f"Hands-on worker for {trade}; prioritize PPE, housekeeping, and production flow with sign-off tracking.",
        f"Entry-level {trade} role; bring reliability, communication, and measurable task completion.",
    ]
    return {"Apprenticeship": app, "Job": job}

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
    summary = strip_banned(norm_ws(form.get("Objective_Final","")))[:MAX_SUMMARY_CHARS]

    # skills (flat)
    skills_all=[]
    for raw in (form["Skills_Transferable"], form["Skills_JobSpecific"], form["Skills_SelfManagement"]):
        skills_all += split_list(raw)
    seen=set(); skills=[]
    for s in skills_all:
        lab=normalize_skill_label(norm_ws(s))
        if lab and lab.lower() not in seen:
            seen.add(lab.lower()); skills.append(lab)
    skills = skills[:MAX_SKILLS]

    certs = [norm_ws(c) for c in split_list(form["Certifications"] )][:MAX_CERTS]

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
    loc = ", ".join([x for x in [data.get('city',''), data.get('state','')] if x])
    if loc: doc.add_paragraph(loc)
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
    hi = [h.strip(" •") for h in re.split(r"[•\n,;]+", body_strength or "") if h.strip()]
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
# Streamlit UI
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
    st.caption("Upload Job History Master (Heading 1 = Role; bullets under it).")
    job_master_upl = st.file_uploader("Job_History_Master.docx", type=["docx"])
    job_master_bytes = job_master_upl.read() if job_master_upl else None

    st.markdown("---")
    st.caption("Upload additional docs to embed (full text) in the Instructor Packet.")
    pathway_uploads = st.file_uploader("Upload pathway documents", type=["pdf","docx","txt"], accept_multiple_files=True)

# Main
st.title("Student Packet: Resume Workshop")
st.subheader("0) Bring Your Stuff (we’ll mine it)")

c0a, c0b = st.columns(2)
with c0a:
    prev_resume_files = st.file_uploader(
        "Previous resume (PDF/DOCX/TXT)", type=["pdf","docx","txt"], accept_multiple_files=True
    )
with c0b:
    jd_files = st.file_uploader(
        "Job descriptions / postings (PDF/DOCX/TXT)", type=["pdf","docx","txt"], accept_multiple_files=True
    )

st.markdown("**Or import by URL (public links, incl. Google Drive):**")
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
# Workshop UI
# ─────────────────────────────────────────────────────────
st.subheader("1. Your Header (Contact Information)")
c1, c2 = st.columns(2)
with c1:
    Name = st.text_input("Name", key="Name")
    Phone = st.text_input("Phone", key="Phone")
    Email = st.text_input("Email", key="Email")
with c2:
    City = st.text_input("City", key="City")
    State = st.text_input("State (2-letter)", key="State")

st.subheader("2. Objective")
c3a, c3b = st.columns(2)
with c3a:
    application_type = st.radio("Are you seeking a:", ["Apprenticeship","Job"], horizontal=True, index=0, key="Path")
    trade = st.selectbox("Target trade:", TRADE_TAXONOMY, index=TRADE_TAXONOMY.index("Electrician – Inside (01)"), key="SelectedTrade")
with c3b:
    wk_pitch = st.text_input("10-second pitch (optional):", st.session_state.get("Pitch",""))
    st.session_state["Pitch"] = wk_pitch

# Objective is not finalized; show starters
starters = objective_starters(st.session_state.get("SelectedTrade",""))
with st.expander("Suggested objective starters"):
    ca, cb = st.columns(2)
    with ca:
        st.markdown("**Apprenticeship**")
        for s in starters["Apprenticeship"]:
            st.caption("• " + s)
    with cb:
        st.markdown("**Job**")
        for s in starters["Job"]:
            st.caption("• " + s)

wk_objective_final = st.text_area("Type your objective (1–2 sentences):", st.session_state.get("Objective_Final",""))

st.subheader("3. Skills (suggestions + your edits)")
suggested_skills = []
if combined_text:
    # suggest from text; keep it lightweight — we’ll also infer from inserted bullets
    hits = {}
    low = combined_text.lower()
    for kw, skill in TRANSFERABLE_KEYWORDS.items():
        if kw in low:
            hits[skill] = hits.get(skill, 0) + 1
    ordered = [s for s,_ in sorted(hits.items(), key=lambda kv: -kv[1])]
    suggested_skills = [s for s in SKILL_CANON if s in ordered][:8]

quick_transfer = st.multiselect("Quick Add: transferable skills from your uploads", SKILL_CANON, default=suggested_skills)
Skills_Transferable = st.text_area("Transferable Skills (comma/newline):", st.session_state.get("Skills_Transferable",""))
Skills_JobSpecific  = st.text_area("Job-Specific Skills (comma/newline):", st.session_state.get("Skills_JobSpecific",""))
Skills_SelfManagement = st.text_area("Self-Management Skills (comma/newline):", st.session_state.get("Skills_SelfManagement",""))

st.subheader("4. Work Experience — Role detection + click-to-insert bullets")
# read job master and detect roles
roles_map = read_job_master_roles(job_master_bytes)
all_roles = list(roles_map.keys())
detected = detect_roles_from_text(combined_text, all_roles) if combined_text else []

# let user choose which Job (1/2/3) receives bullets when clicked
target_job_slot = st.radio("Insert bullets into which job?", ["Job 1","Job 2","Job 3"], horizontal=True, index=0, key="BulletTarget")

# Prepare state for duties fields so we can append
for k in ["Job1_Duties","Job2_Duties","Job3_Duties"]:
    if k not in st.session_state:
        st.session_state[k] = ""

with st.expander("Detected/Available roles — click bullets to insert into the selected job’s Duties"):
    # show detected first, then all
    role_order = detected + [r for r in all_roles if r not in detected]
    for r in role_order:
        st.markdown(f"**{r}**")
        cols = st.columns(2)
        pool = roles_map.get(r, [])[:12]
        half = (len(pool)+1)//2
        for i, col in enumerate(cols):
            with col:
                for b in pool[i*half:(i+1)*half]:
                    if st.button(f"• {b}", key=f"btn_{r}_{i}_{hash(b)%100000}"):
                        # append to the selected job’s duties and infer skills
                        job_key = {"Job 1":"Job1_Duties","Job 2":"Job2_Duties","Job 3":"Job3_Duties"}[st.session_state["BulletTarget"]]
                        cur = st.session_state.get(job_key,"").strip()
                        lines = [ln for ln in cur.splitlines() if ln.strip()]
                        if b not in lines:
                            lines.append(b)
                        st.session_state[job_key] = "\n".join(lines[:MAX_BULLETS_PER_JOB])

                        # infer skills from this single bullet and merge into skill boxes
                        hints = infer_skills_from_bullets([b])
                        def _merge(field:str, labels:List[str]):
                            base = split_list(st.session_state.get(field,""))
                            lowset = set(x.lower() for x in base)
                            for lab in labels:
                                if lab.lower() not in lowset:
                                    base.append(lab)
                                    lowset.add(lab.lower())
                            st.session_state[field] = ", ".join(base[:MAX_SKILLS])
                        if hints.get("Transferable"): _merge("Skills_Transferable", hints["Transferable"])
                        if hints.get("Job-Specific"): _merge("Skills_JobSpecific", hints["Job-Specific"])
                        if hints.get("Self-Management"): _merge("Skills_SelfManagement", hints["Self-Management"])

# job fields
st.markdown("### Job 1")
J1c = st.text_input("Company:", key="Job1_Company")
J1cs = st.text_input("City/State:", key="Job1_CityState")
J1d = st.text_input("Dates (e.g., 2023-06 – Present):", key="Job1_Dates")
J1t = st.text_input("Title:", key="Job1_Title")
J1du = st.text_area("Duties/Accomplishments (1–4 bullets):", key="Job1_Duties", height=120)

st.markdown("### Job 2")
J2c = st.text_input("Company:", key="Job2_Company")
J2cs = st.text_input("City/State:", key="Job2_CityState")
J2d = st.text_input("Dates:", key="Job2_Dates")
J2t = st.text_input("Title:", key="Job2_Title")
J2du = st.text_area("Duties/Accomplishments (1–4 bullets):", key="Job2_Duties", height=120)

st.markdown("### Job 3")
J3c = st.text_input("Company:", key="Job3_Company")
J3cs = st.text_input("City/State:", key="Job3_CityState")
J3d = st.text_input("Dates:", key="Job3_Dates")
J3t = st.text_input("Title:", key="Job3_Title")
J3du = st.text_area("Duties/Accomplishments (1–4 bullets):", key="Job3_Duties", height=120)

st.subheader("5. Certifications")
Certifications = st.text_area(
    "List certifications (comma/newline). If none, write 'None yet' or what you plan to get.",
    st.session_state.get("Certifications","OSHA Outreach 10-Hour (Construction), WA Flagger (expires 3 years from issuance), Forklift — employer evaluation on hire")
)

st.subheader("6. Education")
st.write("Reverse order. Include city/state, dates, and credential/diploma.")
E1s = st.text_input("School/Program 1:", key="Edu1_School"); E1cs = st.text_input("City/State 1:", key="Edu1_CityState")
E1d = st.text_input("Dates 1:", key="Edu1_Dates"); E1c = st.text_input("Certificate/Diploma 1:", key="Edu1_Credential")
E2s = st.text_input("School/Program 2:", key="Edu2_School"); E2cs = st.text_input("City/State 2:", key="Edu2_CityState")
E2d = st.text_input("Dates 2:", key="Edu2_Dates"); E2c = st.text_input("Certificate/Diploma 2:", key="Edu2_Credential")

# Autofill from text — header, education, certs, detected roles (preview)
st.markdown("---")
if st.button("Auto-Fill from Uploaded Text", type="secondary", disabled=(not combined_text)):
    # header
    hdr = parse_header(combined_text)
    for k in ["Name","Phone","Email","City","State"]:
        if not st.session_state.get(k):
            st.session_state[k] = hdr.get(k,"")

    # certs
    detected_certs = parse_certs(combined_text)
    if detected_certs:
        base = st.session_state.get("Certifications","").strip()
        combo = (base + (", " if base else "") + ", ".join(detected_certs)).strip(", ")
        st.session_state["Certifications"] = combo

    # education
    ed = parse_education(combined_text)
    if ed:
        first = ed[0]
        st.session_state["Edu1_School"] = st.session_state.get("Edu1_School","") or first.get("school","")
        st.session_state["Edu1_CityState"] = st.session_state.get("Edu1_CityState","") or first.get("details","")
        st.session_state["Edu1_Dates"] = st.session_state.get("Edu1_Dates","") or first.get("year","")
        st.session_state["Edu1_Credential"] = st.session_state.get("Edu1_Credential","") or first.get("credential","")
    if len(ed) > 1:
        second = ed[1]
        st.session_state["Edu2_School"] = st.session_state.get("Edu2_School","") or second.get("school","")
        st.session_state["Edu2_CityState"] = st.session_state.get("Edu2_CityState","") or second.get("details","")
        st.session_state["Edu2_Dates"] = st.session_state.get("Edu2_Dates","") or second.get("year","")
        st.session_state["Edu2_Credential"] = st.session_state.get("Edu2_Credential","") or second.get("credential","")

    # objective suggestion text (not final)
    st.session_state["Objective_Final"] = st.session_state.get("Objective_Final","")

    st.success("Autofill complete. Review the header/education/certs and use role bullets to build duties.")

# ─────────────────────────────────────────────────────────
# Generate Docs
# ─────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Cover Letter (optional)")
CL_Company = st.text_input("Company/Employer:","")
CL_Role    = st.text_input("Role Title:", f"{st.session_state.get('SelectedTrade','Apprenticeship')} apprentice")
CL_Location= st.text_input("Company Location (City, State):","")
CL_Highlights = st.text_area("Optional: bullet highlights (comma/newline/• allowed):","Reliable • Safety-focused • Coachable")

st.markdown("---")
if st.button("Generate Resume + Cover Letter + Instructor Packet", type="primary"):
    problems=[]
    if not st.session_state.get("Name","").strip():
        problems.append("Name is required.")
    if not (st.session_state.get("Phone","").strip() or st.session_state.get("Email","").strip()):
        problems.append("At least one contact method (Phone or Email) is required.")
    if not tpl_bytes:
        problems.append("Template not found. Put resume_app_template.docx in the repo or upload it in the sidebar.")
    if problems:
        st.error(" | ".join(problems))
        st.stop()

    # merge Quick Add into Transferable
    skills_transfer_final = st.session_state.get("Skills_Transferable","")
    if quick_transfer:
        skills_transfer_final = (skills_transfer_final + (", " if skills_transfer_final.strip() else "") + ", ".join(quick_transfer))

    trade = st.session_state.get("SelectedTrade","Electrician – Inside (01)")
    form = {
        "Name": st.session_state.get("Name",""), "City": st.session_state.get("City",""), "State": st.session_state.get("State",""),
        "Phone": st.session_state.get("Phone",""), "Email": st.session_state.get("Email",""),
        "Pitch": st.session_state.get("Pitch",""),
        "Objective_Final": st.session_state.get("Objective_Final", wk_objective_final) or wk_objective_final,
        "Skills_Transferable": skills_transfer_final,
        "Skills_JobSpecific": st.session_state.get("Skills_JobSpecific",""),
        "Skills_SelfManagement": st.session_state.get("Skills_SelfManagement",""),
        "Certifications": st.session_state.get("Certifications",""),
        "Other_Work": st.session_state.get("Other_Work",""), "Volunteer": st.session_state.get("Volunteer",""),
    }
    # Jobs
    for i in [1,2,3]:
        form[f"Job{i}_Company"]=st.session_state.get(f"Job{i}_Company","")
        form[f"Job{i}_CityState"]=st.session_state.get(f"Job{i}_CityState","")
        form[f"Job{i}_Dates"]=st.session_state.get(f"Job{i}_Dates","")
        form[f"Job{i}_Title"]=st.session_state.get(f"Job{i}_Title","")
        form[f"Job{i}_Duties"]=st.session_state.get(f"Job{i}_Duties","")
    # Education
    for i in [1,2]:
        form[f"Edu{i}_School"]=st.session_state.get(f"Edu{i}_School","")
        form[f"Edu{i}_CityState"]=st.session_state.get(f"Edu{i}_CityState","")
        form[f"Edu{i}_Dates"]=st.session_state.get(f"Edu{i}_Dates","")
        form[f"Edu{i}_Credential"]=st.session_state.get(f"Edu{i}_Credential","")

    # Resume
    try:
        resume_ctx = build_resume_context(form, trade)
        resume_bytes = render_docx_with_template(tpl_bytes, resume_ctx)
    except Exception as e:
        st.error(f"Resume template rendering failed: {e}")
        st.stop()

    # Cover Letter
    cover_bytes = build_cover_letter_docx({
        "name": st.session_state.get("Name",""), "city": st.session_state.get("City",""), "state": st.session_state.get("State",""),
        "phone": clean_phone(st.session_state.get("Phone","")), "email": clean_email(st.session_state.get("Email","")),
        "company": CL_Company, "role": CL_Role, "location": CL_Location,
        "trade_label": trade, "strength": CL_Highlights,
        "application_type": st.session_state.get("Path","Apprenticeship"),
    })

    # Instructor Packet (Workshop reflections + full text of docs)
    reflections = {
        "Notes / Instructor prompts": st.session_state.get("WorkshopNotes",""),
    }
    merged_docs_for_packet = list(pathway_uploads or []) \
                           + list(prev_resume_files or []) \
                           + list(jd_files or []) \
                           + url_fetches
    packet_bytes = build_pathway_packet_docx({"name": st.session_state.get("Name","")}, trade, st.session_state.get("Path","Apprenticeship"), merged_docs_for_packet, reflections)

    safe_name = (st.session_state.get("Name","Student") or "Student").replace(" ","_")
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
    st.success("Generated. Objective is student-authored; roles & bullets wired; skills inferred on insert.")
