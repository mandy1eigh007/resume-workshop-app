# app.py — Resume Workshop (Seattle Tri-County)
# Streamlit single-file app. No APIs. Browser-only. Python 3.11.

from __future__ import annotations
import io, os, re, csv, hashlib, datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple

import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
from docx import Document as DocxWriter
from docx.shared import Pt
from pypdf import PdfReader
import requests

# Optional PDF fallback
try:
    from pdfminer_high_level import extract_text as pdfminer_extract_text  # alt import name in some envs
except Exception:
    try:
        from pdfminer.high_level import extract_text as pdfminer_extract_text
    except Exception:
        pdfminer_extract_text = None

st.set_page_config(page_title="Resume Workshop", layout="wide")

# ─────────────────────────────────────────────────────────
# Constants / regex
# ─────────────────────────────────────────────────────────
MAX_SUMMARY_CHARS = 450
MAX_SKILLS = 12
MAX_CERTS = 12
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
LABEL_RE = re.compile(r"^\s*(name|phone|email|city|state)\s*:\s*(.+)$", re.I)

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
# Cached extraction & URL fetch
# ─────────────────────────────────────────────────────────
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

def _hash_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

@st.cache_data(show_spinner=False)
def _cached_extract_text(name: str, file_hash: str, kind: str, raw: bytes) -> str:
    if kind == "pdf":
        try:
            reader = PdfReader(io.BytesIO(raw)); chunks=[]
            for p in reader.pages:
                txt = p.extract_text() or ""
                chunks.append(txt)
            text = "\n".join(chunks)
            if text.strip(): return text
        except Exception:
            pass
        if pdfminer_extract_text is not None:
            try:
                return pdfminer_extract_text(io.BytesIO(raw)) or ""
            except Exception:
                return ""
        return ""
    elif kind == "docx":
        try:
            from docx import Document as DocxReader
            doc = DocxReader(io.BytesIO(raw))
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception:
            return ""
    else:
        try:
            return raw.decode("utf-8", errors="ignore")
        except Exception:
            return ""

def extract_text_generic(upload) -> str:
    name = getattr(upload, "name", "") or "file"
    lname = name.lower()
    if hasattr(upload, "getvalue"):
        raw = upload.getvalue()
    else:
        raw = upload.read()
    kind = "txt"
    if lname.endswith(".pdf"): kind = "pdf"
    elif lname.endswith(".docx"): kind = "docx"
    h = _hash_bytes(raw)
    return _cached_extract_text(name, h, kind, raw)

# ─────────────────────────────────────────────────────────
# Skills canon & lightweight mining
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

# ─────────────────────────────────────────────────────────
# Trade taxonomy (for objective templating)
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
# Role detection + role bullets from uploaded "Job History" + fallback
# ─────────────────────────────────────────────────────────
ROLE_FALLBACK = {
    "line cook": [
        "Worked safely around hot equipment and sharp tools",
        "Kept stations clean and organized; followed prep lists",
        "Handled deliveries and rotated stock; maintained clear walkways",
        "Stayed on pace to meet production during rushes",
    ],
    "server": [
        "Managed multiple tasks with tight timing while supporting team flow",
        "Maintained a clean, safe work area under pressure",
        "Communicated clearly with team and customers",
    ],
    "retail": [
        "Kept inventory organized and aisles clear for safe flow",
        "Took accurate counts and completed hand-offs",
        "Supported customers and team under time pressure",
    ],
    "warehouse": [
        "Staged materials and verified counts",
        "Operated pallet jacks/hand trucks with PPE",
        "Kept aisles clear and work zones safe",
    ],
    "barista": [
        "Followed recipes and equipment safety steps precisely",
        "Kept stations stocked and organized during rushes",
    ],
    "janitor": [
        "Used chemicals/equipment per safety guidance; kept areas hazard-free",
        "Completed checklists and documented work reliably",
    ],
    "custodian": [
        "Set up spaces, moved materials, and followed safety procedures",
    ],
    "mover": [
        "Lifted and carried materials with safe techniques",
        "Coordinated team moves and protected finished surfaces",
    ],
    "driver": [
        "Loaded/unloaded and secured materials; verified counts",
        "Practiced safe backing/spotting on tight sites",
    ],
    "landscaper": [
        "Operated hand tools safely; maintained clean work zones",
        "Staged materials and debris; followed site directions",
    ],
    "security": [
        "Monitored hazards and enforced basic safety practices",
        "Communicated clearly with teams and visitors on-site",
    ],
    "housekeeper": [
        "Kept work areas hazard-free; followed chemical/PPE guidelines",
        "Worked on schedule with checklists and quality checks",
    ],
}
ROLE_NAME_PATTERNS = {
    "line cook": re.compile(r"\b(line\s*cook|cook)\b", re.I),
    "server": re.compile(r"\b(server|waiter|waitress)\b", re.I),
    "retail": re.compile(r"\b(retail|cashier|sales associate)\b", re.I),
    "warehouse": re.compile(r"\b(warehouse|picker|packer|order selector)\b", re.I),
    "barista": re.compile(r"\b(barista)\b", re.I),
    "janitor": re.compile(r"\b(janitor|janitorial)\b", re.I),
    "custodian": re.compile(r"\b(custodian|custodial)\b", re.I),
    "mover": re.compile(r"\b(mover|moving)\b", re.I),
    "driver": re.compile(r"\b(driver|delivery|courier)\b", re.I),
    "landscaper": re.compile(r"\b(landscap(er|ing)|grounds)\b", re.I),
    "security": re.compile(r"\b(security|guard)\b", re.I),
    "housekeeper": re.compile(r"\b(housekeeper|housekeeping)\b", re.I),
}

