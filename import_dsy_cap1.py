"""
CampusHub - Import DSY CAP Round 1 Cutoffs (2026-27) from 9c529bfc-f112-433a-8ede-91b8e7b26fbf.pdf to Supabase
=================================================================================================================
Imports official Maharashtra State CET Cell Direct Second Year Engineering (DSE) 
CAP Round 1 allotment cutoff records into Supabase PostgreSQL.
"""

import os
import re
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

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

ACADEMIC_YEAR = "2026-2027"
CAP_ROUND = 1
ADMISSION_ROUTE = "BTECH_DSY"
SOURCE_DOC_ID = "20260000-0000-0000-d5e0-000000000001"
DATA_PATH = os.path.join(os.path.dirname(__file__), "assets", "data", "dsy_2026_cap_cutoffs.json")


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


def decode_category(seat_type):
    st = str(seat_type or '').upper().strip()
    core = re.sub(r'^[GLS]+', '', st)
    if 'TFWS' in st:
        return 'TFWS'
    elif 'EWS' in st:
        return 'EWS'
    elif 'MI' in st:
        return 'MINORITY'
    elif 'ORPHAN' in st or 'ORP' in st:
        return 'ORPHAN'
    elif 'PWDR' in st or 'PWD' in st:
        return 'PWD'
    elif 'DEFR' in st or 'DEF' in st:
        return 'DEF'
    elif core.startswith('OPEN') or st in ('GOPEN', 'LOPEN', 'SOPEN'):
        return 'OPEN'
    elif core.startswith('OBC') or st in ('GOBC', 'LOBC', 'SOBC'):
        return 'OBC-NCL'
    elif core.startswith('SEBC') or st in ('GSEBC', 'LSEBC', 'SSEBC'):
        return 'SEBC'
    elif core.startswith('SC') or st in ('GSC', 'LSC', 'SSC'):
        return 'SC'
    elif core.startswith('ST') or st in ('GST', 'LST', 'SST'):
        return 'ST'
    elif core.startswith('VJ') or core.startswith('DT'):
        return 'VJNT'
    elif core.startswith('NTA') or core.startswith('NT1'):
        return 'VJNT'
    elif core.startswith('NTB') or core.startswith('NT2'):
        return 'NT-B'
    elif core.startswith('NTC') or core.startswith('NT3'):
        return 'NT-C'
    elif core.startswith('NTD') or core.startswith('NT4'):
        return 'NT-D'
    return 'OPEN'


