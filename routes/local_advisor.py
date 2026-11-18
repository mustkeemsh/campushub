"""
CollegeHub local advisor (no API key needed).

Answers questions about Maharashtra engineering colleges from:
  1. scraped_institutes.json  - the CAP institute list (373 colleges: code, district, region,
                                intake, status, university, address, minority/autonomy)
  2. The CollegeHub database  - cutoffs, fees and placements when they are available
  3. A built-in primer         - how MHT-CET / JEE / CAP admissions work in Maharashtra

It never invents figures: anything it does not have, it says it does not have.
"""
import os
import re
import gzip
import json
import html
import difflib
import threading

from database import db

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_FILE = os.path.join(BASE_DIR, 'scraped_institutes.json')
KB_FILE = os.path.join(BASE_DIR, 'assets', 'data', 'chatbot_cutoffs.json.gz')

_lock = threading.Lock()
_cache = {"colleges": None, "vocab": set(), "districts": set(), "regions": set(), "universities": {}}

# words that are part of almost every college name or are intent words, never identify one college
_GENERIC = {
    'college', 'colleges', 'engineering', 'engineeering', 'engg', 'institute', 'institutes', 'of', 'the', 'and', 'for',
    'technology', 'technological', 'technical', 'science', 'sciences', 'education', 'educational', 'society',
    'societys', 'trust', 'in', 'maharashtra', 'university', 'autonomous', 'research', 'reserch', 'management',
    'polytechnic', 'shri', 'sri', 'smt', 'dr', 'mrs', 'mr', 'at', 'a', 'an', 'to', 'is', 'are', 'ltd', 'pvt',
    'govt', 'government', 'private', 'campus', 'off', 'tal', 'dist', 'post', 'academy', 'foundation', 'charitable',
    'sanstha', 'mandal', 'vidya', 'vidyalaya', 'mahavidyalaya', 'branch', 'computer', 'mechanical', 'civil',
    'electrical', 'electronics', 'information', 'data', 'artificial', 'intelligence', 'machine', 'learning',
    'telecommunication', 'instrumentation', 'chemical', 'production', 'biotechnology', 'cse', 'entc', 'extc',
    'it', 'aiml', 'ai', 'ds', 'mech', 'tell', 'about', 'me', 'give', 'show', 'details', 'detail', 'info',
    'information', 'cutoff', 'cutoffs', 'fee', 'fees', 'placement', 'placements', 'hostel', 'admission',
    'admissions', 'seats', 'seat', 'intake', 'address', 'location', 'website', 'contact', 'phone', 'what', 'which',
    'where', 'how', 'is', 'there', 'any', 'best', 'top', 'good', 'list', 'near', 'around', 'all', 'my', 'i',
    'can', 'get', 'with', 'percentile', 'rank', 'mht', 'cet', 'jee', 'cap', 'round', 'please', 'you', 'your',
    'do', 'does', 'have', 'has', 'are', 'was', 'be', 'on', 'or', 'that', 'this', 'it', 'its', 'by', 'from',
    'tuition', 'cost', 'package', 'packages', 'salary', 'review', 'reviews', 'rating', 'ranking', 'rankings',
    'number', 'many', 'count', 'total', 'name', 'names', 'want', 'need', 'looking', 'find', 'search', 'exist',
    'available', 'offer', 'offers', 'course', 'courses', 'btech', 'be', 'degree', 'bachelor', 'year', 'first',
}

_BRANCH_WORDS = ['computer', 'mechanical', 'civil', 'electrical', 'electronics', 'information technology',
                 'artificial intelligence', 'data science', 'chemical', 'instrumentation', 'production']

_COLLEGE_ALIASES = {
    'vit': 'vishwakarma institute of technology', 'viit': 'vishwakarma institute of information technology',
    'spit': 'sardar patel institute of technology', 'pict': 'pune institute of computer technology',
    'coep': 'coep technological', 'vjti': 'veermata jijabai', 'rit': 'rajarambapu institute of technology',
    'kjsce': 'somaiya college of engineering', 'mitaoe': 'mit academy of engineering', 'ycce': 'yeshwantrao chavan',
    'gcoea': 'government college of engineering, amravati', 'dypcoe': 'd. y. patil college of engineering',
    'scoe': 'sinhgad college of engineering', 'wce': 'walchand college of engineering',
}

_UNI_ALIASES = {'mu': 'mumbai university', 'bombay': 'mumbai university', 'pune university': 'savitribai phule pune university',
                'nagpur university': 'rashtrasant tukadoji maharaj nagpur university',
                'amravati university': 'sant gadge baba amravati university'}


def _tok(text):
    return re.findall(r'[a-z0-9]+', (text or '').lower())


def _clean(text):
    return re.sub(r'\s+', ' ', html.unescape(text or '')).strip()


def _initials(words, drop=()):
    return ''.join(w[0] for w in words if w and w not in drop)


