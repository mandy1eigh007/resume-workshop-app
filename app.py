# app.py — Resume Workshop & Pathways (Seattle Tri-County)
# Streamlit single-file app. No APIs. Browser-only. Python 3.11.
# Features:
# - Step 0 intake: resumes/JDs via upload, URL (public Drive/GCS), and paste
# - Autofill (header, jobs, education, certs, 3 skill buckets)
# - Job History Library: upload DOCX/TXT with 50+ roles → click-to-insert duties + auto-add aligned skills
# - Objective: show recommendations; student types final
# - Builds Resume (docxtpl), Cover Letter (python-docx), Instructor Packet (verbatim full text)
# - Neutral language (no union/non-union/sub-trade labels in objective/letter)

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
    r"(?P<start>(?:\d{4}|\w{3,9}\s+\d{4}))\s*(?:–|-|to|until|through|—)\s*(?P<end>(?:Present|Current|\d{4}|\w{3,9}\s+\d{4}))",
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
    if "–" in raw or "-" in raw or "—" in raw:
        sep = "–" if "–" in raw else ("—" if "—" in raw else "-")
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

SKILLS_SECTION_RE = re.compile(r"^\s*(skills|core competencies|key skills)\b.*$", re.I | re.M)

JOB_SPECIFIC_KEYWORDS = {
    "hand & power tools":["Hand & power tools","Tool identification","Safe tool use"],
    "blueprint":["Reading blueprints & specs","Plan notes"],
    "schematic":["Reading blueprints & specs","Schematic reading"],
    "conduit":["Hand & power tools","Layout & measurement"],
    "layout":["Layout & measurement","Reading blueprints & specs"],
    "rigging":["Rigging basics","Tagline & signals"],
    "forklift":["Materials handling (wood/concrete/metal)","Operating machinery"],
    "pallet":["Materials handling (wood/concrete/metal)"],
    "ladder":["Ladder safety","Working at heights"],
    "math":["Trades math & measurement"],
    "measure":["Trades math & measurement"],
    "tapemeasure":["Trades math & measurement"],
    "welding":["Welding basics"],
    "brazing":["Brazing/soldering basics"],
    "solder":["Brazing/soldering basics"],
    "lockout":["Regulatory compliance"],
    "osha":["Safety awareness"],
    "ppe":["Safety awareness"]
}

SELF_MGMT_KEYWORDS = {
    "reliable":["Reliability","On-time attendance"],
    "attendance":["On-time attendance","Accountability"],
    "team":["Teamwork & collaboration"],
    "collaborat":["Teamwork & collaboration"],
    "communication":["Communication","Conflict resolution"],
    "customer":["Customer service"],
    "pace":["Time management","Production focus"],
    "deadline":["Time management"],
    "detail":["Attention to detail"],
    "learn":["Adaptability & willingness to learn"],
    "adapt":["Adaptability & willingness to learn"],
    "lead":["Leadership"],
    "stamina":["Physical stamina & dexterity"],
}

ROLE_TO_SKILLS = {
    "line cook": (["Hand & power tools","Knife safety","Sanitation discipline"], ["Time management","Teamwork & collaboration","Attention to detail"]),
    "server": (["Customer service","Cash handling"], ["Communication","Time management","Teamwork & collaboration"]),
    "retail": (["Inventory","Point-of-sale"], ["Customer service","Communication","Attention to detail"]),
    "warehouse": (["Materials handling (wood/concrete/metal)","Pallet jack","Forklift basics"], ["Time management","Teamwork & collaboration","Physical stamina & dexterity"]),
    "barista": (["Sanitation discipline","Equipment cleaning"], ["Customer service","Time management","Attention to detail"]),
    "janitor": (["Chemical safety","Equipment cleaning"], ["Reliability","Attention to detail","Independence"]),
    "custodian": (["Facility setup","Materials handling (wood/concrete/metal)"], ["Reliability","Time management"]),
    "mover": (["Rigging basics","Materials handling (wood/concrete/metal)"], ["Physical stamina & dexterity","Teamwork & collaboration"]),
    "driver": (["Load securement","Route planning"], ["Time management","Communication","Reliability"]),
    "landscaper": (["Equipment operation","Rigging basics"], ["Physical stamina & dexterity","Time management"]),
    "security": (["Incident reporting"], ["Communication","Situational awareness","Reliability"]),
    "housekeeper": (["Equipment cleaning","Chemical safety"], ["Attention to detail","Time management"]),
}

