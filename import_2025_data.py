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

def execute_sql(sql):
    res = requests.post(
        f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/query",
        headers=headers,
        json={"query": sql},
        timeout=60
    )
    if res.status_code not in (200, 201):
        raise RuntimeError(f"SQL execution failed ({res.status_code}): {res.text[:400]}")
    return res.json()

print("1. Loading scraped institutes and extracted courses/cutoffs...")
with open("scraped_institutes.json", "r", encoding="utf-8") as f:
    scraped_institutes = json.load(f)

with open("extracted_courses.json", "r", encoding="utf-8") as f:
    extracted_courses = json.load(f)

with open("extracted_cutoffs.json", "r", encoding="utf-8") as f:
    extracted_cutoffs = json.load(f)

print(f"Loaded {len(scraped_institutes)} institutes, {len(extracted_courses)} courses, {len(extracted_cutoffs)} cutoffs.")

# 2. Register Source Document
SOURCE_DOC_ID = "20250000-0000-0000-0000-000000000001"
source_sql = f"""
INSERT INTO public.source_documents (id, title, source_type, source_url, academic_year, checked_at, verified, notes)
VALUES (
    '{SOURCE_DOC_ID}',
    'Government of Maharashtra State CET Cell - Engineering CAP Round I Cutoff Matrix 2025-26',
    'OFFICIAL_PDF',
    'https://fe2025.mahacet.org/StaticPages/frmInstituteList?did=1884',
    '2025-2026',
    '2026-11-16',
    true,
    'Official CAP Round I cutoff list for Maharashtra and Minority seats (PDF 1566 pages, Academic Year 2025-26)'
)
ON CONFLICT (id) DO UPDATE SET
    title = EXCLUDED.title,
    source_url = EXCLUDED.source_url,
    verified = true;
"""
print("Inserting source document...")
execute_sql(source_sql)

# 3. Check existing institutes in DB
existing_inst_rows = execute_sql("SELECT id, institute_code, institute_name FROM public.institutes;")
existing_by_code = {str(row['institute_code']).strip(): row['id'] for row in existing_inst_rows}
existing_by_norm = {str(row['institute_code']).strip().lstrip('0'): row['id'] for row in existing_inst_rows}

inst_id_map = {} # inst_code -> uuid
inst_insert_values = []
updates_count = 0

for code, inst in scraped_institutes.items():
    code_clean = code.strip()
    norm_code = code_clean.lstrip('0')
    
    name_clean = inst['name'].replace("'", "''")
    addr_clean = (inst.get('address') or '').replace("'", "''")
    dist_clean = (inst.get('district') or '').replace("'", "''")
    reg_clean = (inst.get('region') or '').replace("'", "''")
    type_clean = (inst.get('status') or 'Un-Aided').replace("'", "''")
    uni_clean = (inst.get('university') or '').replace("'", "''")
    
    # Check if this institute already exists in DB
    existing_id = existing_by_code.get(code_clean) or existing_by_norm.get(norm_code)
    
    if existing_id:
        update_sql = f"""
        UPDATE public.institutes
        SET 
            institute_code = '{code_clean}',
            district = CASE WHEN '{dist_clean}' <> '' THEN '{dist_clean}' ELSE district END,
            region = CASE WHEN '{reg_clean}' <> '' THEN '{reg_clean}' ELSE region END,
            address = CASE WHEN '{addr_clean}' <> '' THEN '{addr_clean}' ELSE address END,
            institute_type = '{type_clean}',
            university_name = CASE WHEN '{uni_clean}' <> '' THEN '{uni_clean}' ELSE university_name END,
            source_id = '{SOURCE_DOC_ID}',
            is_published = true
        WHERE id = '{existing_id}';
        """
        execute_sql(update_sql)
        inst_id_map[code_clean] = existing_id
        inst_id_map[norm_code] = existing_id
        updates_count += 1
    else:
        new_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"mh_inst_{code_clean}"))
        inst_id_map[code_clean] = new_id
        inst_id_map[norm_code] = new_id
        inst_insert_values.append(
            f"('{new_id}', '{code_clean}', '{name_clean}', '{dist_clean}', '{reg_clean}', '{addr_clean}', '', '', '{type_clean}', '{uni_clean}', '{SOURCE_DOC_ID}', true)"
        )

print(f"Updated {updates_count} existing institutes. Inserting {len(inst_insert_values)} new institutes...")