def _load():
    with _lock:
        if _cache["colleges"] is not None:
            return _cache["colleges"]
        colleges = []
        try:
            import json
            with open(DATA_FILE, encoding='utf-8') as fh:
                raw = json.load(fh)
        except Exception as exc:
            print(f"[local_advisor] could not read {DATA_FILE}: {exc}")
            raw = {}
        districts, regions, unis, vocab = set(), set(), {}, set()
        for code, v in raw.items():
            name = _clean(v.get('name'))
            if not name:
                continue
            uni = _clean(v.get('university'))
            district = _clean(v.get('district'))
            region = _clean(v.get('region'))
            words = _tok(name)
            col = {
                "code": str(code), "name": name, "status": _clean(v.get('status')),
                "intake": v.get('total_intake') or 0, "address": _clean(v.get('address')),
                "district": district, "region": region, "autonomy": _clean(v.get('autonomy')),
                "minority": _clean(v.get('minority')), "university": uni,
                "tokens": set(words),
                "acronyms": {_initials(words), _initials(words, ('of', 'the', 'and', 'for', 'in', 's'))} - {''},
            }
            colleges.append(col)
            if district:
                districts.add(district.lower())
            if region:
                regions.add(region.lower())
            if uni:
                unis.setdefault(uni.lower(), uni)
        loc_words = set()
        for place in districts | regions:
            loc_words.update(_tok(place))
        for c in colleges:
            vocab |= {t for t in c["tokens"] if t not in _GENERIC and t not in loc_words and len(t) > 2 and not t.isdigit()}
        _cache.update(colleges=colleges, vocab=vocab, districts=districts, regions=regions,
                      universities=unis, loc_words=loc_words)
        return colleges


# ---------------------------------------------------------------------------
# Finding colleges / places in a question
# ---------------------------------------------------------------------------
def _find_colleges(query):
    colleges = _load()
    if not colleges:
        return [], []
    vocab, loc_words = _cache["vocab"], _cache["loc_words"]
    q_tokens = _tok(query)

    # 1) exact institute code (e.g. 06298 / 6298)
    for t in q_tokens:
        if t.isdigit() and 4 <= len(t) <= 5:
            hit = [c for c in colleges if c["code"].lstrip('0') == t.lstrip('0')]
            if hit:
                return hit, []

    # 2a) well-known short names (VIT, SPIT, PICT, WCE ...)
    for t in q_tokens:
        if t in _COLLEGE_ALIASES:
            sub = _COLLEGE_ALIASES[t]
            hit = [c for c in colleges if sub in c["name"].lower()]
            if hit:
                return hit[:6], []

    # 2) acronyms (COEP, VJTI, SPIT, PICT, VIT ...) - only when not an everyday word
    acr_hits = []
    for t in q_tokens:
        if 3 <= len(t) <= 8 and t not in _GENERIC:
            acr_hits += [c for c in colleges if t in c["acronyms"] or t == c["name"].split()[0].lower().strip(',')
                         and t in {'coep', 'vjti', 'spit', 'pict'}]
    if acr_hits:
        uniq = list({c["code"]: c for c in acr_hits}.values())
        if len(uniq) <= 6:
            return uniq, []

    # 3) distinctive name words (fuzzy for typos). Place words (district names) are not used to identify a college
    keep = []
    for t in q_tokens:
        if t in _GENERIC or t in loc_words or t.isdigit() or len(t) < 3:
            continue
        if difflib.get_close_matches(t, list(_GENERIC), n=1, cutoff=0.86):
            continue
        if t in vocab:
            keep.append(t)
        else:
            m = difflib.get_close_matches(t, list(vocab), n=1, cutoff=0.84) if len(t) >= 5 else []
            if m:
                keep.append(m[0])
    if not keep:
        return [], []
    matches = [c for c in colleges if all(k in c["tokens"] for k in keep)]
    if not matches and len(keep) > 1:
        matches = [c for c in colleges if sum(k in c["tokens"] for k in keep) >= len(keep) - 1 and any(k in c["tokens"] for k in keep)]
    # if the question also names a place, use it to narrow down
    place = [t for t in q_tokens if t in loc_words]
    if place and len(matches) > 1:
        narrowed = [c for c in matches if any(p in _tok(c["district"] + ' ' + c["region"] + ' ' + c["name"] + ' ' + c["address"]) for p in place)]
        matches = narrowed or matches
    return matches, keep


def _find_places(query):
    _load()
    q = ' ' + ' '.join(_tok(query)) + ' '
    districts = sorted(d for d in _cache["districts"] if (' ' + d + ' ') in q)
    regions = sorted(r for r in _cache["regions"] if (' ' + r + ' ') in q)
    return districts, regions


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------
def _seats(n):
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return "n/a"


