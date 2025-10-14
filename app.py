# app.py — Resume Workshop & Pathways (Seattle Tri-County)
# Streamlit single-file app. No APIs. Browser-only. Python 3.11.
# This version focuses on: Autofill Engine v2 + Objective Generator v2
# - Parses ANEW-style resumes & your role→construction mappings from DOCX
# - Stronger job, education, cert extraction
# - Construction-forward objective language (no "entry-level contributor")

from __future__ import annotations
import io, os, re, csv, datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple, Optional

import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
from docx import Document as DocxWriter
from docx.shared import Pt
from pypdf import PdfReader
import requests

# Optional better-PDF fallback if installed (no error if missing)
try:
    from pdfminer.high_level import extract_text as pdfminer_extract_text  # type: ignore
except Exception:
    pdfminer_extract_text = None

st.set_page_config(page_title="Resume Workshop & Pathways", layout="wide")

# ─────────────────────────────────────────────────────────
# Limits & regexes
# ─────────────────────────────────────────────────────────
MAX_SUMMARY_CHARS = 450
MAX_SKILLS = 12
MAX_CERTS = 8
MAX_JOBS = 3
MAX_BULLETS_PER_JOB = 5
MAX_SCHOOLS = 2

UNION_BANS = [
    r"\bunion\b", r"\bnon[-\s]?union\b", r"\bibew\b", r"\blocal\s*\d+\b",
    r"\binside\s*wire(man|men)?\b", r"\blow[-\s]?voltage\b", r"\bsound\s+and\s+communication(s)?\b",
    r"\bNECA\b", r"\bIBOE?\b", r"\bopen[-\s]?shop\b"
]
BANNED_RE = re.compile("|".join(UNION_BANS), re.I)
MULTISPACE = re.compile(r"\s+")
FILLER_LEADS = re.compile(r"^\s*(responsible for|duties included|tasked with|in charge of)\s*:?\s*", re.I)
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
    return " ".join(words[:28]) if len(words)>28 else s

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
# File text extraction + public URL fetch
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
# Data classes
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

# ─────────────────────────────────────────────────────────
# Skill canon & category mapping
# ─────────────────────────────────────────────────────────
SKILL_CANON = [
    "Problem-solving","Critical thinking","Attention to detail","Time management",
    "Teamwork & collaboration","Adaptability & willingness to learn","Safety awareness",
    "Conflict resolution","Customer service","Leadership","Reading blueprints & specs",
    "Hand & power tools","Materials handling (wood/concrete/metal)","Operating machinery",
    "Trades math & measurement","Regulatory compliance","Physical stamina & dexterity"
]
SKILL_CATEGORY_MAP = {
    "Problem-solving": "Transferable", "Critical thinking": "Transferable",
    "Attention to detail": "Transferable", "Time management": "Transferable",
    "Teamwork & collaboration": "Transferable",
    "Adaptability & willingness to learn": "Self-Management",
    "Safety awareness": "Job-Specific", "Conflict resolution": "Transferable",
    "Customer service": "Transferable", "Leadership": "Self-Management",
    "Reading blueprints & specs": "Job-Specific", "Hand & power tools": "Job-Specific",
    "Materials handling (wood/concrete/metal)": "Job-Specific",
    "Operating machinery": "Job-Specific", "Trades math & measurement": "Job-Specific",
    "Regulatory compliance": "Job-Specific", "Physical stamina & dexterity": "Self-Management",
}
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
        cat = SKILL_CATEGORY_MAP.get(lab, "Transferable")
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
# Role→construction seeds from your DOCX (Transferable Skills …)
# ─────────────────────────────────────────────────────────
def build_role_map_from_transferable_docx(file) -> Dict[str, Dict[str, List[str]]]:
    """
    Reads sections like:
      '3. Server / Food Service Worker  (Construction Focused)' → bullets
    Returns: { 'server': {'bullets': [...], 'skills': [...]}, ... }
    """
    from docx import Document as DocxReader
    try:
        doc = DocxReader(file)
    except Exception:
        return {}
    role_map: Dict[str, Dict[str, List[str]]] = {}
    cur_role_key = None
    for p in doc.paragraphs:
        text = p.text.strip()
        low = text.lower()
        # Identify "(Construction Focused)" role blocks or generic role headers
        if re.search(r"\(construction\s*focused\)", low) or re.search(r"^\d+\.\s*[A-Za-z].+\(", text):
            # normalize a role key
            base = re.sub(r"\(construction\s*focused\)", "", text, flags=re.I)
            base = re.sub(r"^\d+\.\s*", "", base).strip()
            # e.g., "Server / Food Service Worker"
            role_key = base.split("|")[0].split("—")[0].strip().lower()
            role_key = re.sub(r"[^a-z0-9/ &-]", "", role_key)
            cur_role_key = role_key
            role_map.setdefault(cur_role_key, {"bullets": [], "skills": []})
            continue
        # Collect bullets
        if cur_role_key and (text.startswith("*") or text.startswith("•") or (len(text)>2 and text[0] == "-" and text[1]==" ")):
            b = clean_bullet(text)
            if b and b.lower() not in [x.lower() for x in role_map[cur_role_key]["bullets"]]:
                role_map[cur_role_key]["bullets"].append(b)
        # Opportunistic skill catch (from "What it shows about you" style)
        if cur_role_key and any(k in low for k in ["you", "safety", "tools", "team", "logistics", "organized"]):
            # naive skill tokens
            tokens = []
            if "safety" in low: tokens.append("Safety awareness")
            if "tools" in low: tokens.append("Hand & power tools")
            if "organized" in low: tokens.append("Time management")
            if "logistics" in low: tokens.append("Materials handling (wood/concrete/metal)")
            for t in tokens:
                if t not in role_map[cur_role_key]["skills"]:
                    role_map[cur_role_key]["skills"].append(t)
    return role_map

