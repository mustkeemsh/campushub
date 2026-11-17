import re
import json
import time
from pypdf import PdfReader

print("Loading 2025ENGG_CAP1_CutOff.pdf...")
reader = PdfReader('2025ENGG_CAP1_CutOff.pdf')
total_pages = len(reader.pages)
print(f"Total pages: {total_pages}")

# Load scraped institutes
with open('scraped_institutes.json', 'r', encoding='utf-8') as f:
    scraped_institutes = json.load(f)

# Helper to derive branch from course name
def derive_branch(course_name):
    cn = course_name.upper()
    if 'COMPUTER SCIENCE' in cn or 'COMPUTER ENGINEERING' in cn or 'CSE' in cn:
        return 'CSE'
    elif 'INFORMATION TECHNOLOGY' in cn or 'IT' in cn:
        return 'IT'
    elif 'ARTIFICIAL INTELLIGENCE' in cn or 'DATA SCIENCE' in cn or 'AI' in cn or 'AIML' in cn:
        return 'AIDS'
    elif 'ELECTRONICS AND TELECOMMUNICATION' in cn or 'E&TC' in cn or 'EXTC' in cn:
        return 'ENTC'
    elif 'ELECTRICAL' in cn:
        return 'ELECT'
    elif 'MECHANICAL' in cn:
        return 'MECH'
    elif 'CIVIL' in cn:
        return 'CIVIL'
    elif 'CHEMICAL' in cn:
        return 'CHEM'
    elif 'INSTRUMENTATION' in cn:
        return 'INST'
    elif 'BIOMEDICAL' in cn:
        return 'BIOMED'
    elif 'AUTOMOBILE' in cn:
        return 'AUTO'
    elif 'ROBOTICS' in cn:
        return 'ROBO'
    elif 'AERONAUTICAL' in cn or 'AEROSPACE' in cn:
        return 'AERO'
    elif 'FOOD' in cn:
        return 'FOOD'
    elif 'OIL' in cn or 'PAINT' in cn:
        return 'CHEM'
    elif 'PRODUCTION' in cn:
        return 'PROD'
    return 'OTHER'

# Helper to decode category
def decode_category(seat_type):
    st = seat_type.upper().strip()
    if 'OPEN' in st:
        return 'OPEN'
    elif 'EWS' in st:
        return 'EWS'
    elif 'TFWS' in st:
        return 'TFWS'
    elif 'OBC' in st:
        return 'OBC'
    elif 'SEBC' in st:
        return 'SEBC'
    elif 'SC' in st:
        return 'SC'
    elif 'ST' in st:
        return 'ST'
    elif 'VJ' in st or 'DT' in st:
        return 'VJ/DT'
    elif 'NT1' in st or 'NTB' in st:
        return 'NT-1'
    elif 'NT2' in st or 'NTC' in st:
        return 'NT-2'
    elif 'NT3' in st or 'NTD' in st:
        return 'NT-3'
    elif 'PWD' in st:
        return 'PWD'
    elif 'DEF' in st:
        return 'DEF'
    elif 'ORPHAN' in st:
        return 'ORPHAN'
    return 'OPEN'

institutes_found = {}
courses_found = {}
cutoffs_found = []

current_inst_code = None
current_inst_name = None
current_course_code = None
current_course_name = None

t0 = time.time()