def _db_cutoff_lines(col, branch_filter=None, limit=6):
    """Optional: cutoffs from the CollegeHub database for this college, if it has been imported."""
    try:
        inst = db.get_institute_by_code(col["code"]) or db.get_institute_by_code(col["code"].lstrip('0'))
        if not inst:
            return []
        details = db.get_institute_details(inst.get("id"), published_only=True) or {}
    except Exception:
        return []
    lines = []
    for course in details.get("courses", []):
        label = f"{course.get('course_name')} {course.get('branch') or ''}".lower()
        if branch_filter and not any(b in label for b in branch_filter):
            continue
        cuts = sorted(course.get("cutoffs") or [], key=lambda x: (x.get("cap_round") or 0))
        for x in cuts[:3]:
            lines.append(f"- {course.get('course_name')}: {x.get('category')} / {x.get('seat_pool')}, CAP round {x.get('cap_round')}: "
                         f"**{x.get('cutoff_value')}** {x.get('cutoff_type') or ''} ({x.get('academic_year')})")
        if len(lines) >= limit:
            break
    return lines[:limit]


def _db_extra_lines(col):
    """Fees / placements / contacts from the CollegeHub database (not in the CAP files), if imported."""
    try:
        inst = db.get_institute_by_code(col["code"]) or db.get_institute_by_code(col["code"].lstrip('0'))
        if not inst:
            return []
        d = db.get_institute_details(inst.get("id"), published_only=True) or {}
    except Exception:
        return []
    lines = []
    for p in (d.get("placement_stats") or [])[:4]:
        lines.append(f"- Placement ({p.get('academic_year')}): {p.get('metric_type')} package {_fmt_money(p.get('amount'))}")
    seen = set()
    for course in d.get("courses", []):
        for f in (course.get("fees") or [])[:2]:
            key = (f.get('fee_component'), f.get('amount'))
            if key not in seen and len(seen) < 4:
                seen.add(key)
                lines.append(f"- Fee ({course.get('course_name')}): {f.get('fee_component')} {_fmt_money(f.get('amount'))} ({f.get('academic_year')})")
    for c in (d.get("contacts") or [])[:2]:
        lines.append(f"- Contact ({c.get('contact_type')}): {c.get('contact_value')}")
    if d.get("institute", {}).get("website"):
        lines.append(f"- Website: {d['institute']['website']}")
    return lines


def _fmt_money(v):
    try:
        return f"INR {int(float(v)):,}"
    except (TypeError, ValueError):
        return str(v)


def _college_card(col, want_cutoff=False, branch_filter=None):
    parts = [f"**{col['name']}** (code {col['code']})",
             f"- Location: {col['address']}" + (f" ({col['district']} district, {col['region']} CAP region)" if col['district'] else ""),
             f"- Type: {col['status']}" + (f" | Minority status: {col['minority']}" if col['minority'] and col['minority'] != 'Non-Minority' else ""),
             f"- University: {col['university'] or 'n/a'}",
             f"- Total sanctioned intake (all branches): {_seats(col['intake'])} seats"]
    kb_courses = _cache_courses(_kb_code(col)) if _kb_code(col) else []
    if kb_courses:
        names = sorted({nm for _, nm in kb_courses})
        shown = ", ".join(names[:8]) + (f" and {len(names) - 8} more" if len(names) > 8 else "")
        parts.append(f"- Branches in CAP 2025-26 ({len(names)}): {shown}")
        parts.append("Ask me for this college's cutoff (e.g. \"cutoff for computer OBC\") to see round-wise percentiles.")
        extra_db = _db_extra_lines(col)
        if extra_db:
            parts.append("More details in CollegeHub:")
            parts += extra_db
        return "\n".join(parts)
    extra = _db_cutoff_lines(col, branch_filter)
    if extra:
        parts.append("Cutoffs verified in CollegeHub:")
        parts += extra
    elif want_cutoff:
        parts.append("I don't have verified branch-wise cutoffs for this college loaded yet. Check the **College Predictor** page, or the official CAP cutoff lists on cetcell.mahacet.org.")
    return "\n".join(parts)


def _list_colleges(cols, limit=8):
    cols = sorted(cols, key=lambda c: -(c["intake"] or 0))
    return "\n".join(f"- {c['name']} ({c['district']}, intake {_seats(c['intake'])}, code {c['code']})" for c in cols[:limit])


def _status_filters(query):
    q = query.lower()
    f = []
    if 'government' in q or 'govt' in q:
        f.append(lambda c: c['status'].lower().startswith(('government', 'university')))
    if 'autonomous' in q:
        f.append(lambda c: 'autonomous' in c['status'].lower() and 'non' not in c['autonomy'].lower())
    if 'minority' in q:
        f.append(lambda c: 'minority' in c['status'].lower())
    if 'private' in q or 'un-aided' in q or 'unaided' in q:
        f.append(lambda c: c['status'].lower().startswith('un-aided'))
    return f


# ---------------------------------------------------------------------------
# Built-in admissions primer (general, non time-sensitive)
# ---------------------------------------------------------------------------
_VERIFY = "\n\nRules and dates change every year, so always confirm on the official CET Cell website (cetcell.mahacet.org) or the current admission brochure."