# Default embedded seeds as backup when doc not provided
ROLE_TO_CONSTR_BULLETS_DEFAULT = {
    "line cook": [
        "Worked safely around hot equipment and sharp tools",
        "Followed prep lists and maintained clean, organized stations",
        "Handled deliveries and rotated stock; kept work area hazard-free",
        "Stayed on pace to meet production demands during rushes",
    ],
    "retail": [
        "Kept inventory organized and aisles clear for safe flow",
        "De-escalated issues while maintaining professional communication",
        "Handled cash counts and hand-offs with accuracy",
    ],
    "warehouse": [
        "Staged materials, verified counts, and maintained clear aisles",
        "Operated pallet jacks/hand trucks under PPE rules",
    ],
    "server": [
        "Managed multiple tasks with tight timing while supporting team flow",
        "Maintained a clean, safe work area under pressure",
    ],
    "janitor": [
        "Used chemicals/equipment per safety guidance; kept areas hazard-free",
        "Completed checklists and documented work reliably",
    ],
    "custodian": [
        "Set up spaces, moved materials, and followed safety procedures",
    ],
    "barista": [
        "Followed recipes and equipment safety steps precisely",
        "Kept stations stocked and organized during rushes",
    ],
}

# ─────────────────────────────────────────────────────────
# Parsing ANEW-style content → header/jobs/edu/certs/skills
# ─────────────────────────────────────────────────────────
CERT_KEYWORDS = [
    "osha", "forklift", "flagger", "cpr", "first aid", "hazwoper",
    "twic", "nccer", "confined space", "ppe", "aerial lift", "traffic control",
]

def parse_header(text: str) -> Dict[str,str]:
    name = ""; email = ""; phone = ""; city = ""; state = ""
    m = EMAIL_RE.search(text or "");  email = m.group(0) if m else ""
    m = PHONE_RE.search(text or "");  phone = m.group(0) if m else ""
    m = CITY_STATE_RE.search(text or "")
    if m: city, state = m.group(1), m.group(2).upper()
    # Heuristic: first non-empty candidate line (2–4 words) not containing email/phone/label
    for l in [l.strip() for l in (text or "").splitlines()][:12]:
        if EMAIL_RE.search(l) or PHONE_RE.search(l): continue
        if any(x in l.lower() for x in ["summary","skills","certifications","experience","education"]): continue
        if 2 <= len(l.split()) <= 4 and len(l) <= 60:
            name = l; break
    return {"Name": cap_first(name), "Email": clean_email(email), "Phone": clean_phone(phone),
            "City": cap_first(city), "State": (state or "").strip()}