def detect_roles(text: str) -> List[str]:
    roles=set()
    for label, rx in ROLE_NAME_PATTERNS.items():
        if rx.search(text or ""):
            roles.add(label)
    return sorted(roles)

def bullets_from_job_history_docs(files: List[Any]) -> Dict[str, List[str]]:
    """
    Scrape bullets from uploaded DOCX that look like a job-history dictionary.
    We look for headings equal to role labels and capture bullet-like paragraphs until the next heading.
    """
    role_map: Dict[str, List[str]] = {}
    for f in files or []:
        nm = getattr(f, "name", "").lower()
        if not (nm.endswith(".docx") and ("job" in nm or "history" in nm or "duties" in nm)):
            continue
        try:
            raw = f.getvalue() if hasattr(f, "getvalue") else f.read()
            doc = DocxWriter(io.BytesIO(raw))
            paras = [p.text.strip() for p in doc.paragraphs]
            current_role = None
            for t in paras:
                if not t: 
                    continue
                for label in ROLE_NAME_PATTERNS.keys():
                    if re.fullmatch(rf"\s*{label}\s*", t, re.I):
                        current_role = label
                        role_map.setdefault(current_role, [])
                        break
                else:
                    # bullet or short duty line
                    if current_role:
                        if re.match(r"^[•\-\u2022]\s+", t) or (len(t.split()) <= 20 and t.endswith(".")):
                            role_map[current_role].append(clean_bullet(re.sub(r"^[•\-\u2022-]+\s*", "", t)))
        except Exception:
            continue
    # Merge with fallback
    for k, arr in ROLE_FALLBACK.items():
        role_map.setdefault(k, arr)
    # Dedup + trim
    for k in list(role_map.keys()):
        seen=set(); cleaned=[]
        for b in role_map[k]:
            b = clean_bullet(b)
            if not b: continue
            low=b.lower()
            if low in seen: continue
            seen.add(low); cleaned.append(b)
        role_map[k] = cleaned[:12]
    return role_map