_TOPICS = [
    (('cap round', 'cap rounds', 'centralized admission', 'centralised admission', 'admission process', 'how to apply', 'how admission'),
     "**How CAP (Centralized Admission Process) works in Maharashtra**\n"
     "- Register on the State CET Cell admission portal and upload documents for verification.\n"
     "- A provisional, then final, merit list is published (based on MHT-CET percentile, or JEE Main for All India seats).\n"
     "- You fill an **option form** listing college + branch choices in order of preference.\n"
     "- Seats are allotted in **CAP rounds** (usually 3 to 4 rounds). After each round you can accept, freeze, or try for a better option in the next round.\n"
     "- After the CAP rounds, remaining seats are filled at institute level." + _VERIFY),
    (('tfws', 'tuition fee waiver'),
     "**TFWS (Tuition Fee Waiver Scheme)** is a government scheme that waives tuition fees for a small share of seats in eligible colleges. "
     "It is meant for meritorious students whose family income is within the limit set that year, and an income certificate is needed. "
     "You apply for it during CAP registration." + _VERIFY),
    (('ews',),
     "**EWS (Economically Weaker Section)** is a reservation for students from the open/general category whose family income is below the prescribed limit. "
     "You need a valid EWS certificate when you apply." + _VERIFY),
    (('home university', 'other than home', 'state level', 'ohu', 'seat type', 'seat types'),
     "**Seat types in Maharashtra CAP**\n"
     "- **Home University (HU)**: seats for students whose HSC/district falls under the university the college belongs to.\n"
     "- **Other Than Home University (OHU)**: seats for students from the other universities of Maharashtra.\n"
     "- **State Level (SL)**: seats open to all Maharashtra candidates, and some institute-level or all-India quota seats.\n"
     "The same college can have different cutoffs for each seat type." + _VERIFY),
    (('document', 'documents', 'certificate', 'certificates'),
     "**Documents usually needed for admission**\n"
     "- SSC and HSC (12th) marksheets, leaving/transfer certificate\n"
     "- MHT-CET and/or JEE Main scorecard\n"
     "- Domicile / nationality certificate and Aadhaar\n"
     "- For reserved categories: caste certificate and validity certificate, plus non-creamy layer certificate where applicable (OBC, VJ/NT, SEBC)\n"
     "- Income certificate (for EWS / TFWS) and passport-size photos" + _VERIFY),
    (('eligib', 'qualification', 'minimum marks', 'who can apply'),
     "**Eligibility for B.E. / B.Tech in Maharashtra (typical)**\n"
     "- Passed 12th (HSC) with Physics and Mathematics plus Chemistry, Biotechnology, Biology or a technical/vocational subject.\n"
     "- Minimum marks in PCM are usually 45% (relaxed to 40% for reserved categories from Maharashtra).\n"
     "- A valid **MHT-CET** score (or **JEE Main** for All India seats)." + _VERIFY),
    (('percentile', 'rank'),
     "**Percentile vs rank**: MHT-CET results are given as a *percentile* (it shows how many candidates you scored above, adjusted across exam sessions). "
     "CAP cutoffs in Maharashtra are mostly published as percentile, and a merit rank is derived from it. "
     "A higher percentile means a better chance at top colleges, but cutoffs vary by branch, category, seat type and CAP round." + _VERIFY),
    (('mht', 'cet', 'jee'),
     "**MHT-CET vs JEE Main**: MHT-CET is the Maharashtra state entrance exam used for most CAP seats. JEE Main is used for All India quota seats and for institutes like NITs/IIITs (through JoSAA). "
     "Many students write both. Maharashtra colleges mainly use MHT-CET percentile for state seats." + _VERIFY),
    (('dsy', 'direct second year', 'diploma'),
     "**Direct Second Year (DSY)**: diploma holders can join B.E./B.Tech directly in the 2nd year through a separate CAP process with its own merit list and cutoffs. "
     "CollegeHub's College Predictor has a DSY mode, where you can check your options." + _VERIFY),
    (('category', 'categories', 'reservation', 'obc', 'sebc', 'vj', 'nt1', 'nt2', 'nt3'),
     "**Admission categories in Maharashtra CAP** include Open (General), SC, ST, VJ/DT-A, NT-B, NT-C, NT-D, OBC, SEBC and EWS, and separate TFWS and defence/minority seats. "
     "Your category must be backed by the right certificates. Cutoffs are published separately for each category." + _VERIFY),
    (('scholarship', 'scholarships', 'freeship'),
     "**Scholarships**: Maharashtra students from reserved categories and economically weaker families can apply for government scholarships and fee reimbursement schemes through the state's MahaDBT portal. "
     "TFWS also covers tuition fees for eligible students. Many colleges add their own merit scholarships." + _VERIFY),
    (('option form', 'preference', 'preferences', 'choice filling', 'how to choose', 'which college should'),
     "**Tips for filling the option form**\n"
     "- List more options than you think you need, and order them by *your* preference, not just by cutoff.\n"
     "- Mix ambitious, likely and safe choices (use last year's cutoffs from the College Predictor as a guide).\n"
     "- Compare branch, placements, location, fees and hostel, not only the college name.\n"
     "- Keep a few government or autonomous colleges as safe options." + _VERIFY),
    (('cutoff', 'cutoffs', 'cut off', 'closing', 'predict'),
     "**Cutoffs** are the last admitted percentile (or rank) for a branch, category and seat type in a CAP round. "
     "Use the **College Predictor** page (/recommendations) to see which colleges match your percentile, category and branch. "
     "Remember that last year's cutoffs are a guide, not a guarantee." + _VERIFY),
]