def _extract_explicit_skills_block(text: str) -> List[str]:
    if not text: return []
    lines = text.splitlines()
    start = None
    for i,l in enumerate(lines):
        if SKILLS_SECTION_RE.search(l):
            start = i+1
            break
    if start is None: return []
    out=[]
    for j in range(start, min(start+40, len(lines))):
        ln = lines[j].strip()
        if not ln: continue
        if re.match(r"^\s*(experience|work history|employment|education|objective|summary)\b", ln, re.I):
            break
        m = re.match(r"^[•\-\u2022]*\s*(.+)$", ln)
        chunk = m.group(1) if m else ln
        out += [p.strip() for p in re.split(r"[,\u2022•;]+", chunk) if p.strip()]
    return out

def mine_resume_skills(full_text: str, detected_roles: List[str]) -> Dict[str, List[str]]:
    low = (full_text or "").lower()
    explicit = [_ for _ in _extract_explicit_skills_block(full_text)]
    explicit_norm = [normalize_skill_label(x) for x in explicit]

    js_pool=set(); sm_pool=set(); tr_pool=set(suggest_transferable_skills_from_text(full_text))

    for k, labs in JOB_SPECIFIC_KEYWORDS.items():
        if k in low:
            for lab in labs: js_pool.add(normalize_skill_label(lab))

    for k, labs in SELF_MGMT_KEYWORDS.items():
        if k in low:
            for lab in labs: sm_pool.add(normalize_skill_label(lab))

    for r in (detected_roles or []):
        rkey = r.lower().strip()
        for key, (jobspec, selfmgmt) in ROLE_TO_SKILLS.items():
            if key in rkey:
                for lab in jobspec: js_pool.add(normalize_skill_label(lab))
                for lab in selfmgmt: sm_pool.add(normalize_skill_label(lab))

    for lab in explicit_norm:
        if not lab: continue
        if any(tok in lab.lower() for tok in ["tool","blueprint","conduit","rigging","forklift","ladder","weld","solder","braz","math","measure","layout","schematic","lockout","osha","ppe","inventory","point-of-sale","custodian","janitor"]):
            js_pool.add(lab)
        elif any(tok in lab.lower() for tok in ["reliab","attendance","team","collab","communicat","customer","lead","stamina","adapt","learn","detail","time"]):
            sm_pool.add(lab)
        else:
            tr_pool.add(lab)

    transferable = []
    seen=set()
    for s in SKILL_CANON + sorted(tr_pool):
        lab = normalize_skill_label(s)
        if lab and lab.lower() not in seen:
            transferable.append(lab); seen.add(lab.lower())
        if len(transferable) >= MAX_SKILLS: break

    jobspec = sorted(js_pool)[:MAX_SKILLS]
    selfmgmt = sorted(sm_pool)[:MAX_SKILLS]

    return {"Transferable": transferable, "Job-Specific": jobspec, "Self-Management": selfmgmt}

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
# Role→construction seed bullets (small built-in; upload expands)
# ─────────────────────────────────────────────────────────
BUILTIN_ROLE_BULLETS = {
    "Line Cook": [
        "Worked safely around hot equipment and sharp tools",
        "Kept stations clean and organized; followed prep lists",
        "Handled deliveries and rotated stock; kept walkways clear",
        "Stayed on pace to meet production during rushes",
    ],
    "Server": [
        "Communicated with customers and team under time pressure",
        "Handled cash counts and hand-offs accurately",
        "Kept stations clean; restocked and closed down per checklist",
    ],
    "Warehouse": [
        "Staged materials and verified counts; kept aisles clear",
        "Operated pallet jacks/hand trucks under PPE rules",
    ],
    "Retail": [
        "Kept inventory organized; assisted customers with products",
        "Operated POS accurately and closed out drawers cleanly",
    ],
}