def parse_edu_blocks(text: str) -> List[School]:
    out=[]
    lines = [l.strip() for l in (text or "").splitlines()]
    # Look for education header and pull nearby lines
    edu_idx = None
    for i,l in enumerate(lines):
        if re.match(r"^\s*(education)\s*$", l, flags=re.I):
            edu_idx = i; break
    if edu_idx is None:
        # fallback: any GED/HS/College cues
        pass
    block = lines[edu_idx: edu_idx+15] if edu_idx is not None else lines
    # Simple heuristics: lines with school/program + potential city/state + year
    i=0
    while i < len(block) and len(out) < MAX_SCHOOLS:
        l = block[i]
        if re.search(r"(high school|college|university|cptc|program|certificate|diploma)", l, re.I):
            school = cap_first(l)
            cred=""; year=""; details=""
            for la in block[i+1:i+5]:
                if re.search(r"\b(20\d{2}|19\d{2})\b", la): year = la.strip()
                if CITY_STATE_RE.search(la): details = cap_first(la.strip())
                if any(x in la.lower() for x in ["diploma","degree","certificate","ged","program"]) and not cred:
                    cred = cap_first(la.strip())
            out.append(School(school=school, credential=cred, year=year, details=details))
        i += 1
    return out[:MAX_SCHOOLS]

def parse_certs(text: str) -> List[str]:
    low = (text or "").lower()
    found=set()
    for k in CERT_KEYWORDS:
        if k in low:
            if k=="osha": found.add("OSHA-10")
            elif k=="first aid": found.add("First Aid")
            elif k=="aerial lift": found.add("Aerial Lift")
            else: found.add(k.title())
    # Also read typical ANEW listing layout (label, tabbed bullets)
    for line in (text or "").splitlines():
        if re.search(r"flagger", line, re.I): found.add("Flagger")
        if re.search(r"forklift", line, re.I): found.add("Forklift")
        if re.search(r"cpr", line, re.I): found.add("CPR")
    return sorted(found)

def parse_skills_block(text: str) -> List[str]:
    # Grab lines under "Skills" header in ANEW-style content
    lines = [l.rstrip() for l in (text or "").splitlines()]
    out=[]
    on=False
    for l in lines:
        if re.match(r"^\s*skills\s*$", l, flags=re.I):
            on=True; continue
        if on:
            if not l.strip(): break
            if re.match(r"^\s*(certifications|experience|education)\s*$", l, flags=re.I): break
            if l.strip():
                out.append(re.sub(r"^[\t•\-\*]+\s*", "", l).strip())
    return out[:MAX_SKILLS]

def parse_jobs_blocks(text: str) -> List[Job]:
    # Targets formats from your docs: "Role   Company | City, State | Dates", followed by bullets
    lines = [l for l in (text or "").splitlines()]
    out=[]
    i=0
    while i < len(lines) and len(out) < MAX_JOBS:
        l = lines[i].strip()
        # detect "Experience" header and then role/company lines
        if re.match(r"^\s*experience\s*$", l, flags=re.I):
            i+=1; continue
        # Examples: "Maintenance Worker DSHS Facility", or "Server / Food Service Worker  (Construction Focused)"
        if l and not any(h in l.lower() for h in ["summary","skills","certifications","education"]):
            head = l
            # Pull city/state | dates from same or next lines with pipes or commas
            trail = " ".join(lines[i+1:i+3])
            comp = ""; role=""; cityst=""; start=""; end=""
            # Try split by tabs/pipes/dashes
            # e.g., "ABC Corporate Services | Seattle, WA | Jan 2020 – Feb 2023"
            mcity = CITY_STATE_RE.search(head) or CITY_STATE_RE.search(trail)
            if mcity: cityst = f"{mcity.group(1)}, {mcity.group(2).upper()}"
            mdate = DATE_RANGE_RE.search(head) or DATE_RANGE_RE.search(trail)
            if mdate: start,end = mdate.group("start"), mdate.group("end")
            # Separate role and company by double spaces or pipe
            parts = re.split(r"\s{2,}|\s\|\s| — | – ", head)
            if len(parts)>=2:
                # Heuristic: choose role first, company second
                role = parts[0].strip()
                comp = parts[1].strip()
            else:
                # fallback: assume first token block is role
                role = head.strip()
            # Gather bullets
            bullets=[]
            j=i+1
            while j < len(lines):
                line = lines[j].strip()
                if not line: 
                    j+=1; 
                    if bullets: break
                    continue
                if any(h in line.lower() for h in ["summary","skills","certifications","education"]): break
                if re.match(r"^\s*[•\-\*]\s+|^\t", lines[j]):  # bullet
                    bullets.append(clean_bullet(re.sub(r"^[\t•\-\*]+\s*", "", line)))
                else:
                    # stop at next probable header/role line
                    if DATE_RANGE_RE.search(line) or CITY_STATE_RE.search(line): 
                        # could be still same job; continue
                        pass
                    elif len(bullets) and len(line.split())<=4:
                        break
                if len(bullets) >= MAX_BULLETS_PER_JOB: break
                j+=1
            job = Job(company=cap_first(comp), role=cap_first(role), city=cap_first(cityst), start=start, end=end, bullets=bullets)
            job.trim(MAX_BULLETS_PER_JOB)
            if any([job.company, job.role]) and (job.bullets or start or cityst):
                out.append(job)
            i = max(j, i+1)
        i+=1
    return out[:MAX_JOBS]