# ─────────────────────────────────────────────────────────
# Parsing helpers (header/education)
# ─────────────────────────────────────────────────────────
def parse_header(text: str) -> Dict[str,str]:
    name = ""; email = ""; phone = ""; city = ""; state = ""
    for l in (text or "").splitlines()[:80]:
        m = LABEL_RE.match(l)
        if not m: continue
        key, val = m.group(1).lower(), m.group(2).strip()
        if key=="name" and not name: name = val
        elif key=="phone" and not phone: phone = val
        elif key=="email" and not email: email = val
        elif key=="city" and not city: city = val
        elif key=="state" and not state: state = val
    if not email:
        m = EMAIL_RE.search(text or "");  email = m.group(0) if m else ""
    if not phone:
        m = PHONE_RE.search(text or "");  phone = m.group(0) if m else ""
    if not (city and state):
        mcs = CITY_STATE_RE.search(text or "")
        if mcs:
            city, state = mcs.group(1), mcs.group(2).upper()
    if not name:
        top = "\n".join([l.strip() for l in (text or "").splitlines()[:15] if l.strip()])
        sep_line = re.sub(r"[•·–—\-•]+", "|", top)
        for cand in sep_line.split("\n"):
            if "@" in cand or re.search(r"\d{3}.*\d{4}", cand):
                parts = [p.strip() for p in cand.split("|") if p.strip()]
                for p in parts:
                    if EMAIL_RE.search(p) or PHONE_RE.search(p): continue
                    if CITY_STATE_RE.search(p): continue
                    if 2 <= len(p.split()) <= 4 and not re.search(r"\d", p):
                        caps = sum(w[:1].isupper() for w in p.split())
                        if caps >= 2:
                            name = p
                            break
                if name: break
    return {"Name": cap_first(name), "Email": clean_email(email), "Phone": clean_phone(phone),
            "City": cap_first(city), "State": (state or "").strip().upper()}

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

# ───────────────── Objective suggestions (not auto-fill) ─────────────────
def objective_suggestions(app_type: str, trade: str) -> List[str]:
    trade = strip_banned(trade)
    if app_type == "Apprenticeship":
        return [
            f"Seeking entry into an {trade} apprenticeship—ready to show up, work safe, and learn fast.",
            f"Applying to begin {trade} apprenticeship training; focused on safety, pace, and reliability.",
            f"Motivated to start {trade} apprenticeship; bring teamwork, tool basics, and coachability."
        ]
    else:
        return [
            f"Seeking full-time work in {trade}-related crews; ready to contribute on day one.",
            f"Aiming for entry-level role supporting {trade} scope—safety-first and production-minded.",
            f"Looking for hands-on job in {trade}; dependable, on time, and ready to learn."
        ]

# ─────────────────────────────────────────────────────────
# Use Transferable Skills doc + Roadmaps doc for suggestions
# ─────────────────────────────────────────────────────────
def parse_transferable_skills_doc(files: List[Any]) -> List[str]:
    out=[]
    for f in files or []:
        nm = getattr(f,"name","").lower()
        if nm.endswith(".docx") and "transferable" in nm:
            try:
                raw = f.getvalue() if hasattr(f,"getvalue") else f.read()
                doc = DocxWriter(io.BytesIO(raw))
                for p in doc.paragraphs:
                    t = p.text.strip()
                    if not t: continue
                    if len(t.split()) <= 7 or t.startswith(("•","-","—")):
                        out.append(clean_bullet(re.sub(r"^[•\-\u2022]+\s*","",t)))
            except Exception:
                pass
    # normalize + dedup
    seen=set(); final=[]
    for s in out:
        lab = normalize_skill_label(s)
        if lab and lab.lower() not in seen:
            seen.add(lab.lower()); final.append(lab)
    return final[:40]

def parse_roadmaps_doc(files: List[Any], trade_label: str) -> Dict[str, List[str]]:
    """
    Extracts suggested certs/steps for a given trade label from a Roadmaps DOCX.
    Returns {"certs":[...], "steps":[...]} when found, else empty lists.
    """
    result = {"certs": [], "steps": []}
    for f in files or []:
        nm = getattr(f,"name","").lower()
        if nm.endswith(".docx") and ("roadmap" in nm or "apprenticeship" in nm):
            try:
                raw = f.getvalue() if hasattr(f,"getvalue") else f.read()
                doc = DocxWriter(io.BytesIO(raw))
            except Exception:
                continue
            paras = [p.text.strip() for p in doc.paragraphs]
            # locate trade section
            idx = -1
            for i,t in enumerate(paras):
                if t and trade_label.lower() in t.lower():
                    idx = i; break
            if idx < 0: 
                continue
            # collect lines until next likely heading (all-caps or empty break with new cap)
            block=[]
            for t in paras[idx:]:
                if t and t.isupper() and t.lower()!=trade_label.lower():
                    break
                block.append(t)
            # mine for cert hints and steps
            cert_hits=set()
            for t in block:
                low=t.lower()
                if any(k in low for k in ["osha","flagger","forklift","cpr","first aid","aerial lift","traffic control","nccer"]):
                    if "osha" in low: cert_hits.add("OSHA-10")
                    if "flagger" in low: cert_hits.add("Flagger (WA)")
                    if "forklift" in low: cert_hits.add("Forklift")
                    if "cpr" in low or "first aid" in low: cert_hits.add("CPR/First Aid")
                    if "aerial lift" in low: cert_hits.add("Aerial Lift")
                    if "traffic control" in low: cert_hits.add("Traffic Control")
                    if "nccer" in low: cert_hits.add("NCCER")
            steps=[]
            for t in block:
                if re.match(r"^[•\-\u2022]\s+", t) or (len(t.split())<=14 and t.endswith(".")):
                    steps.append(clean_bullet(re.sub(r"^[•\-\u2022-]+\s*","",t)))
            result["certs"] = sorted(cert_hits)
            result["steps"] = steps[:12]
            return result
    return result