# ─────────────────────────────────────────────────────────
# Parsing helpers (header/jobs/edu/certs)
# ─────────────────────────────────────────────────────────
def parse_header(text: str) -> Dict[str,str]:
    if not text:
        return {"Name":"", "Email":"", "Phone":"", "City":"", "State":""}

    top_block = "\n".join([l.strip() for l in (text or "").splitlines()[:50]])
    sep_norm = re.sub(r"[•·–—\-•/]+", "|", top_block)

    email = ""
    m = EMAIL_RE.search(text or "")
    if m: email = m.group(0)

    phone = ""
    m = PHONE_RE.search(text or "")
    if m: phone = m.group(0)

    city = ""; state = ""
    mcs_top = CITY_STATE_RE.search(top_block)
    if mcs_top:
        city, state = mcs_top.group(1), mcs_top.group(2).upper()
    else:
        mcs_any = CITY_STATE_RE.search(text or "")
        if mcs_any:
            city, state = mcs_any.group(1), mcs_any.group(2).upper()

    name = ""
    candidates = []
    for raw in sep_norm.split("\n"):
        line = raw.strip().strip("|").strip()
        if not line: 
            continue
        if EMAIL_RE.search(line) or PHONE_RE.search(line):
            continue
        if re.search(r"\b(objective|summary|skills|experience|education|certifications)\b", line, re.I):
            continue
        toks = [t for t in re.split(r"\s+", line) if t]
        if 2 <= len(toks) <= 4 and not any(re.search(r"\d", t) for t in toks):
            caps = sum(t[:1].isalpha() and t[:1].isupper() for t in toks)
            if caps >= 2:
                candidates.append(line)
    if candidates:
        name = candidates[0]
    else:
        for l in (text or "").splitlines()[:15]:
            L = l.strip()
            if L and not EMAIL_RE.search(L) and not PHONE_RE.search(L) and not re.search(r"\b(objective|summary|skills|experience|education)\b", L, re.I):
                if re.search(r"[A-Za-z]", L) and len(L.split()) <= 4:
                    name = L
                    break

    return {
        "Name": cap_first(name),
        "Email": clean_email(email),
        "Phone": clean_phone(phone),
        "City": cap_first(city),
        "State": (state or "").strip()
    }

def _safe_company_token(token: str) -> bool:
    if CITY_STATE_RE.fullmatch(token):
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9 .'\-&]{2,}", token))

