"""
Build the chatbot's cutoff knowledge base from the official CAP PDFs.

Usage (from the project folder; needs `pdftotext` from poppler-utils installed):
    python scripts/build_chatbot_kb.py

Reads   : 2025ENGG_CAP1_CutOff.pdf ... 2025ENGG_CAP4_CutOff.pdf (and optionally the DSY json)
Writes  : assets/data/chatbot_cutoffs.json.gz

Re-run it whenever you add next year's CAP PDFs (edit PDF_FILES / YEAR below).
"""
import os
import re
import sys
import gzip
import json
import glob
import subprocess

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
YEAR = "2025-26"
PDF_FILES = {1: "2025ENGG_CAP1_CutOff.pdf", 2: "2025ENGG_CAP2_CutOff*.pdf",
             3: "2025ENGG_CAP3_CutOff.pdf", 4: "2025ENGG_CAP4_CutOff.pdf"}
DSY_JSON = os.path.join(BASE, "assets", "data", "dsy_2026_cap_cutoffs.json")
OUT = os.path.join(BASE, "assets", "data", "chatbot_cutoffs.json.gz")

POOLS = [
    ("Home University Seats Allotted to Home University Candidates", "HH"),
    ("Home University Seats Allotted to Other Than Home University Candidates", "HO"),
    ("Other Than Home University Seats Allotted to Other Than Home University Candidates", "OO"),
    ("Other Than Home University Seats Allotted to Home University Candidates", "OH"),
]
INST_RE = re.compile(r'^(\d{4,5})\s*-\s*(.+)$')
COURSE_RE = re.compile(r'^(\d{9,10}[A-Z]?)\s*-\s*(.+)$')
def pool_code(line):
    if line == 'State Level':
        return 'SL'
    for text, code in POOLS:
        if line.startswith(text):
            return code
    if line.startswith('Minority Seats'):
        return 'MI'
    if line.startswith('All India'):
        return 'AI'
    return None


def pdf_to_text(path):
    # -layout keeps the table columns, which lets us put every value under its exact seat-type header
    return subprocess.run(['pdftotext', '-layout', path, '-'], capture_output=True, text=True, check=True).stdout


ROW_RE = re.compile(r'^\s*(I{1,3}|IV|VI{0,3}|IX|X{1,2}I{0,3})(-Non)?(\s|$)')
PCT_RE = re.compile(r'\((\d+(?:\.\d+)?)\)')
NUM_RE = re.compile(r'(?<![\d.(])\d+(?![\d.)])')


def is_noise(line):
    s = line.strip()
    return (not s) or s in {'D', 'i', 'r', '*', '1'} or s.startswith(
        ('State Common Entrance', 'Cut Off List', 'Master of Engineering', 'Government of Maharashtra', 'Legends',
         'Maharashtra State Seats', 'Admissions A.Y', 'PWDR :'))


def header_tokens(line):
    """[(text, x_start, x_end)] for the seat-type header line (ignoring the word 'Stage')."""
    return [(m.group(0), m.start(), m.end()) for m in re.finditer(r'\S+', line) if m.group(0) != 'Stage']