def parse_header_jobs_edu_skills_certs_from_text(full_text: str) -> Dict[str, Any]:
    header = parse_header(full_text)
    jobs = parse_jobs_blocks(full_text)
    edus = parse_edu_blocks(full_text)
    certs = parse_certs(full_text)
    skills = parse_skills_block(full_text)
    # categorize skills
    cat = categorize_skills(skills)
    return {
        "header": header,
        "jobs": [asdict(j) for j in jobs],
        "schools": [asdict(s) for s in edus],
        "certs": sorted(certs),
        "skills_cat": cat
    }

# ─────────────────────────────────────────────────────────
# Job bullets suggestion (trade + role seeds)
# ─────────────────────────────────────────────────────────
def suggest_bullets_from_role(role_label: str, role_map: Dict[str, Dict[str, List[str]]]) -> List[str]:
    role_l = (role_label or "").lower()
    for key, payload in role_map.items():
        if key in role_l:
            return [clean_bullet(b) for b in (payload.get("bullets") or [])][:MAX_BULLETS_PER_JOB]
    # partial matches
    for key, payload in role_map.items():
        tokens = [t.strip() for t in key.split("/") if t.strip()]
        if any(t in role_l for t in tokens):
            return [clean_bullet(b) for b in (payload.get("bullets") or [])][:MAX_BULLETS_PER_JOB]
    # fallback default snippets
    for key, seeds in ROLE_TO_CONSTR_BULLETS_DEFAULT.items():
        if key in role_l:
            return [clean_bullet(b) for b in seeds][:MAX_BULLETS_PER_JOB]
    return []

# ─────────────────────────────────────────────────────────
# Objective Generator v2 (construction-forward)
# ─────────────────────────────────────────────────────────
def build_objective(trade: str, pitch: str, skills_cat: Dict[str,List[str]]) -> str:
    # pull a couple of high-signal skills
    ts = skills_cat.get("Job-Specific", []) + skills_cat.get("Transferable", [])
    ts = [s for s in ts if s.lower() not in {"customer service"}]
    picks = ", ".join(ts[:3]) if ts else "safety, teamwork, and reliable production"
    p = norm_ws(pitch or "")
    # Construction voice, short and jobsite credible:
    core = f"Ready to contribute on day one in {trade} — bringing {picks}. "
    if p:
        core += f"{p} "
    core += "Show up, work safe, learn fast, and help the crew hit targets."
    # sanitize and cap
    core = strip_banned(core)[:MAX_SUMMARY_CHARS]
    # ban “entry-level contributor” forever
    core = core.replace("entry-level contributor", "apprentice-ready contributor")
    return core

# ─────────────────────────────────────────────────────────
# Resume context + rendering
# ─────────────────────────────────────────────────────────
def build_resume_context(form: Dict[str,Any], trade_label: str) -> Dict[str,Any]:
    Name=cap_first(form["Name"]); City=cap_first(form["City"]); State=(form["State"] or "").strip().upper()
    phone=clean_phone(form["Phone"]); email=clean_email(form["Email"])
    # Objective: if user didn’t edit, generate
    if form.get("Objective_Final","").strip():
        summary = strip_banned(norm_ws(form["Objective_Final"]))[:MAX_SUMMARY_CHARS]
    else:
        # construct from inputs
        skills_cat = categorize_skills(
            split_list(form.get("Skills_Transferable","")) +
            split_list(form.get("Skills_JobSpecific","")) +
            split_list(form.get("Skills_SelfManagement",""))
        )
        summary = build_objective(trade_label, form.get("Pitch",""), skills_cat)

    # Skills normalization + dedupe
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
        if not any([company, title, duties]): continue
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

    other_work = norm_ws(form.get("Other_Work",""))
    volunteer  = norm_ws(form.get("Volunteer",""))
    tail=[]
    if other_work: tail.append(f"Other work: {other_work}")
    if volunteer:  tail.append(f"Volunteer: {volunteer}")
    if tail:
        add="  •  ".join(tail)
        summary = (summary + " " + add).strip()[:MAX_SUMMARY_CHARS]

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

