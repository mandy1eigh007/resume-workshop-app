# app.py — Resume Workshop & Pathways (Seattle tri-county, union + open-shop lanes)
# Single-file Streamlit app. No AI, no API keys. Works with your DOCX resume template.
# Features:
# - Workshop intake → resume (docxtpl) + cover letter (python-docx) + instructor packet (full-text of uploads)
# - Trade picker (guidebook order + Lineman), Boost Plan panel per trade (certs, hold-over jobs, pipelines)
# - JD upload parsing (PDF/DOCX/TXT), conservative text cleanup/normalization
# - Neutral objective/letter language (no union/non-union/inside-wire/etc.)

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

st.set_page_config(page_title="Resume Workshop & Pathways", layout="wide")

# ─────────────────────────────────────────────────────────
# Guardrails & cleanup
# ─────────────────────────────────────────────────────────
MAX_SUMMARY_CHARS = 450
MAX_SKILLS = 12
MAX_CERTS = 8
MAX_JOBS = 3
MAX_BULLETS_PER_JOB = 4
MAX_SCHOOLS = 2

BANNED_TERMS = [
    r"\bunion\b", r"\bnon[-\s]?union\b", r"\bibew\b", r"\blocal\s*\d+\b",
    r"\binside\s+wire(man|men)?\b", r"\blow[-\s]?voltage\b", r"\bsound\s+and\s+communication(s)?\b"
]
BANNED_RE = re.compile("|".join(BANNED_TERMS), re.I)

FILLER_LEADS = re.compile(r"^\s*(responsible for|duties included|tasked with|in charge of)\s*:?\s*", re.I)
MULTISPACE = re.compile(r"\s+")
PHONE_DIGITS = re.compile(r"\D+")

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
# Skills canon & synonyms (conservative)
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
    "stamina":"Physical stamina & dexterity",
}
def normalize_skill_label(s: str) -> str:
    base = (s or "").strip()
    key = re.sub(r"\s+"," ",base.lower())
    mapped = _SKILL_SYNONYMS.get(key)
    if mapped: return mapped
    return re.sub(r"\s+"," ",base).strip().title()

# ─────────────────────────────────────────────────────────
# File text extraction
# ─────────────────────────────────────────────────────────
def extract_text_from_pdf(file) -> str:
    try:
        reader = PdfReader(file); chunks=[]
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
# Trade taxonomy — Seattle guidebook order (+ Lineman)
# Families used for dropdown. Specialties/Pathways only where it helps routing/boost plan.
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
    # Not in book, but required per your instruction:
    "High Voltage – Outside Lineman (NW Line JATC)",
    "Power Line Clearance Tree Trimmer (NW Line JATC)",
]

