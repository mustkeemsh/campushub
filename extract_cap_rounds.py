import re
import json
import time
from pypdf import PdfReader

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
    elif 'MI' in st:
        return 'MINORITY'
    return 'OPEN'

def extract_cutoffs_from_pdf(pdf_path, round_num):
    print(f"\n==========================================")
    print(f"Extracting CAP Round {round_num} from {pdf_path}...")
    t0 = time.time()
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    print(f"Total pages: {total_pages}")
    
    institutes_found = {}
    courses_found = {}
    cutoffs_found = []
    
    current_inst_code = None
    current_inst_name = None
    current_course_code = None
    current_course_name = None
    
    for p_idx in range(total_pages):
        page_text = reader.pages[p_idx].extract_text()
        if not page_text:
            continue
        lines = [l.strip() for l in page_text.split('\n') if l.strip()]
        
        i = 0
        n = len(lines)
        while i < n:
            line = lines[i]
            
            # Check for Institute: e.g. '01002 - Government College of Engineering, Amravati'
            inst_m = re.match(r'^(\d{4,5})\s*-\s*([^\n\r]+)$', line)
            if inst_m and len(inst_m.group(1)) <= 5:
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
            seat_pool_type = 'MH'
            if line == 'State Level':
                pool_label = 'State Level'
            elif 'Home University Seats Allotted to Home University Candidates' in line:
                pool_label = 'Home University Seats'
            elif 'Home University Seats Allotted to Other Than Home University Candidates' in line:
                pool_label = 'HU to Other HU Candidates'
            elif 'Other Than Home University Seats Allotted to Other Than Home University Candidates' in line:
                pool_label = 'Other Than Home University Seats'
            elif 'Other Than Home University Seats Allotted to Home University Candidates' in line:
                pool_label = 'Other Than Home University Seats to HU'
            elif 'Minority Seats Allotted to Maharashtra State' in line:
                pool_label = 'Minority Seats'
            elif 'Maharashtra State Seats Allotted to All India' in line:
                pool_label = 'AI Seats'
                seat_pool_type = 'AI'
                
            if pool_label and current_course_code:
                i += 1
                # Next line(s) contain seat type abbreviations
                seat_types = []
                while i < n and not re.match(r'^\s*(I|MH)\b', lines[i]) and not re.match(r'^\s*\d{3,7}\b', lines[i]) and lines[i] != 'Stage':
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
                        
                # Parse Stage I or MH cutoffs
                if i < n and (re.match(r'^\s*(I|MH)\s+', lines[i]) or lines[i].startswith('I ') or lines[i].startswith('MH ')):
                    stage_line = lines[i]
                    i += 1
                    first_num = re.sub(r'^\s*(I|MH)\s*', '', stage_line).strip()
                    val_lines = []
                    if first_num:
                        val_lines.append(first_num)
                        
                    while i < n and lines[i] != 'Stage' and not re.match(r'^(\d{4,5}|\d{9,10})\s*-', lines[i]):
                        val_lines.append(lines[i])
                        i += 1
                        
                    raw_text = ' '.join(val_lines)
                    pairs = re.findall(r'(\d{1,7})\s*\(([0-9\.]+)\)', raw_text)
                    
                    for idx, (rank, percentile) in enumerate(pairs):
                        st_code = clean_seat_types[idx] if idx < len(clean_seat_types) else f'CAT_{idx+1}'
                        cutoffs_found.append({
                            'round': round_num,
                            'inst_code': current_inst_code or current_course_code[:5],
                            'choice_code': current_course_code,
                            'pool': pool_label,
                            'seat_pool': seat_pool_type,
                            'seat_type': st_code,
                            'category': decode_category(st_code),
                            'rank': int(rank),
                            'percentile': float(percentile),
                            'page': p_idx + 1
                        })
                continue
                
            i += 1

    elapsed = time.time() - t0
    print(f"Round {round_num} completed in {elapsed:.2f}s!")
    print(f"Institutes: {len(institutes_found)}, Courses: {len(courses_found)}, Cutoffs: {len(cutoffs_found)}")
    if cutoffs_found:
        print(f"Sample: {cutoffs_found[0]}")
    
    return institutes_found, courses_found, cutoffs_found

if __name__ == '__main__':
    rounds_config = [
        ('2025ENGG_CAP2_CutOff - Copy.pdf', 2),
        ('2025ENGG_CAP3_CutOff.pdf', 3),
        ('2025ENGG_CAP4_CutOff.pdf', 4)
    ]
    
    all_extracted = {}
    for path, r_num in rounds_config:
        insts, courses, cuts = extract_cutoffs_from_pdf(path, r_num)
        all_extracted[r_num] = {
            'institutes': insts,
            'courses': courses,
            'cutoffs': cuts
        }
        with open(f'extracted_cap{r_num}_cutoffs.json', 'w', encoding='utf-8') as f:
            json.dump(cuts, f)
        with open(f'extracted_cap{r_num}_summary.json', 'w', encoding='utf-8') as f:
            json.dump({
                'round': r_num,
                'total_institutes': len(insts),
                'total_courses': len(courses),
                'total_cutoffs': len(cuts),
                'sample': cuts[0] if cuts else None
            }, f, indent=2)
            
    print("\nAll extractions finished!")