_GREETING = re.compile(r'^\s*(hi|hello|hey|hii+|namaste|good (morning|afternoon|evening)|thanks|thank you|ok|okay)\b[\s!.?]*$', re.I)


def _primer_answer(query):
    q = ' ' + query.lower() + ' '
    for keys, text in _TOPICS:
        for k in keys:
            if (' ' + k) in q:
                return text
    return None


# ---------------------------------------------------------------------------
# Cutoff knowledge base (built from the official CAP PDFs by scripts/build_chatbot_kb.py)
# ---------------------------------------------------------------------------
_kb_cache = {"kb": None, "by_college": None}

_CATEGORY_WORDS = {
    'open': 'OPEN', 'general': 'OPEN', 'gen': 'OPEN', 'sc': 'SC', 'st': 'ST', 'vj': 'VJ', 'vjda': 'VJ', 'dt': 'VJ',
    'nt1': 'NT1', 'ntb': 'NT1', 'nt2': 'NT2', 'ntc': 'NT2', 'nt3': 'NT3', 'ntd': 'NT3', 'obc': 'OBC',
    'sebc': 'SEBC', 'ews': 'EWS', 'tfws': 'TFWS',
}
_CATEGORY_LABEL = {'OPEN': 'Open', 'SC': 'SC', 'ST': 'ST', 'VJ': 'VJ/DT', 'NT1': 'NT-B', 'NT2': 'NT-C', 'NT3': 'NT-D',
                   'OBC': 'OBC', 'SEBC': 'SEBC', 'EWS': 'EWS', 'TFWS': 'TFWS'}
_POOL_LABEL = {'SL': 'State Level', 'HH': 'Home University seats', 'OO': 'Other-than-Home-University seats',
               'HO': 'Home Univ. seats (other-univ. candidates)', 'OH': 'Other-univ. seats (home-univ. candidates)'}

# branch keyword in the question -> text that must appear in the course name
_BRANCH_MAP = [
    (r'\b(cse|computer science|computer engineering|computer)\b', 'computer'),
    (r'\binformation technology\b|\bit (branch|course|engineering|cutoff|seats)\b', 'information technology'),
    (r'\b(aiml|ai ?& ?ml|artificial intelligence|machine learning|ai)\b', 'artificial intelligence'),
    (r'\b(data science|ai ?& ?ds|aids)\b', 'data science'),
    (r'\b(entc|extc|e&tc|electronics (and|&) telecom\w*)\b', 'electronics and telecommunication'),
    (r'\belectronics\b', 'electronics'),
    (r'\belectrical\b', 'electrical'),
    (r'\b(mechanical|mech)\b', 'mechanical'),
    (r'\bcivil\b', 'civil'),
    (r'\bchemical\b', 'chemical'),
    (r'\binstrumentation\b', 'instrumentation'),
    (r'\bproduction\b', 'production'),
    (r'\bbio ?technology\b', 'biotechnology'),
    (r'\bbio ?medical\b', 'biomedical'),
    (r'\bautomobile\b', 'automobile'),
    (r'\brobotics\b', 'robotics'),
    (r'\b(aeronautical|aerospace)\b', 'aero'),
]


def _kb():
    if _kb_cache["kb"] is not None:
        return _kb_cache["kb"] or None
    with _lock:
        if _kb_cache["kb"] is None:
            try:
                with gzip.open(KB_FILE, 'rt', encoding='utf-8') as fh:
                    kb = json.load(fh)
                by_college = {}
                for choice, name in kb.get('courses', {}).items():
                    code = choice[:5] if choice[:5] in kb['colleges'] else choice[:4].zfill(5)
                    by_college.setdefault(code, []).append((choice, name))
                _kb_cache["by_college"] = by_college
                _kb_cache["kb"] = kb
            except Exception as exc:
                print(f"[local_advisor] cutoff knowledge base not available ({exc}). "
                      f"Run: python scripts/build_chatbot_kb.py")
                _kb_cache["kb"] = {}
    return _kb_cache["kb"] or None


def _kb_code(col):
    """Map a scraped institute record to the 5-digit code used in the CAP cutoff PDFs."""
    kb = _kb()
    if not kb:
        return None
    code = col["code"].zfill(5)
    return code if code in kb["colleges"] else None


def _branch_terms(query):
    q = query.lower()
    terms = []
    for pat, term in _BRANCH_MAP:
        if re.search(pat, q) and term not in terms:
            terms.append(term)
    return terms


def _category_gender(query):
    toks = _tok(query)
    cat = next((_CATEGORY_WORDS[t] for t in toks if t in _CATEGORY_WORDS and not (t == 'st' and 'tfws' in toks)), None)
    gender = 'L' if re.search(r'\b(girl|girls|female|ladies|lady|woman|women)\b', query.lower()) else 'G'
    return cat, gender