# ─────────────────────────────────────────────────────────
# Resume rendering
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

    # Skills
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
        "skills": skills, "certs": certs,
        "jobs": [asdict(j) for j in jobs if any([j.company,j.role,j.bullets])],
        "schools": [asdict(s) for s in schools if any([s.school,s.credential,s.year,s.details])],
        "trade_label": trade_label,
    }

def render_docx_with_template(template_bytes: bytes, context: Dict[str,Any]) -> bytes:
    tpl = DocxTemplate(io.BytesIO(template_bytes))
    tpl.render(context)
    out = io.BytesIO(); tpl.save(out); out.seek(0)
    return out.getvalue()

# ────────── Instructor Packet (full text + Roadmap excerpt) ──────────
def _add_toc(doc: DocxWriter, entries: List[str]):
    doc.add_heading("Table of Contents", level=1)
    for i, e in enumerate(entries, 1):
        doc.add_paragraph(f"{i}. {e}")

def _add_sources_table(doc: DocxWriter, sources: List[Any]):
    doc.add_heading("Sources Imported", level=1)
    table = doc.add_table(rows=1, cols=3)
    hdr = table.rows[0].cells
    hdr[0].text = "File"
    hdr[1].text = "Type"
    hdr[2].text = "Imported"
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    for s in sources:
        name = getattr(s, "name", "file")
        typ = os.path.splitext(name)[1].lower().lstrip(".") or "txt"
        row = table.add_row().cells
        row[0].text = name
        row[1].text = typ
        row[2].text = now

def _roadmap_slice_from_docx(doc_bytes: bytes, trade_label: str) -> List[str]:
    try:
        doc = DocxWriter(io.BytesIO(doc_bytes))
        paras = [p.text.strip() for p in doc.paragraphs]
    except Exception:
        return []
    start_idx = -1
    for idx, t in enumerate(paras):
        if t and trade_label.lower() in t.lower():
            start_idx = idx; break
    if start_idx < 0:
        return []
    block = []
    for t in paras[start_idx:]:
        if t and t.isupper() and t.lower() != trade_label.lower():
            break
        block.append(t)
    return [x for x in block if x is not None]

def build_pathway_packet_docx(student: Dict[str,str], trade_label: str, app_type: str, sources: List[Any], reflections: Dict[str,str]) -> bytes:
    doc = DocxWriter()
    styles = doc.styles['Normal']; styles.font.name = 'Calibri'; styles.font.size = Pt(11)

    toc_entries = ["Workshop Notes", "Full Text of Uploaded/Imported Files"]
    doc.add_heading("Instructor Pathway Packet", level=0)
    meta = f"Student: {student.get('name','')} | Target: {trade_label} | Application type: {app_type}"
    doc.add_paragraph(meta); doc.add_paragraph("")

    # Roadmap excerpt if provided
    roadmap_slice: List[str] = []
    for upl in sources or []:
        nm = getattr(upl, "name", "").lower()
        if nm.endswith(".docx") and ("roadmap" in nm or "apprenticeship" in nm):
            try:
                raw = upl.getvalue() if hasattr(upl, "getvalue") else upl.read()
                roadmap_slice = _roadmap_slice_from_docx(raw, trade_label)
                if roadmap_slice: break
            except Exception:
                pass
    if roadmap_slice:
        toc_entries.append("Trade Roadmap (Relevant Excerpt)")

    _add_toc(doc, toc_entries)
    _add_sources_table(doc, sources)

    doc.add_page_break()
    doc.add_heading("Workshop Notes", level=1)
    for k,v in reflections.items():
        doc.add_paragraph(k+":")
        for line in (v or "").splitlines():
            doc.add_paragraph(line)

    doc.add_page_break()
    doc.add_heading("Full Text of Uploaded/Imported Files", level=1)
    for upl in sources or []:
        doc.add_page_break()
        doc.add_heading(getattr(upl,"name","(file)"), level=2)
        text = extract_text_generic(upl)
        if text.strip():
            for line in text.splitlines():
                doc.add_paragraph(line)
        else:
            doc.add_paragraph("Couldn’t extract text. Tip: upload text-based PDF or DOCX, not scans.")

    if roadmap_slice:
        doc.add_page_break()
        doc.add_heading("Trade Roadmap (Relevant Excerpt)", level=1)
        for line in roadmap_slice:
            doc.add_paragraph(line)

    out = io.BytesIO(); doc.save(out); out.seek(0)
    return out.getvalue()