# ─────────────────────────────────────────────────────────
# Boost plans per trade (concise, app-readable). You can expand text anytime.
# Keep language neutral (resume objective stays union-agnostic).
# ─────────────────────────────────────────────────────────
BOOST: Dict[str, Dict[str, Any]] = {
    # pattern for each:
    # "Trade Name": {
    #   "certs": [ ... ],
    #   "hold_over_jobs": [ ... ],
    #   "pipelines_union": [ ... ],
    #   "pipelines_open": [ ... ],
    #   "math": "...",
    #   "notes": "...",
    # }
    "Electrician – Inside (01)": {
        "certs": [
            "OSHA-30 (Construction Outreach)",
            "Clean driving record; valid DL",
            "Basic hand/power tool proficiency",
        ],
        "hold_over_jobs": [
            "Electrical supplier/material handler",
            "Solar install helper (under supervision)",
            "Low-voltage helper (exposure to cabling, terminations)",
        ],
        "pipelines_union": [
            "Puget Sound Electrical JATC (IBEW/NECA) – Inside (01)",
            "Municipal utility apprenticeships (e.g., Electrician Constructor cycles)",
        ],
        "pipelines_open": [
            "ABC Western Washington – Electrical apprenticeship (01/02/06 routes)",
            "CITC – Electrical apprenticeship (verify ARTS listing)",
        ],
        "math": "Target algebra/geometry, measurement & conversions. Use local ABE/pre-college math for quick ramp.",
        "notes": "WA requires apprenticeship route for 01 licensing; keep resume objective neutral (no union/non-union labels)."
    },
    "Electrician – Limited Energy (06)": {
        "certs": [
            "OSHA-30",
            "Vendor micro-credentials helpful (fire alarm/CCTV/voice-data)",
        ],
        "hold_over_jobs": [
            "Security/Fire alarm install helper",
            "Data cabling tech helper",
        ],
        "pipelines_union": [
            "PSEJATC – Limited Energy (06)",
        ],
        "pipelines_open": [
            "ABC WW – Limited Energy",
            "CITC – Low-voltage/06",
        ],
        "math": "Basic DC concepts, low-voltage color codes, measurement.",
        "notes": "Keep objective neutral; do not say 'low-voltage' in the summary line."
    },
    "Electrician – Residential (02)": {
        "certs": ["OSHA-30"],
        "hold_over_jobs": ["Residential electrical helper", "Warehouse/parts runner"],
        "pipelines_union": ["PSEJATC – Residential (02)"],
        "pipelines_open": ["ABC WW – Residential", "CITC – Residential"],
        "math": "Algebra, measurement, basic circuits.",
        "notes": "Neutral objective."
    },
    "High Voltage – Outside Lineman (NW Line JATC)": {
        "certs": [
            "CDL-B (work toward CDL-A)",
            "OSHA-30",
            "First Aid/CPR (site standard)",
        ],
        "hold_over_jobs": [
            "Groundman with line contractors",
            "Traffic control (Flagger) on line projects",
            "Yard/utility material handler",
        ],
        "pipelines_union": [
            "NW Line JATC – Outside Lineman (regional)",
            "Seattle City Light – PAL → Line apprenticeship cycles",
        ],
        "pipelines_open": [
            "Direct-hire trainee roles with merit-shop line contractors (confirm job is legitimate; ARTS if they claim 'apprenticeship')"
        ],
        "math": "Strong arithmetic, ratios, mechanical reasoning; prep for CAST-style testing.",
        "notes": "Be climbing/fitness ready; travel likely. Keep resume objective neutral."
    },
    "Power Line Clearance Tree Trimmer (NW Line JATC)": {
        "certs": [
            "CDL-B permit early",
            "Intro to Arboriculture Safety (free micro-course)",
            "Pesticide study prep (WSU/WSDA manuals) if vegetation mgmt applies",
        ],
        "hold_over_jobs": [
            "Vegetation management groundworker",
            "Traffic control",
            "Yard/material staging for line crews",
        ],
        "pipelines_union": [
            "NW Line JATC – Tree Trimmer (year-round application; monthly ranking)"
        ],
        "pipelines_open": [
            "Direct-hire vegetation management companies; verify training & safety standards"
        ],
        "math": "Measurement & rigging ratios basics.",
        "notes": "Resume objective stays neutral; tree/line proximity work emphasizes safety and comms."
    },
    "Carpenter (General)": {
        "certs": ["OSHA-30", "Employer forklift eval on hire"],
        "hold_over_jobs": ["Framing helper", "Concrete formwork helper", "Warehouse/tool crib"],
        "pipelines_union": ["Western States Carpenters – JATC (regional)"],
        "pipelines_open": ["CITC – Carpentry"],
        "math": "Fractions, angles, layout (rise/run).",
        "notes": "Add rigging/fall-protection awareness modules where possible."
    },
    "Carpenter – Interior Systems": {
        "certs": ["OSHA-30", "MEWP (employer eval on hire)"],
        "hold_over_jobs": ["Drywall stocking/board hanger helper", "Acoustical ceiling install helper"],
        "pipelines_union": ["Western States Carpenters – Interior Systems"],
        "pipelines_open": ["CITC – Carpentry/Scaffold Erector"],
        "math": "Tape measure fluency, layout.",
        "notes": "ICRA (healthcare) awareness helps."
    },
    "Millwright": {
        "certs": ["OSHA-30"],
        "hold_over_jobs": ["Industrial maintenance helper", "Fabrication shop helper"],
        "pipelines_union": ["Carpenters/Millwright JATC"],
        "pipelines_open": ["Check ARTS for open-shop millwright sponsors"],
        "math": "Precision measurement.",
        "notes": "Welding/rigger basics stand out."
    },
    "Pile Driver": {
        "certs": ["OSHA-30", "MEWP (employer eval on hire)"],
        "hold_over_jobs": ["Marine yard helper", "Concrete/bridge prep"],
        "pipelines_union": ["Pile Drivers – UBC"],
        "pipelines_open": ["ARTS search for open-shop marine/pile apprenticeships"],
        "math": "Rigging angles, load basics.",
        "notes": "Water work readiness and fitness."
    },
    "Cement Mason (OPCMIA 528)": {
        "certs": ["OSHA-30"],
        "hold_over_jobs": ["Concrete placement/labor"],
        "pipelines_union": ["OPCMIA 528 apprenticeship"],
        "pipelines_open": ["ARTS check for cement mason open-shop sponsors"],
        "math": "Measurement, slopes/grades.",
        "notes": "Early morning starts; weather-ready."
    },
    "Drywall Finisher (IUPAT)": {
        "certs": ["OSHA-30", "MEWP (employer eval)"],
        "hold_over_jobs": ["Finisher helper", "Paint prep"],
        "pipelines_union": ["IUPAT finishing apprenticeship"],
        "pipelines_open": ["CITC – Painting (finish path)"],
        "math": "Measurement, batch ratios.",
        "notes": "Dust control & PPE habits."
    },
    "Elevator Constructor (IUEC/NEIEP)": {
        "certs": ["OSHA-30"],
        "hold_over_jobs": ["Mechanical/electrical helper roles, facilities maintenance"],
        "pipelines_union": ["NEIEP/Local 19 opportunities portal"],
        "pipelines_open": ["Rare open-shop; verify in ARTS if claimed"],
        "math": "Algebra/trig basics; precision layout.",
        "notes": "Customer-facing professionalism matters."
    },
    "Ironworker (Local 86)": {
        "certs": ["OSHA-30"],
        "hold_over_jobs": ["Rebar placing helper", "Fab shop helper"],
        "pipelines_union": ["Ironworkers Local 86 apprenticeship"],
        "pipelines_open": ["Check ARTS for open-shop ironworker/rebar sponsors"],
        "math": "Fractions, angles, reading simple details.",
        "notes": "Working at heights; fitness."
    },
    "Laborer (LIUNA 242/252/292)": {
        "certs": ["OSHA-30", "Flagger → Traffic Control Supervisor after hours"],
        "hold_over_jobs": ["TC/Flagging crews", "General site labor", "Erosion control"],
        "pipelines_union": ["Laborers JATC (by local)"],
        "pipelines_open": ["CITC – Construction Craft Laborer"],
        "math": "Basic measurement & production math.",
        "notes": "Great entry while ranking elsewhere."
    },
    "Operating Engineer (IUOE 302/612)": {
        "certs": ["OSHA-30", "CDL-A path helpful"],
        "hold_over_jobs": ["Equipment yard helper", "Civil labor with grading crews"],
        "pipelines_union": ["IUOE 302/612 apprenticeship"],
        "pipelines_open": ["CITC – Heavy Equipment Operator (if listed)"],
        "math": "Grade math, production math.",
        "notes": "Expect travel and outdoor work."
    },
    "Painter (IUPAT DC5)": {
        "certs": ["OSHA-30", "MEWP (employer eval)"],
        "hold_over_jobs": ["Prep/labor, warehouse tinting"],
        "pipelines_union": ["IUPAT DC5 – Painter"],
        "pipelines_open": ["CITC – Painting"],
        "math": "Ratios for mixing, coverage math.",
        "notes": "Customer-facing; finish quality."
    },
    "Plasterer (OPCMIA 528)": {
        "certs": ["OSHA-30"],
        "hold_over_jobs": ["Stucco/lath helper"],
        "pipelines_union": ["OPCMIA 528"],
        "pipelines_open": ["ARTS for open-shop plaster pathways"],
        "math": "Measurement, ratios.",
        "notes": "Exterior/weather work."
    },
    "Plumber / Steamfitter / HVAC-R (UA 32 / UA 26)": {
        "certs": ["EPA 608 (Universal)", "OSHA-30"],
        "hold_over_jobs": ["HVAC helper", "Plumbing warehouse/runner", "Sheet-metal shop helper"],
        "pipelines_union": ["UA 32/SAPT (King)", "UA 26 (Pierce/Snohomish)"],
        "pipelines_open": ["CITC – Plumbing/HVAC (verify ARTS listing)"],
        "math": "Fractions, pressure/temp basics, measurement.",
        "notes": "Service roles need DL/MVR; brazing helps."
    },
    "Roofer (Local 54/153)": {
        "certs": ["OSHA-30", "MEWP employer eval"],
        "hold_over_jobs": ["Roof tear-off/prep", "Materials hoisting"],
        "pipelines_union": ["Roofers Local 54 (King/Snohomish), 153 (Pierce)"],
        "pipelines_open": ["ARTS for open-shop roofing sponsors"],
        "math": "Squares/coverage math.",
        "notes": "Heights & weather stamina."
    },
    "Sheet Metal (SMART 66)": {
        "certs": ["OSHA-30", "EPA 608 for service track"],
        "hold_over_jobs": ["Duct shop helper", "Install helper"],
        "pipelines_union": ["SMART 66 JATC (fabrication/install/service/TAB)"],
        "pipelines_open": ["CITC – Sheet Metal"],
        "math": "Layout, measurement, basic geometry.",
        "notes": "Controls/service cross with electrical rules—keep objective neutral."
    },
    "Sprinkler Fitter (UA 699)": {
        "certs": ["OSHA-30"],
        "hold_over_jobs": ["Fire protection install helper", "Warehouse/pipe prep"],
        "pipelines_union": ["UA 699 – Sprinkler Fitter"],
        "pipelines_open": ["ARTS for open-shop sprinkler apprenticeships"],
        "math": "Measurement, prints reading basics.",
        "notes": "NICET later is valuable."
    },
    "Boilermaker (Local 104, 502)": {
        "certs": ["OSHA-30"],
        "hold_over_jobs": ["Shop fabrication helper", "Welder’s helper"],
        "pipelines_union": ["IBB Local 104 / 502"],
        "pipelines_open": ["ARTS for shop-based boilermaker/fab apprenticeships"],
        "math": "Blueprint basics, measurement.",
        "notes": "Welding certs make you stand out."
    },
    "Bricklayer / BAC Allied (Brick/Tile/Terrazzo/Marble/PCC)": {
        "certs": ["OSHA-30"],
        "hold_over_jobs": ["Masonry laborer", "Tile setter helper"],
        "pipelines_union": ["BAC 1 WA/AK"],
        "pipelines_open": ["ARTS for open-shop masonry/tile"],
        "math": "Layout, coverage math.",
        "notes": "Back/ergonomics awareness."
    },
    "Floor Layer (IUPAT)": {
        "certs": ["OSHA-30"],
        "hold_over_jobs": ["Flooring install helper", "Warehouse/tint"],
        "pipelines_union": ["IUPAT Floor Layers"],
        "pipelines_open": ["ARTS for open-shop floor covering"],
        "math": "Coverage & takeoff math.",
        "notes": "Customer-facing install work."
    },
    "Glazier (IUPAT 188)": {
        "certs": ["OSHA-30", "MEWP employer eval"],
        "hold_over_jobs": ["Glass shop helper", "Install helper"],
        "pipelines_union": ["Glaziers Local 188"],
        "pipelines_open": ["CITC – Glazier"],
        "math": "Measurement/reading shop drawings.",
        "notes": "Handling glass safely is key."
    },
    "Heat & Frost Insulator (Local 7)": {
        "certs": ["OSHA-30"],
        "hold_over_jobs": ["Mechanical insulation helper"],
        "pipelines_union": ["Local 7 – Insulators"],
        "pipelines_open": ["ARTS for open-shop insulation"],
        "math": "Measurement, layout.",
        "notes": "Industrial/jobsite PPE focus."
    },
}