def parse_round(text):
    colleges, courses, cutoffs = {}, {}, {}
    stats = {"blocks": 0, "mismatch": 0}
    lines = text.replace('\f', '\n').split('\n')
    n = len(lines)
    cur_course = None
    i = 0
    while i < n:
        s = lines[i].strip()
        m = COURSE_RE.match(s)
        if m:
            name, j = m.group(2), i + 1
            while j < n and j - i < 4 and not lines[j].strip().startswith('Status:'):
                if lines[j].strip():
                    name += ' ' + lines[j].strip()
                j += 1
            cur_course = m.group(1)
            courses.setdefault(cur_course, name.strip())
            i = j
            continue
        m = INST_RE.match(s)
        if m and not s.startswith(('Status', 'Cut Off')):
            colleges.setdefault(m.group(1).zfill(5), m.group(2).strip())
            i += 1
            continue
        pc = pool_code(s)
        if not (pc and cur_course):
            i += 1
            continue
        # ---- one table block: header + stage rows
        i += 1
        while i < n and not lines[i].strip():
            i += 1
        if i >= n:
            break
        header = header_tokens(lines[i])
        i += 1
        # wrapped header fragments (e.g. "PWDROBC" / "S") sit on the next line(s), before any stage row
        while i < n and lines[i].strip() and not ROW_RE.match(lines[i]) and not is_noise(lines[i]) \
                and not pool_code(lines[i].strip()) and not COURSE_RE.match(lines[i].strip()):
            for frag, fs, fe in header_tokens(lines[i]):
                if not header:
                    break
                k = min(range(len(header)), key=lambda q: abs(header[q][2] - fs))
                t, a, b = header[k]
                header[k] = (t + frag, a, max(b, fe))
            i += 1
        centers = [((a + b) / 2.0, t) for t, a, b in header]
        block, ok = {}, True
        while i < n:
            line = lines[i]
            if not line.strip():
                i += 1
                continue
            if not ROW_RE.match(line):
                break
            first = line.split()[0]
            offset = line.find(first) + len(first)
            ranks = [(mm.start() + offset + len(mm.group(0)) / 2.0, int(mm.group(0))) for mm in NUM_RE.finditer(line[offset:])]
            i += 1
            pcts = []
            if i < n:
                pcts = [(mm.start() + len(mm.group(0)) / 2.0, float(mm.group(1))) for mm in PCT_RE.finditer(lines[i])]
                if pcts or lines[i].strip() in ('PWD', 'Defence', 'DEF', 'Orphan'):
                    i += 1
            if len(ranks) != len(pcts) or not centers:
                ok = False
                continue
            used = set()
            for (x, r), (_, pv) in zip(ranks, pcts):
                k = min(range(len(centers)), key=lambda q: abs(centers[q][0] - x))
                if abs(centers[k][0] - x) > 9 or k in used:
                    ok = False
                    continue
                used.add(k)
                block[centers[k][1]] = [r, round(pv, 2)]
        stats["blocks"] += 1
        if not ok:
            stats["mismatch"] += 1
        if block:
            cutoffs.setdefault(cur_course, {}).setdefault(pc, {}).update(block)
    return colleges, courses, cutoffs, stats


def main():
    kb = {"year": YEAR, "colleges": {}, "courses": {}, "rounds": {}, "dsy": {}}
    for rnd, pattern in PDF_FILES.items():
        hits = glob.glob(os.path.join(BASE, pattern))
        if not hits:
            print(f"! CAP round {rnd}: no PDF matching {pattern}, skipped")
            continue
        print(f"Parsing CAP round {rnd}: {os.path.basename(hits[0])} ...", flush=True)
        colleges, courses, cutoffs, stats = parse_round(pdf_to_text(hits[0]))
        kb["colleges"].update(colleges)
        kb["courses"].update(courses)
        kb["rounds"][str(rnd)] = cutoffs
        print(f"   {len(colleges)} colleges, {len(courses)} courses, {stats['blocks']} blocks, "
              f"{stats['mismatch']} with count mismatch")

    if os.path.exists(DSY_JSON):
        print("Adding DSY cutoffs ...")
        rows = json.load(open(DSY_JSON, encoding='utf-8'))
        dsy = {}
        for r in rows:
            code = str(r.get('college_code', '')).zfill(5)
            course = r.get('course_name') or r.get('branch_code') or 'n/a'
            dsy.setdefault(code, {}).setdefault(course, {})[f"{r.get('seat_type')}"] = [r.get('rank'), r.get('score')]
            kb["colleges"].setdefault(code, r.get('college_name'))
        kb["dsy"] = dsy
        print(f"   {len(dsy)} colleges with DSY data")

    with gzip.open(OUT, 'wt', encoding='utf-8') as fh:
        json.dump(kb, fh, separators=(',', ':'))
    print(f"Wrote {OUT} ({os.path.getsize(OUT)/1024/1024:.1f} MB)")


if __name__ == '__main__':
    sys.exit(main())