def parse_jobs(text: str) -> List[Dict[str,Any]]:
    out=[]
    lines = [l.rstrip() for l in (text or "").splitlines()]
    i=0
    while i < len(lines) and len(out) < MAX_JOBS:
        head = lines[i].strip()
        if not head:
            i+=1; continue
        if re.match(r"^\s*(summary|objective|skills|certifications|education)\s*$", head, re.I):
            i+=1; continue

        window = " ".join(lines[i:i+3])
        parts = re.split(r"\s*\|\s*|\s{2,}| — | – | — ", head)
        role=""; company=""; cityst=""; dates=""

        mdate = DATE_RANGE_RE.search(window)
        if mdate:
            dates = f"{mdate.group('start')} – {mdate.group('end')}"
        mcity = CITY_STATE_RE.search(window)
        if mcity:
            cityst = f"{mcity.group(1)}, {mcity.group(2).upper()}"

        if len(parts) >= 2:
            cand_role = parts[0].strip()
            cand_co   = parts[1].strip()
            if _safe_company_token(cand_co):
                role, company = cand_role, cand_co
            else:
                if _safe_company_token(cand_role) and not _safe_company_token(cand_co):
                    company, role = cand_role, cand_co
                else:
                    role = cand_role
        else:
            role = head

        bullets=[]
        j=i+1
        while j < len(lines):
            ln = lines[j].strip()
            if not ln:
                if bullets:
                    break
                j+=1
                continue
            if re.match(r"^\s*(summary|objective|skills|certifications|education)\s*$", ln, re.I):
                break
            if re.match(r"^[•\-\u2022]\s+", ln) or lines[j].startswith("\t"):
                bullets.append(clean_bullet(re.sub(r"^[•\-\u2022\-]+\s*", "", ln)))
                if len(bullets) >= MAX_BULLETS_PER_JOB:
                    break
            else:
                if DATE_RANGE_RE.search(ln) or CITY_STATE_RE.search(ln):
                    pass
                elif len(ln.split()) <= 4 and bullets:
                    break
            j+=1

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
                mcs = CITY_STATE_RE.search(la)
                if mcs: details = f"{mcs.group(1)}, {mcs.group(2).upper()}"
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
# Objective generator (recommendations only; student types final)
# ─────────────────────────────────────────────────────────
def build_objective_recos(trade: str) -> List[str]:
    return [
        f"Seeking entry into a {trade} apprenticeship—show up safe, learn fast, support the crew.",
        f"Looking for hands-on work in {trade}—reliable, safety-minded, ready to learn on pace.",
        f"Aiming to start in {trade}: bring safety, teamwork, and clean work habits; build skill the right way."
    ]

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

    # Summary/objective: student final (if empty, keep blank)
    summary = strip_banned(norm_ws(form.get("Objective_Final","")))[:MAX_SUMMARY_CHARS] if form.get("Objective_Final","").strip() else ""

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

    other_work = norm_ws(form.get("Other_Work",""))
    volunteer  = norm_ws(form.get("Volunteer",""))
    tail=[]
    if other_work: tail.append(f"Other work: {other_work}")
    if volunteer:  tail.append(f"Volunteer: {volunteer}")
    if tail and summary:
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

    # Include full text of uploaded/imported docs (verbatim)
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
# Job History Library parsing (DOCX/TXT)
# ─────────────────────────────────────────────────────────
from docx import Document as DocxReader

def parse_job_history_txt(text: str) -> Dict[str, List[str]]:
    roles: Dict[str, List[str]] = {}
    current = None
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line: continue
        m = re.match(r"^##\s*Role\s*:\s*(.+)$", line, re.I)
        if m:
            current = cap_first(m.group(1).strip())
            roles.setdefault(current, [])
            continue
        if current:
            b = re.sub(r"^[•\-\u2022]+\s*", "", line).strip()
            if b: roles[current].append(clean_bullet(b))
    return roles

def parse_job_history_docx(file) -> Dict[str, List[str]]:
    roles: Dict[str, List[str]] = {}
    try:
        doc = DocxReader(file)
    except Exception:
        return roles
    current = None
    for p in doc.paragraphs:
        text = (p.text or "").strip()
        if not text: continue
        sty = (getattr(p.style, "name", "") or "").lower()
        is_heading = ("heading" in sty) or text.lower().startswith("role:")
        if is_heading:
            m = re.search(r"(role\s*:\s*)?(.+)$", text, re.I)
            lab = cap_first(m.group(2).strip() if m else text)
            current = lab
            roles.setdefault(current, [])
            continue
        if current:
            if "list bullet" in sty or re.match(r"^[•\-\u2022]\s+", text):
                roles[current].append(clean_bullet(re.sub(r"^[•\-\u2022\-]+\s*", "", text)))
    return roles

def load_job_history_library(upload_file) -> Dict[str, List[str]]:
    library: Dict[str, List[str]] = {}
    if upload_file is not None:
        name = (getattr(upload_file, "name", "") or "").lower()
        try:
            if name.endswith(".docx"):
                library = parse_job_history_docx(upload_file); upload_file.seek(0)
            elif name.endswith(".txt"):
                txt = upload_file.getvalue().decode("utf-8", errors="ignore")
                library = parse_job_history_txt(txt)
        except Exception:
            library = {}
    # Merge with small built-in seeds so we always have something
    norm_map = {k.lower(): k for k in (library.keys())}
    for bk, bullets in BUILTIN_ROLE_BULLETS.items():
        if bk.lower() not in norm_map:
            library[bk] = bullets
    return library