def _find_percentile(query):
    q = query.lower()
    m = (re.search(r'(\d{2,3}(?:\.\d+)?)\s*(?:%ile|percentile|percentiles|percent|%|pr\b)', q)
         or re.search(r'percentile\s*(?:of|is|was|:)?\s*(\d{2,3}(?:\.\d+)?)', q))
    if m:
        v = float(m.group(1))
        if 0 < v <= 100:
            return v
    return None


def _course_cells(choice, cat, gender, rounds=('1', '2', '3', '4')):
    """{pool: {round: (seat_code, rank, pct)}} for the category, using the G/L seat column the student needs."""
    kb = _kb()
    out = {}
    codes = [cat] if cat in ('EWS', 'TFWS') else [f"{gender}{cat}{sfx}" for sfx in 'SHO']
    for r in rounds:
        pools = kb['rounds'].get(r, {}).get(choice, {})
        for pool, seats in pools.items():
            for code in codes:
                if code in seats:
                    rank, pct = seats[code]
                    out.setdefault(pool, {})[r] = (code, rank, pct)
    return out


def _fmt_cells(cells):
    lines = []
    for pool in ('SL', 'HH', 'OO', 'HO', 'OH'):
        if pool not in cells:
            continue
        per = cells[pool]
        seq = " | ".join(f"R{r} {per[r][2]:.2f}" for r in sorted(per))
        last = per[max(per)]
        lines.append(f"- {_POOL_LABEL[pool]}: {seq} percentile (latest rank {last[1]:,}, seat {last[0]})")
    return lines


def _cutoff_text(col, query, user_pct=None):
    """Branch-wise cutoffs for one college from the CAP 2025-26 lists."""
    kb = _kb()
    code = _kb_code(col)
    if not kb or not code:
        return None
    courses = _cache_courses(code)
    if not courses:
        return None
    terms = _branch_terms(query)
    cat, gender = _category_gender(query)
    cat_used = cat or 'OPEN'
    if terms:
        picked = [(ch, nm) for ch, nm in courses if any(t in nm.lower() for t in terms)]
    else:
        picked = list(courses)
    if not picked:
        names = ", ".join(sorted({nm for _, nm in courses})[:12])
        return (f"**{col['name']}** has no matching branch in the 2025-26 CAP list. Branches it offers: {names}.")

    label = f"{_CATEGORY_LABEL[cat_used]}{' (ladies)' if gender == 'L' and cat_used not in ('EWS', 'TFWS') else ''}"
    head = f"**{col['name']}**: CAP 2025-26 cutoffs for **{label}** category (percentile; higher = tougher)"
    body = []
    if len(picked) > 4:
        rows = []
        for ch, nm in picked:
            cells = _course_cells(ch, cat_used, gender)
            pref = cells.get('SL') or next(iter(cells.values()), None)
            if pref:
                last = pref[max(pref)]
                rows.append((last[2], nm, last[1], max(pref)))
        if not rows:
            return head + f"\nNo {label} cutoffs were published for this college."
        rows.sort(reverse=True)
        body = [f"- {nm}: {pct:.2f} (CAP round {r}, rank {rank:,})" for pct, nm, rank, r in rows[:12]]
        body.append("Name a branch (e.g. \"computer\" or \"mechanical\") to see all rounds and seat types.")
    else:
        for ch, nm in picked:
            cells = _course_cells(ch, cat_used, gender)
            body.append(f"**{nm}**")
            lines = _fmt_cells(cells)
            body += lines or [f"- No {label} cutoff was published for this branch."]
            if user_pct is not None and cells:
                pref = cells.get('SL') or next(iter(cells.values()))
                best = max(v[2] for v in pref.values())
                worst = min(v[2] for v in pref.values())
                if user_pct >= best:
                    body.append(f"- Your {user_pct:g} percentile is above every round's cutoff here, so this looks reachable.")
                elif user_pct >= worst:
                    body.append(f"- Your {user_pct:g} percentile is within range of the later-round cutoffs, so it is possible but not certain.")
                else:
                    body.append(f"- Your {user_pct:g} percentile is below the cutoffs here, so this would be ambitious.")
    note = "\nThese are last year's closing cutoffs, so use them as a guide, not a guarantee."
    return head + "\n" + "\n".join(body) + note


def _cache_courses(code):
    _kb()
    return sorted(_kb_cache["by_college"].get(code, []), key=lambda x: x[1])


def _branches_text(col):
    code = _kb_code(col)
    courses = _cache_courses(code) if code else []
    if not courses:
        return None
    names = sorted({nm for _, nm in courses})
    return f"**{col['name']}** has {len(names)} branches in the CAP 2025-26 list:\n" + "\n".join(f"- {n}" for n in names)