def run_import():
    print("=" * 60)
    print("Starting DSY CAP Round 1 Cutoff Import to Supabase")
    print("=" * 60)

    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Missing extracted data at {DATA_PATH}")

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        cutoffs_data = json.load(f)

    print(f"Loaded {len(cutoffs_data)} records from {DATA_PATH}")

    # 1. Register Source Document
    print("\n--- 1. Registering Source Document ---")
    source_sql = f"""
    INSERT INTO public.source_documents (id, title, source_type, source_url, academic_year, checked_at, verified, notes)
    VALUES (
        '{SOURCE_DOC_ID}',
        'Government of Maharashtra - DSE CAP Round I Cutoff Matrix 2026-27 (Direct Second Year Engineering)',
        'OFFICIAL_PDF',
        'https://fe2026.mahacet.org/dse2026',
        '{ACADEMIC_YEAR}',
        '2026-11-17',
        true,
        'Official CAP Round I cutoff for Direct Second Year Engineering ( lateral entry ) from 9c529bfc-f112-433a-8ede-91b8e7b26fbf.pdf ({len(cutoffs_data)} records)'
    )
    ON CONFLICT (id) DO UPDATE SET
        title = EXCLUDED.title,
        notes = EXCLUDED.notes,
        verified = true;
    """
    execute_sql(source_sql)
    print("Source document registered successfully.")

    # 2. Get Institutes Map
    print("\n--- 2. Checking Institutes ---")
    inst_rows = execute_sql("SELECT id, institute_code FROM public.institutes;")
    inst_id_map = {}
    for r in inst_rows:
        c = str(r['institute_code']).strip()
        inst_id_map[c] = r['id']
        inst_id_map[c.lstrip('0')] = r['id']
    print(f"Existing institutes in DB: {len(inst_rows)}")

    # 3. Get Courses Map
    print("\n--- 3. Checking DSY Courses ---")
    course_rows = execute_sql(f"SELECT id, choice_code FROM public.courses WHERE academic_year = '{ACADEMIC_YEAR}' AND admission_route = '{ADMISSION_ROUTE}';")
    course_id_map = {str(r['choice_code']).strip(): r['id'] for r in course_rows}
    print(f"Existing {ACADEMIC_YEAR} DSY courses: {len(course_id_map)}")

    # Check if any new courses need to be inserted
    new_courses = []
    for item in cutoffs_data:
        choice_code = str(item.get("choice_code", "")).strip()
        if not choice_code or choice_code in course_id_map:
            continue
        inst_code = str(item.get("college_code", choice_code[:4])).strip()
        inst_id = inst_id_map.get(inst_code) or inst_id_map.get(inst_code.lstrip('0'))
        if not inst_id:
            continue
        c_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"mh_dsy_course_{choice_code}_{ACADEMIC_YEAR}"))
        c_name = str(item.get("course_name", "Engineering")).replace("'", "''")
        branch = str(item.get("branch_code", "OTHER")).replace("'", "''")
        new_courses.append(
            f"('{c_id}', '{inst_id}', '{ACADEMIC_YEAR}', '{ADMISSION_ROUTE}', '{choice_code}', '{c_name}', '{branch}', 60, '{SOURCE_DOC_ID}', true)"
        )
        course_id_map[choice_code] = c_id

    if new_courses:
        print(f"Inserting {len(new_courses)} missing DSY courses...")
        for i in range(0, len(new_courses), 150):
            chunk = new_courses[i:i+150]
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
        print("Missing DSY courses inserted.")
    else:
        print("All DSY courses are already mapped.")

    # 4. Insert CAP Round 1 Cutoffs
    print("\n--- 4. Inserting CAP Round 1 Cutoffs ---")
    cutoff_insert_values = []
    skipped = 0

    for item in cutoffs_data:
        choice_clean = str(item.get("choice_code", "")).strip()
        course_id = course_id_map.get(choice_clean)
        if not course_id:
            skipped += 1
            continue

        seat_type = str(item.get("seat_type") or "GOPEN").replace("'", "''")
        category = str(item.get("category") or decode_category(seat_type)).replace("'", "''")
        quota = str(item.get("quota") or "SL").replace("'", "''")
        rank_val = item.get("rank")
        score_val = item.get("score")
        page_num = item.get("page", 1)

        val_to_use = score_val if score_val is not None else (rank_val if rank_val is not None else 0.0)
        try:
            val_to_use = float(val_to_use)
        except Exception:
            val_to_use = 0.0

        cut_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"cut_dsy_{ACADEMIC_YEAR}_r{CAP_ROUND}_{choice_clean}_{seat_type}_{rank_val}_{score_val}_{page_num}"))

        cutoff_insert_values.append(
            f"('{cut_id}', '{course_id}', '{ACADEMIC_YEAR}', {CAP_ROUND}, '{quota}', '{category}', '{seat_type}', {val_to_use}, 'percentile', '{SOURCE_DOC_ID}', {page_num}, true)"
        )

    print(f"Prepared {len(cutoff_insert_values)} CAP 1 cutoff rows (skipped {skipped})")

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
        elapsed = time.time() - t_start
        print(f"  Batch {b_idx+1}/{total_batches} ({len(chunk)} rows) - Elapsed: {elapsed:.1f}s")

    print(f"\nImport finished! Inserted CAP 1 cutoffs in {time.time()-t_start:.1f}s.")

    # 5. Verification
    print("\n--- 5. Verification ---")
    summary = execute_sql(f"""
    SELECT academic_year, admission_route, cap_round, count(*) as cnt
    FROM public.cutoffs c
    JOIN public.courses co ON c.course_id = co.id
    WHERE academic_year = '{ACADEMIC_YEAR}' AND admission_route = '{ADMISSION_ROUTE}'
    GROUP BY academic_year, admission_route, cap_round
    ORDER BY cap_round;
    """)
    print("DSY Cutoffs in Database:")
    for row in summary:
        print(f"  {row['academic_year']} | {row['admission_route']} | Round {row['cap_round']} | {row['cnt']} cutoffs")


if __name__ == "__main__":
    run_import()