def _split_highlights(raw: str) -> List[str]:
    return split_list(raw)

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
    hi = _split_highlights(body_strength)
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
# Sidebar — template & optional “knowledge” uploads
# ─────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Templates & Knowledge")
    tpl_bytes=None
    if os.path.exists("resume_app_template.docx"):
        with open("resume_app_template.docx","rb") as f: tpl_bytes=f.read()
    upl_tpl = st.file_uploader("Upload RESUME DOCX template (optional)", type=["docx"])
    if upl_tpl is not None: tpl_bytes = upl_tpl.read()

    st.markdown("---")
    st.caption("Upload 'Transferable Skills to Construction' (DOCX). We’ll auto-build role→construction bullets & skills from your doc.")
    transferable_doc = st.file_uploader("Transferable Skills DOCX (optional)", type=["docx"])

    st.caption("Upload Roadmaps DOCX (optional). We’ll expose a Trade Tips panel (full integration next pass).")
    roadmaps_doc = st.file_uploader("Seattle Construction Trades Roadmaps (optional)", type=["docx"])

    st.markdown("---")
    st.caption("Upload additional pathway docs (full text goes into Instructor Packet).")
    pathway_uploads = st.file_uploader("Upload pathway documents", type=["pdf","docx","txt"], accept_multiple_files=True)

# Build role map now if provided
ROLE_MAP = {}
if transferable_doc is not None:
    ROLE_MAP = build_role_map_from_transferable_docx(transferable_doc)

# ─────────────────────────────────────────────────────────
# Main — Step 0: Intake
# ─────────────────────────────────────────────────────────
st.title("Student Packet: Resume Workshop")

st.subheader("0) Bring Your Stuff (we’ll mine it)")
c0a, c0b = st.columns(2)
with c0a:
    prev_resume_files = st.file_uploader("Previous resume (PDF/DOCX/TXT)", type=["pdf","docx","txt"], accept_multiple_files=True)
with c0b:
    jd_files = st.file_uploader("Job descriptions / postings (PDF/DOCX/TXT)", type=["pdf","docx","txt"], accept_multiple_files=True)

st.markdown("**Or import by URL (public links only: Google Drive/GCS):**")
url_list = st.text_area("One URL per line", "")
url_fetches = []
if url_list.strip():
    for i, raw in enumerate(url_list.splitlines(), start=1):
        u = raw.strip()
        if not u: continue
        nb = fetch_url_to_named_bytes(u, fallback_name=f"url_{i}")
        if nb is not None:
            url_fetches.append(nb)
        else:
            st.warning(f"Could not fetch: {u} (is it public?)")

st.markdown("**Or paste text directly:**")
paste_box = st.text_area("Paste any job description or resume text here", "")

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

# Autofill
if "autofilled" not in st.session_state:
    st.session_state["autofilled"] = False

def set_if_empty(key: str, val: str):
    if key not in st.session_state or not str(st.session_state.get(key,"")).strip():
        st.session_state[key] = val

if st.button("Auto-Fill from Uploaded Text", type="secondary", disabled=(not combined_text)):
    prof = parse_header_jobs_edu_skills_certs_from_text(combined_text)
    hdr = prof.get("header", {})
    for k,v in {"Name":"Name","Phone":"Phone","Email":"Email","City":"City","State":"State"}.items():
        set_if_empty(v, hdr.get(k,""))

    # Jobs
    jobs = prof.get("jobs", [])
    for idx in range(1, MAX_JOBS+1):
        j = jobs[idx-1] if idx-1 < len(jobs) else {}
        set_if_empty(f"Job{idx}_Company", j.get("company",""))
        set_if_empty(f"Job{idx}_CityState", j.get("city",""))
        dates = " – ".join([x for x in [j.get("start",""), j.get("end","")] if x]).strip(" –")
        set_if_empty(f"Job{idx}_Dates", dates)
        set_if_empty(f"Job{idx}_Title", j.get("role",""))

        # Suggest bullets from role mapping
        role_label = j.get("role","")
        suggested = suggest_bullets_from_role(role_label, ROLE_MAP) if ROLE_MAP else suggest_bullets_from_role(role_label, {})
        merged = suggested or (j.get("bullets") or [])
        set_if_empty(f"Job{idx}_Duties", "\n".join(merged))

    # Education
    schools = prof.get("schools",[])
    for idx in range(1, MAX_SCHOOLS+1):
        s = schools[idx-1] if idx-1 < len(schools) else {}
        set_if_empty(f"Edu{idx}_School", s.get("school",""))
        set_if_empty(f"Edu{idx}_CityState", s.get("details",""))
        set_if_empty(f"Edu{idx}_Dates", s.get("year",""))
        set_if_empty(f"Edu{idx}_Credential", s.get("credential",""))

    # Certs
    certs = prof.get("certs",[])
    if certs:
        set_if_empty("Certifications", ", ".join(sorted(certs)))

    # Skills by category
    sk = prof.get("skills_cat", {})
    if sk:
        if sk.get("Transferable"): set_if_empty("Skills_Transferable", ", ".join(sk["Transferable"]))
        if sk.get("Job-Specific"): set_if_empty("Skills_JobSpecific", ", ".join(sk["Job-Specific"]))
        if sk.get("Self-Management"): set_if_empty("Skills_SelfManagement", ", ".join(sk["Self-Management"]))

    st.session_state["autofilled"] = True
    st.success("Autofill complete. The form below has been pre-populated.")

