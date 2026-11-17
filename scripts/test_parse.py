import pypdf
import re

def parse_page(page):
    elements = []
    def visitor(text, cm, tm, font_dict, font_size):
        s = text.strip()
        if s:
            elements.append({'x': tm[4], 'y': tm[5], 'text': s})
    page.extract_text(visitor_text=visitor)
    
    # Sort elements by y descending (top to bottom), then x ascending (left to right)
    elements.sort(key=lambda e: (-round(e['y'], 1), round(e['x'], 1)))
    
    # Find college and course
    all_lines = page.extract_text().split('\n')
    college_code, college_name, choice_code, course_name, status = None, None, None, None, None
    for i, line in enumerate(all_lines):
        line = line.strip()
        m_col = re.match(r'^(\d{4,5})\s*-\s*(.+)', line)
        if m_col and not college_code and 'Academic Year' not in line:
            college_code = m_col.group(1).lstrip('0') or m_col.group(1)
            college_name = m_col.group(2).strip()
        m_crs = re.match(r'^(\d{9,10})\s*-\s*(.+)', line)
        if m_crs and not choice_code:
            choice_code = m_crs.group(1)
            course_name = m_crs.group(2).strip()
        if line.startswith('Status :'):
            status = line.replace('Status :', '').strip()

    # Find known category headers
    known_cat_patterns = [
        r'^(?:G|L)(?:OPEN|SC|ST|OBC|SEBC|NTA|NTB|NTC|NTD|NT1|NT2|NT3)$',
        r'^(?:EWS|TFWS|ORPNONINST|ORPINST|DEF[A-Z]+|PWD[A-Z]+)$'
    ]
    
    cat_headers = []
    for el in elements:
        t = el['text']
        if any(re.match(pat, t) for pat in known_cat_patterns):
            cat_headers.append(el)
            
    # Find rank and score pairs
    ranks = [el for el in elements if re.match(r'^\d+$', el['text']) and int(el['text']) <= 250000 and 80 < el['y'] < 600]
    scores = [el for el in elements if re.match(r'^\(\d+\.?\d*\)$', el['text']) and 80 < el['y'] < 600]
    
    cutoffs = []
    for rank_el in ranks:
        matched_score = min(
            (s for s in scores if abs(s['x'] - rank_el['x']) < 25 and 0 < (rank_el['y'] - s['y']) < 25),
            key=lambda s: abs(s['x'] - rank_el['x']) + (rank_el['y'] - s['y']),
            default=None
        )
        matched_cat = min(
            (c for c in cat_headers if abs(c['x'] - rank_el['x']) < 35 and c['y'] > rank_el['y']),
            key=lambda c: abs(c['x'] - rank_el['x']),
            default=None
        )
        if matched_cat and matched_score:
            score_val = float(matched_score['text'].strip('()'))
            rank_val = int(rank_el['text'])
            cutoffs.append({
                'seat_type': matched_cat['text'],
                'rank': rank_val,
                'score': score_val
            })
    return {
        'college_code': college_code,
        'college_name': college_name,
        'choice_code': choice_code,
        'course_name': course_name,
        'status': status,
        'cutoffs': cutoffs
    }

if __name__ == '__main__':
    reader = pypdf.PdfReader('c:/Users/LOQ/Desktop/campushub/9c529bfc-f112-433a-8ede-91b8e7b26fbf.pdf')
    for p in [0, 10, 50, 100, 333, 1602, 1604]:
        res = parse_page(reader.pages[p])
        print(f"=== Page {p+1}: {res['college_code']} ({res['college_name']}) - {res['course_name']} ({len(res['cutoffs'])} cutoffs) ===")
        for c in res['cutoffs']:
            print("  ", c)
