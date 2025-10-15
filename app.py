# ─────────────────────────────────────────────────────────
# Header parsing (v2): more tolerant, scans wider, better name pick
# ─────────────────────────────────────────────────────────
def parse_header(text: str) -> Dict[str,str]:
    if not text:
        return {"Name":"", "Email":"", "Phone":"", "City":"", "State":""}

    # Normalize: collapse fancy bullets/separators to pipes for easy tokening
    top_block = "\n".join([l.strip() for l in (text or "").splitlines()[:50]])
    sep_norm = re.sub(r"[•·–—\-•/]+", "|", top_block)

    # Email/phone anywhere in the full doc (fallback)
    email = ""
    m = EMAIL_RE.search(text or "")
    if m:
        email = m.group(0)
    phone = ""
    m = PHONE_RE.search(text or "")
    if m:
        phone = m.group(0)

    # Try to grab city/state from the top first; fallback to anywhere
    city = ""; state = ""
    mcs_top = CITY_STATE_RE.search(top_block)
    if mcs_top:
        city, state = mcs_top.group(1), mcs_top.group(2).upper()
    else:
        mcs_any = CITY_STATE_RE.search(text or "")
        if mcs_any:
            city, state = mcs_any.group(1), mcs_any.group(2).upper()

    # Name hunting: look at top lines that are not section headings, not contact tokens
    name = ""
    candidates = []
    for raw in sep_norm.split("\n"):
        line = raw.strip().strip("|").strip()
        if not line: 
            continue
        # skip lines that are obviously contact or headings
        if EMAIL_RE.search(line) or PHONE_RE.search(line):
            continue
        if re.search(r"\b(objective|summary|skills|experience|education|certifications)\b", line, re.I):
            continue
        # good name candidates: 2–4 tokens, initial-capped words, no digits
        toks = [t for t in re.split(r"\s+", line) if t]
        if 2 <= len(toks) <= 4 and not any(re.search(r"\d", t) for t in toks):
            caps = sum(t[:1].isalpha() and t[:1].isupper() for t in toks)
            if caps >= 2:
                candidates.append(line)
    if candidates:
        name = candidates[0]
    else:
        # last resort: very first non-empty non-heading line
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