# ─────────────────────────────────────────────────────────
# Workshop UI
# ─────────────────────────────────────────────────────────
st.subheader("What is the Difference Between a Construction Facing Resume and a Traditional Resume?")
st.markdown("""
**Construction Facing Resume**  
• **Purpose:** Getting into a trade, apprenticeship, or construction company.  
• **Focus:** Hands-on skills (tools, materials), certs (OSHA-10, Flagger, Forklift), physical abilities, build projects, and jobsite language.  
• **Experience:** Translate non-construction roles into site value (teamwork, time, safety).
""")
wk_q1 = st.text_area("Write three things you will include on a construction-facing resume that you wouldn’t on a traditional resume:", height=120)

st.subheader("1. Why a Resume Matters in Construction")
st.write("It’s your first proof you can show up safe, use tools, learn fast, and support a crew.")

st.subheader("2. Your Header (Contact Information)")
c1, c2 = st.columns(2)
with c1:
    Name = st.text_input("Name", key="Name")
    Phone = st.text_input("Phone", key="Phone")
    Email = st.text_input("Email", key="Email")
with c2:
    City = st.text_input("City", key="City")
    State = st.text_input("State (2-letter)", key="State")

st.subheader("3. Writing Your Objective")
c3a, c3b = st.columns(2)
with c3a:
    application_type = st.radio("Are you seeking a job or apprenticeship?", ["Apprenticeship","Job"], horizontal=True, index=0)
    trade = st.selectbox("What trade are you aiming for?", TRADE_TAXONOMY, index=TRADE_TAXONOMY.index("Electrician – Inside (01)"))
with c3b:
    wk_pitch = st.text_input("10-second pitch (what you want them to know):", st.session_state.get("Pitch",""))
    st.session_state["Pitch"] = wk_pitch

wk_objective_final = st.text_area(
    "Objective (1–2 sentences — edit or leave blank and we’ll generate):",
    st.session_state.get("Objective_Final","")
)

st.subheader("4. Your Skills (Auto-categorized — edit freely)")
st.caption("Transferable = universal work skills; Job-Specific = tools/safety/site; Self-Management = reliability, leadership, stamina.")
auto_suggested = []  # suggestion is now driven by actual parse; still can add in future
Skills_Transferable = st.text_area("Transferable Skills (comma/newline):", st.session_state.get("Skills_Transferable",""))
Skills_JobSpecific  = st.text_area("Job-Specific Skills (comma/newline):", st.session_state.get("Skills_JobSpecific",""))
Skills_SelfManagement = st.text_area("Self-Management Skills (comma/newline):", st.session_state.get("Skills_SelfManagement",""))

st.subheader("5. Work Experience – Job 1")
J1c = st.text_input("Job 1 – Company:", key="Job1_Company")
J1cs = st.text_input("Job 1 – City/State:", key="Job1_CityState")
J1d = st.text_input("Job 1 – Dates (e.g., 2023-06 – Present):", key="Job1_Dates")
J1t = st.text_input("Job 1 – Title:", key="Job1_Title")
# role-mapped bullets suggestion on the fly
seed1 = "\n".join(suggest_bullets_from_role(st.session_state.get("Job1_Title",""), ROLE_MAP or {}))
J1du = st.text_area("Job 1 – Duties/Accomplishments (1–5 bullets):", key="Job1_Duties", value=st.session_state.get("Job1_Duties", seed1), height=140)

