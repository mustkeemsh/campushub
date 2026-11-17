import os
import json
import uuid
import time
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("SUPABASE_ACCESS_TOKEN")
PROJECT_REF = os.getenv("SUPABASE_PROJECT_REF", "uwaddyejdswshzamhjfs")

if not TOKEN:
    raise ValueError("SUPABASE_ACCESS_TOKEN is required in .env")

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def execute_sql(sql, retries=3):
    for attempt in range(retries):
        try:
            res = requests.post(
                f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/query",
                headers=headers,
                json={"query": sql},
                timeout=90
            )
            if res.status_code in (200, 201):
                return res.json()
            err_msg = res.text[:400]
            if attempt < retries - 1:
                print(f"Warning: query returned {res.status_code}, retrying ({attempt+1}/{retries})...")
                time.sleep(2)
            else:
                raise RuntimeError(f"SQL execution failed ({res.status_code}): {err_msg}")
        except Exception as e:
            if attempt < retries - 1:
                print(f"Warning: request error: {e}, retrying ({attempt+1}/{retries})...")
                time.sleep(2)
            else:
                raise e

print("==================================================")
print("CampusHub - Importing CAP Rounds 2, 3, 4 Data")
print("==================================================")

# 1. Register Source Documents
SOURCE_DOCS = {
    2: "20250000-0000-0000-0000-000000000002",
    3: "20250000-0000-0000-0000-000000000003",
    4: "20250000-0000-0000-0000-000000000004"
}

source_docs_meta = [
    (
        SOURCE_DOCS[2],
        'Government of Maharashtra State CET Cell - Engineering CAP Round II Cutoff Matrix 2025-26',
        'Official CAP Round II cutoff list for Maharashtra and Minority seats (PDF 1516 pages, Academic Year 2025-26)'
    ),
    (
        SOURCE_DOCS[3],
        'Government of Maharashtra State CET Cell - Engineering CAP Round III Cutoff Matrix 2025-26',
        'Official CAP Round III cutoff list for Maharashtra and Minority seats (PDF 1359 pages, Academic Year 2025-26)'
    ),
    (
        SOURCE_DOCS[4],
        'Government of Maharashtra State CET Cell - Engineering CAP Round IV Cutoff Matrix 2025-26',
        'Official CAP Round IV cutoff list for Maharashtra and Minority seats (PDF 1234 pages, Academic Year 2025-26)'
    )
]

for doc_id, title, notes in source_docs_meta:
    source_sql = f"""
    INSERT INTO public.source_documents (id, title, source_type, source_url, academic_year, checked_at, verified, notes)
    VALUES (
        '{doc_id}',
        '{title}',
        'OFFICIAL_PDF',
        'https://fe2025.mahacet.org/StaticPages/frmInstituteList?did=1884',
        '2025-2026',
        '2026-11-16',
        true,
        '{notes}'
    )
    ON CONFLICT (id) DO UPDATE SET
        title = EXCLUDED.title,
        notes = EXCLUDED.notes,
        verified = true;
    """
    execute_sql(source_sql)
print("Source documents for Rounds 2, 3, 4 registered successfully.")

# 2. Load Institutes and build inst_id_map
inst_rows = execute_sql("SELECT id, institute_code FROM public.institutes;")
inst_id_map = {}
for r in inst_rows:
    c = str(r['institute_code']).strip()
    inst_id_map[c] = r['id']
    inst_id_map[c.lstrip('0')] = r['id']
print(f"Loaded {len(inst_rows)} institutes from database.")

# Check if scraped_institutes has any missing in DB
with open("scraped_institutes.json", "r", encoding="utf-8") as f:
    scraped_institutes = json.load(f)

inst_insert_values = []
for code, inst in scraped_institutes.items():
    code_clean = code.strip()
    norm = code_clean.lstrip('0')
    if code_clean not in inst_id_map and norm not in inst_id_map:
        new_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"mh_inst_{code_clean}"))
        name_clean = inst['name'].replace("'", "''")
        addr_clean = (inst.get('address') or '').replace("'", "''")
        dist_clean = (inst.get('district') or '').replace("'", "''")
        reg_clean = (inst.get('region') or '').replace("'", "''")
        type_clean = (inst.get('status') or 'Un-Aided').replace("'", "''")
        uni_clean = (inst.get('university') or '').replace("'", "''")
        inst_insert_values.append(
            f"('{new_id}', '{code_clean}', '{name_clean}', '{dist_clean}', '{reg_clean}', '{addr_clean}', '', '', '{type_clean}', '{uni_clean}', '{SOURCE_DOCS[2]}', true)"
        )
        inst_id_map[code_clean] = new_id
        inst_id_map[norm] = new_id

if inst_insert_values:
    print(f"Inserting {len(inst_insert_values)} missing institutes...")
    chunk_sql = f"""
    INSERT INTO public.institutes (id, institute_code, institute_name, district, region, address, pincode, website, institute_type, university_name, source_id, is_published)
    VALUES {','.join(inst_insert_values)}
    ON CONFLICT (institute_code) DO NOTHING;
    """
    execute_sql(chunk_sql)

