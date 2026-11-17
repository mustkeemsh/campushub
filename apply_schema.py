import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("SUPABASE_ACCESS_TOKEN")
PROJECT_REF = os.getenv("SUPABASE_PROJECT_REF", "uwaddyejdswshzamhjfs")

if not TOKEN:
    raise ValueError("SUPABASE_ACCESS_TOKEN not set in environment or .env file.")

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

print(f"Reading schema.sql...")
with open("schema.sql", "r", encoding="utf-8") as f:
    sql_script = f.read()

print(f"Sending SQL script to Supabase ({len(sql_script)} bytes)...")
res = requests.post(
    f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/query",
    headers=headers,
    json={"query": sql_script},
    timeout=60
)

print(f"Status Code: {res.status_code}")
if res.status_code in (200, 201):
    print("SUCCESS: schema.sql executed on remote Supabase database!")
else:
    print(f"Error response: {res.text}")

# Now query the list of public tables
check_res = requests.post(
    f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/query",
    headers=headers,
    json={"query": "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;"},
    timeout=15
)

if check_res.status_code in (200, 201):
    tables = [row["tablename"] for row in check_res.json()]
    print(f"\nAll Public Tables currently in Supabase ({len(tables)}):")
    for t in tables:
        print(f"  - {t}")
else:
    print(f"Check error: {check_res.text}")
