import re
import json
import time
import urllib3
import requests
from concurrent.futures import ThreadPoolExecutor

urllib3.disable_warnings()

# 1. Parse all institutes from mahacet_institutes.html
with open('mahacet_institutes.html', 'r', encoding='utf-8') as f:
    html = f.read()

tables = re.findall(r'<table[^>]*>(.*?)</table>', html, re.DOTALL | re.IGNORECASE)
rows = re.findall(r'<tr[^>]*>(.*?)</tr>', tables[1], re.DOTALL | re.IGNORECASE)

institutes = {}
for r in rows[1:]:
    cells = re.findall(r'<td[^>]*>(.*?)</td>', r, re.DOTALL | re.IGNORECASE)
    clean_cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
    if len(clean_cells) >= 5:
        sr_no = clean_cells[0]
        code = clean_cells[1]
        name = clean_cells[2]
        status = clean_cells[3]
        intake = clean_cells[4]
        
        # Link for summary
        m_link = re.search(r'href="([^"]+)"', cells[1])
        link = m_link.group(1) if m_link else f'frmInstituteSummary.aspx?InstituteCode={code}'
        
        institutes[code] = {
            'code': code,
            'name': name,
            'status': status,
            'total_intake': int(intake) if intake.isdigit() else 0,
            'link': link,
            'address': '',
            'region': '',
            'district': '',
            'autonomy': '',
            'minority': '',
            'university': ''
        }

print(f'Parsed {len(institutes)} institutes from list page.')

# 2. Fetch summary pages with ThreadPoolExecutor
headers = {'User-Agent': 'Mozilla/5.0'}

def fetch_summary(inst):
    code = inst['code']
    url = f'https://fe2025.mahacet.org/StaticPages/frmInstituteSummary.aspx?InstituteCode={code}'
    try:
        r = requests.get(url, headers=headers, timeout=12, verify=False)
        if r.status_code == 200:
            txt = r.text
            # Address
            m_addr = re.search(r'Institute Address</td>\s*<td[^>]*>(.*?)</td>', txt, re.IGNORECASE | re.DOTALL)
            if not m_addr:
                m_addr = re.search(r'Institute Address\s*</td>\s*<td[^>]*>\s*([^<]+)', txt, re.IGNORECASE)
            # Region & District
            m_reg = re.search(r'Region</td>\s*<td[^>]*>(.*?)</td>', txt, re.IGNORECASE | re.DOTALL)
            m_dist = re.search(r'District</td>\s*<td[^>]*>(.*?)</td>', txt, re.IGNORECASE | re.DOTALL)
            # Autonomy & Minority
            m_auto = re.search(r'Autonomy Status</td>\s*<td[^>]*>(.*?)</td>', txt, re.IGNORECASE | re.DOTALL)
            m_min = re.search(r'Minority Status</td>\s*<td[^>]*>(.*?)</td>', txt, re.IGNORECASE | re.DOTALL)
            # University from first course row
            m_uni = re.search(r'Course Details.*?University.*?<tr[^>]*>\s*<td[^>]*>.*?</td>\s*<td[^>]*>.*?</td>\s*<td[^>]*>(.*?)</td>', txt, re.IGNORECASE | re.DOTALL)
            
            clean = lambda m: re.sub(r'<[^>]+>', '', m.group(1)).strip() if m else ''
            
            inst['address'] = clean(m_addr)
            inst['region'] = clean(m_reg)
            inst['district'] = clean(m_dist)
            inst['autonomy'] = clean(m_auto)
            inst['minority'] = clean(m_min)
            inst['university'] = clean(m_uni)
    except Exception as e:
        pass
    return inst

print('Fetching details for institutes...')
t0 = time.time()
with ThreadPoolExecutor(max_workers=25) as executor:
    updated_list = list(executor.map(fetch_summary, institutes.values()))

print(f'Fetched details for {len(updated_list)} institutes in {time.time()-t0:.2f}s.')

with open('scraped_institutes.json', 'w', encoding='utf-8') as f:
    json.dump({inst['code']: inst for inst in updated_list}, f, indent=2)

print('Saved to scraped_institutes.json')
sample = updated_list[0]
print('Sample institute:', sample)