batch_size = 100
for i in range(0, len(inst_insert_values), batch_size):
    chunk = inst_insert_values[i:i+batch_size]
    chunk_sql = f"""
    INSERT INTO public.institutes (id, institute_code, institute_name, district, region, address, pincode, website, institute_type, university_name, source_id, is_published)
    VALUES {','.join(chunk)}
    ON CONFLICT (institute_code) DO UPDATE SET
        institute_name = EXCLUDED.institute_name,
        district = CASE WHEN EXCLUDED.district <> '' THEN EXCLUDED.district ELSE institutes.district END,
        region = CASE WHEN EXCLUDED.region <> '' THEN EXCLUDED.region ELSE institutes.region END,
        address = CASE WHEN EXCLUDED.address <> '' THEN EXCLUDED.address ELSE institutes.address END,
        institute_type = EXCLUDED.institute_type,
        university_name = CASE WHEN EXCLUDED.university_name <> '' THEN EXCLUDED.university_name ELSE institutes.university_name END,
        source_id = EXCLUDED.source_id,
        is_published = true;
    """
    execute_sql(chunk_sql)
print("All institutes inserted/updated successfully.")

# Re-read institutes from DB to ensure complete inst_id_map
all_inst_rows = execute_sql("SELECT id, institute_code FROM public.institutes;")
for row in all_inst_rows:
    code = str(row['institute_code']).strip()
    inst_id_map[code] = row['id']
    inst_id_map[code.lstrip('0')] = row['id']

print(f"Total institutes in database now: {len(all_inst_rows)}")

# 4. Prepare Courses
course_id_map = {} # choice_code -> uuid
course_insert_values = []

for choice_code, cdata in extracted_courses.items():
    choice_clean = choice_code.strip()
    c_inst_code = cdata.get('inst_code', choice_clean[:5]).strip()
    
    inst_id = inst_id_map.get(c_inst_code) or inst_id_map.get(c_inst_code.lstrip('0'))
    if not inst_id:
        inst_id = inst_id_map.get(choice_clean[:4]) or inst_id_map.get(choice_clean[:5])
        
    if not inst_id:
        continue
        
    course_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"mh_course_{choice_clean}_2025"))
    course_id_map[choice_clean] = course_id
    
    c_name = cdata.get('course_name', 'Engineering').replace("'", "''")
    branch = cdata.get('branch', 'OTHER').replace("'", "''")
    
    course_insert_values.append(
        f"('{course_id}', '{inst_id}', '2025-2026', 'BTECH_FIRST_YEAR', '{choice_clean}', '{c_name}', '{branch}', 60, '{SOURCE_DOC_ID}', true)"
    )

print(f"Upserting {len(course_insert_values)} courses in batches...")
batch_size = 150
for i in range(0, len(course_insert_values), batch_size):
    chunk = course_insert_values[i:i+batch_size]
    chunk_sql = f"""
    INSERT INTO public.courses (id, institute_id, academic_year, admission_route, choice_code, course_name, branch, intake, source_id, is_published)
    VALUES {','.join(chunk)}
    ON CONFLICT (academic_year, choice_code) DO UPDATE SET
        course_name = EXCLUDED.course_name,
        branch = EXCLUDED.branch,
        source_id = EXCLUDED.source_id,
        is_published = true;
    """
    execute_sql(chunk_sql)
print("Courses upserted successfully.")

# Re-read courses from DB to ensure complete course_id_map
all_course_rows = execute_sql("SELECT id, choice_code FROM public.courses WHERE academic_year = '2025-2026';")
for row in all_course_rows:
    cc = str(row['choice_code']).strip()
    course_id_map[cc] = row['id']

print(f"Total 2025-2026 courses in database now: {len(all_course_rows)}")

# 5. Prepare Cutoffs
cutoff_insert_values = []
skipped = 0

for cut in extracted_cutoffs:
    choice_clean = cut['choice_code'].strip()
    course_id = course_id_map.get(choice_clean)
    if not course_id:
        skipped += 1
        continue
        
    seat_type = cut.get('seat_type', 'OPEN').replace("'", "''")
    category = cut.get('category', 'OPEN').replace("'", "''")
    percentile = cut.get('percentile', 0.0)
    page_num = cut.get('page', 1)
    
    cut_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"cut_{choice_clean}_{seat_type}_{percentile}_{page_num}"))
    
    cutoff_insert_values.append(
        f"('{cut_id}', '{course_id}', '2025-2026', 1, 'MH', '{category}', '{seat_type}', {percentile}, 'percentile', '{SOURCE_DOC_ID}', {page_num}, true)"
    )

print(f"Total cutoffs to insert: {len(cutoff_insert_values)} (skipped {skipped})")

# Insert in chunks of 1500
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
        print(f"  Inserted batch {b_idx+1}/{total_batches} ({len(chunk)} rows) - Total time: {time.time()-t_start:.1f}s")

print(f"All {len(cutoff_insert_values)} cutoffs inserted successfully in {time.time()-t_start:.1f}s!")

# Verification counts
final_counts = execute_sql("""
SELECT 
    (SELECT count(*) FROM public.institutes) as total_institutes,
    (SELECT count(*) FROM public.courses WHERE academic_year = '2025-2026') as courses_2025,
    (SELECT count(*) FROM public.cutoffs WHERE academic_year = '2025-2026') as cutoffs_2025;
""")
print("Final Database Counts:", final_counts)