for p_idx in range(total_pages):
    page_text = reader.pages[p_idx].extract_text()
    lines = [l.strip() for l in page_text.split('\n') if l.strip()]
    
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        
        # Check for Institute: e.g. '01002 - Government College of Engineering, Amravati'
        inst_m = re.match(r'^(\d{4,5})\s*-\s*([^\n\r]+)$', line)
        if inst_m and len(inst_m.group(1)) <= 5 and not inst_m.group(1).endswith('10'):
            current_inst_code = inst_m.group(1).strip()
            current_inst_name = inst_m.group(2).strip()
            if current_inst_code not in institutes_found:
                institutes_found[current_inst_code] = {
                    'code': current_inst_code,
                    'name': current_inst_name
                }
            i += 1
            continue
            
        # Check for Course: e.g. '0100219110 - Civil Engineering'
        course_m = re.match(r'^(\d{9,10}[A-Z]?)\s*-\s*([^\n\r]+)$', line)
        if course_m:
            current_course_code = course_m.group(1).strip()
            current_course_name = course_m.group(2).strip()
            if current_course_code not in courses_found:
                inst_code = current_inst_code
                if not inst_code:
                    # In DTE codes, first 5 digits is institute code
                    inst_code = current_course_code[:5]
                courses_found[current_course_code] = {
                    'choice_code': current_course_code,
                    'course_name': current_course_name,
                    'branch': derive_branch(current_course_name),
                    'inst_code': inst_code
                }
            i += 1
            continue
            
        # Check for Pool Header
        pool_label = None
        if 'State Level' in line:
            pool_label = 'State Level'
        elif 'Home University Seats Allotted to Home University Candidates' in line:
            pool_label = 'Home University Seats'
        elif 'Home University Seats Allotted to Other Than Home University Candidates' in line:
            pool_label = 'HU to Other HU Candidates'
        elif 'Other Than Home University Seats Allotted to Other Than Home University Candidates' in line:
            pool_label = 'Other Than Home University Seats'
        elif 'Other Than Home University Seats Allotted to Home University Candidates' in line:
            pool_label = 'Other Than Home University Seats to HU'
            
        if pool_label and current_course_code:
            i += 1
            # Next line(s) contain seat type abbreviations
            seat_types = []
            while i < n and not re.match(r'^\s*I\b', lines[i]) and not re.match(r'^\s*\d{3,7}\b', lines[i]) and lines[i] != 'Stage':
                tokens = lines[i].split()
                for tok in tokens:
                    if re.match(r'^[A-Z0-9]+$', tok):
                        seat_types.append(tok)
                i += 1
                
            clean_seat_types = []
            for tok in seat_types:
                if len(tok) == 1 and clean_seat_types:
                    clean_seat_types[-1] = clean_seat_types[-1] + tok
                else:
                    clean_seat_types.append(tok)
                    
            # Parse Stage I cutoffs
            if i < n and (re.match(r'^\s*I\s+', lines[i]) or lines[i].startswith('I ')):
                stage_line = lines[i]
                i += 1
                first_num = re.sub(r'^\s*I\s*', '', stage_line).strip()
                val_lines = []
                if first_num:
                    val_lines.append(first_num)
                    
                while i < n and lines[i] != 'Stage' and not re.match(r'^\s*II\b', lines[i]) and not re.match(r'^(\d{4,5}|\d{9,10})\s*-', lines[i]):
                    val_lines.append(lines[i])
                    i += 1
                    
                raw_text = ' '.join(val_lines)
                pairs = re.findall(r'(\d{1,7})\s*\(([0-9\.]+)\)', raw_text)
                
                for idx, (rank, percentile) in enumerate(pairs):
                    st_code = clean_seat_types[idx] if idx < len(clean_seat_types) else f'CAT_{idx+1}'
                    cutoffs_found.append({
                        'inst_code': current_inst_code,
                        'choice_code': current_course_code,
                        'pool': pool_label,
                        'seat_type': st_code,
                        'category': decode_category(st_code),
                        'rank': int(rank),
                        'percentile': float(percentile),
                        'page': p_idx + 1
                    })
            continue
            
        i += 1

print(f"Extraction completed in {time.time()-t0:.2f}s!")
print(f"Unique Institutes: {len(institutes_found)}")
print(f"Unique Courses: {len(courses_found)}")
print(f"Total Cutoff Records: {len(cutoffs_found)}")

# Save summary
with open('extracted_cap1_summary.json', 'w', encoding='utf-8') as f:
    json.dump({
        'total_institutes': len(institutes_found),
        'total_courses': len(courses_found),
        'total_cutoffs': len(cutoffs_found),
        'sample_cutoff': cutoffs_found[0] if cutoffs_found else None
    }, f, indent=2)

with open('extracted_cutoffs.json', 'w', encoding='utf-8') as f:
    json.dump(cutoffs_found, f)

with open('extracted_courses.json', 'w', encoding='utf-8') as f:
    json.dump(courses_found, f)