# ─────────────────────────────────────────────────────────
# Sidebar — template + extra docs
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
    st.caption("Upload supporting docs (PDF/DOCX/TXT). These embed (full text) in the Instructor Packet and power suggestions.")
    pathway_uploads = st.file_uploader("Upload roadmaps / transferable skills / job history docs", type=["pdf","docx","txt"], accept_multiple_files=True)

# ─────────────────────────────────────────────────────────
# Intake (uploads/URLs/paste)
# ─────────────────────────────────────────────────────────
st.title("Resume Workshop")

st.subheader("Bring Your Stuff (we’ll mine it)")
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
paste_box = st.text_area("Paste any resume or job description text here", "")

def extract_multi(files) -> str:
    txt = ""
    for f in files or []:
        txt += "\n" + extract_text_generic(f)
    return txt

prev_resume_text = extract_multi(prev_resume_files)
jd_text_files = extract_multi(jd_files) + extract_multi(url_fetches)
supporting_text = extract_multi(pathway_uploads)
jd_text_paste = paste_box or ""
combined_text = "\n".join([prev_resume_text, jd_text_files, jd_text_paste]).strip()

if combined_text:
    st.caption(f"Loaded text from {len(prev_resume_files or [])} resume file(s), "
               f"{len(jd_files or []) + len(url_fetches)} JD file(s)/URL(s), "
               f"and {'pasted text' if jd_text_paste else 'no pasted text'}.")
    st.info((combined_text[:900] + "…").replace("\n"," "))

# ─────────────────────────────────────────────────────────
# Parse header/education + build suggestion maps
# ─────────────────────────────────────────────────────────
if "parsed_header" not in st.session_state:
    st.session_state["parsed_header"] = {}
if "parsed_schools" not in st.session_state:
    st.session_state["parsed_schools"] = []
if "role_suggestions" not in st.session_state:
    st.session_state["role_suggestions"] = {}
if "xfer_skills_doc" not in st.session_state:
    st.session_state["xfer_skills_doc"] = []
if "roadmap_hints" not in st.session_state:
    st.session_state["roadmap_hints"] = {"certs": [], "steps": []}

def parse_now():
    text = combined_text
    st.session_state["parsed_header"] = parse_header(text)
    st.session_state["parsed_schools"] = parse_education(text)
    # Role bullets from uploaded Job History docs
    role_map = bullets_from_job_history_docs(pathway_uploads or [])
    detected = detect_roles(text)
    st.session_state["role_suggestions"] = {r: role_map.get(r, ROLE_FALLBACK.get(r, [])) for r in (detected or role_map.keys())}
    # Transferable skills doc
    st.session_state["xfer_skills_doc"] = parse_transferable_skills_doc(pathway_uploads or [])
    # Roadmaps doc for chosen trade (we'll refresh again when trade changes)
    st.session_state["roadmap_hints"] = {"certs": [], "steps": []}

content_fp = hashlib.md5((combined_text[:5000] + "|".join(sorted([getattr(x,"name","") for x in (pathway_uploads or [])]))).encode("utf-8","ignore")).hexdigest()
if st.session_state.get("last_fp") != content_fp and (combined_text or pathway_uploads):
    parse_now(); st.session_state["last_fp"] = content_fp
    st.success("Parsed uploads: header/education, detected roles, skills, and roadmap-ready.")