st.subheader("5. Work Experience – Job 2")
J2c = st.text_input("Job 2 – Company:", key="Job2_Company")
J2cs = st.text_input("Job 2 – City/State:", key="Job2_CityState")
J2d = st.text_input("Job 2 – Dates:", key="Job2_Dates")
J2t = st.text_input("Job 2 – Title:", key="Job2_Title")
seed2 = "\n".join(suggest_bullets_from_role(st.session_state.get("Job2_Title",""), ROLE_MAP or {}))
J2du = st.text_area("Job 2 – Duties/Accomplishments (1–5 bullets):", key="Job2_Duties", value=st.session_state.get("Job2_Duties", seed2), height=140)

st.subheader("5. Work Experience – Job 3")
J3c = st.text_input("Job 3 – Company:", key="Job3_Company")
J3cs = st.text_input("Job 3 – City/State:", key="Job3_CityState")
J3d = st.text_input("Job 3 – Dates:", key="Job3_Dates")
J3t = st.text_input("Job 3 – Title:", key="Job3_Title")
seed3 = "\n".join(suggest_bullets_from_role(st.session_state.get("Job3_Title",""), ROLE_MAP or {}))
J3du = st.text_area("Job 3 – Duties/Accomplishments (1–5 bullets):", key="Job3_Duties", value=st.session_state.get("Job3_Duties", seed3), height=140)

st.subheader("6. Certifications")
Certifications = st.text_area(
    "List certifications (comma/newline). If none, write 'None yet' or what you plan to get.",
    st.session_state.get("Certifications","OSHA-10, Flagger (WA), Forklift operator (employer evaluation on hire)")
)

st.subheader("7. Education")
st.write("Reverse order. Include city/state, dates, and credential/diploma.")
E1s = st.text_input("School/Program 1:", key="Edu1_School"); E1cs = st.text_input("City/State 1:", key="Edu1_CityState")
E1d = st.text_input("Dates 1:", key="Edu1_Dates"); E1c = st.text_input("Certificate/Diploma 1:", key="Edu1_Credential")
E2s = st.text_input("School/Program 2:", key="Edu2_School"); E2cs = st.text_input("City/State 2:", key="Edu2_CityState")
E2d = st.text_input("Dates 2:", key="Edu2_Dates"); E2c = st.text_input("Certificate/Diploma 2:", key="Edu2_Credential")

st.subheader("8. Optional Sections")
Other_Work = st.text_area("Other Work Experience (optional):", st.session_state.get("Other_Work",""))
Volunteer  = st.text_area("Volunteer Experience (optional):", st.session_state.get("Volunteer",""))

st.subheader("9. Build Your Resume (Draft)")
wk_draft_header = st.text_area("HEADER (draft, optional):","", height=80)
wk_draft_objective = st.text_area("OBJECTIVE (draft, optional):","", height=80)
wk_draft_skills = st.text_area("SKILLS (draft, optional):","", height=120)
wk_draft_work = st.text_area("WORK EXPERIENCE (draft, optional):","", height=140)
wk_draft_certs = st.text_area("CERTIFICATIONS (draft, optional):","", height=80)
wk_draft_edu = st.text_area("EDUCATION (draft, optional):","", height=80)

if roadmaps_doc is not None:
    st.info("Trade Tips loaded from Roadmaps (integration pass #2 will personalize by selected trade).")

st.markdown("**Final Checklist**")
st.markdown("""
- [ ] One page only  
- [ ] Professional font (10–12 pt)  
- [ ] Saved as PDF  
- [ ] Reviewed by peer  
- [ ] Reviewed by instructor  
""")

st.markdown("---")
st.subheader("Cover Letter (optional)")
CL_Company = st.text_input("Company/Employer:","")
CL_Role    = st.text_input("Role Title:", f"{trade} apprentice")
CL_Location= st.text_input("Company Location (City, State):","")
CL_Highlights = st.text_area("Optional: bullet highlights (comma/newline/• allowed):","Reliable • Safety-focused • Coachable")