# ─────────────────────────────────────────────────────────
# Sidebar — template + extra docs + job history
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
    st.caption("Upload additional instructor/pathway docs (PDF/DOCX/TXT). These get embedded (full text) in the Instructor Packet.")
    pathway_uploads = st.file_uploader("Upload pathway documents", type=["pdf","docx","txt"], accept_multiple_files=True)

    st.markdown("---")
    st.header("Job History Library")
    st.caption("Upload the role→bullets library (DOCX or TXT). Format: role as a heading (or 'Role: X'), bullets beneath.")
    job_hist_file = st.file_uploader("Upload Job History Master", type=["docx", "txt"], accept_multiple_files=False)

# ─────────────────────────────────────────────────────────
# Main — Step 0: Intake (uploads/URLs/paste)
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
jd_text_paste = paste_box or ""
combined_text = "\n".join([prev_resume_text, jd_text_files, jd_text_paste]).strip()

if combined_text:
    st.caption(f"Loaded text from {len(prev_resume_files or [])} resume file(s), "
               f"{len(jd_files or []) + len(url_fetches)} JD file(s)/URL(s), "
               f"and {'pasted text' if jd_text_paste else 'no pasted text'}.")
    preview = combined_text[:1000].replace("\n"," ")
    st.info(f"Preview: {preview}…")

# ─────────────────────────────────────────────────────────
# Autofill — parses everything and writes into session state
# ─────────────────────────────────────────────────────────
if "autofilled_once" not in st.session_state:
    st.session_state["autofilled_once"] = False

def set_if_empty(key: str, val: str):
    if key not in st.session_state or not str(st.session_state.get(key,"")).strip():
        st.session_state[key] = val

def autofill_from_text(text: str, trade_for_objective: str) -> Dict[str, Any]:
    parsed: Dict[str, Any] = {"header":{}, "jobs":[], "schools":[], "certs":[], "skills_cat":{}}

    # Header
    hdr = parse_header(text)
    parsed["header"] = hdr
    for k,v in {"Name":"Name","Phone":"Phone","Email":"Email","City":"City","State":"State"}.items():
        set_if_empty(v, hdr.get(k,""))

    # Jobs
    jobs = parse_jobs(text)
    parsed["jobs"] = jobs
    st.session_state["autofilled_jobs"] = jobs
    for idx in range(1, MAX_JOBS+1):
        j = jobs[idx-1] if idx-1 < len(jobs) else {}
        set_if_empty(f"Job{idx}_Company", j.get("company",""))
        set_if_empty(f"Job{idx}_CityState", j.get("city",""))
        dates = " – ".join([x for x in [j.get("start",""), j.get("end","")] if x]).strip(" –")
        set_if_empty(f"Job{idx}_Dates", dates)
        set_if_empty(f"Job{idx}_Title", j.get("role",""))
        # seed duties with whatever we parsed (students can overwrite)
        if j.get("bullets"):
            set_if_empty(f"Job{idx}_Duties", "\n".join(j.get("bullets")[:MAX_BULLETS_PER_JOB]))

    # Education
    schools = parse_education(text)
    parsed["schools"] = schools
    for idx in range(1, MAX_SCHOOLS+1):
        s = schools[idx-1] if idx-1 < len(schools) else {}
        set_if_empty(f"Edu{idx}_School", s.get("school",""))
        set_if_empty(f"Edu{idx}_CityState", s.get("details",""))
        set_if_empty(f"Edu{idx}_Dates", s.get("year",""))
        set_if_empty(f"Edu{idx}_Credential", s.get("credential",""))

    # Certs
    certs = parse_certs(text)
    parsed["certs"] = certs
    if certs:
        set_if_empty("Certifications", ", ".join(sorted(certs)))

    # Skills — mine 3 categories
    detected_role_labels = [ (j.get("role","") or "").lower() for j in jobs ]
    skills_cat = mine_resume_skills(text, detected_role_labels)
    parsed["skills_cat"] = skills_cat

    if skills_cat.get("Transferable"):
        set_if_empty("Skills_Transferable", ", ".join(skills_cat["Transferable"]))
    if skills_cat.get("Job-Specific"):
        set_if_empty("Skills_JobSpecific", ", ".join(skills_cat["Job-Specific"]))
    if skills_cat.get("Self-Management"):
        set_if_empty("Skills_SelfManagement", ", ".join(skills_cat["Self-Management"]))

    # Objective recommendations only (student types final)
    if not st.session_state.get("Objective_Final","").strip():
        recos = build_objective_recos(trade_for_objective)
        st.session_state["Objective_Recos"] = recos

    return parsed