with st.expander("Parsed Data (preview)"):
    st.write({"Header": st.session_state.get("parsed_header",{}),
              "Detected roles": list(st.session_state.get("role_suggestions",{}).keys()),
              "Schools": st.session_state.get("parsed_schools",[])})

# ─────────────────────────────────────────────────────────
# Build the resume
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

ph = st.session_state.get("parsed_header", {})
c_apply1, c_apply2 = st.columns([1,3])
with c_apply1:
    if st.button("Apply Parsed Header", disabled=not ph):
        for k in ["Name","Phone","Email","City","State"]:
            if ph.get(k):
                st.session_state[k] = ph[k]
        st.success("Header applied from uploads.")
with c_apply2:
    st.caption("Detected → click once to fill: " + ", ".join([f"{k}: {ph.get(k,'')}" for k in ["Name","Phone","Email","City","State"] if ph.get(k)]) if ph else "No header detected yet.")

st.subheader("Objective")
c3a, c3b = st.columns(2)
with c3a:
    application_type = st.radio("Focus", ["Apprenticeship","Job"], horizontal=True, index=0)
    trade = st.selectbox("Trade target", TRADE_TAXONOMY, index=TRADE_TAXONOMY.index("Electrician – Inside (01)"), key="SelectedTrade")
with c3b:
    wk_pitch = st.text_input("10-second pitch (optional):", st.session_state.get("Pitch",""))
    st.session_state["Pitch"] = wk_pitch
wk_objective_final = st.text_area("Type your objective (1–2 sentences):", key="Objective_Final", placeholder="State the goal (apprenticeship or job), the trade, and what you bring (safety, pace, reliability).")
with st.expander("Suggested objective starters"):
    for s in objective_suggestions(application_type, st.session_state.get("SelectedTrade","")):
        st.write("• " + s)

# Refresh roadmap hints for selected trade
if pathway_uploads:
    st.session_state["roadmap_hints"] = parse_roadmaps_doc(pathway_uploads, st.session_state.get("SelectedTrade",""))

# ─────────────────────────────────────────────────────────
# Skills — suggestions (click to add)
# ─────────────────────────────────────────────────────────
st.subheader("Skills")
suggested_transferable = suggest_transferable_skills_from_text(combined_text)
from_doc = st.session_state.get("xfer_skills_doc", [])
merged_suggestions = []
seen=set()
for s in (suggested_transferable + from_doc):
    lab = normalize_skill_label(s)
    if lab.lower() not in seen:
        seen.add(lab.lower()); merged_suggestions.append(lab)
st.caption("Click suggestions to add; edit freely.")
csk1, csk2, csk3 = st.columns(3)
with csk1:
    Skills_Transferable = st.text_area("Transferable (comma/newline):", st.session_state.get("Skills_Transferable",""))
with csk2:
    Skills_JobSpecific  = st.text_area("Job-Specific (comma/newline):", st.session_state.get("Skills_JobSpecific",""))
with csk3:
    Skills_SelfManagement = st.text_area("Self-Management (comma/newline):", st.session_state.get("Skills_SelfManagement",""))

# Quick add buttons
if merged_suggestions:
    st.write("Suggested skills:")
    cols = st.columns(4)
    for i, sk in enumerate(merged_suggestions[:24]):
        if cols[i%4].button(sk, key=f"add_skill_{i}"):
            # heuristic place
            bucket = "Skills_Transferable"
            if sk in {"Reading blueprints & specs","Hand & power tools","Operating machinery","Materials handling (wood/concrete/metal)","Trades math & measurement","Regulatory compliance","Safety awareness"}:
                bucket = "Skills_JobSpecific"
            elif sk in {"Leadership","Adaptability & willingness to learn","Physical stamina & dexterity"}:
                bucket = "Skills_SelfManagement"
            cur = st.session_state.get(bucket,"")
            add = (cur + (", " if cur.strip() else "") + sk)
            st.session_state[bucket] = add

# Roadmap-suggested certs/steps
rh = st.session_state.get("roadmap_hints", {"certs":[], "steps":[]})
if rh["certs"] or rh["steps"]:
    with st.expander("From Roadmap: suggested certs & steps"):
        if rh["certs"]:
            st.write("Suggested certs: " + ", ".join(rh["certs"]))
        if rh["steps"]:
            for s in rh["steps"][:10]:
                st.write("• " + s)

