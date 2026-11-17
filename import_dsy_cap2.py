"""
CampusHub - Extract DSY CAP Round 2 Cutoffs (2026-27) from PDF and Import to Supabase
=====================================================================================
This script:
1. Parses the DSE (Direct Second Year) CAP Round 2 cutoff PDF
2. Extracts institutes, courses, and cutoff data  
3. Imports everything into Supabase with admission_route = 'BTECH_DSY'
"""

import re
import json
import uuid
import time
import os
import requests
from pypdf import PdfReader
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("SUPABASE_ACCESS_TOKEN")
PROJECT_REF = os.getenv("SUPABASE_PROJECT_REF", "uwaddyejdswshzamhjfs")

if not TOKEN:
    raise ValueError("SUPABASE_ACCESS_TOKEN is required in .env")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

ACADEMIC_YEAR = "2026-2027"
CAP_ROUND = 2
ADMISSION_ROUTE = "BTECH_DSY"
PDF_PATH = "UG_DSE_CAP2_Cutoff_All_Institutes_2026_27.pdf"
SOURCE_DOC_ID = "20260000-0000-0000-d5e0-000000000002"


# ============================================================================
# Helpers
# ============================================================================

def execute_sql(sql, retries=3):
    for attempt in range(retries):
        try:
            res = requests.post(
                f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/query",
                headers=HEADERS,
                json={"query": sql},
                timeout=120
            )
            if res.status_code in (200, 201):
                return res.json()
            err_msg = res.text[:500]
            if attempt < retries - 1:
                print(f"  Warning: query returned {res.status_code}, retrying ({attempt+1}/{retries})...")
                time.sleep(3)
            else:
                raise RuntimeError(f"SQL execution failed ({res.status_code}): {err_msg}")
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                print(f"  Warning: request error: {e}, retrying ({attempt+1}/{retries})...")
                time.sleep(3)
            else:
                raise


def derive_branch(course_name):
    cn = course_name.upper()
    if 'COMPUTER SCIENCE' in cn or 'COMPUTER ENGINEERING' in cn or 'CSE' in cn:
        return 'CSE'
    elif 'INFORMATION TECHNOLOGY' in cn or cn.strip() == 'IT':
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
    elif 'TEXTILE' in cn:
        return 'TEXTILE'
    elif 'PRINTING' in cn:
        return 'PRINT'
    elif 'POLYMER' in cn or 'PLASTIC' in cn:
        return 'POLYMER'
    elif 'METALLURG' in cn:
        return 'META'
    elif 'MINING' in cn:
        return 'MINING'
    elif 'BIOTECHNOLOGY' in cn:
        return 'BIOTECH'
    elif 'CYBER' in cn:
        return 'CYBER'
    elif 'IOT' in cn or 'INTERNET OF THINGS' in cn:
        return 'IOT'
    return 'OTHER'


def decode_category(seat_type):
    st = seat_type.upper().strip()
    # Remove G/L/S/PWD/DEF prefixes for category detection
    # Strip common prefixes: G (General), L (Ladies), S (State)
    core = re.sub(r'^[GLS]+', '', st)
    
    if 'TFWS' in st:
        return 'TFWS'
    elif 'EWS' in st:
        return 'EWS'
    elif 'MI' in st:
        return 'MINORITY'
    elif 'ORPHAN' in st or 'ORP' in st:
        return 'ORPHAN'
    elif 'PWDR' in st:
        return 'PWD'
    elif 'PWD' in st:
        return 'PWD'
    elif 'DEFR' in st:
        return 'DEF'
    elif 'DEF' in st:
        return 'DEF'
    elif core.startswith('OPEN') or st == 'GOPEN' or st == 'LOPEN' or st == 'SOPEN':
        return 'OPEN'
    elif core.startswith('OBC') or st in ('GOBC', 'LOBC', 'SOBC'):
        return 'OBC'
    elif core.startswith('SEBC') or st in ('GSEBC', 'LSEBC', 'SSEBC'):
        return 'SEBC'
    elif core.startswith('SC') or st in ('GSC', 'LSC', 'SSC'):
        return 'SC'
    elif core.startswith('ST') or st in ('GST', 'LST', 'SST'):
        return 'ST'
    elif core.startswith('VJ') or core.startswith('DT'):
        return 'VJ/DT'
    elif core.startswith('NTA') or core.startswith('NT1'):
        return 'NT-1'
    elif core.startswith('NTB') or core.startswith('NT2'):
        return 'NT-2'
    elif core.startswith('NTC') or core.startswith('NT3'):
        return 'NT-3'
    elif core.startswith('NTD') or core.startswith('NT4'):
        return 'NT-D'
    elif 'OPEN' in st:
        return 'OPEN'
    return 'OPEN'