# 3. Load Courses and ensure all 2025-2026 courses exist
with open("extracted_courses.json", "r", encoding="utf-8") as f:
    all_courses = json.load(f)

course_rows = execute_sql("SELECT id, choice_code FROM public.courses WHERE academic_year = '2025-2026';")
course_id_map = {str(r['choice_code']).strip(): r['id'] for r in course_rows}
print(f"Existing 2025-2026 courses in database: {len(course_id_map)}")

course_insert_values = []
for choice_code, cdata in all_courses.items():
    choice_clean = choice_code.strip()
    if choice_clean in course_id_map:
        continue
    c_inst_code = cdata.get('inst_code', choice_clean[:5]).strip()
    inst_id = inst_id_map.get(c_inst_code) or inst_id_map.get(c_inst_code.lstrip('0'))
    if not inst_id:
        inst_id = inst_id_map.get(choice_clean[:4]) or inst_id_map.get(choice_clean[:5])
    if not inst_id:
        continue
    course_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"mh_course_{choice_clean}_2025"))
    c_name = cdata.get('course_name', 'Engineering').replace("'", "''")
    branch = cdata.get('branch', 'OTHER').replace("'", "''")
    course_insert_values.append(
        f"('{course_id}', '{inst_id}', '2025-2026', 'BTECH_FIRST_YEAR', '{choice_clean}', '{c_name}', '{branch}', 60, '{SOURCE_DOCS[2]}', true)"
    )
    course_id_map[choice_clean] = course_id

if course_insert_values:
    print(f"Upserting {len(course_insert_values)} new courses...")
    batch_size = 150
    for i in range(0, len(course_insert_values), batch_size):
        chunk = course_insert_values[i:i+batch_size]
        chunk_sql = f"""
        INSERT INTO public.courses (id, institute_id, academic_year, admission_route, choice_code, course_name, branch, intake, source_id, is_published)
        VALUES {','.join(chunk)}
        ON CONFLICT (academic_year, choice_code) DO UPDATE SET
            course_name = EXCLUDED.course_name,
            branch = EXCLUDED.branch,
            is_published = true;
        """
        execute_sql(chunk_sql)
    print("New courses upserted.")

# Re-read all courses
course_rows = execute_sql("SELECT id, choice_code FROM public.courses WHERE academic_year = '2025-2026';")
course_id_map = {str(r['choice_code']).strip(): r['id'] for r in course_rows}
print(f"Total 2025-2026 courses now ready: {len(course_id_map)}")

# 4. Insert Cutoffs for Round 2, Round 3, and Round 4
total_cutoffs_inserted = 0

for r_num in [2, 3, 4]:
    print(f"\n--- Preparing CAP Round {r_num} Cutoffs ---")
    json_path = f"extracted_cap{r_num}_cutoffs.json"
    with open(json_path, "r", encoding="utf-8") as f:
        cuts = json.load(f)
    print(f"Loaded {len(cuts)} records from {json_path}")
    
    source_doc_id = SOURCE_DOCS[r_num]
    cutoff_insert_values = []
    skipped = 0
    
    for c in cuts:
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
        
        cut_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"cut_2025_round{r_num}_{choice_clean}_{seat_type}_{rank}_{percentile}_{page_num}"))
        
        cutoff_insert_values.append(
            f"('{cut_id}', '{course_id}', '2025-2026', {r_num}, '{seat_pool}', '{category}', '{seat_type}', {percentile}, 'percentile', '{source_doc_id}', {page_num}, true)"
        )
        
    print(f"Round {r_num}: {len(cutoff_insert_values)} valid cutoffs to insert (skipped {skipped})")
    
    batch_size = 1500
    total_batches = (len(cutoff_insert_values) + batch_size - 1) // batch_size
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
            print(f"  Round {r_num}: Batch {b_idx+1}/{total_batches} ({len(chunk)} rows) - Elapsed: {time.time()-t_start:.1f}s")
            
    total_cutoffs_inserted += len(cutoff_insert_values)
    print(f"CAP Round {r_num} complete! Inserted {len(cutoff_insert_values)} rows in {time.time()-t_start:.1f}s.")

print("\n==================================================")
print("Verification and Final Database Summary")
print("==================================================")

summary = execute_sql("""
SELECT academic_year, cap_round, count(*) 
FROM public.cutoffs 
GROUP BY academic_year, cap_round 
ORDER BY academic_year, cap_round;
""")
print("Cutoffs in Database by Year and Round:")
for row in summary:
    print(f"  Academic Year: {row['academic_year']} | CAP Round: {row['cap_round']} | Count: {row['count']}")

total_overall = execute_sql("SELECT count(*) as total FROM public.cutoffs;")
print(f"\nGrand Total Cutoffs in Database: {total_overall[0]['total']}")