# ─────────────────────────────────────────────────────────
# Work Experience — role-driven suggestions
# ─────────────────────────────────────────────────────────
st.subheader("Work Experience — Click to insert duty bullets by role")
role_suggestions = st.session_state.get("role_suggestions", {})
if role_suggestions:
    role_names = list(role_suggestions.keys())
    selected_role = st.selectbox("Detected/Available roles", role_names, index=0)
    bullets = role_suggestions.get(selected_role, [])
    st.caption("Click bullets to insert into Job 1/2/3 duties. You control titles/companies/dates.")
    cwe = st.columns(3)
    for idx in range(1,4):
        cwe[idx-1].markdown(f"**Job {idx} duties**")
    rows = (len(bullets)+2)//3
    for r in range(rows):
        cols = st.columns(3)
        for c in range(3):
            i = r*3 + c
            if i < len(bullets):
                b = bullets[i]
                if cols[c].button("• " + b, key=f"b_{selected_role}_{i}"):
                    key = f"Job{c+1}_Duties"
                    cur = st.session_state.get(key,"")
                    new = (cur + ("\n" if cur.strip() else "") + b)
                    st.session_state[key] = new
else:
    st.info("Upload a Job History DOCX (with role headings and bullets) or include role words (e.g., 'line cook', 'server') in your resume text to see suggestions here.")

# Manual job fields
for j in range(1,4):
    st.markdown(f"**Job {j}**")
    st.text_input(f"Company {j}:", key=f"Job{j}_Company")
    st.text_input(f"City/State {j}:", key=f"Job{j}_CityState")
    st.text_input(f"Dates {j} (e.g., 2023-06 – Present):", key=f"Job{j}_Dates")
    st.text_input(f"Title {j}:", key=f"Job{j}_Title")
    st.text_area(f"Duties/Accomplishments {j} (1–4 bullets):", key=f"Job{j}_Duties", height=100)

# Certifications & Education
st.subheader("Certifications")
default_certs = "OSHA-10, Flagger (WA), Forklift operator (employer evaluation on hire)"
if rh["certs"]:
    default_certs = ", ".join(sorted(set([*rh["certs"], *split_list(default_certs)])))
Certifications = st.text_area("List certifications (comma/newline):", st.session_state.get("Certifications", default_certs))

st.subheader("Education")
E1s = st.text_input("School/Program 1:", key="Edu1_School"); E1cs = st.text_input("City/State 1:", key="Edu1_CityState")
E1d = st.text_input("Dates 1:", key="Edu1_Dates"); E1c = st.text_input("Certificate/Diploma 1:", key="Edu1_Credential")
E2s = st.text_input("School/Program 2:", key="Edu2_School"); E2cs = st.text_input("City/State 2:", key="Edu2_CityState")
E2d = st.text_input("Dates 2:", key="Edu2_Dates"); E2c = st.text_input("Certificate/Diploma 2:", key="Edu2_Credential")

# ─────────────────────────────────────────────────────────
# Generate Docs
# ─────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Build Files")
CL_Company = st.text_input("Cover Letter — Company:","")
CL_Role    = st.text_input("Cover Letter — Role Title:", f"{st.session_state.get('SelectedTrade','')} apprentice")
CL_Location= st.text_input("Cover Letter — Company Location (City, State):","")
CL_Highlights = st.text_area("Cover Letter — Highlights (comma/newline/• allowed):","Reliable • Safety-focused • Coachable")