def _dsy_text(col, query):
    """Direct Second Year (diploma) cutoffs. The DSY list only contains seat types that had allotments."""
    kb = _kb()
    code = _kb_code(col) if kb else None
    data = (kb or {}).get('dsy', {}).get(code or '', {})
    if not data:
        return None
    terms = _branch_terms(query)
    cat, gender = _category_gender(query)
    dsy_name = {'NT1': 'NTB', 'NT2': 'NTC', 'NT3': 'NTD'}
    want = dsy_name.get(cat, cat) if cat else None
    lines = []
    for course, seats in sorted(data.items()):
        if terms and not any(t in course.lower() for t in terms):
            continue
        rows = []
        for seat, (rank, score) in seats.items():
            base = seat.upper()
            if base[:1] in ('G', 'L') and base[1:] not in ('',):
                base = base[1:]
            rows.append((seat, base, rank, score))
        if want:
            picked = [r for r in rows if r[1] == want and (r[0][:1] in (gender, want[:1]) or True)]
            picked = sorted(picked, key=lambda r: 0 if r[0].upper().startswith(gender) else 1)[:1]
        else:
            picked = sorted(rows, key=lambda r: (r[1] != 'OPEN', r[0]))[:3]
        if not picked:
            have = ", ".join(sorted({r[0] for r in rows})[:6])
            lines.append(f"- {course}: no {_CATEGORY_LABEL.get(cat, 'matching')} entry in the DSY list (seat types listed: {have})")
        for seat, _, rank, score in picked:
            rtxt = f"rank {rank:,}" if isinstance(rank, int) else f"rank {rank}"
            lines.append(f"- {course} ({seat}): score {score}, {rtxt}")
    if not lines:
        return None
    return (f"**{col['name']}**: Direct Second Year (DSY) CAP round 2 cutoffs"
            + (f", {_CATEGORY_LABEL[cat]} category" if cat else "") + ":\n" + "\n".join(lines[:12])
            + "\nDSY merit is based on diploma marks, and only seat types with allotments are listed.")


def _predict(query, user_pct):
    """Which colleges/branches a student can aim for, from the CAP 2025-26 cutoffs."""
    kb = _kb()
    colleges = _load()
    if not kb or not colleges:
        return None
    cat, gender = _category_gender(query)
    cat = cat or 'OPEN'
    terms = _branch_terms(query)
    districts, regions = _find_places(query)
    filters = _status_filters(query)
    by_code = {c["code"].zfill(5): c for c in colleges}

    likely, possible, reach = [], [], []
    for code, courses in _cache_courses_all():
        col = by_code.get(code)
        if col is None:
            continue
        if districts and col['district'].lower() not in districts:
            continue
        if regions and col['region'].lower() not in regions:
            continue
        if not all(f(col) for f in filters):
            continue
        for ch, nm in courses:
            if terms and not any(t in nm.lower() for t in terms):
                continue
            cells = _course_cells(ch, cat, gender)
            pref = cells.get('SL') or cells.get('HH')
            if not pref:
                continue
            hi = max(v[2] for v in pref.values())
            lo = min(v[2] for v in pref.values())
            item = (hi, col['name'], nm, col['district'])
            if user_pct >= hi:
                likely.append(item)
            elif user_pct >= lo:
                possible.append(item)
            elif user_pct >= hi - 2.5:
                reach.append(item)
    if not (likely or possible or reach):
        return {"kind": "predictor", "text": f"I couldn't find {_CATEGORY_LABEL[cat]}-category seats near {user_pct:g} percentile with those filters. Try a different branch or place."}

    def fmt(items, n, label):
        items = sorted(items, key=lambda x: -x[0])[:n]
        return [f"- {c} | {b} ({d}): cutoff {hi:.2f}" for hi, c, b, d in items] if items else []

    where = ', '.join(x.title() for x in (districts or regions)) or 'Maharashtra'
    out = [f"**Options for {user_pct:g} percentile, {_CATEGORY_LABEL[cat]} category, {where}** (CAP 2025-26 State Level cutoffs):"]
    for title, items, n in (("Likely (you are above all rounds' cutoffs)", likely, 8),
                            ("Possible (within later-round cutoffs)", possible, 5),
                            ("Ambitious (slightly above your percentile)", reach, 4)):
        lines = fmt(items, n, title)
        if lines:
            out.append(f"{title}:")
            out += lines
    out.append("\nThis uses last year's cutoffs and State Level seats; Home University seats and this year's merit can differ. Tell me a branch or district to narrow it down.")
    return {"kind": "predictor", "text": "\n".join(out)}


def _cache_courses_all():
    _kb()
    return list(_kb_cache["by_college"].items())


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
_INTENT_CUTOFF = re.compile(r'cut ?off|closing|percentile|%ile|rank|chance|admission|get admission|can i get|eligible', re.I)


