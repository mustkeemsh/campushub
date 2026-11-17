import os
import re
import json
import uuid
import pypdf

PDF_PATH = r"c:\Users\LOQ\Desktop\campushub\9c529bfc-f112-433a-8ede-91b8e7b26fbf.pdf"
OUTPUT_JSON = r"c:\Users\LOQ\Desktop\campushub\assets\data\dsy_2026_cap_cutoffs.json"

def normalize_branch(course_name):
    c = course_name.lower()
    if 'artificial intelligence and data science' in c or 'ai and data science' in c:
        return 'AIDS'
    elif 'artificial intelligence' in c or 'machine learning' in c:
        return 'AIML'
    elif 'computer' in c or 'software' in c:
        return 'CSE'
    elif 'information technology' in c:
        return 'IT'
    elif 'telecommunication' in c or 'electronics and comm' in c or 'entc' in c or 'tele comm' in c:
        return 'ENTC'
    elif 'electrical' in c:
        return 'ELECT'
    elif 'mechanical' in c:
        return 'MECH'
    elif 'civil' in c:
        return 'CIVIL'
    elif 'robotics' in c:
        return 'ROBO'
    elif 'chemical' in c:
        return 'CHEM'
    elif 'instrumentation' in c:
        return 'INST'
    elif 'textile' in c:
        return 'TEXT'
    elif 'automobile' in c or 'automotive' in c:
        return 'AUTO'
    elif 'biotech' in c:
        return 'BIOTECH'
    elif 'aerospace' in c or 'aeronautical' in c:
        return 'AERO'
    return 'OTHER'

def normalize_category(seat_type):
    st = seat_type.upper()
    if st in ('GOPEN', 'LOPEN', 'OPEN', 'DEFOPEN', 'PWDOPEN'):
        return 'OPEN'
    elif st in ('GOBC', 'LOBC', 'OBC', 'DEFOBC', 'PWDOBC'):
        return 'OBC-NCL'
    elif st in ('GSC', 'LSC', 'SC', 'DEFSC', 'PWDSC'):
        return 'SC'
    elif st in ('GST', 'LST', 'ST', 'DEFST', 'PWDST'):
        return 'ST'
    elif st in ('GSEBC', 'LSEBC', 'SEBC'):
        return 'SEBC'
    elif st in ('GNTA', 'LNTA', 'NTA', 'VJ', 'VJNT'):
        return 'VJNT'
    elif st in ('GNTB', 'LNTB', 'NTB', 'NT1'):
        return 'NT-B'
    elif st in ('GNTC', 'LNTC', 'NTC', 'NT2'):
        return 'NT-C'
    elif st in ('GNTD', 'LNTD', 'NTD', 'NT3'):
        return 'NT-D'
    elif st == 'EWS':
        return 'EWS'
    elif st == 'TFWS':
        return 'TFWS'
    elif 'DEF' in st:
        return 'DEF'
    elif 'PWD' in st:
        return 'PWD'
    elif 'ORP' in st:
        return 'ORPHAN'
    return 'OPEN'

def parse_pdf():
    print(f"Opening PDF: {PDF_PATH}")
    reader = pypdf.PdfReader(PDF_PATH)
    total_pages = len(reader.pages)
    print(f"Total pages: {total_pages}")
    
    known_cat_patterns = [
        r'^(?:G|L)(?:OPEN|SC|ST|OBC|SEBC|NTA|NTB|NTC|NTD|NT1|NT2|NT3)$',
        r'^(?:EWS|TFWS|ORPNONINST|ORPINST|DEF[A-Z]+|PWD[A-Z]+)$'
    ]

    all_records = []
    skipped_pages = 0
    
    for p_idx in range(total_pages):
        page = reader.pages[p_idx]
        text = page.extract_text()
        
        # Extract college & course from text lines
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        college_code, college_name, choice_code, course_name, status = None, None, None, None, None
        
        for line in lines:
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
                
        if not college_code or not course_name:
            skipped_pages += 1
            continue

        branch_code = normalize_branch(course_name)
        
        # Visitor for text coordinates
        elements = []
        def visitor(t, cm, tm, font_dict, font_size):
            s = t.strip()
            if s:
                elements.append({'x': tm[4], 'y': tm[5], 'text': s})
                
        try:
            page.extract_text(visitor_text=visitor)
        except Exception:
            pass
            
        elements.sort(key=lambda e: (-round(e['y'], 1), round(e['x'], 1)))
        
        cat_headers = []
        for el in elements:
            t = el['text']
            if any(re.match(pat, t) for pat in known_cat_patterns):
                cat_headers.append(el)
                
        ranks = [el for el in elements if re.match(r'^\d+$', el['text']) and int(el['text']) <= 250000 and 80 < el['y'] < 600]
        scores = [el for el in elements if re.match(r'^\(\d+\.?\d*\)$', el['text']) and 80 < el['y'] < 600]
        
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
                try:
                    score_val = float(matched_score['text'].strip('()'))
                    rank_val = int(rank_el['text'])
                    seat_type = matched_cat['text']
                    cat_normalized = normalize_category(seat_type)
                    
                    all_records.append({
                        'page': p_idx + 1,
                        'college_code': college_code,
                        'college_name': college_name,
                        'choice_code': choice_code,
                        'course_name': course_name,
                        'branch_code': branch_code,
                        'status': status or 'Un-Aided',
                        'seat_type': seat_type,
                        'category': cat_normalized,
                        'rank': rank_val,
                        'score': score_val,
                        'quota': 'SL'
                    })
                except Exception:
                    continue

        if (p_idx + 1) % 250 == 0 or (p_idx + 1) == total_pages:
            print(f"Processed {p_idx + 1}/{total_pages} pages ({len(all_records)} cutoffs extracted so far)...")
            
    print(f"Extraction complete! Total cutoffs: {len(all_records)}, Skipped pages: {skipped_pages}")
    return all_records

if __name__ == '__main__':
    records = parse_pdf()
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=2)
    print(f"Saved {len(records)} records to {OUTPUT_JSON}")