if st.button("Generate Resume + Cover Letter + Instructor Packet", type="primary"):
    problems=[]
    if not st.session_state.get("Name","").strip():
        problems.append("Name is required.")
    if not (st.session_state.get("Phone","").strip() or st.session_state.get("Email","").strip()):
        problems.append("At least one contact method (Phone or Email) is required.")
    if not st.session_state.get("Objective_Final","").strip():
        problems.append("Objective is required (type it; we show suggestions above).")
    if problems:
        st.error(" | ".join(problems))
        st.stop()

    trade_sel = st.session_state.get("SelectedTrade","Electrician – Inside (01)")
    # Merge skills fields
    form = {
        "Name": st.session_state.get("Name",""), "City": st.session_state.get("City",""), "State": st.session_state.get("State",""),
        "Phone": st.session_state.get("Phone",""), "Email": st.session_state.get("Email",""),
        "Objective_Final": st.session_state.get("Objective_Final",""),
        "Skills_Transferable": st.session_state.get("Skills_Transferable",""),
        "Skills_JobSpecific": st.session_state.get("Skills_JobSpecific",""),
        "Skills_SelfManagement": st.session_state.get("Skills_SelfManagement",""),
        "Certifications": Certifications,
    }
    # Jobs
    for i in range(1,4):
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
    if not tpl_bytes:
        st.error("Template not found. Put resume_app_template.docx in the repo or upload it in the sidebar.")
        st.stop()
    try:
        resume_ctx = build_resume_context(form, trade_sel)
        resume_bytes = render_docx_with_template(tpl_bytes, resume_ctx)
    except Exception as e:
        st.error(f"Resume template rendering failed: {e}")
        st.stop()

    # Cover Letter
    def _split_highlights(raw: str) -> List[str]: return split_list(raw)
    def build_cover_letter_docx(data: Dict[str,str]) -> bytes:
        doc = DocxWriter()
        styles = doc.styles['Normal']; styles.font.name = 'Calibri'; styles.font.size = Pt(11)
        doc.add_paragraph(f"{data.get('name','')}")
        doc.add_paragraph(f"{data.get('city','')}, {data.get('state','')}")
        contact = ", ".join([x for x in [data.get('phone',''), data.get('email','')] if x])
        if contact: doc.add_paragraph(contact)
        doc.add_paragraph("")
        today = datetime.date.today().strftime("%B %d, %Y")
        doc.add_paragraph(today)
        if data.get("company"): doc.add_paragraph(strip_banned(data["company"]))
        if data.get("location"): doc.add_paragraph(data["location"])
        doc.add_paragraph("")
        doc.add_paragraph("Dear Hiring Committee,")
        app_type = data.get("application_type","Apprenticeship")
        p1 = doc.add_paragraph()
        role = strip_banned(data.get("role",""))
        p1.add_run(f"I’m applying for a {role} {('apprenticeship' if app_type=='Apprenticeship' else 'position')} in the {strip_banned(data.get('trade_label',''))} scope. I bring reliability, safety awareness, and hands-on readiness.")
        p2 = doc.add_paragraph()
        p2.add_run("My background includes tool basics, teamwork on real schedules, and a commitment to safe, quality production.")
        hi = _split_highlights(strip_banned(data.get("strength","")))
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

    cover_bytes = build_cover_letter_docx({
        "name": form["Name"], "city": form["City"], "state": form["State"], "phone": clean_phone(form["Phone"]), "email": clean_email(form["Email"]),
        "company": CL_Company, "role": CL_Role, "location": CL_Location,
        "trade_label": trade_sel, "strength": CL_Highlights, "application_type": application_type,
    })

    # Instructor Packet (Workshop notes + full text)
    reflections = {"Objective": form["Objective_Final"]}
    merged_docs_for_packet = list(pathway_uploads or []) + list(prev_resume_files or []) + list(jd_files or []) + url_fetches
    packet_bytes = build_pathway_packet_docx({"name": form["Name"]}, trade_sel, application_type, merged_docs_for_packet, reflections)

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

    # Intake CSV
    csv_fields = [
        "Name","City","State","Phone","Email","Objective_Final",
        "Skills_Transferable","Skills_JobSpecific","Skills_SelfManagement","Certifications",
        "Job1_Company","Job1_CityState","Job1_Dates","Job1_Title","Job1_Duties",
        "Job2_Company","Job2_CityState","Job2_Dates","Job2_Title","Job2_Duties",
        "Job3_Company","Job3_CityState","Job3_Dates","Job3_Title","Job3_Duties",
        "Edu1_School","Edu1_CityState","Edu1_Dates","Edu1_Credential",
        "Edu2_School","Edu2_CityState","Edu2_Dates","Edu2_Credential"
    ]
    buf=io.StringIO(); w=csv.writer(buf); w.writerow(csv_fields); w.writerow([form.get(k,"") for k in csv_fields])
    st.download_button("Download Intake CSV", data=buf.getvalue().encode("utf-8"),
                       file_name=f"{safe_name}_Workshop_Intake.csv", mime="text/csv",
                       use_container_width=True)
    st.success("Generated. Objective stays student-written; suggestions powered by your docs. Neutral language enforced.")