def answer(query):
    """Return {"text": str, "kind": str} or None if this question isn't something we can answer locally."""
    colleges = _load()
    q = query.lower()

    if _GREETING.match(query):
        return {"kind": "greeting", "text": "Hi! I'm the CollegeHub Advisor. Ask me about any engineering college in Maharashtra: branches, cutoffs, seats, location, or how CAP admissions work. You can also tell me your percentile to see which colleges you can aim for."}

    user_pct = _find_percentile(query)
    asks_cutoff = bool(_INTENT_CUTOFF.search(q))
    asks_branches = bool(re.search(r'\b(branches|branch list|courses|streams|offer|offers|programs?)\b', q))
    asks_dsy = bool(re.search(r'\b(dsy|direct second year|diploma)\b', q))
    want_cutoff = any(w in q for w in ('cutoff', 'cut off', 'cutoffs', 'closing'))

    found = []
    if colleges:
        found, _ = _find_colleges(query)

    # 1) a specific college
    if found:
        if len(found) > 3:
            return {"kind": "institute", "text": f"I found {len(found)} colleges that match. Which one do you mean?\n" + _list_colleges(found, 8)}
        parts = []
        for c in found:
            text = None
            if asks_dsy:
                text = _dsy_text(c, query) or f"I don't have DSY cutoff data for **{c['name']}** with those filters."
                parts.append(text)
                continue
            if text is None and (asks_cutoff or _branch_terms(query)) and not asks_branches:
                text = _cutoff_text(c, query, user_pct)
            if text is None and asks_branches:
                text = _branches_text(c)
            if text is None:
                text = _college_card(c, want_cutoff, _branch_terms(query))
            parts.append(text)
        kind = 'cutoff' if any('cutoffs' in t for t in parts) else 'institute'
        if re.search(r'\b(fees?|hostel|placements?|package|salary|nirf|ranking|website|phone|contact|email|facilit\w+|faculty|campus)\b', q) \
                and not any('More details in CollegeHub' in t for t in parts):
            parts.append("I don't have verified fee, hostel, placement or contact details for this college in CollegeHub yet. "
                         "Please check the college's official website or admission office for those.")
        return {"kind": kind, "text": "\n\n".join(parts)}

    # 2) "which colleges can I get with N percentile"
    if user_pct is not None:
        pred = _predict(query, user_pct)
        if pred:
            return pred

    # 3) districts / regions / universities
    if colleges:
        districts, regions = _find_places(query)
        uni_hit = None
        for key, label in list(_cache["universities"].items()) + [(a, _UNI_ALIASES[a]) for a in _UNI_ALIASES]:
            real = _cache["universities"].get(label, _cache["universities"].get(key))
            if real:
                words = _tok(key)
                acr = _initials([w for w in words if w not in {'of', 'the'}])
                if (len(acr) >= 4 and re.search(r'\b' + acr + r'\b', q)) or (' ' + key.split(',')[0] + ' ') in (' ' + q + ' ') or (len(key) <= 3 and re.search(r'\b' + key + r'\b colleges?', q)):
                    uni_hit = real
                    break
        asks_list = bool(re.search(r'\b(colleges?|institutes?|list|which|top|best|options|available|how many|number)\b', q))
        if (districts or regions or uni_hit) and asks_list:
            filters = _status_filters(query)
            pool = colleges
            if districts:
                pool = [c for c in pool if c['district'].lower() in districts]
            if regions:
                pool = [c for c in pool if c['region'].lower() in regions]
            if uni_hit:
                pool = [c for c in pool if c['university'] == uni_hit]
            for f in filters:
                pool = [c for c in pool if f(c)]
            where = ', '.join(x.title() for x in (districts or regions)) or (uni_hit or 'Maharashtra')
            if not pool:
                return {"kind": "district", "text": f"I couldn't find engineering colleges in the CAP list for **{where}** matching that filter."}
            govt = sum(1 for c in pool if c['status'].lower().startswith(('government', 'university')))
            seats = sum(int(c['intake'] or 0) for c in pool)
            head = f"**{len(pool)} engineering {'college' if len(pool) == 1 else 'colleges'}** found for {where} ({govt} government/university, about {seats:,} total seats)."
            body = "Largest by seat intake:\n" + _list_colleges(pool, 8)
            tail = ("\n\nI don't hold official quality rankings, so this list is sorted by seats. "
                    "Tell me your percentile and category and I'll show which of these you can aim for.") if re.search(r'\b(top|best)\b', q) else ""
            return {"kind": "district", "text": head + "\n" + body + tail}

        if re.search(r'how many .*(college|institute)|number of .*(college|institute)', q) and 'maharashtra' in q:
            by_region = {}
            for c in colleges:
                by_region[c['region'] or 'Other'] = by_region.get(c['region'] or 'Other', 0) + 1
            reg = ', '.join(f"{k}: {v}" for k, v in sorted(by_region.items(), key=lambda x: -x[1]))
            return {"kind": "overview", "text": f"The CAP institute list in CollegeHub has **{len(colleges)} engineering institutes** across Maharashtra.\nBy CAP region: {reg}."}

    # 4) general admissions knowledge
    primer = _primer_answer(query)
    if primer:
        return {"kind": "general", "text": primer}

    return None


def context_for_ai(query):
    """Facts from the CAP data to give the AI model as verified context (used when an API key exists)."""
    res = answer(query)
    if res and res["kind"] in ("institute", "district", "overview", "cutoff", "predictor"):
        return res["text"]
    return ""