# Auto-run autofill once when text is present (no extra clicks)
if combined_text and not st.session_state.get("autofilled_once", False):
    _ = autofill_from_text(combined_text, st.session_state.get("SelectedTrade","Electrician – Inside (01)"))
    st.session_state["autofilled_once"] = True
    st.success("Autofill complete (header, jobs, schools, certs, skills). Review below.")

# Manual trigger as well
if st.button("Auto-Fill from Uploaded Text", type="secondary", disabled=(not combined_text)):
    parsed_snapshot = autofill_from_text(combined_text, st.session_state.get("SelectedTrade","Electrician – Inside (01)"))
    with st.expander("Autofill Debug (what the parser captured)"):
        st.write(parsed_snapshot)
    st.success("Autofill complete. Fields below are pre-populated—review and edit as needed.")

# ─────────────────────────────────────────────────────────
# Build the resume (straight to fields; no “difference” lesson)
# ─────────────────────────────────────────────────────────
st.subheader("1. Your Header")
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
    application_type = st.radio("Are you seeking a job or apprenticeship?", ["Apprenticeship","Job"], horizontal=True, index=0)
    trade = st.selectbox("What trade are you aiming for?", TRADE_TAXONOMY, index=TRADE_TAXONOMY.index("Electrician – Inside (01)"), key="SelectedTrade")
with c3b:
    wk_pitch = st.text_input("10-second pitch (optional):", st.session_state.get("Pitch",""))
    st.session_state["Pitch"] = wk_pitch

st.caption("Type your objective (1–2 sentences). Keep it crew-forward, safety/pace/reliability. (We show recommendations below.)")
wk_objective_final = st.text_area("Objective (student writes final):", st.session_state.get("Objective_Final",""))
if st.session_state.get("Objective_Recos"):
    with st.expander("Suggested objective starters"):
        for i, r in enumerate(st.session_state["Objective_Recos"], start=1):
            st.markdown(f"- {r}")

st.subheader("3. Skills (auto suggestions + editable)")
suggested_skills = suggest_transferable_skills_from_text(combined_text)
quick_transfer = st.multiselect("Quick Add: transferable skills from your uploads", SKILL_CANON, default=suggested_skills)
Skills_Transferable = st.text_area("Transferable (comma/newline):", st.session_state.get("Skills_Transferable",""))
Skills_JobSpecific  = st.text_area("Job-Specific (comma/newline):", st.session_state.get("Skills_JobSpecific",""))
Skills_SelfManagement = st.text_area("Self-Management (comma/newline):", st.session_state.get("Skills_SelfManagement",""))

# ─────────────────────────────────────────────────────────
# Work Experience — Recommendations from Role Library
# ─────────────────────────────────────────────────────────
role_library = load_job_history_library(job_hist_file)
detected_roles = []
for j in st.session_state.get("autofilled_jobs", []) if "autofilled_jobs" in st.session_state else []:
    r = (j.get("role","") or "").strip()
    if r: detected_roles.append(r)
all_roles = sorted(set(list(role_library.keys()) + [cap_first(r) for r in detected_roles]), key=str.lower)

st.subheader("4. Work Experience — Click to insert duty bullets by role")
sel_roles = st.multiselect("Detected/Available roles (searchable):", options=all_roles)
insert_target = st.radio("Insert selected bullets into:", ["Job 1", "Job 2", "Job 3"], horizontal=True)
if "chosen_bullets" not in st.session_state:
    st.session_state["chosen_bullets"] = []

