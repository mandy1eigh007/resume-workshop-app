# app.py — Resume Workshop & Pathways (Seattle Tri-County)
# Single-file Streamlit app. No APIs. Uses your DOCX template to build a resume.
# What this does:
#  - Step 0: Intake of prior resume, job descriptions (files/URLs), and pasted text
#  - Steps 1–9: Full "Student Packet: Resume Workshop" flow (exact workshop wording)
#  - Keyword + rule-based parsing from uploads/paste → prefill header, jobs, education, certs, skills
#  - Builds Resume (docxtpl), Cover Letter (python-docx), and Instructor Packet (full text of uploads)
#  - Neutral objective language (no union/non-union/inside-wire/low-voltage labels)

from __future__ import annotations
import io, os, re, csv, datetime, json
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple, Optional

import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
from docx import Document as DocxWriter
from docx.shared import Pt
from pypdf import PdfReader
import requests

# Optional fallback for text-heavy PDFs if installed (no error if missing)
try:
    from pdfminer.high_level import extract_text as pdfminer_extract_text  # type: ignore
except Exception:  # pragma: no cover
    pdfminer_extract_text = None

st.set_page_config(page_title="Resume Workshop & Pathways", layout="wide")

# ─────────────────────────────────────────────────────────
# Small helpers & cleanup
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
    r"\bNECA\b", r"\bIBOE?\b", r"\bopen[-\s]?shop\b"
]
BANNED_RE = re.compile("|".join(UNION_BANS), re.I)

FILLER_LEADS = re.compile(r"^\s*(responsible for|duties included|tasked with|in charge of)\s*:?\s*", re.I)
MULTISPACE = re.compile(r"\s+")
PHONE_DIGITS = re.compile(r"\D+")
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(\+?1[\s\-\.])?\(?\d{3}\)?[\s\-\.]?\d{3}[\s\-\.]?\d{4}")

CITY_STATE_RE = re.compile(r"\b([A-Za-z .'-]{2,}),\s*([A-Za-z]{2})\b")
DATE_RANGE_RE = re.compile(
    r"(?P<start>(?:\d{4}|\w{3,9}\s+\d{4}))\s*(?:–|-|to|until|through)\s*(?P<end>(?:Present|Current|\d{4}|\w{3,9}\s+\d{4}))",
    re.I
)

def strip_banned(text: str) -> str:
    return BANNED_RE.sub("", text or "").strip()

def norm_ws(s: str) -> str:
    s = (s or "").strip()
    return MULTISPACE.sub(" ", s)

def cap_first(s: str) -> str:
    s = norm_ws(s)
    return s[:1].upper()+s[1:] if s else s

def clean_bullet(s: str) -> str:
    s = norm_ws(s); s = FILLER_LEADS.sub("", s); s = re.sub(r"\.+$","", s)
    s = re.sub(r"^[•\-\u2022]+\s*", "", s)
    s = cap_first(s); words = s.split()
    return " ".join(words[:24]) if len(words)>24 else s

def clean_phone(s: str) -> str:
    digits = PHONE_DIGITS.sub("", s or "")
    if len(digits)==11 and digits.startswith("1"): digits = digits[1:]
    if len(digits)==10: return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return norm_ws(s or "")

def clean_email(s: str) -> str:
    return (s or "").strip().lower()

def split_list(raw: str) -> List[str]:
    if not raw: return []
    parts = [p.strip(" •\t") for p in re.split(r"[,\n;]+", raw)]
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
    # Try pypdf first (fast), then pdfminer if available (better layout text)
    try:
        reader = PdfReader(file); chunks=[]
        for p in reader.pages:
            txt = p.extract_text() or ""
            chunks.append(txt)
        text = "\n".join(chunks)
        if text.strip(): return text
    except Exception:
        pass
    # Fallback to pdfminer if installed
    if pdfminer_extract_text is not None:
        try:
            if hasattr(file, "getvalue"):
                data = file.getvalue()
                bio = io.BytesIO(data)
            else:
                file.seek(0)
                bio = file
            text = pdfminer_extract_text(bio) or ""
            return text
        except Exception:
            return ""
    return ""