# ─────────────────────────────────────────────────────────
# JD → hint bullets by trade (lightweight heuristics)
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

def suggest_bullets(text: str, trade: str) -> List[str]:
    low = (text or "").lower()
    hints = TRADE_HINTS.get(trade, {})
    out=[]
    for kw, stub in hints.items():
        if kw in low: out.append(stub)
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
        bs=[clean_bullet(b) for b in (self.bullets or []) if b.strip()]
        self.bullets = bs[:k]

@dataclass
class School:
    school:str=""; credential:str=""; year:str=""; details:str=""

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
    if body_strength:
        doc.add_paragraph("Highlights:")
        for line in split_list(body_strength):
            doc.add_paragraph(f"• {line}")

    doc.add_paragraph("")
    doc.add_paragraph("Thank you for your consideration. I’m ready to support your crew and learn the trade the right way.")
    doc.add_paragraph("")
    doc.add_paragraph("Sincerely,")
    doc.add_paragraph(data.get("name",""))

    bio = io.BytesIO(); doc.save(bio); bio.seek(0)
    return bio.getvalue()

def build_pathway_packet_docx(student: Dict[str,str], trade_label: str, app_type: str, sources: List[Any]) -> bytes:
    doc = DocxWriter()
    styles = doc.styles['Normal']; styles.font.name = 'Calibri'; styles.font.size = Pt(11)

    doc.add_heading("Instructor Pathway Packet", level=0)
    meta = f"Student: {student.get('name','')} | Target: {trade_label} | Application type: {app_type}"
    doc.add_paragraph(meta); doc.add_paragraph("")

    for upl in sources or []:
        doc.add_page_break()
        doc.add_heading(upl.name, level=1)
        text = extract_text_generic(upl)
        if text.strip():
            for line in text.splitlines():
                doc.add_paragraph(line)
        else:
            doc.add_paragraph("[Text could not be extracted from this file.]")

    out = io.BytesIO(); doc.save(out); out.seek(0)
    return out.getvalue()

