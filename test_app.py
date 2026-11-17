import json
import unittest
from app import create_app
from database import db
from config import Config

class TestCollegeHub(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        db.use_live_supabase = False
        self.client = self.app.test_client()

    def test_01_public_faqs(self):
        """Test public FAQ listing and filtering."""
        res = self.client.get('/api/faqs')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['status'], 'success')
        self.assertGreater(data['count'], 0)
        # Verify all returned FAQs are published
        for f in data['data']:
            self.assertEqual(f['status'], 'published')

        # Test category filter
        res_cat = self.client.get('/api/faqs?category=admissions')
        data_cat = json.loads(res_cat.data)
        self.assertEqual(data_cat['status'], 'success')
        for f in data_cat['data']:
            self.assertEqual(f['category'], 'admissions')

        # Test search query
        res_q = self.client.get('/api/faqs?q=documents')
        data_q = json.loads(res_q.data)
        self.assertEqual(data_q['status'], 'success')
        self.assertTrue(any('documents' in f['question'].lower() or 'documents' in f['keywords'].lower() for f in data_q['data']))

    def test_02_categories_endpoint(self):
        """Test categories endpoint returns all 8 categories."""
        res = self.client.get('/api/categories')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['status'], 'success')
        category_keys = [c['key'] for c in data['data']]
        for expected in Config.CATEGORIES:
            self.assertIn(expected, category_keys)
        self.assertEqual(len(category_keys), 8)

    def test_03_chat_assistant_match(self):
        """Test chatbot correctly matches approved FAQ."""
        payload = {"message": "What documents are needed for admission?"}
        res = self.client.post('/api/chat', json=payload)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['status'], 'matched')
        self.assertTrue(data['matched'])
        self.assertIn('Marksheets', data['answer'])
        self.assertEqual(data['faq']['category'], 'admissions')

    def test_04_chat_assistant_strict_fallback(self):
        """Test chatbot returns explicit mandatory fallback when question is outside approved FAQs."""
        payload = {"message": "What is the secret alien recipe for soup on Mars?"}
        res = self.client.post('/api/chat', json=payload)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['status'], 'fallback')
        self.assertFalse(data['matched'])
        self.assertIn("I couldn't find a reliable answer to that question in the approved college FAQs", data['answer'])

    def test_05_vote_endpoint(self):
        """Test upvoting an FAQ."""
        res = self.client.post('/api/faqs/ad-001/vote')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['status'], 'success')
        self.assertGreaterEqual(data['upvotes_count'], 1)

    def test_06_admin_auth_and_session(self):
        """Test admin login, failure handling, session check, /api/admin/me, and logout."""
        # Unauthenticated /api/admin/me check
        res_me_unauth = self.client.get('/api/admin/me')
        self.assertEqual(res_me_unauth.status_code, 200)
        data_me_unauth = json.loads(res_me_unauth.data)
        self.assertFalse(data_me_unauth['authenticated'])

        # Unauthenticated session check
        res = self.client.get('/api/admin/session')
        data = json.loads(res.data)
        self.assertFalse(data['authenticated'])

        # Protected route rejected without login
        res_prot = self.client.get('/api/admin/metrics')
        self.assertEqual(res_prot.status_code, 401)

        # Wrong password
        res_wrong = self.client.post('/api/admin/login', json={"username": "admin", "password": "wrongpassword"})
        self.assertEqual(res_wrong.status_code, 401)

        # Correct password (hashed verification)
        res_ok = self.client.post('/api/admin/login', json={"username": Config.ADMIN_USERNAME, "password": Config.ADMIN_PASSWORD})
        self.assertEqual(res_ok.status_code, 200)
        data_ok = json.loads(res_ok.data)
        self.assertEqual(data_ok['status'], 'success')

        # /api/admin/me should now be authenticated
        res_me = self.client.get('/api/admin/me')
        data_me = json.loads(res_me.data)
        self.assertTrue(data_me['authenticated'])
        self.assertEqual(data_me['username'], Config.ADMIN_USERNAME)

        # Session should now be authenticated
        res_sess = self.client.get('/api/admin/session')
        data_sess = json.loads(res_sess.data)
        self.assertTrue(data_sess['authenticated'])

        # Protected route now accessible
        res_metrics = self.client.get('/api/admin/metrics')
        self.assertEqual(res_metrics.status_code, 200)
        m_data = json.loads(res_metrics.data)
        self.assertEqual(m_data['status'], 'success')
        self.assertIn('total', m_data['data'])

        # Logout
        res_logout = self.client.post('/api/admin/logout')
        self.assertEqual(res_logout.status_code, 200)
        res_sess2 = self.client.get('/api/admin/me')
        data_sess2 = json.loads(res_sess2.data)
        self.assertFalse(data_sess2['authenticated'])

    def test_07_admin_faq_crud(self):
        """Test full Admin FAQ lifecycle: Create, Read, Update, Status Change, Delete with PATCH and PUT."""
        # Login first
        self.client.post('/api/admin/login', json={"username": Config.ADMIN_USERNAME, "password": Config.ADMIN_PASSWORD})

        # 0. Test validation errors on create
        res_bad1 = self.client.post('/api/admin/faqs', json={"question": "", "answer": "Valid"})
        self.assertEqual(res_bad1.status_code, 400)
        res_bad2 = self.client.post('/api/admin/faqs', json={"question": "Valid", "answer": ""})
        self.assertEqual(res_bad2.status_code, 400)
        res_bad3 = self.client.post('/api/admin/faqs', json={"question": "Valid", "answer": "Valid", "category": "nonexistent"})
        self.assertEqual(res_bad3.status_code, 400)
        res_bad4 = self.client.post('/api/admin/faqs', json={"question": "Valid", "answer": "Valid", "status": "unknown"})
        self.assertEqual(res_bad4.status_code, 400)

        # 1. Create FAQ
        new_faq = {
            "question": "Where is the Mechanical Engineering CAD/CAM laboratory located?",
            "answer": "The Advanced CAD/CAM & Robotics Laboratory is located on the 2nd Floor of the West Engineering Complex (Wing B, Room 204).",
            "category": "departments",
            "keywords": "mechanical, cad, cam, lab, robotics, engineering",
            "status": "published"
        }
        res_create = self.client.post('/api/admin/faqs', json=new_faq)
        self.assertEqual(res_create.status_code, 201)
        created_data = json.loads(res_create.data)
        created_id = created_data['data']['id']
        self.assertEqual(created_data['data']['category'], 'departments')

        # 2. Update FAQ with PATCH
        res_patch = self.client.patch(f'/api/admin/faqs/{created_id}', json={
            "question": "Where is the Mechanical Engineering CAD/CAM laboratory located? (Patched)",
            "status": "draft"
        })
        self.assertEqual(res_patch.status_code, 200)
        patch_data = json.loads(res_patch.data)
        self.assertIn('(Patched)', patch_data['data']['question'])
        self.assertEqual(patch_data['data']['status'], 'draft')

        # 3. Update FAQ with PUT
        res_update = self.client.put(f'/api/admin/faqs/{created_id}', json={
            "question": "Where is the Mechanical Engineering CAD/CAM laboratory located? (Updated)",
            "keywords": "mechanical, cad, cam, lab, robotics, 3d printing"
        })
        self.assertEqual(res_update.status_code, 200)
        updated_data = json.loads(res_update.data)
        self.assertIn('(Updated)', updated_data['data']['question'])

        # 4. Patch Status via dedicated sub-route
        res_status = self.client.patch(f'/api/admin/faqs/{created_id}/status', json={"status": "inactive"})
        self.assertEqual(res_status.status_code, 200)
        status_data = json.loads(res_status.data)
        self.assertEqual(status_data['data']['status'], 'inactive')

        # 5. Delete FAQ
        res_del = self.client.delete(f'/api/admin/faqs/{created_id}')
        self.assertEqual(res_del.status_code, 200)
        del_data = json.loads(res_del.data)
        self.assertEqual(del_data['status'], 'success')

    def test_08_html_pages_serve(self):
        """Test public and prototype HTML views return 200 and proper content."""
        pages = ['/', '/faqs', '/recommendations', '/about', '/admin-login', '/signin', '/login', '/signup', '/profile', '/saved', '/settings']
        for p in pages:
            res = self.client.get(p)
            self.assertEqual(res.status_code, 200, f"Page {p} should return 200")
            self.assertIn(b'CollegeHub', res.data)
            res.close()

    def test_09_college_recommendations_flow(self):
        """Test College Recommendations API: input validation, strict exam & score-type matching, and cutoff labeling."""
        # 1. Validation error: missing exam
        res_bad1 = self.client.post('/api/recommendations', json={"score": 95.0, "score_type": "percentile"})
        self.assertEqual(res_bad1.status_code, 400)

        # 2. Validation error: missing score type
        res_bad2 = self.client.post('/api/recommendations', json={"exam": "MHT-CET", "score": 95.0})
        self.assertEqual(res_bad2.status_code, 400)

        # 3. Validation error: invalid numeric score & out-of-range bounds
        res_bad3 = self.client.post('/api/recommendations', json={"exam": "MHT-CET", "score": "abc", "score_type": "percentile"})
        self.assertEqual(res_bad3.status_code, 400)
        res_bad_pct = self.client.post('/api/recommendations', json={"exam": "MHT-CET", "score": 105.0, "score_type": "percentile"})
        self.assertEqual(res_bad_pct.status_code, 400)
        res_bad_rank = self.client.post('/api/recommendations', json={"exam": "JEE Main", "score": 0, "score_type": "rank"})
        self.assertEqual(res_bad_rank.status_code, 400)
        # Marks scoring must be rejected (discontinued)
        res_bad_marks = self.client.post('/api/recommendations', json={"exam": "MHT-CET", "score": 150, "score_type": "marks"})
        self.assertEqual(res_bad_marks.status_code, 400)

        # 4. Valid MHT-CET profile with 98.42 percentile
        profile = {
            "exam": "MHT-CET",
            "score": 98.42,
            "score_type": "percentile",
            "category": "OBC-NCL",
            "preferred_course": "B.Tech",
            "preferred_branches": ["CSE", "AIDS", "QUANT"]
        }
        res_rec = self.client.post('/api/recommendations', json=profile)
        self.assertEqual(res_rec.status_code, 200)
        data = json.loads(res_rec.data)
        self.assertEqual(data['status'], 'success')
        self.assertGreater(data['count'], 0)

        # Verify recommendation structure & labels
        labels = [item['match_label'] for item in data['recommendations']]
        self.assertIn("Historical match", labels)
        self.assertIn("More competitive", labels)
        self.assertIn("Insufficient cutoff data", labels)

        # Verify historical match logic: score >= closing cutoff
        hist_items = [item for item in data['recommendations'] if item['match_label'] == "Historical match"]
        for item in hist_items:
            self.assertGreaterEqual(profile['score'], item['record']['closing_value'])
            self.assertIn("Historical Match", item['explanation'])
            self.assertIsNotNone(item.get('match_percentage'))
            self.assertGreater(item['match_percentage'], 0.0)
            self.assertIsNotNone(item.get('admission_probability'))
            self.assertGreaterEqual(item['admission_probability'], 70.0)
            self.assertIsNotNone(item.get('probability_tier'))
            self.assertIn('round_cutoffs', item['record'])
            rc = item['record']['round_cutoffs']
            self.assertTrue(1 in rc or '1' in rc)
            self.assertTrue(2 in rc or '2' in rc)
            self.assertTrue(3 in rc or '3' in rc)
            self.assertTrue(4 in rc or '4' in rc)

        # Verify matching percentage sorting: matching items must appear first
        first_competitive_idx = None
        last_historical_idx = None
        for idx, item in enumerate(data['recommendations']):
            if item['match_type'] == 'historical_match':
                last_historical_idx = idx
            elif item['match_type'] == 'more_competitive' and first_competitive_idx is None:
                first_competitive_idx = idx
        if first_competitive_idx is not None and last_historical_idx is not None:
            self.assertLess(last_historical_idx, first_competitive_idx, "Historical matches must be shown first")

        # Verify insufficient data handling
        insuf_items = [item for item in data['recommendations'] if item['match_label'] == "Insufficient cutoff data"]
        for item in insuf_items:
            self.assertIsNone(item['record']['closing_value'])
            self.assertIn("not yet available", item['explanation'].lower())

        # Verify University Wise sorting
        univ_profile = {
            "exam": "MHT-CET",
            "score": 98.5,
            "score_type": "percentile",
            "category": "OPEN",
            "preferred_course": "B.Tech",
            "preferred_branches": ["CSE", "AIDS"],
            "sort_by": "university"
        }
        res_univ = self.client.post('/api/recommendations', json=univ_profile)
        self.assertEqual(res_univ.status_code, 200)
        univ_data = json.loads(res_univ.data)
        self.assertGreater(len(univ_data['recommendations']), 0)
        univ_names = [item['record'].get('university', '').strip().lower() for item in univ_data['recommendations']]
        self.assertEqual(univ_names, sorted(univ_names))

        # 5. Test JEE Main Rank Flow (Strict exam and score-type segregation)
        jee_profile = {
            "exam": "JEE Main",
            "score": 4500,
            "score_type": "rank",
            "category": "OPEN",
            "preferred_course": "B.Tech",
            "preferred_branches": ["CSE"]
        }
        res_jee = self.client.post('/api/recommendations', json=jee_profile)
        self.assertEqual(res_jee.status_code, 200)
        jee_data = json.loads(res_jee.data)
        self.assertGreater(jee_data['count'], 0)
        for item in jee_data['recommendations']:
            self.assertEqual(item['record']['exam'], 'JEE Main')
            self.assertEqual(item['record']['score_type'], 'rank')

        # Check rank comparisons: student rank 4500 vs VNIT (7850) -> match, NITK (3406) -> more competitive
        vnit_item = next(i for i in jee_data['recommendations'] if 'Visvesvaraya' in i['record']['college_name'] or i['record'].get('college_code') == 'VNIT')
        self.assertEqual(vnit_item['match_label'], 'Historical match')
        self.assertLessEqual(jee_profile['score'], vnit_item['record']['closing_rank'])

        nitk_item = next(i for i in jee_data['recommendations'] if 'Surathkal' in i['record']['college_name'] or i['record'].get('college_code') == 'NITK')
        self.assertEqual(nitk_item['match_label'], 'More competitive')
        self.assertGreater(jee_profile['score'], nitk_item['record']['closing_rank'])

        # 6. Test MHT-CET Rank Flow (Comparing State Merit Rank against college closing rank)
        cet_rank_profile = {
            "exam": "MHT-CET",
            "score": 200,
            "score_type": "rank",
            "category": "OPEN",
            "preferred_course": "B.Tech",
            "preferred_branches": ["CSE"]
        }
        res_cet_rank = self.client.post('/api/recommendations', json=cet_rank_profile)
        self.assertEqual(res_cet_rank.status_code, 200)
        cet_rank_data = json.loads(res_cet_rank.data)
        self.assertGreater(cet_rank_data['count'], 0)
        coep_rank_item = next(i for i in cet_rank_data['recommendations'] if 'COEP' in i['record']['college_name'])
        self.assertEqual(coep_rank_item['match_label'], 'Historical match')
        self.assertLessEqual(cet_rank_profile['score'], coep_rank_item['record']['closing_rank'])

    def test_10_csv_import_validation_and_preview(self):
        """Test CSV import preview: required fields, score limits, duplicate detection, and missing metadata."""
        # 1. Unauthenticated request rejected
        res_unauth = self.client.post('/api/admin/import/preview', json={"csv_text": "dummy"})
        self.assertEqual(res_unauth.status_code, 401)

        # Authenticate admin
        self.client.post('/api/admin/login', json={
            "username": Config.ADMIN_USERNAME,
            "password": Config.ADMIN_PASSWORD
        })

        # 2. Missing metadata checks
        res_no_url = self.client.post('/api/admin/import/preview', json={
            "csv_text": "college_code,college_name\n6006,COEP",
            "source_url": "",
            "academic_year": "2024-2025",
            "date_checked": "2024-08-26"
        })
        self.assertEqual(res_no_url.status_code, 400)

        # 3. Missing required CSV headers
        res_bad_headers = self.client.post('/api/admin/import/preview', json={
            "csv_text": "college_code,college_name\n6006,COEP",
            "source_url": "https://fe2024.mahacet.org",
            "academic_year": "2024-2025",
            "date_checked": "2024-08-26"
        })
        self.assertEqual(res_bad_headers.status_code, 400)
        bad_headers_data = json.loads(res_bad_headers.data)
        self.assertIn("Missing required CSV header columns", bad_headers_data['message'])

        # 4. Valid CSV with duplicate detection and range validation
        csv_payload = """college_code,college_name,campus_type,district,city,state,program,branch_code,branch_name,exam,score_type,category,quota,round,cutoff_value,annual_fees_inr,hostel_available,remarks
8888,Walchand Institute of Tech,Autonomous,Solapur,Solapur,Maharashtra,B.Tech,CSE,Computer Science & Engineering,MHT-CET,percentile,OPEN,SL,CAP Round II,96.8500,105000,true,Valid Row 1
8888,Walchand Institute of Tech,Autonomous,Solapur,Solapur,Maharashtra,B.Tech,CSE,Computer Science & Engineering,MHT-CET,percentile,OPEN,SL,CAP Round II,96.8500,105000,true,Duplicate Row in File
8888,Different College Name For Code 8888,Autonomous,Solapur,Solapur,Maharashtra,B.Tech,IT,Information Technology,MHT-CET,percentile,OPEN,SL,CAP Round II,95.1000,105000,true,Code Conflict
8889,Government College of Tech,Government,Amravati,Amravati,Maharashtra,B.Tech,CSE,Computer Science & Engineering,MHT-CET,percentile,OPEN,SL,CAP Round II,105.5000,32000,true,Percentile > 100 Error
6006,COEP Technological University,State University,Pune,Pune,Maharashtra,B.Tech,CSE,Computer Science & Engineering,MHT-CET,percentile,OPEN,SL,CAP Round II,99.8512,92000,true,Duplicate in Database
8890,New Emerging College,Private,Nagpur,Nagpur,Maharashtra,B.Tech,AI,Artificial Intelligence,MHT-CET,percentile,OPEN,SL,CAP Round II,,,true,Missing Fees and Missing Cutoff (Preserved as Null)
"""
        res_preview = self.client.post('/api/admin/import/preview', json={
            "csv_text": csv_payload,
            "source_url": "https://fe2024.mahacet.org/StaticPages/HomePage",
            "academic_year": "2024-2025",
            "date_checked": "2024-08-26"
        })
        self.assertEqual(res_preview.status_code, 200)
        preview_data = json.loads(res_preview.data)
        summary = preview_data['summary']
        self.assertEqual(summary['total_rows'], 6)
        self.assertGreater(summary['valid_rows'], 0)
        self.assertGreater(summary['error_rows'], 0)
        self.assertGreater(summary['duplicate_rows'], 0)

        # Confirm Row 1 is valid
        self.assertEqual(preview_data['rows'][0]['status'], 'valid')

        # Confirm Row 2 is flagged as duplicate in file
        self.assertEqual(preview_data['rows'][1]['status'], 'duplicate')
        self.assertIn("Duplicate cutoff record in file", preview_data['rows'][1]['warnings'][0])

        # Confirm Row 3 has college code conflict error
        self.assertEqual(preview_data['rows'][2]['status'], 'error')
        self.assertIn("College code conflict", preview_data['rows'][2]['errors'][0])

        # Confirm Row 4 has percentile > 100 error
        self.assertEqual(preview_data['rows'][3]['status'], 'error')
        self.assertIn("must be between 0.0 and 100.0", preview_data['rows'][3]['errors'][0])

        # Confirm Row 5 is flagged as duplicate of database record
        self.assertEqual(preview_data['rows'][4]['status'], 'duplicate')
        self.assertIn("Duplicate cutoff in database", preview_data['rows'][4]['warnings'][0])

        # Confirm Row 6 preserves missing fees and missing cutoff as None (not invented)
        row6 = preview_data['rows'][5]
        self.assertEqual(row6['status'], 'valid')
        self.assertIsNone(row6['data']['cutoff_value'])
        self.assertIsNone(row6['data']['annual_fees_inr'])

    def test_11_csv_import_commit_and_approval_workflow(self):
        """Test import staging: records saved as 'pending_approval', isolated from students until admin approves."""
        # Authenticate admin
        self.client.post('/api/admin/login', json={
            "username": Config.ADMIN_USERNAME,
            "password": Config.ADMIN_PASSWORD
        })

        # 1. Commit valid record
        new_row = {
            "college_code": "7777",
            "college_name": "Symbiosis Institute of Technology",
            "campus_type": "Deemed University",
            "city": "Pune",
            "district": "Pune",
            "state": "Maharashtra",
            "program": "B.Tech",
            "branch_code": "ROBO",
            "branch_name": "Robotics & Automation",
            "exam": "MHT-CET",
            "score_type": "percentile",
            "category": "OPEN",
            "quota": "SL",
            "round": "CAP Round II",
            "cutoff_value": 94.5000,
            "annual_fees_inr": 280000,
            "hostel_available": True,
            "remarks": "Lavale campus"
        }

        res_commit = self.client.post('/api/admin/import/commit', json={
            "valid_rows": [new_row],
            "source_url": "https://fe2024.mahacet.org/StaticPages/HomePage",
            "academic_year": "2024-2025",
            "date_checked": "2024-08-26",
            "batch_name": "Test Robotics Allotment Batch"
        })
        self.assertEqual(res_commit.status_code, 201)
        commit_data = json.loads(res_commit.data)['data']
        batch_id = commit_data['batch_id']
        self.assertEqual(commit_data['status'], 'pending_approval')
        self.assertEqual(commit_data['count'], 1)

        # 2. CRITICAL: Confirm unapproved record is NOT published to public student recommendations
        res_rec_unapproved = self.client.post('/api/recommendations', json={
            "exam": "MHT-CET",
            "score": 95.0,
            "score_type": "percentile",
            "category": "OPEN",
            "preferred_course": "B.Tech",
            "preferred_branches": ["ROBO"]
        })
        rec_data_unapproved = json.loads(res_rec_unapproved.data)
        # Should be 0 since the record is pending approval
        self.assertEqual(rec_data_unapproved['count'], 0)

        # 3. Check batch appears in admin approval queue
        res_batches = self.client.get('/api/admin/import/batches')
        self.assertEqual(res_batches.status_code, 200)
        batches_list = json.loads(res_batches.data)['data']
        target_batch = next((b for b in batches_list if b['id'] == batch_id), None)
        self.assertIsNotNone(target_batch)
        self.assertEqual(target_batch['status'], 'pending_approval')

        # 4. Check batch details
        res_batch_det = self.client.get(f'/api/admin/import/batches/{batch_id}')
        self.assertEqual(res_batch_det.status_code, 200)
        batch_details = json.loads(res_batch_det.data)['data']
        self.assertEqual(len(batch_details['records']), 1)
        self.assertEqual(batch_details['records'][0]['status'], 'pending_approval')
        self.assertFalse(batch_details['records'][0]['is_active'])

        # 5. Approve batch
        res_approve = self.client.post(f'/api/admin/import/batches/{batch_id}/approve')
        self.assertEqual(res_approve.status_code, 200)
        approve_data = json.loads(res_approve.data)['data']
        self.assertEqual(approve_data['status'], 'approved')
        self.assertEqual(approve_data['approved_count'], 1)

        # 6. CRITICAL: Now that batch is approved, verify it DOES appear in student recommendations!
        res_rec_approved = self.client.post('/api/recommendations', json={
            "exam": "MHT-CET",
            "score": 95.0,
            "score_type": "percentile",
            "category": "OPEN",
            "preferred_course": "B.Tech",
            "preferred_branches": ["ROBO"]
        })
        rec_data_approved = json.loads(res_rec_approved.data)
        self.assertEqual(rec_data_approved['count'], 1)
        self.assertEqual(rec_data_approved['recommendations'][0]['match_label'], 'Historical match')
        self.assertEqual(rec_data_approved['recommendations'][0]['record']['branch_code'], 'ROBO')

    def test_12_template_and_sample_downloads(self):
        """Test download routes for blank CSV template and authentic Maharashtra sample CSV."""
        # 1. Blank Template Download
        with self.client.get('/api/admin/import/template') as res_tpl:
            self.assertEqual(res_tpl.status_code, 200)
            self.assertIn('text/csv', res_tpl.content_type)
            self.assertIn(b'college_code', res_tpl.data)
            self.assertIn(b'cutoff_value', res_tpl.data)
            self.assertIn(b'annual_fees_inr', res_tpl.data)
            self.assertIn(b'hostel_available', res_tpl.data)

        # 2. Sample Maharashtra CSV Download
        with self.client.get('/api/admin/import/sample') as res_smp:
            self.assertEqual(res_smp.status_code, 200)
            self.assertIn('text/csv', res_smp.content_type)
            self.assertIn(b'COEP Technological University', res_smp.data)
            self.assertIn(b'6006', res_smp.data)
            self.assertIn(b'Veermata Jijabai Technological Institute', res_smp.data)

    def test_13_relational_hierarchy_and_joins(self):
        """
        Test the normalized relational hierarchy:
        College -> Courses -> Cutoffs / Fees
        College details, contacts, placements, facilities, and sources link back to the college.
        """
        # 1. Fetch COEP Technological University by code
        coep = db.get_institute_by_code('6006', published_only=True)
        self.assertIsNotNone(coep)
        self.assertEqual(coep['institute_name'], 'COEP Technological University')
        self.assertEqual(coep['district'], 'Pune')

        # 2. Verify complete relational profile
        details = db.get_institute_details(coep['id'], published_only=True)
        self.assertIsNotNone(details)
        self.assertIn('institute', details)
        self.assertIn('contacts', details)
        self.assertIn('courses', details)
        self.assertIn('placement_stats', details)
        self.assertIn('amenities', details)
        self.assertIn('source_document', details)

        # Verify contacts link back to college
        contacts = details['contacts']
        self.assertGreater(len(contacts), 0)
        phone_contact = next((c for c in contacts if c['contact_type'] == 'admissions_phone'), None)
        self.assertIsNotNone(phone_contact)
        self.assertEqual(phone_contact['contact_value'], '+91-20-25507000')

        # Verify courses link back to college and contain cutoffs & fees
        courses = details['courses']
        self.assertGreater(len(courses), 0)
        cse_course = next((c for c in courses if c['branch'] == 'CSE'), None)
        self.assertIsNotNone(cse_course)
        self.assertEqual(cse_course['admission_route'], 'BTECH_FIRST_YEAR')
        self.assertEqual(cse_course['choice_code'], '600624510')

        # Verify cutoffs linked to CSE course
        course_cutoffs = cse_course.get('cutoffs', [])
        self.assertGreater(len(course_cutoffs), 0)
        open_cutoff = next((cut for cut in course_cutoffs if cut['category'] == 'OPEN'), None)
        self.assertIsNotNone(open_cutoff)
        self.assertEqual(open_cutoff['seat_pool'], 'MH')
        self.assertEqual(open_cutoff['cutoff_value'], 99.8512)

        # Verify fees linked to CSE course
        course_fees = cse_course.get('fees', [])
        self.assertGreater(len(course_fees), 0)
        open_fee = next((f for f in course_fees if f['category'] == 'OPEN'), None)
        self.assertIsNotNone(open_fee)
        self.assertEqual(open_fee['amount'], 92000)

        # Verify placements link back to college
        placements = details['placement_stats']
        self.assertGreater(len(placements), 0)
        highest_stat = next((p for p in placements if p['metric_type'] == 'highest'), None)
        self.assertIsNotNone(highest_stat)
        self.assertEqual(highest_stat['amount'], 5050000)

        # Verify amenities link back to college
        amenities = details['amenities']
        self.assertGreater(len(amenities), 0)
        wifi_amenity = next((a for a in amenities if 'Wi-Fi' in a['name']), None)
        self.assertIsNotNone(wifi_amenity)

        # Verify source provenance
        source_doc = details['source_document']
        self.assertIsNotNone(source_doc)
        self.assertTrue(source_doc['verified'])
        self.assertIn('fe2024.mahacet.org', source_doc['source_url'])

    def test_14_relational_institutes_and_courses_api(self):
        """Test public REST API endpoints serving normalized relational data."""
        # 1. GET /api/institutes
        res = self.client.get('/api/institutes')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['status'], 'success')
        self.assertGreaterEqual(data['count'], 6)
        codes = [i['institute_code'] for i in data['data']]
        self.assertIn('6006', codes)  # COEP
        self.assertIn('3012', codes)  # VJTI
        self.assertIn('6271', codes)  # PICT

        # Test filter by district
        res_pune = self.client.get('/api/institutes?district=Pune')
        self.assertEqual(res_pune.status_code, 200)
        pune_data = json.loads(res_pune.data)
        for i in pune_data['data']:
            self.assertEqual(i['district'], 'Pune')

        # Test search query
        res_search = self.client.get('/api/institutes?q=Walchand')
        self.assertEqual(res_search.status_code, 200)
        search_data = json.loads(res_search.data)
        self.assertGreater(search_data['count'], 0)
        self.assertIn('6007', [i['institute_code'] for i in search_data['data']])

        # 2. GET /api/institutes/<id>
        coep_id = '10000000-0000-0000-0000-000000006006'
        res_detail = self.client.get(f'/api/institutes/{coep_id}')
        self.assertEqual(res_detail.status_code, 200)
        detail_data = json.loads(res_detail.data)['data']
        self.assertEqual(detail_data['institute']['institute_code'], '6006')
        self.assertGreater(len(detail_data['courses']), 0)
        self.assertGreater(len(detail_data['contacts']), 0)
        self.assertGreater(len(detail_data['placement_stats']), 0)

        # 3. GET /api/courses
        res_courses = self.client.get('/api/courses')
        self.assertEqual(res_courses.status_code, 200)
        courses_data = json.loads(res_courses.data)
        self.assertGreaterEqual(courses_data['count'], 7)

        # Test filter courses by admission_route
        res_route = self.client.get('/api/courses?route=BTECH_FIRST_YEAR')
        self.assertEqual(res_route.status_code, 200)
        route_data = json.loads(res_route.data)
        for c in route_data['data']:
            self.assertEqual(c['admission_route'], 'BTECH_FIRST_YEAR')

        # 4. GET /api/amenities
        res_amenities = self.client.get('/api/amenities')
        self.assertEqual(res_amenities.status_code, 200)
        amenities_data = json.loads(res_amenities.data)
        self.assertGreaterEqual(amenities_data['count'], 5)
        amenity_names = [a['name'] for a in amenities_data['data']]
        self.assertTrue(any('Wi-Fi' in n for n in amenity_names))
        self.assertTrue(any('Library' in n for n in amenity_names))

        # 5. GET /api/sources
        res_sources = self.client.get('/api/sources')
        self.assertEqual(res_sources.status_code, 200)
        sources_data = json.loads(res_sources.data)
        self.assertGreaterEqual(sources_data['count'], 2)
        for s in sources_data['data']:
            self.assertTrue(s['verified'])

        # 6. GET /api/branches - all saved academic branches
        res_branches = self.client.get('/api/branches')
        self.assertEqual(res_branches.status_code, 200)
        branches_data = json.loads(res_branches.data)
        self.assertEqual(branches_data['status'], 'success')
        self.assertGreaterEqual(branches_data['count'], 20)
        branch_codes = [b['code'] for b in branches_data['data']]
        self.assertIn('CSE', branch_codes)
        self.assertIn('AIDS', branch_codes)
        self.assertIn('IT', branch_codes)
        self.assertIn('ENTC', branch_codes)
        self.assertIn('ELECT', branch_codes)
        self.assertIn('MECH', branch_codes)
        self.assertIn('CIVIL', branch_codes)
        self.assertIn('CHEM', branch_codes)
        self.assertIn('ROBO', branch_codes)

        # Test filter by program
        res_btech = self.client.get('/api/branches?program=B.Tech')
        self.assertEqual(res_btech.status_code, 200)
        btech_data = json.loads(res_btech.data)
        self.assertGreaterEqual(btech_data['count'], 20)
        for b in btech_data['data']:
            self.assertEqual(b['program'], 'B.Tech')


    def test_15_seat_pool_vs_admission_route_distinction(self):
        """
        Crucial requirement test:
        Keep MH, AI, and Diploma in the seat_pool source-label field, and keep
        admission_route (BTECH_FIRST_YEAR, BTECH_DSY, DIPLOMA_AFTER_SSC) separately
        so Diploma quota in a cutoff file is never conflated with the DSY route.
        """
        # Query courses: verify route values
        courses = db.get_courses(published_only=True)
        routes = {c['admission_route'] for c in courses}
        # Routes must represent academic entry stage
        for r in routes:
            self.assertIn(r, ['BTECH_FIRST_YEAR', 'BTECH_DSY', 'DIPLOMA_AFTER_SSC'])

        # Query cutoffs: verify seat_pool values
        cutoffs = db.get_cutoffs(published_only=True)
        seat_pools = {c['seat_pool'] for c in cutoffs}
        # Seat pools must preserve official counseling quota categories (MH, AI, Diploma)
        self.assertTrue('MH' in seat_pools or 'AI' in seat_pools)

        # Verify that seat_pool 'MH' or 'AI' exists under a course whose route is 'BTECH_FIRST_YEAR'
        coep_cse = next((c for c in courses if c['choice_code'] == '600624510'), None)
        self.assertIsNotNone(coep_cse)
        self.assertEqual(coep_cse['admission_route'], 'BTECH_FIRST_YEAR')

        coep_cutoffs = db.get_cutoffs(course_id=coep_cse['id'], published_only=True)
        self.assertGreater(len(coep_cutoffs), 0)
        for cut in coep_cutoffs:
            # Cutoffs preserve seat_pool quota label while course retains route
            self.assertIn(cut['seat_pool'], ['MH', 'AI', 'Diploma', 'Home_Univ', 'SL'])
            self.assertNotEqual(cut['seat_pool'], coep_cse['admission_route'])

    def test_16_stateless_in_memory_student_recommendations(self):
        """
        Crucial requirement test:
        The recommendation form does not need a student table at first.
        Process the student's marks, preferences, and optional category for the
        recommendation without saving them.
        """
        # Execute recommendation calculation with candidate marks and category
        payload = {
            "exam": "MHT-CET",
            "score": 99.86,
            "score_type": "percentile",
            "category": "OPEN",
            "preferred_course": "B.Tech",
            "preferred_branches": ["CSE"]
        }
        res = self.client.post('/api/recommendations', json=payload)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['status'], 'success')
        self.assertGreater(data['count'], 0)

        # Assert no student record was created in database
        # Verify that no student-persisting table exists or was populated
        self.assertFalse(hasattr(db, '_local_students'))
        self.assertFalse(hasattr(db, 'students'))

    def test_17_publication_and_verification_gating(self):
        """
        Row Level Security & Publication Gating:
        Public visitors should have read access only to published, active records.
        Records remain unpublished (is_published = false, verified = false) until approved.
        """
        # 1. Unapproved or unpublished institute ID should return 404
        res_nonexistent = self.client.get('/api/institutes/non-existent-id')
        self.assertEqual(res_nonexistent.status_code, 404)

        # 2. Add an unpublished draft institute and verify it is hidden from public /api/institutes
        draft_inst_id = "inst-draft-hidden-01"
        draft_inst = {
            "id": draft_inst_id,
            "institute_code": "0001",
            "institute_name": "Unpublished Secret Campus",
            "district": "Pune",
            "is_published": False
        }
        db._local_institutes.append(draft_inst)

        # Public list must NOT contain the unpublished draft institute
        res_public = self.client.get('/api/institutes')
        public_codes = [i['institute_code'] for i in json.loads(res_public.data)['data']]
        self.assertNotIn("0001", public_codes)

        # Direct GET must return 404 for unpublished institute
        res_direct = self.client.get(f'/api/institutes/{draft_inst_id}')
        self.assertEqual(res_direct.status_code, 404)

        # 3. Clean up draft item
        db._local_institutes = [i for i in db._local_institutes if i.get("id") != draft_inst_id]

    def test_18_login_page_and_user_info_flow(self):
        """
        Test Login page and info capture flow:
        - Route accessibility for /login and /login.html
        - Extraction and processing of user info from login payload
        - Role-aware authentication for Student, Parent, and Admin
        - Session persistence and retrieval via /api/auth/me
        - Session termination via /api/auth/logout
        """
        # 1. Login page route accessibility
        res_login_html = self.client.get('/login')
        self.assertEqual(res_login_html.status_code, 200)
        self.assertIn(b'Log in to CollegeHub', res_login_html.data)
        res_login_html.close()

        # 2. Validation: missing fields
        res_no_ident = self.client.post('/api/auth/login', json={"password": "secret"})
        self.assertEqual(res_no_ident.status_code, 400)
        self.assertIn("required", json.loads(res_no_ident.data)['message'].lower())

        res_no_pass = self.client.post('/api/auth/login', json={"identifier": "test@example.com"})
        self.assertEqual(res_no_pass.status_code, 400)
        self.assertIn("password is required", json.loads(res_no_pass.data)['message'].lower())

        # 3. Student Login: Taking info from login page (Full Name, Email, Role)
        login_payload = {
            "identifier": "rahul.sharma@example.com",
            "password": "Password123!",
            "role": "student",
            "full_name": "Rahul Sharma",
            "remember_me": True
        }
        res_student = self.client.post('/api/auth/login', json=login_payload)
        self.assertEqual(res_student.status_code, 200)
        data_student = json.loads(res_student.data)
        self.assertEqual(data_student['status'], 'success')
        self.assertEqual(data_student['user']['name'], 'Rahul Sharma')
        self.assertEqual(data_student['user']['email'], 'rahul.sharma@example.com')
        self.assertEqual(data_student['user']['role'], 'student')
        self.assertEqual(data_student['user']['initials'], 'RS')
        self.assertTrue(data_student['user']['applicant_id'].startswith('#CH-2025-'))
        self.assertEqual(data_student['redirect_url'], '/profile')

        # Verify session persistence via /api/auth/me
        res_me = self.client.get('/api/auth/me')
        self.assertEqual(res_me.status_code, 200)
        data_me = json.loads(res_me.data)
        self.assertTrue(data_me['logged_in'])
        self.assertEqual(data_me['user']['name'], 'Rahul Sharma')

        # 4. Name derivation when full_name is omitted
        login_no_name = {
            "identifier": "priya.patil@test.com",
            "password": "Password123!",
            "role": "student"
        }
        res_derived = self.client.post('/api/auth/login', json=login_no_name)
        self.assertEqual(res_derived.status_code, 200)
        data_derived = json.loads(res_derived.data)
        self.assertEqual(data_derived['user']['name'], 'Priya Patil')
        self.assertEqual(data_derived['user']['initials'], 'PP')

        # 5. Parent Role Login
        login_parent = {
            "identifier": "sunil.patil.parent@gmail.com",
            "password": "Password123!",
            "role": "parent",
            "full_name": "Sunil Patil"
        }
        res_parent = self.client.post('/api/auth/login', json=login_parent)
        self.assertEqual(res_parent.status_code, 200)
        data_parent = json.loads(res_parent.data)
        self.assertEqual(data_parent['user']['role'], 'parent')
        self.assertEqual(data_parent['user']['role_label'], 'Parent / Guardian')

        # 6. Admin Authentication via Login flow
        login_admin = {
            "identifier": "admin",
            "password": Config.ADMIN_PASSWORD,
            "role": "advisor"
        }
        res_admin = self.client.post('/api/auth/login', json=login_admin)
        self.assertEqual(res_admin.status_code, 200)
        data_admin = json.loads(res_admin.data)
        self.assertEqual(data_admin['user']['role'], 'admin')
        self.assertEqual(data_admin['redirect_url'], '/admin')

        # Invalid Admin Credentials
        login_bad_admin = {
            "identifier": "admin",
            "password": "WrongPassword!",
            "role": "advisor"
        }
        res_bad_admin = self.client.post('/api/auth/login', json=login_bad_admin)
        self.assertEqual(res_bad_admin.status_code, 401)

        # 7. Logout Flow
        res_logout = self.client.post('/api/auth/logout')
        self.assertEqual(res_logout.status_code, 200)

        # Verify session cleared
        res_after_logout = self.client.get('/api/auth/me')
        self.assertEqual(res_after_logout.status_code, 200)
        self.assertFalse(json.loads(res_after_logout.data)['logged_in'])

        # 8. User Registration Flow (/api/auth/register)
        reg_payload = {
            "full_name": "Aarav Deshmukh",
            "email": "aarav.deshmukh@example.com",
            "password": "SecurePassword2025!",
            "role": "student",
            "program": "Computer Science & Engineering"
        }
        res_reg = self.client.post('/api/auth/register', json=reg_payload)
        self.assertEqual(res_reg.status_code, 201)
        data_reg = json.loads(res_reg.data)
        self.assertEqual(data_reg['status'], 'success')
        self.assertEqual(data_reg['user']['name'], 'Aarav Deshmukh')
        self.assertEqual(data_reg['user']['initials'], 'AD')
        self.assertTrue(data_reg['user']['applicant_id'].startswith('#CH-2025-'))

        # Verify active session immediately after registration
        res_reg_me = self.client.get('/api/auth/me')
        self.assertEqual(res_reg_me.status_code, 200)
        self.assertTrue(json.loads(res_reg_me.data)['logged_in'])
        self.assertEqual(json.loads(res_reg_me.data)['user']['email'], 'aarav.deshmukh@example.com')

    def test_19_google_login_and_password_reset_verification(self):
        """Test Google authentication flow and 6-digit verification code password reset."""
        # 1. Google Login Validation
        res_bad_google = self.client.post('/api/auth/google', json={})
        self.assertEqual(res_bad_google.status_code, 400)

        # Successful Google Login
        google_payload = {
            "email": "priya.sharma@gmail.com",
            "name": "Priya Sharma",
            "picture": "https://lh3.googleusercontent.com/sample.jpg",
            "google_id": "google-sub-12345",
            "role": "student"
        }
        res_google = self.client.post('/api/auth/google', json=google_payload)
        self.assertEqual(res_google.status_code, 200)
        data_google = json.loads(res_google.data)
        self.assertEqual(data_google['status'], 'success')
        self.assertEqual(data_google['user']['email'], 'priya.sharma@gmail.com')
        self.assertEqual(data_google['user']['name'], 'Priya Sharma')
        self.assertEqual(data_google['user']['provider'], 'google')

        # Check session is active
        res_me = self.client.get('/api/auth/me')
        self.assertEqual(res_me.status_code, 200)
        self.assertEqual(json.loads(res_me.data)['user']['name'], 'Priya Sharma')

        # Logout
        self.client.post('/api/auth/logout')

        # 2. Send Verification Code for Password Reset
        res_bad_email = self.client.post('/api/auth/send-reset-code', json={"email": "invalid"})
        self.assertEqual(res_bad_email.status_code, 400)

        target_email = "student.test@example.com"
        res_code = self.client.post('/api/auth/send-reset-code', json={"email": target_email})
        self.assertEqual(res_code.status_code, 200)
        data_code = json.loads(res_code.data)
        self.assertEqual(data_code['status'], 'success')
        self.assertIn('verification_code', data_code)
        code = data_code['verification_code']
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())

        # 3. Verify Code Validation
        res_wrong_code = self.client.post('/api/auth/verify-reset-code', json={
            "email": target_email,
            "code": "000000" if code != "000000" else "111111"
        })
        self.assertEqual(res_wrong_code.status_code, 400)

        res_verify = self.client.post('/api/auth/verify-reset-code', json={
            "email": target_email,
            "code": code
        })
        self.assertEqual(res_verify.status_code, 200)
        self.assertEqual(json.loads(res_verify.data)['status'], 'success')

        # 4. Reset Password
        res_short_pass = self.client.post('/api/auth/reset-password', json={
            "email": target_email,
            "code": code,
            "new_password": "123"
        })
        self.assertEqual(res_short_pass.status_code, 400)

        new_pass = "BrandNewSecret2025!"
        res_reset = self.client.post('/api/auth/reset-password', json={
            "email": target_email,
            "code": code,
            "new_password": new_pass
        })
        self.assertEqual(res_reset.status_code, 200)
        self.assertEqual(json.loads(res_reset.data)['status'], 'success')

        # 5. Verify Login with New Password
        res_login_old = self.client.post('/api/auth/login', json={
            "identifier": target_email,
            "password": "WrongPassword123"
        })
        self.assertEqual(res_login_old.status_code, 401)

        res_login_new = self.client.post('/api/auth/login', json={
            "identifier": target_email,
            "password": new_pass
        })
        self.assertEqual(res_login_new.status_code, 200)
        self.assertEqual(json.loads(res_login_new.data)['status'], 'success')

    def test_20_google_redirect_and_email_otp_security(self):
        """Test Google OAuth redirect to accounts.google.com and OTP security."""
        # 1. Google OAuth login endpoint redirects browser directly
        res_redirect = self.client.get('/api/auth/google/login')
        self.assertEqual(res_redirect.status_code, 302)
        location = res_redirect.headers.get('Location', '')
        self.assertTrue('google.com' in location or 'supabase.co' in location)

        # 2. Short URL alias /auth/google also redirects
        res_short = self.client.get('/auth/google')
        self.assertEqual(res_short.status_code, 302)

        # 3. Google OAuth callback error handling
        res_err = self.client.get('/api/auth/google/callback?error=access_denied')
        self.assertEqual(res_err.status_code, 302)
        self.assertIn('/login?error=access_denied', res_err.headers.get('Location', ''))

        # 4. OTP Non-Leakage in Production Mode: verification_code must NOT be returned in JSON
        self.app.config['TESTING'] = False
        res_prod = self.client.post('/api/auth/send-reset-code', json={"email": "student.prod@example.com"})
        self.assertEqual(res_prod.status_code, 200)
        data_prod = json.loads(res_prod.data)
        self.assertEqual(data_prod['status'], 'success')
        self.assertNotIn('verification_code', data_prod)
        self.app.config['TESTING'] = True


if __name__ == '__main__':
    unittest.main()
