import time
from routes.api_recommendations import compute_dsy_recommendations

t0 = time.time()
res, status = compute_dsy_recommendations({
    'admission_type': 'dsy',
    'diploma_branch': 'Computer Engineering',
    'metric_type': 'rank',
    'score': 2500,
    'category': 'OPEN',
    'preferred_engineering_branches': ['CSE', 'AIDS', 'IT'],
    'preferred_districts': ['Pune', 'Mumbai Suburban', 'Mumbai City'],
    'quota': 'SL',
    'cap_round': 'CAP Round I',
    'admission_year': '2026-2027',
    'sort_by': 'rank_asc'
})
t1 = time.time()

print(f"Computed in {(t1 - t0) * 1000:.1f}ms")
print("Status:", status if isinstance(status, int) else 200)
print("Count:", res.get("count"))
print("Data status:", res.get("data_status"))
recs = res.get("recommendations", [])
print(f"Total recommendations returned: {len(recs)}")
if recs:
    print("\nTop 5 within cutoff range (sorted by rank):")
    for r in recs[:5]:
        print(f"  #{r.get('closing_rank')} | {r.get('college')} | {r.get('engineering_branch')} | {r.get('cutoff_value')} | {r.get('match_label')}")
