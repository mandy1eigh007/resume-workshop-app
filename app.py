# app.py — Resume Workshop & Pathways (Seattle Tri-County)
# Streamlit single-file app. No APIs. Browser-only. Python 3.11.
# Fixes in this build:
# - Robust Autofill: pulls Name, Phone, Email, City/State, Company, Title, Dates, Bullets
# - Restored auto skills (cleaner) + Quick Add; pre-fills all 3 skill boxes
# - Objective: auto-generates on Autofill (crew-ready tone), student can edit
# - Removed obsolete "Step 9: Draft" section
# - Safer company parsing (won’t misread City/State as Company)

from __future__ import annotations
import io, os, re, csv, datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

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
    r"\bneca\b", r"\biboe?\b", r"\bopen[-\s]?shop\b"
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
# Role→construction seed bullets (quick bridge)
# ─────────────────────────────────────────────────────────
ROLE_TO_CONSTR_BULLETS = {
    "line cook": [
        "Worked safely around hot equipment and sharp tools",
        "Kept stations clean and organized; followed prep lists",
        "Handled deliveries and rotated stock; maintained clear walkways",
        "Stayed on pace to meet production during rushes",
    ],
    "retail": [
        "Kept inventory organized and aisles clear for safe flow",
        "Communicated with customers and team under time pressure",
        "Handled cash counts and hand-offs accurately",
    ],
    "warehouse": [
        "Staged materials, verified counts, and kept aisles clear",
        "Operated pallet jacks/hand trucks under PPE rules",
    ],
    "barista": [
        "Followed recipes and equipment safety steps precisely",
        "Kept stations stocked and organized during rushes",
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
    "military": [
        "Followed procedures, PPE, and safety briefings precisely",
        "Worked in teams with accountability and time standards",
    ],
}

# ─────────────────────────────────────────────────────────
# Parsing helpers (header/jobs/edu/certs)
# ─────────────────────────────────────────────────────────
def parse_header(text: str) -> Dict[str,str]:
    name = ""; email = ""; phone = ""; city = ""; state = ""
    # Collect email/phone anywhere
    m = EMAIL_RE.search(text or "");  email = m.group(0) if m else ""
    m = PHONE_RE.search(text or "");  phone = m.group(0) if m else ""
    # Try to find a top contact line and split it
    top = "\n".join([l.strip() for l in (text or "").splitlines()[:12] if l.strip()])
    # Replace separators with | for simpler splitting
    sep_line = re.sub(r"[•·–—\-•]+", "|", top)
    for candidate in sep_line.split("\n"):
        if "@" in candidate or re.search(r"\d{3}.*\d{4}", candidate):
            # candidate like: "Jane Doe | Seattle, WA | (206) 555-1234 | jane@x.com"
            parts = [p.strip() for p in candidate.split("|") if p.strip()]
            # Name is any early part with 2–4 words, few/no digits, not city/state
            for p in parts:
                if EMAIL_RE.search(p) or PHONE_RE.search(p): continue
                if CITY_STATE_RE.search(p): 
                    # store city/state
                    city, state = CITY_STATE_RE.search(p).groups()[0], CITY_STATE_RE.search(p).groups()[1].upper()
                    continue
                if sum(w[0:1].isupper() for w in p.split()) >= 2 and not re.search(r"\d", p) and len(p.split())<=4:
                    name = p; break
    # If name still empty, scan first lines for a clean 2–4-word title-cased line
    if not name:
        for l in [l.strip() for l in (text or "").splitlines()[:10]]:
            if EMAIL_RE.search(l) or PHONE_RE.search(l): continue
            if any(h in l.lower() for h in ["objective","summary","skills","experience","education"]): continue
            if 2 <= len(l.split()) <= 4 and all(w and w[0].isalpha() for w in l.split()):
                # heuristic: title case-ish
                tokens = l.split()
                if sum(t[:1].isupper() for t in tokens) >= 2:
                    name = l; break
    # City/State standalone search if not found above
    if not city or not state:
        m = CITY_STATE_RE.search(text or "")
        if m: city, state = m.group(1), m.group(2).upper()
    return {"Name": cap_first(name), "Email": clean_email(email), "Phone": clean_phone(phone),
            "City": cap_first(city), "State": (state or "").strip()}

def _safe_company_token(token: str) -> bool:
    # Reject tokens that are just a city/state
    if CITY_STATE_RE.fullmatch(token): return False
    if re.fullmatch(r"[A-Za-z .'\-&]{2,}", token): return True
    return False

def parse_jobs(text: str) -> List[Dict[str,Any]]:
    out=[]
    lines = [l.rstrip() for l in (text or "").splitlines()]
    i=0
    while i < len(lines) and len(out) < MAX_JOBS:
        head = lines[i].strip()
        if not head:
            i+=1; continue
        # Hard stop on obvious headers
        if re.match(r"^\s*(summary|objective|skills|certifications|education)\s*$", head, re.I):
            i+=1; continue

        # Look ahead for detail lines
        window = " ".join(lines[i:i+3])

        # Try pattern: "Role | Company | City, ST | Jan 2022 – May 2024"
        parts = re.split(r"\s*\|\s*|\s{2,}| — | – ", head)
        role=""; company=""; cityst=""; dates=""
        # Dates from head or next line(s)
        mdate = DATE_RANGE_RE.search(window)
        if mdate: dates = f"{mdate.group('start')} – {mdate.group('end')}"
        # City/ST from head or next lines
        mcity = CITY_STATE_RE.search(window)
        if mcity: cityst = f"{mcity.group(1)}, {mcity.group(2).upper()}"

        if len(parts) >= 2:
            # pick role then company (skip tokens that look like city/state)
            cand_role = parts[0].strip()
            cand_co   = parts[1].strip()
            if _safe_company_token(cand_co):
                role, company = cand_role, cand_co
            else:
                # try swapping if first is actually company and second is role
                if _safe_company_token(cand_role) and not _safe_company_token(cand_co):
                    company, role = cand_role, cand_co
                else:
                    role = cand_role
        else:
            role = head

        # Collect bullets beneath
        bullets=[]
        j=i+1
        while j < len(lines):
            ln = lines[j].strip()
            if not ln:
                if bullets: break
                j+=1; continue
            if re.match(r"^\s*(summary|objective|skills|certifications|education)\s*$", ln, re.I):
                break
            if re.match(r"^[•\-\u2022]\s+", ln) or lines[j].startswith("\t"):
                bullets.append(clean_bullet(re.sub(r"^[•\-\u2022\-]+\s*", "", ln)))
                if len(bullets) >= MAX_BULLETS_PER_JOB: break
            else:
                # stop at next likely job line
                if DATE_RANGE_RE.search(ln) or CITY_STATE_RE.search(ln):
                    pass
                elif len(ln.split()) <= 4 and bullets:
                    break
            j+=1

        # If company accidentally equals city/state, clear it
        if company and CITY_STATE_RE.fullmatch(company):
            company = ""

        if any([company, role, cityst, dates, bullets]):
            out.append({
                "company": cap_first(company),
                "role": cap_first(role),
                "city": cap_first(cityst),
                "start": parse_dates(dates)[0] if dates else "",
                "end": parse_dates(dates)[1] if dates else "",
                "bullets": bullets
            })
        i = max(j, i+1)
    return out[:MAX_JOBS]

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
                if re.search(r"\b(20\d{2}|19\d{2})\b", la): year = la.strip()
                if CITY_STATE_RE.search(la):
                    m = CITY_STATE_RE.search(la); details = f"{m.group(1)}, {m.group(2).upper()}"
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
    # catch explicit mentions in lines
    for line in (text or "").splitlines():
        if re.search(r"flagger", line, re.I): found.add("Flagger")
        if re.search(r"forklift", line, re.I): found.add("Forklift")
        if re.search(r"\bcpr\b", line, re.I): found.add("CPR")
    return sorted(found)

def parse_skills_from_text(text: str) -> Dict[str, List[str]]:
    # Mine suggestions from text and place into 3 categories
    base = suggest_transferable_skills_from_text(text)
    cat = categorize_skills(base)
    return cat

# ─────────────────────────────────────────────────────────
# Objective generator (crew-forward)
# ─────────────────────────────────────────────────────────
def build_objective(trade: str, pitch: str, skills_cat: Dict[str,List[str]]) -> str:
    top = (skills_cat.get("Job-Specific", []) + skills_cat.get("Transferable", []))[:3]
    picks = ", ".join(top) if top else "safety, teamwork, and reliable production"
    p = norm_ws(pitch or "")
    core = f"Ready to contribute in {trade}—bringing {picks}. "
    if p: core += f"{p} "
    core += "Show up, work safe, learn fast, and help the crew hit targets."
    core = strip_banned(core)[:MAX_SUMMARY_CHARS]
    return core

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

    # Objective = use provided, else generate
    if