def extract_text_from_docx(file) -> str:
    try:
        from docx import Document as DocxReader
        doc = DocxReader(file)
        parts=[]
        for p in doc.paragraphs:
            parts.append(p.text)
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
        super().__init__(data)
        self.name = name

def _drive_direct(url: str) -> str:
    # Convert Google Drive share links to direct-download
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
# Skills canon & maps
# ─────────────────────────────────────────────────────────
SKILL_CANON = [
    "Problem-solving","Critical thinking","Attention to detail","Time management",
    "Teamwork & collaboration","Adaptability & willingness to learn","Safety awareness",
    "Conflict resolution","Customer service","Leadership","Reading blueprints & specs",
    "Hand & power tools","Materials handling (wood/concrete/metal)","Operating machinery",
    "Trades math & measurement","Regulatory compliance","Physical stamina & dexterity"
]
# Which category each canonical skill usually belongs to
SKILL_CATEGORY_MAP = {
    "Problem-solving": "Transferable",
    "Critical thinking": "Transferable",
    "Attention to detail": "Transferable",
    "Time management": "Transferable",
    "Teamwork & collaboration": "Transferable",
    "Adaptability & willingness to learn": "Self-Management",
    "Safety awareness": "Job-Specific",
    "Conflict resolution": "Transferable",
    "Customer service": "Transferable",
    "Leadership": "Self-Management",
    "Reading blueprints & specs": "Job-Specific",
    "Hand & power tools": "Job-Specific",
    "Materials handling (wood/concrete/metal)": "Job-Specific",
    "Operating machinery": "Job-Specific",
    "Trades math & measurement": "Job-Specific",
    "Regulatory compliance": "Job-Specific",
    "Physical stamina & dexterity": "Self-Management",
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
    "rigging":"Operating machinery", "conduit":"Hand & power tools", "braz":"Hand & power tools",
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
        cat = SKILL_CATEGORY_MAP.get(lab, "Transferable")
        out[cat].append(lab)
    return out

# ─────────────────────────────────────────────────────────
# Trade taxonomy (for objective phrasing)
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
# JD → hint bullets by trade (heuristic)
# ─────────────────────────────────────────────────────────
TRADE_HINTS = {
    "High Voltage – Outside Lineman (NW Line JATC)": {
        "wire":"Assisted with wire pulls and site staging",
        "climb":"Maintained climbing readiness and proper PPE use",
        "bucket":"Supported bucket-truck operations per direction",
        "energized":"Followed safety protocols around energized equipment",
    },
    "Power Line Clearance Tree Trimmer (NW Line JATC)": {
        "rigging":"Supported ground rigging and controlled lower",
        "chainsaw":"Used chainsaw under supervision; maintained safety zone",
        "climb":"Followed signals; assisted crews and used PPE",
    },
    "Electrician – Inside (01)": {
        "conduit":"Assisted with conduit measurements and layout",
        "panel":"Maintained organized work area and accounted for hardware",
        "blueprint":"Read basic plan notes with guidance",
    },
    "Carpenter (General)": {
        "framing":"Assisted with layout and framing tasks; verified measurements",
        "forms":"Set and stripped simple forms with supervision",
    },
    "Plumber / Steamfitter / HVAC-R (UA 32 / UA 26)": {
        "brazing":"Assisted with torch/brazing under supervision",
        "hvac":"Handled materials and maintained clean, safe work zones",
    },
}

# Non-construction roles → seed bullets that translate well to construction
ROLE_TO_CONSTR_BULLETS = {
    "line cook": [
        "Worked safely around hot equipment and sharp tools",
        "Followed prep lists and maintained clean, organized stations",
        "Handled supply deliveries and rotated stock (first-in, first-out)",
        "Stayed on pace to meet real-time production demands"
    ],
    "cook": [
        "Followed safety and sanitation procedures under time pressure",
        "Prepared materials and set up stations to production standards",
    ],
    "retail": [
        "Worked customer lines with calm, clear communication",
        "Stocked materials and kept aisles hazard-free",
        "Handled cash, counts, and shift hand-offs reliably"
    ],
    "warehouse": [
        "Moved materials, staged orders, and verified counts",
        "Operated basic equipment under supervision and followed PPE rules",
    ],
    "barista": [
        "Followed recipes and equipment safety steps precisely",
        "Kept work area clean, stocked, and organized during rushes",
    ],
    "server": [
        "Communicated clearly and managed multiple tasks with deadlines",
        "Maintained a clean, safe work area and supported team flow",
    ],
    "janitor": [
        "Used chemicals and equipment per safety guidance",
        "Completed checklists and documented work reliably",
    ],
    "custodian": [
        "Set up spaces, moved materials, and followed safety procedures",
        "Performed preventive tasks on routine schedules",
    ],
    "military": [
        "Followed procedures, PPE, and safety briefings precisely",
        "Worked in teams with accountability and time standards",
    ],
}

def suggest_bullets(text: str, trade: str, role_hint: str = "") -> List[str]:
    low = (text or "").lower()
    # Trade hints based on JD text
    hints = TRADE_HINTS.get(trade, {})
    out=[]
    for kw, stub in hints.items():
        if kw in low: out.append(stub)
    # Role-to-construction seed
    rh = role_hint.lower().strip()
    for key, seeds in ROLE_TO_CONSTR_BULLETS.items():
        if key in rh and seeds:
            out.extend(seeds)
            break
    if not out and low.strip():
        out = [
            "Maintained clean work zones and followed safety procedures",
            "Handled materials and supported crew tasks as directed",
        ]
    seen=set(); dedup=[]
    for b in out:
        k=b.lower()
        if k in seen: continue
        seen.add(k); dedup.append(clean_bullet(b))
    return dedup[:MAX_BULLETS_PER_JOB]

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
# Text parsing → Autofill profile (header/jobs/edu/certs/skills)
# ─────────────────────────────────────────────────────────
CERT_KEYWORDS = [
    "osha", "forklift", "flagger", "cpr", "first aid", "hazwoper",
    "twic", "nccer", "confined space", "ppe", "aerial lift", "traffic control"
]
EDU_CUES = ["high school", "diploma", "ged", "college", "university", "degree", "certificate", "program"]
JOB_CUES = ["company", "employer", "experience", "work history", "position", "title"]

def parse_header(text: str) -> Dict[str,str]:
    name = ""
    email = ""
    phone = ""
    city = ""
    state = ""
    # Email / phone
    m = EMAIL_RE.search(text or "")
    if m: email = m.group(0)
    m = PHONE_RE.search(text or "")
    if m: phone = m.group(0)
    # City/State (grab the first plausible)
    m = CITY_STATE_RE.search(text or "")
    if m:
        city, state = m.group(1), m.group(2).upper()
    # Naive name heuristic: first non-empty line that isn't email/phone and has 2–4 words
    lines = [l.strip() for l in (text or "").splitlines()]
    for l in lines[:10]:
        if EMAIL_RE.search(l) or PHONE_RE.search(l): continue
        if len(l.split()) in (2,3,4) and len(l) <= 60 and not l.lower().startswith(("objective","summary","skills")):
            name = l
            break
    return {"Name": cap_first(name), "Email": clean_email(email), "Phone": clean_phone(phone),
            "City": cap_first(city), "State": (state or "").strip()}

def parse_jobs(text: str) -> List[Job]:
    out=[]
    lines = [l.strip() for l in (text or "").splitlines()]
    # Group into blocks by blank lines
    blocks=[]; cur=[]
    for l in lines:
        if not l.strip():
            if cur: blocks.append("\n".join(cur)); cur=[]
        else:
            cur.append(l)
    if cur: blocks.append("\n".join(cur))
    # Heuristic: a block with a role/company line + some bullets or sentences
    for b in blocks:
        if len(out) >= MAX_JOBS: break
        role=""; company=""; cityst=""; dates=""
        # Find date range
        m = DATE_RANGE_RE.search(b)
        if m:
            dates = f"{m.group('start')} – {m.group('end')}"
        # Find company/role cues
        head = b.splitlines()[0]
        # Patterns like "Line Cook — Denny's, Tacoma, WA"
        hr = re.split(r"[–—\-|•]+", head)
        if len(hr)>=2:
            role = hr[0].strip()
            company = hr[1].strip()
        else:
            # fallback
            role = head.strip()
        m2 = CITY_STATE_RE.search(b)
        if m2:
            cityst = f"{m2.group(1)}, {m2.group(2).upper()}"
        # Bullets: collect first 4 non-empty subsequent lines
        bullets=[]
        for l in b.splitlines()[1:]:
            l2 = l.strip()
            if not l2: continue
            if len(l2) < 3: continue
            if EMAIL_RE.search(l2) or PHONE_RE.search(l2): continue
            if l2.lower().startswith(("responsibilities", "summary", "skills", "education")): break
            bullets.append(clean_bullet(l2))
            if len(bullets) >= MAX_BULLETS_PER_JOB: break
        # Some blocks are education/certs; filter out obvious non-job cues
        if not any(x in b.lower() for x in ["experience","company","employer","position","title"]) and len(bullets) < 1:
            continue
        j = Job(company=cap_first(company), role=cap_first(role), city=cap_first(cityst), start="", end="", bullets=bullets)
        if dates:
            s,e = parse_dates(dates); j.start, j.end = s, e
        # Add role→construction bullets if relevant
        j.bullets = suggest_bullets(text, trade="", role_hint=j.role)
        out.append(j)
    return out[:MAX_JOBS]

def parse_education(text: str) -> List[School]:
    out=[]
    lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
    for i,l in enumerate(lines):
        low = l.lower()
        if any(cue in low for cue in EDU_CUES):
            # The line + next line(s) often hold school, credential, year
            school = cap_first(l)
            cred = ""
            year = ""
            details = ""
            lookahead = lines[i+1:i+4]
            for la in lookahead:
                if re.search(r"\b(20\d{2}|19\d{2})\b", la): year = la
                if any(x in la.lower() for x in ["diploma","degree","certificate","ged","program"]): cred = cap_first(la)
                if CITY_STATE_RE.search(la): details = cap_first(la)
            out.append(School(school=school, credential=cred, year=year, details=details))
            if len(out) >= MAX_SCHOOLS: break
    return out

def parse_certs(text: str) -> List[str]:
    low = (text or "").lower()
    found=set()
    for k in CERT_KEYWORDS:
        if k in low:
            # Normalize label
            if k=="osha":
                found.add("OSHA-10")
            elif k=="first aid":
                found.add("First Aid")
            elif k=="aerial lift":
                found.add("Aerial Lift")
            elif k=="twic":
                found.add("TWIC")
            else:
                found.add(k.title())
    return sorted(found)

def parse_skills_from_text(text: str) -> Dict[str, List[str]]:
    # Use keyword scanning, then categorize
    base = suggest_transferable_skills_from_text(text)
    cat = categorize_skills(base)
    return cat

def autofill_from_text(text: str) -> Dict[str, Any]:
    header = parse_header(text)
    jobs = parse_jobs(text)
    edus = parse_education(text)
    certs = parse_certs(text)
    skills_cat = parse_skills_from_text(text)
    return {
        "header": header,
        "jobs": [asdict(j) for j in jobs],
        "schools": [asdict(s) for s in edus],
        "certs": certs,
        "skills_cat": skills_cat
    }

# ─────────────────────────────────────────────────────────
# Resume context + rendering
# ─────────────────────────────────────────────────────────
def build_resume_context(form: Dict[str,Any], trade_label: str) -> Dict[str,Any]:
    Name=cap_first(form["Name"]); City=cap_first(form["City"]); State=(form["State"] or "").strip().upper()
    phone=clean_phone(form["Phone"]); email=clean_email(form["Email"])
    summary = strip_banned(norm_ws(form["Objective_Final"]))[:MAX_SUMMARY_CHARS]

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
    if not raw: return []
    parts = [p.strip(" •\t") for p in re.split(r"[,\n;•]+", raw)]
    return [p for p in parts if p]

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

    # Include Workshop reflections verbatim (no summarizing)
    doc.add_heading("Workshop Reflections", level=1)
    for k,v in reflections.items():
        doc.add_paragraph(k+":")
        for line in (v or "").splitlines():
            doc.add_paragraph(line)

    # Include the full text of uploaded/imported docs
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
# Sidebar — template & optional instructor docs
# ─────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Templates & Docs")

    tpl_bytes=None
    if os.path.exists("resume_app_template.docx"):
        with open("resume_app_template.docx","rb") as f: tpl_bytes=f.read()
    upl_tpl = st.file_uploader("Upload RESUME DOCX template (optional)", type=["docx"])
    if upl_tpl is not None: tpl_bytes = upl_tpl.read()

    st.markdown("---")
    st.caption("Upload additional instructor/pathway docs (PDF/DOCX/TXT). These get embedded (full text) in the Instructor Packet.")
    pathway_uploads = st.file_uploader("Upload pathway documents", type=["pdf","docx","txt"], accept_multiple_files=True)

# ─────────────────────────────────────────────────────────
# Main — Step 0: Bring Your Stuff (uploads/URLs/paste)
# ─────────────────────────────────────────────────────────
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

st.markdown("**Or import by URL (public links only: Google Drive Share or public GCS):**")
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
paste_box = st.text_area("Paste any job description text here", "")

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
    preview = combined_text[:800].replace("\n"," ")
    st.info(f"Preview: {preview}…")

# ─────────────────────────────────────────────────────────
# Autofill button — writes to session_state for stable prefill
# ─────────────────────────────────────────────────────────
if "autofilled" not in st.session_state:
    st.session_state["autofilled"] = False

def set_if_empty(key: str, val: str):
    if key not in st.session_state or not str(st.session_state.get(key,"")).strip():
        st.session_state[key] = val

if st.button("Auto-Fill from Uploaded Text", type="secondary", disabled=(not combined_text)):
    prof = autofill_from_text(combined_text)
    hdr = prof.get("header", {})
    set_if_empty("Name", hdr.get("Name",""))
    set_if_empty("Phone", hdr.get("Phone",""))
    set_if_empty("Email", hdr.get("Email",""))
    set_if_empty("City", hdr.get("City",""))
    set_if_empty("State", hdr.get("State",""))

    # Jobs
    jobs = prof.get("jobs", [])
    for idx in range(1, MAX_JOBS+1):
        j = jobs[idx-1] if idx-1 < len(jobs) else {}
        set_if_empty(f"Job{idx}_Company", j.get("company",""))
        set_if_empty(f"Job{idx}_CityState", j.get("city",""))
        dates = " – ".join([x for x in [j.get("start",""), j.get("end","")] if x]).strip(" –")
        set_if_empty(f"Job{idx}_Dates", dates)
        set_if_empty(f"Job{idx}_Title", j.get("role",""))
        set_if_empty(f"Job{idx}_Duties", "\n".join(j.get("bullets",[]) or []))

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
    st.success("Autofill complete. You can edit any field below.")

# ─────────────────────────────────────────────────────────
# Step 1: What is the Difference… (+ reflection #1)
# ─────────────────────────────────────────────────────────
st.subheader("What is the Difference Between a Construction Facing Resume and a Traditional Resume?")
st.markdown("""
**Construction Facing Resume**  
• **Purpose:** Designed specifically for getting into a trade, apprenticeship, or construction company.  
• **Focus:**  
  - Highlights hands-on skills (tools, materials).  
  - Includes certifications like OSHA-10, Forklift, Flagger, CPR.  
  - Shows physical abilities (lifting, standing, operating equipment).  
  - Lists projects/build experiences (tiny houses, ACE stations, shop builds).  
  - Speaks the language of trades (framing, layout, demo, site prep).  
• **Experience:** Translate non-construction jobs to construction skills (teamwork, time management, safety).

**Traditional Resume**  
• **Purpose:** Office/retail/service roles.  
• **Focus:** Education and past jobs first; general soft skills; rarely lists certs/physical abilities/build projects.

**Key Takeaway:** When applying to construction, **show what you can build, operate, or handle on a site**. Prove safety and apprentice-style work habits.
""")
wk_q1 = st.text_area("Write down three things you will include on your construction facing resume that you would not include on a traditional resume:", height=120)

# ─────────────────────────────────────────────────────────
# Step 2: Why a Resume Matters (+ 10-second pitch)
# ─────────────────────────────────────────────────────────
st.subheader("1. Why a Resume Matters in Construction")
st.markdown("A resume is your first impression for unions, contractors, and apprenticeships. It shows you are ready to work safely, use tools, and be a dependable team member.")
wk_pitch = st.text_area("Write what you want an employer to know about you in 10 seconds:", height=120)

# ─────────────────────────────────────────────────────────
# Step 3: Header (Contact Information)
# ─────────────────────────────────────────────────────────
st.subheader("2. Your Header (Contact Information)")
c1, c2 = st.columns(2)
with c1:
    Name = st.text_input("Name", key="Name")
    Phone = st.text_input("Phone", key="Phone")
    Email = st.text_input("Email", key="Email")
with c2:
    City = st.text_input("City", key="City")
    State = st.text_input("State (2-letter)", key="State")

# ─────────────────────────────────────────────────────────
# Step 4: Writing Your Objective
# ─────────────────────────────────────────────────────────
st.subheader("3. Writing Your Objective")
c3a, c3b = st.columns(2)
with c3a:
    application_type = st.radio("Are you seeking a job or apprenticeship?", ["Apprenticeship","Job"], horizontal=True, index=0)
    trade = st.selectbox("What trade are you aiming for?", TRADE_TAXONOMY, index=TRADE_TAXONOMY.index("Electrician – Inside (01)"))
with c3b:
    wk_obj_seek = st.text_input("What job/apprenticeship are you seeking?", f"{trade}")
    wk_obj_quality = st.text_input("One skill or quality to highlight:", "safety mindset")

default_role = f"{trade} pre-apprentice" if application_type=="Apprenticeship" else f"Entry-level {trade}"
wk_objective_final = st.text_area("Write your final objective here (1–2 sentences):",
    f"I’m seeking hands-on experience as an entry-level contributor in {trade}, bringing a {wk_obj_quality}, reliability, and readiness to learn.")

# ─────────────────────────────────────────────────────────
# Step 5: Your Skills Section (auto-categorized + editable)
# ─────────────────────────────────────────────────────────
st.subheader("4. Your Skills Section")
st.caption("We auto-categorize from your uploads. Edit or add anything. Transferable = universal work skills. Job-Specific = site/tool/safety. Self-Management = reliability, leadership, stamina.")
auto_suggested = suggest_transferable_skills_from_text(combined_text)
quick_transfer = st.multiselect("Quick add transferable skills (suggested from your uploads):",
                                SKILL_CANON, default=auto_suggested)
Skills_Transferable = st.text_area("Transferable Skills (comma/newline):", st.session_state.get("Skills_Transferable",""))
Skills_JobSpecific  = st.text_area("Job-Specific Skills (comma/newline):", st.session_state.get("Skills_JobSpecific",""))
Skills_SelfManagement = st.text_area("Self-Management Skills (comma/newline):", st.session_state.get("Skills_SelfManagement",""))

# ─────────────────────────────────────────────────────────
# Step 6: Work Experience — Jobs 1–3 (prefilled if autofill was used)
# ─────────────────────────────────────────────────────────
st.subheader("5. Work Experience – Job 1")
seed1 = "\n".join(suggest_bullets(combined_text, trade, role_hint=st.session_state.get("Job1_Title","")))
J1c = st.text_input("Job 1 – Company:", key="Job1_Company")
J1cs = st.text_input("Job 1 – City/State:", key="Job1_CityState")
J1d = st.text_input("Job 1 – Dates (e.g., 2023-06 – Present):", key="Job1_Dates")
J1t = st.text_input("Job 1 – Title:", key="Job1_Title")
J1du = st.text_area("Job 1 – Duties/Accomplishments (1–4 bullets):", key="Job1_Duties", value=st.session_state.get("Job1_Duties", seed1), height=120)

st.subheader("5. Work Experience – Job 2")
J2c = st.text_input("Job 2 – Company:", key="Job2_Company")
J2cs = st.text_input("Job 2 – City/State:", key="Job2_CityState")
J2d = st.text_input("Job 2 – Dates:", key="Job2_Dates")
J2t = st.text_input("Job 2 – Title:", key="Job2_Title")
J2du = st.text_area("Job 2 – Duties/Accomplishments (1–4 bullets):", key="Job2_Duties", height=120)

st.subheader("5. Work Experience – Job 3")
J3c = st.text_input("Job 3 – Company:", key="Job3_Company")
J3cs = st.text_input("Job 3 – City/State:", key="Job3_CityState")
J3d = st.text_input("Job 3 – Dates:", key="Job3_Dates")
J3t = st.text_input("Job 3 – Title:", key="Job3_Title")
J3du = st.text_area("Job 3 – Duties/Accomplishments (1–4 bullets):", key="Job3_Duties", height=120)

# ─────────────────────────────────────────────────────────
# Step 7: Certifications
# ─────────────────────────────────────────────────────────
st.subheader("6. Certifications")
Certifications = st.text_area("List any certifications (comma/newline). If none, write 'None yet' or what you plan to get.",
                              st.session_state.get("Certifications","OSHA-10, Flagger (WA), Forklift operator (employer evaluation on hire)"))

# ─────────────────────────────────────────────────────────
# Step 8: Education (two blocks)
# ─────────────────────────────────────────────────────────
st.subheader("7. Education")
st.markdown("List in reverse order with city/state, dates, and certificate/diploma.")
E1s = st.text_input("School/Program 1:", key="Edu1_School"); E1cs = st.text_input("City/State 1:", key="Edu1_CityState")
E1d = st.text_input("Dates 1:", key="Edu1_Dates"); E1c = st.text_input("Certificate/Diploma 1:", key="Edu1_Credential")
E2s = st.text_input("School/Program 2:", key="Edu2_School"); E2cs = st.text_input("City/State 2:", key="Edu2_CityState")
E2d = st.text_input("Dates 2:", key="Edu2_Dates"); E2c = st.text_input("Certificate/Diploma 2:", key="Edu2_Credential")

# ─────────────────────────────────────────────────────────
# Step 9: Optional Sections
# ─────────────────────────────────────────────────────────
st.subheader("8. Optional Sections")
Other_Work = st.text_area("Other Work Experience (optional):", st.session_state.get("Other_Work",""))
Volunteer  = st.text_area("Volunteer Experience (optional):", st.session_state.get("Volunteer",""))

# ─────────────────────────────────────────────────────────
# Step 10: Build Your Resume (Draft reflection area)
# ─────────────────────────────────────────────────────────
st.subheader("9. Build Your Resume (Draft)")
wk_draft_header = st.text_area("HEADER (draft, optional):","", height=80)
wk_draft_objective = st.text_area("OBJECTIVE (draft, optional):","", height=80)
wk_draft_skills = st.text_area("SKILLS (draft, optional):","", height=120)
wk_draft_work = st.text_area("WORK EXPERIENCE (draft, optional):","", height=140)
wk_draft_certs = st.text_area("CERTIFICATIONS (draft, optional):","", height=80)
wk_draft_edu = st.text_area("EDUCATION (draft, optional):","", height=80)

# ─────────────────────────────────────────────────────────
# Final Checklist (for display only)
# ─────────────────────────────────────────────────────────
st.markdown("**Final Checklist**")
st.markdown("""
- [ ] One page only  
- [ ] Professional font (10–12 pt)  
- [ ] Saved as PDF  
- [ ] Reviewed by peer  
- [ ] Reviewed by instructor  
""")

# ─────────────────────────────────────────────────────────
# Cover Letter minimal fields (generated neutral)
# ─────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Cover Letter (optional)")
CL_Company = st.text_input("Company/Employer (for the letter):","")
CL_Role    = st.text_input("Role Title (for the letter):", f"{default_role}")
CL_Location= st.text_input("Company Location (City, State):","")
CL_Highlights = st.text_area("Optional: bullet highlights (comma/newline/• allowed):","Reliable • Safety-focused • Coachable")

# ─────────────────────────────────────────────────────────
# Submit + Build
# ─────────────────────────────────────────────────────────
if st.button("Generate Resume + Cover Letter + Instructor Packet", type="primary"):
    problems=[]
    if not Name.strip(): problems.append("Name is required.")
    if not (Phone.strip() or Email.strip()): problems.append("At least one contact method (Phone or Email) is required.")
    if wk_objective_final.strip()=="": problems.append("Objective is required.")
    if problems:
        st.error(" | ".join(problems))
        st.stop()

    # Merge quick-add transferable skills into the field
    skills_transfer_final = st.session_state.get("Skills_Transferable","")
    if quick_transfer:
        skills_transfer_final = (skills_transfer_final + (", " if skills_transfer_final.strip() else "") + ", ".join(quick_transfer))

    # Build intake form dict
    form = {
        "Name": Name, "City": City, "State": State,
        "Phone": Phone, "Email": Email,
        "Objective_Seeking": wk_obj_seek, "Objective_Quality": wk_obj_quality,
        "Objective_Final": wk_objective_final,
        "Skills_Transferable": skills_transfer_final,
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

    # Resume via template
    if not tpl_bytes:
        st.error("Template not found. Put resume_app_template.docx in the repo or upload it in the sidebar.")
        st.stop()
    try:
        resume_ctx = build_resume_context(form, trade)
        resume_bytes = render_docx_with_template(tpl_bytes, resume_ctx)
    except Exception as e:
        st.error(f"Resume template rendering failed: {e}")
        st.stop()

    # Cover letter
    cover_bytes = build_cover_letter_docx({
        "name": Name, "city": City, "state": State, "phone": clean_phone(Phone), "email": clean_email(Email),
        "company": CL_Company, "role": CL_Role, "location": CL_Location,
        "trade_label": trade, "strength": CL_Highlights,
        "application_type": application_type,
    })

    # Build Instructor Packet (Workshop reflections + full text of docs)
    reflections = {
        "Three construction-resume items (vs traditional)": wk_q1,
        "10-second pitch": wk_pitch,
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

    # Intake CSV snapshot — fixed column order
    csv_fields = [
        "Name","City","State","Phone","Email",
        "Objective_Seeking","Objective_Quality","Objective_Final",
        "Skills_Transferable","Skills_JobSpecific","Skills_SelfManagement",
        "Certifications",
        "Job1_Company","Job1_CityState","Job1_Dates","Job1_Title","Job1_Duties",
        "Job2_Company","Job2_CityState","Job2_Dates","Job2_Title","Job2_Duties",
        "Job3_Company","Job3_CityState","Job3_Dates","Job3_Title","Job3_Duties",
        "Edu1_School","Edu1_CityState","Edu1_Dates","Edu1_Credential",
        "Edu2_School","Edu2_CityState","Edu2_Dates","Edu2_Credential",
        "Other_Work","Volunteer"
    ]
    buf=io.StringIO(); w=csv.writer(buf)
    w.writerow(csv_fields); w.writerow([form.get(k,"") for k in csv_fields])
    st.download_button("Download Intake CSV", data=buf.getvalue().encode("utf-8"),
                       file_name=f"{safe_name}_Workshop_Intake.csv", mime="text/csv",
                       use_container_width=True)
    st.success("Generated. Objective/letter sanitized to avoid union/non-union or sub-trade labels.")