# ─────────────────────────────────────────────────────────
# Generate Docs
# ─────────────────────────────────────────────────────────
if st.button("Generate Resume + Cover Letter + Instructor Packet", type="primary"):
    problems=[]
    if not Name.strip(): problems.append("Name is required.")
    if not (Phone.strip() or Email.strip()): problems.append("At least one contact method (Phone or Email) is required.")
    if problems:
        st.error(" | ".join(problems)); st.stop()

    # If objective empty, generate one on the fly
    objective_final = wk_objective_final.strip()
    if not objective_final:
        # build temp skills_cat for objective
        skills_cat = categorize_skills(
            split_list(st.session_state.get("Skills_Transferable","")) +
            split_list(st.session_state.get("Skills_JobSpecific","")) +
            split_list(st.session_state.get("Skills_SelfManagement",""))
        )
        objective_final = build_objective(trade, st.session_state.get("Pitch",""), skills_cat)

    form = {
        "Name": Name, "City": City, "State": State,
        "Phone": Phone, "Email": Email,
        "Pitch": st.session_state.get("Pitch",""),
        "Objective_Final": objective_final,
        "Skills_Transferable": st.session_state.get("Skills_Transferable",""),
        "Skills_JobSpecific": st.session_state.get("Skills_JobSpecific",""),
        "Skills_SelfManagement": st.session_state.get("Skills_SelfManagement",""),
        "Certifications": Certifications,
        "Other_Work": Other_Work, "Volunteer": Volunteer,
    }
    # Jobs
    for i,(co,cs,d,ti,du) in enumerate([
        (J1c,J1cs,J1d,J1t,J1du),
        (J2c,J2cs,J2d,J2t,J2du),
        (J3c,J3cs,J3d,J3t,J3du),
    ], start=1):
        form[f"Job{i}_Company"]=co; form[f"Job{i}_CityState"]=cs; form[f"Job{i}_Dates"]=d
        form[f"Job{i}_Title"]=ti; form[f"Job{i}_Duties"]=du
    # Education
    for i,(sch,cs,d,cr) in enumerate([
        (E1s,E1cs,E1d,E1c),
        (E2s,E2cs,E2d,E2c),
    ], start=1):
        form[f"Edu{i}_School"]=sch; form[f"Edu{i}_CityState"]=cs; form[f"Edu{i}_Dates"]=d; form[f"Edu{i}_Credential"]=cr

    # Resume
    if not tpl_bytes:
        st.error("Template not found. Put resume_app_template.docx in the repo or upload it in the sidebar.")
        st.stop()
    try:
        resume_ctx = build_resume_context(form, trade)
        resume_bytes = render_docx_with_template(tpl_bytes, resume_ctx)
    except Exception as e:
        st.error(f"Resume template rendering failed: {e}"); st.stop()

    # Cover Letter
    cover_bytes = build_cover_letter_docx({
        "name": Name, "city": City, "state": State, "phone": clean_phone(Phone), "email": clean_email(Email),
        "company": CL_Company, "role": CL_Role, "location": CL_Location,
        "trade_label": trade, "strength": CL_Highlights,
        "application_type": application_type,
    })

    # Instructor Packet
    reflections = {
        "Three construction-resume items (vs traditional)": wk_q1,
        "10-second pitch": st.session_state.get("Pitch",""),
        "Draft HEADER": wk_draft_header,
        "Draft OBJECTIVE": wk_draft_objective,
        "Draft SKILLS": wk_draft_skills,
        "Draft WORK EXPERIENCE": wk_draft_work,
        "Draft CERTIFICATIONS": wk_draft_certs,
        "Draft EDUCATION": wk_draft_edu,
    }
    merged_docs_for_packet = list(pathway_uploads or []) \
                           + list(prev_resume_files or []) \
                           + list(jd_files or []) \
                           + url_fetches
    packet_bytes = build_pathway_packet_docx({"name": Name}, trade, application_type, merged_docs_for_packet, reflections)

    safe_name = (Name or "Student").replace(" ","_")
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

    # Intake CSV (fixed column order)
    csv_fields = [
        "Name","City","State","Phone","Email",
        "Objective_Final",
        "Skills_Transferable","Skills_JobSpecific","Skills_SelfManagement",
        "Certifications",
        "Job1_Company","Job1_CityState","Job1_Dates","Job1_Title","Job1_Duties",
        "Job2_Company","Job2_CityState","Job2_Dates","Job2_Title","Job2_Duties",
        "Job3_Company","Job3_CityState","Job3_Dates","Job3_Title","Job3_Duties",
        "Edu1_School","Edu1_CityState","Edu1_Dates","Edu1_Credential",
        "Edu2_School","Edu2_CityState","Edu2_Dates","Edu2_Credential",
        "Other_Work","Volunteer","Pitch"
    ]
    buf=io.StringIO(); w=csv.writer(buf)
    w.writerow(csv_fields); w.writerow([form.get(k,"") for k in csv_fields])
    st.download_button("Download Intake CSV", data=buf.getvalue().encode("utf-8"),
                       file_name=f"{safe_name}_Workshop_Intake.csv", mime="text/csv",
                       use_container_width=True)
    st.success("Generated. Objective uses jobsite language; union/sub-trade labels sanitized.")