chosen = []
for role in sel_roles:
    bullets = role_library.get(role, [])
    if not bullets: continue
    with st.expander(f"{role} — bullets"):
        for i, b in enumerate(bullets, start=1):
            if st.checkbox(f"{b}", key=f"rb_{role}_{i}"):
                chosen.append((role, b))

add_skills = st.checkbox("Also add aligned skills when inserting bullets", value=True)

def _append_to_job_duties(job_key: str, new_lines: List[str]):
    cur = st.session_state.get(job_key, "")
    cur_lines = [ln for ln in (cur.splitlines() if cur else []) if ln.strip()]
    for ln in new_lines:
        if ln not in cur_lines:
            cur_lines.append(ln)
    st.session_state[job_key] = "\n".join(cur_lines[:MAX_BULLETS_PER_JOB])

def _append_skills_for_roles(roles: List[str]):
    t = split_list(st.session_state.get("Skills_Transferable",""))
    j = split_list(st.session_state.get("Skills_JobSpecific",""))
    for r in roles:
        key = r.lower()
        for k,(js,selfm) in ROLE_TO_SKILLS.items():
            if k in key:
                for s in js:
                    if s not in j: j.append(s)
                for s in selfm:
                    if s not in t: t.append(s)
    st.session_state["Skills_Transferable"] = ", ".join(t[:MAX_SKILLS])
    st.session_state["Skills_JobSpecific"]  = ", ".join(j[:MAX_SKILLS])

if st.button("Insert selected bullets"):
    targets = {"Job 1": "Job1_Duties", "Job 2":"Job2_Duties", "Job 3":"Job3_Duties"}
    if chosen:
        roles_only, bullets_only = zip(*chosen)
        _append_to_job_duties(targets[insert_target], list(bullets_only))
        if add_skills:
            _append_skills_for_roles(list(roles_only))
        st.success(f"Inserted {len(chosen)} bullet(s) into {insert_target} and updated skills.")
    else:
        st.info("Select at least one bullet from the role lists above.")

# ─────────────────────────────────────────────────────────
# Work Experience Inputs
# ─────────────────────────────────────────────────────────
st.subheader("4a. Work Experience – Job 1")
J1c = st.text_input("Job 1 – Company:", key="Job1_Company")
J1cs = st.text_input("Job 1 – City/State:", key="Job1_CityState")
J1d = st.text_input("Job 1 – Dates (e.g., 2023-06 – Present):", key="Job1_Dates")
J1t = st.text_input("Job 1 – Title:", key="Job1_Title")
J1du = st.text_area("Job 1 – Duties/Accomplishments (1–4 bullets):", key="Job1_Duties", height=120)

st.subheader("4b. Work Experience – Job 2")
J2c = st.text_input("Job 2 – Company:", key="Job2_Company")
J2cs = st.text_input("Job 2 – City/State:", key="Job2_CityState")
J2d = st.text_input("Job 2 – Dates:", key="Job2_Dates")
J2t = st.text_input("Job 2 – Title:", key="Job2_Title")
J2du = st.text_area("Job 2 – Duties/Accomplishments (1–4 bullets):", key="Job2_Duties", height=120)

st.subheader("4c. Work Experience – Job 3")
J3c = st.text_input("Job 3 – Company:", key="Job3_Company")
J3cs = st.text_input("Job 3 – City/State:", key="Job3_CityState")
J3d = st.text_input("Job 3 – Dates:", key="Job3_Dates")
J3t = st.text_input("Job 3 – Title:", key="Job3_Title")
J3du = st.text_area("Job 3 – Duties/Accomplishments (1–4 bullets):", key="Job3_Duties", height=120)

# ─────────────────────────────────────────────────────────
# Certifications & Education
# ─────────────────────────────────────────────────────────
st.subheader("5. Certifications")
Certifications = st.text_area(
    "List certifications (comma/newline). If none, write 'None yet' or what you plan to get.",
    st.session_state.get("Certifications","OSHA-10, Flagger (WA), Forklift operator (employer evaluation on hire)")
)

