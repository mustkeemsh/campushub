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
import html
import difflib
import threading

from database import db

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_FILE = os.path.join(BASE_DIR, 'scraped_institutes.json')

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


def _college_card(col, want_cutoff=False, branch_filter=None):
    parts = [f"**{col['name']}** (code {col['code']})",
             f"- Location: {col['address']}" + (f" ({col['district']} district, {col['region']} CAP region)" if col['district'] else ""),
             f"- Type: {col['status']}" + (f" | Minority status: {col['minority']}" if col['minority'] and col['minority'] != 'Non-Minority' else ""),
             f"- University: {col['university'] or 'n/a'}",
             f"- Total sanctioned intake (all branches): {_seats(col['intake'])} seats"]
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
# Public entry point
# ---------------------------------------------------------------------------
def answer(query):
    """Return {"text": str, "kind": str} or None if this question isn't something we can answer locally."""
    colleges = _load()
    q = query.lower()

    if _GREETING.match(query):
        return {"kind": "greeting", "text": "Hi! I'm the CollegeHub Advisor. Ask me about any engineering college in Maharashtra: location, seats, type, university, cutoffs, or how CAP admissions work."}

    branch_filter = [b for b in _BRANCH_WORDS if b in q] or (['computer'] if re.search(r'\b(cse|computer)\b', q) else None)
    want_cutoff = any(w in q for w in ('cutoff', 'cut off', 'cutoffs', 'closing'))

    # 1) a specific college
    if colleges:
        found, _ = _find_colleges(query)
        if found:
            if len(found) <= 3:
                cards = "\n\n".join(_college_card(c, want_cutoff, branch_filter) for c in found)
                return {"kind": "institute", "text": cards + "\n\nFor branch-wise cutoffs, try the College Predictor page."}
            return {"kind": "institute", "text": f"I found {len(found)} colleges that match. Which one do you mean?\n" + _list_colleges(found, 8)}

    # 2) districts / regions / universities
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
        asks_list = bool(re.search(r'\b(colleges?|institutes?|list|which|top|best|options|options|available|how many|number)\b', q))
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
                    "Use the College Predictor to see which ones fit your percentile.") if re.search(r'\b(top|best)\b', q) else ""
            return {"kind": "district", "text": head + "\n" + body + tail}

        if re.search(r'how many .*(college|institute)|number of .*(college|institute)', q) and 'maharashtra' in q:
            by_region = {}
            for c in colleges:
                by_region[c['region'] or 'Other'] = by_region.get(c['region'] or 'Other', 0) + 1
            reg = ', '.join(f"{k}: {v}" for k, v in sorted(by_region.items(), key=lambda x: -x[1]))
            return {"kind": "overview", "text": f"The CAP institute list in CollegeHub has **{len(colleges)} engineering institutes** across Maharashtra.\nBy CAP region: {reg}."}

    # 3) general admissions knowledge
    primer = _primer_answer(query)
    if primer:
        return {"kind": "general", "text": primer}

    return None


def context_for_ai(query):
    """Facts from the CAP institute list to give the AI model as verified context (used when an API key exists)."""
    res = answer(query)
    if res and res["kind"] in ("institute", "district", "overview"):
        return res["text"]
    return ""