# ─────────────────────────────────────────────────────────
# Sidebar — template & docs
# ─────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Templates & Docs")

    tpl_bytes=None
    if os.path.exists("resume_app_template.docx"):
        with open("resume_app_template.docx","rb") as f: tpl_bytes=f.read()
    upl_tpl = st.file_uploader("Upload RESUME DOCX template (optional)", type=["docx"])
    if upl_tpl is not None: tpl_bytes = upl_tpl.read()

    st.markdown("---")
    st.caption("Upload pathway/source docs (PDF/DOCX/TXT). Full text is embedded in the Instructor Packet.")
    pathway_uploads = st.file_uploader("Upload pathway documents", type=["pdf","docx","txt"], accept_multiple_files=True)

# ─────────────────────────────────────────────────────────
# Main UI — Workshop
# ─────────────────────────────────────────────────────────
st.title("Resume Workshop & Pathways (Seattle Tri-County)")

# 1) Target trade + application type
st.subheader("1) Target Trade & Application Type")
c1, c2 = st.columns([1,2])
with c1:
    application_type = st.radio("Applying for:", ["Apprenticeship","Job"], index=0, horizontal=True)
with c2:
    trade = st.selectbox("Trade (guidebook order + lineman):", TRADE_TAXONOMY, index=TRADE_TAXONOMY.index("Electrician – Inside (01)"))