st.subheader("6. Education")
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
    if not Name.strip(): problems.append("Name is required.")
    if not (Phone.strip() or Email.strip()): problems.append("At least one contact method (Phone or Email) is required.")
    if problems:
        st.error(" | ".join(problems)); st.stop()

    # Merge Quick Add into Transferable
    skills_transfer_final = st.session_state.get("Skills_Transferable","")
    if quick_transfer:
        skills_transfer_final = (skills_transfer_final + (", " if skills_transfer_final.strip() else "") + ", ".join(quick_transfer))

    trade_sel = st.session_state.get("SelectedTrade","Electrician – Inside (01)")
    form = {
        "Name": Name, "City": City, "State": State,
        "Phone": Phone, "Email": Email,
        "Pitch": st.session_state.get("Pitch",""),
        "Objective_Final": wk_objective_final,  # student-typed final (recommendations shown above)
        "Skills_Transferable": skills_transfer_final,
        "Skills_JobSpecific": st.session_state.get("Skills_JobSpecific",""),
        "Skills_SelfManagement": st.session_state.get("Skills_SelfManagement",""),
        "Certifications": Certifications,
        "Other_Work": st.session_state.get("Other_Work",""), "Volunteer": st.session_state.get("Volunteer",""),
    }
    # Jobs
    for i,(co,cs,d,ti,du) in enumerate([
        (st.session_state.get("Job1_Company",""), st.session_state.get("Job1_CityState",""), st.session_state.get("Job1_Dates",""), st.session_state.get("Job1_Title",""), st.session_state.get("Job1_Duties","")),
        (st.session_state.get("Job2_Company",""), st.session_state.get("Job2_CityState",""), st.session_state.get("Job2_Dates",""), st.session_state.get("Job2_Title",""), st.session_state.get("Job2_Duties","")),
        (st.session_state.get("Job3_Company",""), st.session_state.get("Job3_CityState",""), st.session_state.get("Job3_Dates",""), st.session_state.get("Job3_Title",""), st.session_state.get("Job3_Duties","")),
    ], start=1):
        form[f"Job{i}_Company"]=co; form[f"Job{i}_CityState"]=cs; form[f"Job{i}_Dates"]=d
        form[f"Job{i}_Title"]=ti; form[f"Job{i}_Duties"]=du
    # Education
    for i,(sch,cs,d,cr) in enumerate([
        (st.session_state.get("Edu1_School",""), st.session_state.get("Edu1_CityState",""), st.session_state.get("Edu1_Dates",""), st.session_state.get("Edu1_Credential","")),
        (st.session_state.get("Edu2_School",""), st.session_state.get("Edu2_CityState",""), st.session_state.get("Edu2_Dates",""), st.session_state.get("Edu2_Credential","")),
    ], start=1):
        form[f"Edu{i}_School"]=sch; form[f"Edu{i}_CityState"]=cs; form[f"Edu{i}_Dates"]=d; form[f"Edu{i}_Credential"]=cr

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
    cover_bytes = build_cover_letter_docx({
        "name": Name, "city": City, "state": State, "phone": clean_phone(Phone), "email": clean_email(Email),
        "company": CL_Company, "role": CL_Role, "location": CL_Location,
        "trade_label": trade_sel, "strength": CL_Highlights,
        "application_type": application_type,
    })

    # Instructor Packet (Workshop reflections + full text of docs)
    reflections = {
        "Objective (student final)": wk_objective_final,
        "10-second pitch": wk_pitch,
        "Skills – Transferable": st.session_state.get("Skills_Transferable",""),
        "Skills – Job-Specific": st.session_state.get("Skills_JobSpecific",""),
        "Skills – Self-Management": st.session_state.get("Skills_SelfManagement",""),
    }
    merged_docs_for_packet = list(pathway_uploads or []) \
                           + list(prev_resume_files or []) \
                           + list(jd_files or []) \
                           + url_fetches
    packet_bytes = build_pathway_packet_docx({"name": Name}, trade_sel, application_type, merged_docs_for_packet, reflections)

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
    st.success("Generated. Objective stays student-written; skills and duties are suggestion-driven and editable.")