# ============================================================================
# Step 1: Extract from PDF
# ============================================================================

def extract_dsy_cutoffs(pdf_path):
    print(f"\n{'='*60}")
    print(f"Extracting DSY CAP Round {CAP_ROUND} from {pdf_path}...")
    print(f"{'='*60}")
    
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
            
            # Skip header/footer lines
            if line.startswith('GOVERNMENT OF MAHARASHTRA') or \
               line.startswith('State Common Entrance') or \
               line.startswith('Cut Off List for') or \
               line.startswith('Legends') or \
               line.startswith('Page ') or \
               line.startswith('Status :') or \
               line.startswith('DEFR :'):
                i += 1
                continue
            
            # Check for Institute: e.g. '1002 - Government College of Engineering, Amravati'
            inst_m = re.match(r'^(\d{4,5})\s*-\s*(.+)$', line)
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
            course_m = re.match(r'^(\d{9,10}[A-Z]?)\s*-\s*(.+)$', line)
            if course_m:
                current_course_code = course_m.group(1).strip()
                current_course_name = course_m.group(2).strip()
                if current_course_code not in courses_found:
                    inst_code = current_inst_code or current_course_code[:5]
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
            if line == 'State Level Seats' or line == 'State Level':
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
            elif 'Minority Seats' in line and 'Maharashtra' in line:
                pool_label = 'Minority Seats'
            elif 'Maharashtra State Seats Allotted to All India' in line:
                pool_label = 'AI Seats'
                seat_pool_type = 'AI'
            
            if pool_label and current_course_code:
                i += 1
                # Next line(s) contain seat type abbreviations (e.g., GOPEN GSC GOBC)
                seat_types = []
                while i < n:
                    test_line = lines[i]
                    # Stop if we hit a Stage line, another institute/course, or legend
                    if re.match(r'^Stage', test_line):
                        break
                    if re.match(r'^\d{4,5}\s*-', test_line):
                        break
                    if re.match(r'^\d{9,10}', test_line):
                        break
                    if test_line.startswith('Legends'):
                        break
                    if test_line.startswith('Page '):
                        break
                    if test_line.startswith('Status :'):
                        break
                    # This line should contain seat type tokens
                    tokens = test_line.split()
                    all_seat = True
                    for tok in tokens:
                        if not re.match(r'^[A-Z][A-Z0-9\-]+$', tok) and tok not in ('MI-MH', 'MI'):
                            all_seat = False
                            break
                    if all_seat and tokens:
                        seat_types.extend(tokens)
                        i += 1
                    else:
                        break
                
                # Now parse Stage lines
                while i < n:
                    test_line = lines[i]
                    # Match Stage-I, Stage-II, Stage-3, Stage-7, Stage-MI-MH, etc.
                    stage_m = re.match(r'^Stage[-\s]*([\w\-]+)\s*(.*)', test_line)
                    if not stage_m:
                        break
                    
                    stage_label = stage_m.group(1)
                    rest = stage_m.group(2).strip()
                    i += 1
                    
                    # Collect continuation lines for this stage
                    val_parts = [rest] if rest else []
                    while i < n:
                        next_line = lines[i]
                        if re.match(r'^Stage', next_line):
                            break
                        if re.match(r'^\d{4,5}\s*-', next_line):
                            break
                        if re.match(r'^\d{9,10}', next_line):
                            break
                        if next_line.startswith('Legends'):
                            break
                        if next_line.startswith('Page '):
                            break
                        if next_line.startswith('Status :'):
                            break
                        if next_line.startswith('GOVERNMENT'):
                            break
                        if next_line == 'State Level Seats' or next_line == 'State Level':
                            break
                        if 'Home University' in next_line or 'Minority Seats' in next_line:
                            break
                        # Check if it looks like a continuation of values
                        if re.search(r'\d+\s*\([0-9.]+\)', next_line):
                            val_parts.append(next_line)
                            i += 1
                        else:
                            break
                    
                    raw_text = ' '.join(val_parts)
                    pairs = re.findall(r'(\d{1,7})\s*\(([0-9.]+)\)', raw_text)
                    
                    for idx, (rank, percentile) in enumerate(pairs):
                        st_code = seat_types[idx] if idx < len(seat_types) else f'CAT_{idx+1}'
                        cutoffs_found.append({
                            'round': CAP_ROUND,
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
    print(f"\nExtraction completed in {elapsed:.1f}s!")
    print(f"  Institutes: {len(institutes_found)}")
    print(f"  Courses:    {len(courses_found)}")
    print(f"  Cutoffs:    {len(cutoffs_found)}")
    if cutoffs_found:
        print(f"  Sample: {cutoffs_found[0]}")
    
    return institutes_found, courses_found, cutoffs_found


# ============================================================================
# Step 2: Import to Supabase
# ============================================================================

def import_to_supabase(institutes, courses, cutoffs):
    print(f"\n{'='*60}")
    print(f"Importing DSY CAP Round {CAP_ROUND} ({ACADEMIC_YEAR}) to Supabase")
    print(f"{'='*60}")
    
    # 2a. Register Source Document
    print("\n--- Registering source document ---")
    source_sql = f"""
    INSERT INTO public.source_documents (id, title, source_type, source_url, academic_year, checked_at, verified, notes)
    VALUES (
        '{SOURCE_DOC_ID}',
        'Government of Maharashtra - DSE CAP Round II Cutoff Matrix 2026-27 (Direct Second Year Engineering)',
        'OFFICIAL_PDF',
        'https://dse2026.mahacet.org',
        '{ACADEMIC_YEAR}',
        '2026-11-17',
        true,
        'Official CAP Round II cutoff for Direct Second Year Engineering - {len(cutoffs)} cutoff entries from {len(institutes)} institutes, {len(courses)} courses'
    )
    ON CONFLICT (id) DO UPDATE SET
        title = EXCLUDED.title,
        notes = EXCLUDED.notes,
        verified = true;
    """
    execute_sql(source_sql)
    print("  Source document registered.")
    
    # 2b. Load existing institutes and build map
    print("\n--- Loading existing institutes ---")
    inst_rows = execute_sql("SELECT id, institute_code FROM public.institutes;")
    inst_id_map = {}
    for r in inst_rows:
        c = str(r['institute_code']).strip()
        inst_id_map[c] = r['id']
        inst_id_map[c.lstrip('0')] = r['id']
    print(f"  Existing institutes in DB: {len(inst_rows)}")
    
    # Insert missing institutes
    inst_insert_values = []
    for code, inst in institutes.items():
        code_clean = code.strip()
        norm = code_clean.lstrip('0')
        if code_clean not in inst_id_map and norm not in inst_id_map:
            new_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"mh_inst_{code_clean}"))
            name_clean = inst['name'].replace("'", "''")
            inst_insert_values.append(
                f"('{new_id}', '{code_clean}', '{name_clean}', '', '', '', '', '', 'Un-Aided', '', '{SOURCE_DOC_ID}', true)"
            )
            inst_id_map[code_clean] = new_id
            inst_id_map[norm] = new_id
    
    if inst_insert_values:
        print(f"  Inserting {len(inst_insert_values)} new institutes...")
        for i in range(0, len(inst_insert_values), 100):
            chunk = inst_insert_values[i:i+100]
            chunk_sql = f"""
            INSERT INTO public.institutes (id, institute_code, institute_name, district, region, address, pincode, website, institute_type, university_name, source_id, is_published)
            VALUES {','.join(chunk)}
            ON CONFLICT (institute_code) DO NOTHING;
            """
            execute_sql(chunk_sql)
        print(f"  Institutes upserted.")
    else:
        print("  No new institutes needed.")
    
    # 2c. Ensure courses exist with BTECH_DSY route
    print("\n--- Loading existing DSY courses ---")
    course_rows = execute_sql(f"SELECT id, choice_code FROM public.courses WHERE academic_year = '{ACADEMIC_YEAR}' AND admission_route = '{ADMISSION_ROUTE}';")
    course_id_map = {str(r['choice_code']).strip(): r['id'] for r in course_rows}
    print(f"  Existing {ACADEMIC_YEAR} DSY courses: {len(course_id_map)}")
    
    course_insert_values = []
    for choice_code, cdata in courses.items():
        choice_clean = choice_code.strip()
        if choice_clean in course_id_map:
            continue
        c_inst_code = cdata.get('inst_code', choice_clean[:5]).strip()
        inst_id = inst_id_map.get(c_inst_code) or inst_id_map.get(c_inst_code.lstrip('0'))
        if not inst_id:
            inst_id = inst_id_map.get(choice_clean[:4]) or inst_id_map.get(choice_clean[:5])
        if not inst_id:
            continue
        course_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"mh_dsy_course_{choice_clean}_{ACADEMIC_YEAR}"))
        c_name = cdata.get('course_name', 'Engineering').replace("'", "''")
        branch = cdata.get('branch', 'OTHER').replace("'", "''")
        course_insert_values.append(
            f"('{course_id}', '{inst_id}', '{ACADEMIC_YEAR}', '{ADMISSION_ROUTE}', '{choice_clean}', '{c_name}', '{branch}', 60, '{SOURCE_DOC_ID}', true)"
        )
        course_id_map[choice_clean] = course_id
    
    if course_insert_values:
        print(f"  Inserting {len(course_insert_values)} DSY courses...")
        for i in range(0, len(course_insert_values), 150):
            chunk = course_insert_values[i:i+150]
            chunk_sql = f"""
            INSERT INTO public.courses (id, institute_id, academic_year, admission_route, choice_code, course_name, branch, intake, source_id, is_published)
            VALUES {','.join(chunk)}
            ON CONFLICT (academic_year, choice_code) DO UPDATE SET
                course_name = EXCLUDED.course_name,
                branch = EXCLUDED.branch,
                admission_route = EXCLUDED.admission_route,
                is_published = true;
            """
            execute_sql(chunk_sql)
        print(f"  DSY courses upserted.")
    else:
        print("  No new courses needed.")
    
    # Re-read all DSY courses
    course_rows = execute_sql(f"SELECT id, choice_code FROM public.courses WHERE academic_year = '{ACADEMIC_YEAR}';")
    course_id_map = {str(r['choice_code']).strip(): r['id'] for r in course_rows}
    print(f"  Total {ACADEMIC_YEAR} courses now: {len(course_id_map)}")
    
    # 2d. Insert Cutoffs
    print(f"\n--- Inserting CAP Round {CAP_ROUND} DSY cutoffs ---")
    cutoff_insert_values = []
    skipped = 0
    
    for c in cutoffs:
        choice_clean = c['choice_code'].strip()
        course_id = course_id_map.get(choice_clean)
        if not course_id:
            skipped += 1
            continue
        
        seat_type = c.get('seat_type', 'OPEN').replace("'", "''")
        category = c.get('category', 'OPEN').replace("'", "''")
        seat_pool = c.get('seat_pool', 'MH')
        percentile = float(c.get('percentile', 0.0))
        rank = int(c.get('rank', 0))
        page_num = int(c.get('page', 1))
        
        cut_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"cut_dsy_{ACADEMIC_YEAR}_round{CAP_ROUND}_{choice_clean}_{seat_type}_{rank}_{percentile}_{page_num}"))
        
        cutoff_insert_values.append(
            f"('{cut_id}', '{course_id}', '{ACADEMIC_YEAR}', {CAP_ROUND}, '{seat_pool}', '{category}', '{seat_type}', {percentile}, 'percentile', '{SOURCE_DOC_ID}', {page_num}, true)"
        )
    
    print(f"  Valid cutoffs to insert: {len(cutoff_insert_values)} (skipped {skipped} with no matching course)")
    
    batch_size = 1500
    total_batches = (len(cutoff_insert_values) + batch_size - 1) // batch_size if cutoff_insert_values else 0
    t_start = time.time()
    
    for b_idx in range(total_batches):
        start_idx = b_idx * batch_size
        chunk = cutoff_insert_values[start_idx:start_idx+batch_size]
        chunk_sql = f"""
        INSERT INTO public.cutoffs (id, course_id, academic_year, cap_round, seat_pool, category, seat_type_code, cutoff_value, cutoff_type, source_id, source_page, is_published)
        VALUES {','.join(chunk)}
        ON CONFLICT (id) DO NOTHING;
        """
        execute_sql(chunk_sql)
        if (b_idx + 1) % 5 == 0 or b_idx == total_batches - 1:
            elapsed = time.time() - t_start
            print(f"  Batch {b_idx+1}/{total_batches} ({len(chunk)} rows) - Elapsed: {elapsed:.1f}s")
    
    print(f"\n  DSY CAP Round {CAP_ROUND} import complete! Inserted {len(cutoff_insert_values)} cutoff rows in {time.time()-t_start:.1f}s.")
    
    # 2e. Verification
    print(f"\n{'='*60}")
    print("Verification Summary")
    print(f"{'='*60}")
    
    summary = execute_sql("""
    SELECT academic_year, admission_route, cap_round, count(*) as cnt
    FROM public.cutoffs c
    JOIN public.courses co ON c.course_id = co.id
    GROUP BY academic_year, admission_route, cap_round
    ORDER BY academic_year, admission_route, cap_round;
    """)
    print("Cutoffs in Database by Year, Route, and Round:")
    for row in summary:
        print(f"  {row['academic_year']} | {row['admission_route']} | Round {row['cap_round']} | {row['cnt']} cutoffs")
    
    total = execute_sql("SELECT count(*) as total FROM public.cutoffs;")
    print(f"\nGrand Total Cutoffs: {total[0]['total']}")


# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    # Step 1: Extract
    institutes, courses, cutoffs = extract_dsy_cutoffs(PDF_PATH)
    
    # Save extracted data for reference
    with open('extracted_dsy_cap2_cutoffs.json', 'w', encoding='utf-8') as f:
        json.dump(cutoffs, f, indent=2)
    with open('extracted_dsy_cap2_courses.json', 'w', encoding='utf-8') as f:
        json.dump(courses, f, indent=2)
    print(f"\nExtracted data saved to extracted_dsy_cap2_cutoffs.json and extracted_dsy_cap2_courses.json")
    
    # Step 2: Import
    import_to_supabase(institutes, courses, cutoffs)
    
    print("\n" + "="*60)
    print("ALL DONE! DSY CAP Round 2 (2026-27) imported successfully.")
    print("="*60)