# 2) Boost Plan (read-only guidance per trade)
st.subheader("2) Boost Plan (Do these to stand out)")
bp = BOOST.get(trade, {})
if not bp:
    st.info("Select a trade to view its Boost Plan.")
else:
    a,b = st.columns(2)
    with a:
        st.markdown("**Certifications / Prep**")
        for x in bp.get("certs", []): st.write(f"- {x}")
        st.markdown("**Hold-over Jobs (while you apply/rank)**")
        for x in bp.get("hold_over_jobs", []): st.write(f"- {x}")
        st.markdown("**Math / Study Focus**")
        st.write(bp.get("math",""))
    with b:
        st.markdown("**Pipelines — Union**")
        for x in bp.get("pipelines_union", []): st.write(f"- {x}")
        st.markdown("**Pipelines — Open-shop**")
        for x in bp.get("pipelines_open", []): st.write(f"- {x}")
        st.markdown("**Notes**")
        st.write(bp.get("notes",""))

# 3) Upload job descriptions/postings (optional)
st.subheader("3) Upload Job Descriptions / Postings (optional)")
uploads = st.file_uploader("Upload one or more files (PDF/DOCX/TXT). We’ll mine light hints.", type=["pdf","docx","txt"], accept_multiple_files=True)
jd_text = ""
if uploads:
    for f in uploads:
        jd_text += "\n" + extract_text_generic(f)

