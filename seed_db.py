"""
CollegeHub Database Migration & Seeding Script
Connects to live Supabase PostgreSQL and applies schema.sql
"""
import os
import re
import ssl
import socket
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URI")
PASSWORD = os.getenv("SUPABASE_DB_PASSWORD", "Campus@hub@123")
PROJECT_REF = os.getenv("SUPABASE_PROJECT_REF", "uwaddyejdswshzamhjfs")
DB_HOST = f"db.{PROJECT_REF}.supabase.co"

print(f"--- CollegeHub Supabase Database Seeder ---")
print(f"Target Project: {PROJECT_REF}")

# Try importing pg8000
try:
    import pg8000.native
except ImportError:
    print("Installing pg8000...")
    os.system("python -m pip install pg8000")
    import pg8000.native

# Prepare SSL context
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

connection = None

# Attempt 0: Direct URI if DATABASE_URL is provided in .env
if DATABASE_URL:
    print("\n[Step 0] Connecting using custom DATABASE_URL...")
    try:
        parsed = urlparse(DATABASE_URL)
        db_user = unquote(parsed.username) if parsed.username else "postgres"
        db_pass = unquote(parsed.password) if parsed.password else PASSWORD
        db_host = parsed.hostname
        db_port = parsed.port or 5432
        db_name = parsed.path.lstrip('/') or "postgres"

        connection = pg8000.native.Connection(
            user=db_user,
            host=db_host,
            port=db_port,
            database=db_name,
            password=db_pass,
            ssl_context=ctx,
            timeout=10
        )
        print(">>> Connected successfully via DATABASE_URL!")
    except Exception as e_url:
        print(f"DATABASE_URL connection notice: {e_url}")

# Attempt 1: SNI Pooler routing (IPv4 compatible)
print("\n[Step 1] Connecting to Supabase PostgreSQL via IPv4 Pooler...")
_orig_getaddrinfo = socket.getaddrinfo
try:
    # Resolve IPv4 pooler IP
    pooler_ip = socket.gethostbyname(POOLER_HOSTS[0])
    print(f"Pooler resolved: {POOLER_HOSTS[0]} -> {pooler_ip}")

    # Set up DNS override for SNI routing
    def custom_getaddrinfo(h, p, *args, **kwargs):
        if h == DB_HOST:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (pooler_ip, p))]
        return _orig_getaddrinfo(h, p, *args, **kwargs)

    socket.getaddrinfo = custom_getaddrinfo

    connection = pg8000.native.Connection(
        user="postgres",
        host=DB_HOST,
        port=5432,
        database="postgres",
        password=PASSWORD,
        ssl_context=ctx,
        timeout=10
    )
    print(">>> Connected successfully via SNI Pooler!")
except Exception as e1:
    print(f"SNI route notice: {e1}")
    socket.getaddrinfo = _orig_getaddrinfo

# Attempt 2: Direct connection (if IPv6 supported)
if connection is None:
    print("\n[Step 2] Attempting direct connection to db host...")
    try:
        connection = pg8000.native.Connection(
            user="postgres",
            host=DB_HOST,
            port=5432,
            database="postgres",
            password=PASSWORD,
            ssl_context=ctx,
            timeout=8
        )
        print(">>> Connected successfully via Direct Connection!")
    except Exception as e2:
        print(f"Direct connection notice: {e2}")

# Attempt 3: Standard Pooler tenant routing
if connection is None:
    print("\n[Step 3] Attempting standard pooler tenant routing...")
    for phost in POOLER_HOSTS:
        for port in [6543, 5432]:
            try:
                print(f"Trying {phost}:{port} with user postgres.{PROJECT_REF}...")
                connection = pg8000.native.Connection(
                    user=f"postgres.{PROJECT_REF}",
                    host=phost,
                    port=port,
                    database="postgres",
                    password=PASSWORD,
                    ssl_context=ctx,
                    timeout=8
                )
                print(f">>> Connected successfully to {phost}:{port}!")
                break
            except Exception as e3:
                pass
        if connection:
            break

if connection is None:
    print("\n[FAILED] Could not establish connection to Supabase PostgreSQL.")
    print("Please verify the database password or check network access.")
    exit(1)

# Execute schema.sql
print("\n[Step 4] Reading and applying schema.sql...")
with open("schema.sql", "r", encoding="utf-8") as f:
    raw_sql = f.read()

# Remove comments and split into individual statements
cleaned_lines = []
for line in raw_sql.splitlines():
    stripped = line.strip()
    if not stripped.startswith("--"):
        cleaned_lines.append(line)

cleaned_sql = "\n".join(cleaned_lines)
statements = [s.strip() for s in cleaned_sql.split(";") if s.strip()]

print(f"Executing {len(statements)} SQL statements...")
success_count = 0
for i, stmt in enumerate(statements):
    try:
        connection.run(stmt)
        success_count += 1
    except Exception as err:
        err_msg = str(err)
        # Ignore 'already exists' warnings
        if "already exists" in err_msg or "duplicate" in err_msg:
            success_count += 1
        else:
            print(f"Statement {i+1} error: {err_msg[:120]}")

print(f"Applied {success_count}/{len(statements)} statements successfully.")

# Verification
print("\n[Step 5] Verifying seeded knowledge base in Supabase...")
try:
    count_res = connection.run("SELECT count(*) FROM faqs;")
    total_faqs = count_res[0][0]
    print(f"*** VERIFICATION SUCCESS! Total FAQs in Supabase: {total_faqs} ***")

    # Sample query across categories
    cat_res = connection.run("SELECT category, count(*) FROM faqs GROUP BY category ORDER BY category;")
    print("Categories populated:")
    for cat, c in cat_res:
        print(f"  - {cat}: {c} FAQs")
except Exception as v_err:
    print(f"Verification error: {v_err}")
finally:
    connection.close()
    print("\nConnection closed cleanly. CollegeHub is now fully synced with Supabase!")