# 4) Contact & objective
with st.form("workshop"):
    st.subheader("4) Contact & Objective")
    c1, c2 = st.columns(2)
    with c1:
        Name = st.text_input("Name","")
        City = st.text_input("City","")
        State = st.text_input("State (2-letter)","")
        Phone = st.text_input("Phone","")
        Email = st.text_input("Email","")
    with c2:
        default_role = f"{trade} pre-apprentice" if application_type=="Apprenticeship" else f"Entry-level {trade}"
        Obj_Seeking = st.text_input("Target role (neutral wording):", default_role)
        Obj_Quality = st.text_input("One strength to highlight:", "safety mindset")
        Objective_Final = st.text_area("Final objective (1–2 sentences):",
            "I’m seeking hands-on experience as an entry-level contributor in construction, bringing a safety mindset, reliability, and readiness to learn.")

    # 5) Skills
    st.subheader("5) Skills")
    quick_transfer = st.multiselect("Quick add transferable skills:", SKILL_CANON, default=[])
    Skills_Transferable = st.text_area("Transferable Skills (comma/newline):","")
    Skills_JobSpecific = st.text_area("Job-Specific Skills (comma/newline):","")
    Skills_SelfManagement = st.text_area("Self-Management Skills (comma/newline):","")

    # 6) Work Experience
    st.subheader("6) Work Experience (up to 3)")
    job_blocks=[]
    jd_defaults = suggest_bullets(jd_text, trade) if jd_text else []
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
            defaults = "\n".join(jd_defaults) if (idx==1 and jd_defaults) else ""
            JobDuties  = st.text_area(f"Job {idx} – Duties/Accomplishments (1–4 bullets):", key=f"J{idx}du", value=defaults, placeholder=placeholder)
        job_blocks.append((JobCompany, JobCitySt, JobDates, JobTitle, JobDuties))

    # 7) Certifications
    st.subheader("7) Certifications")
    default_certs = "OSHA-10, Flagger (WA), Forklift operator (employer eval required on hire)"
    Certifications = st.text_area("List certifications (comma/newline).", default_certs)

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

    # 10) Cover Letter
    st.subheader("10) Cover Letter")
    CL_Company = st.text_input("Company/Employer (for the letter):","")
    CL_Role    = st.text_input("Role Title (for the letter):", default_role)
    CL_Location= st.text_input("Company Location (City, State):","")
    CL_Highlights = st.text_area("Optional: bullet highlights (comma/newline):","Reliable • Safety-focused • Coachable")

    submitted = st.form_submit_button("Generate Resume + Cover Letter + Instructor Packet", type="primary")

# ─────────────────────────────────────────────────────────
# Build → Export
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

    # Intake dict
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

    trade_label = trade

    # Resume via template
    if not tpl_bytes:
        st.error("Template not found. Put resume_app_template.docx in the repo or upload it in the sidebar.")
        st.stop()
    try:
        resume_ctx = build_resume_context(form, trade_label)
        resume_bytes = render_docx_with_template(tpl_bytes, resume_ctx)
    except Exception as e:
        st.error(f"Resume template rendering failed: {e}")
        st.stop()

    # Cover letter
    cover_bytes = build_cover_letter_docx({
        "name": Name, "city": City, "state": State, "phone": clean_phone(Phone), "email": clean_email(Email),
        "company": CL_Company, "role": CL_Role, "location": CL_Location,
        "trade_label": trade_label, "strength": CL_Highlights,
        "application_type": application_type,
    })

    # Instructor Packet (full text)
    packet_bytes = build_pathway_packet_docx({"name": Name}, trade_label, application_type, pathway_uploads)

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

    # Intake CSV snapshot
    buf=io.StringIO(); w=csv.writer(buf); fields=list(form.keys()); w.writerow(fields); w.writerow([form[k] for k in fields])
    st.download_button("Download Intake CSV", data=buf.getvalue().encode("utf-8"),
                       file_name=f"{safe_name}_Workshop_Intake.csv", mime="text/csv",
                       use_container_width=True)
    st.success("Files generated. Objective/letter sanitized to avoid union/non-union or sub-trade labels.")
