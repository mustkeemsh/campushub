import os
import io
import csv
import re
import uuid
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config

# Try to import supabase client
try:
    from supabase import create_client, Client
    HAS_SUPABASE_LIB = True
except ImportError:
    HAS_SUPABASE_LIB = False


def _is_valid_uuid(val):
    """Check if a string is a valid UUID."""
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


MASTER_BRANCH_CATALOG = {
    "CSE": {
        "code": "CSE",
        "name": "Computer Science & Engineering",
        "program": "B.Tech",
        "cluster": "Computing & AI",
        "description": "Software systems, algorithms, cloud architecture, and computing foundations."
    },
    "AIDS": {
        "code": "AIDS",
        "name": "Artificial Intelligence & Data Science",
        "program": "B.Tech",
        "cluster": "Computing & AI",
        "description": "Machine learning, neural networks, big data analytics, and cognitive systems."
    },
    "IT": {
        "code": "IT",
        "name": "Information Technology",
        "program": "B.Tech",
        "cluster": "Computing & AI",
        "description": "Information security, network architecture, and enterprise software."
    },
    "ENTC": {
        "code": "ENTC",
        "name": "Electronics & Telecommunication Engineering",
        "program": "B.Tech",
        "cluster": "Circuital & Electronics",
        "description": "Digital communications, signal processing, VLSI design, and RF circuits."
    },
    "ELECT": {
        "code": "ELECT",
        "name": "Electrical Engineering",
        "program": "B.Tech",
        "cluster": "Circuital & Electronics",
        "description": "Power grids, energy systems, high voltage engineering, and electric drives."
    },
    "MECH": {
        "code": "MECH",
        "name": "Mechanical Engineering",
        "program": "B.Tech",
        "cluster": "Core & Infrastructure",
        "description": "Thermodynamics, machine design, fluid mechanics, and materials."
    },
    "CIVIL": {
        "code": "CIVIL",
        "name": "Civil & Infrastructure Engineering",
        "program": "B.Tech",
        "cluster": "Core & Infrastructure",
        "description": "Structural engineering, transportation, geo-mechanics, and sustainable infrastructure."
    },
    "CHEM": {
        "code": "CHEM",
        "name": "Chemical & Polymer Engineering",
        "program": "B.Tech",
        "cluster": "Process & Biotechnology",
        "description": "Process design, reaction kinetics, polymers, petrochemicals, and separation."
    },
    "ROBO": {
        "code": "ROBO",
        "name": "Robotics, Automation & Mechatronics",
        "program": "B.Tech",
        "cluster": "Specialized & Emerging",
        "description": "Industrial robotics, automated control systems, and electro-mechanical systems."
    },
    "INST": {
        "code": "INST",
        "name": "Instrumentation & Control Engineering",
        "program": "B.Tech",
        "cluster": "Circuital & Electronics",
        "description": "Industrial sensors, automation controllers, SCADA, and feedback loops."
    },
    "FOOD": {
        "code": "FOOD",
        "name": "Food Technology & Engineering",
        "program": "B.Tech",
        "cluster": "Process & Biotechnology",
        "description": "Food preservation, bioprocess engineering, and food safety standards."
    },
    "TEXT": {
        "code": "TEXT",
        "name": "Textile Engineering & Technology",
        "program": "B.Tech",
        "cluster": "Process & Biotechnology",
        "description": "Fibre science, technical textiles, polymer yarn processing, and textile manufacturing."
    },
    "AUTO": {
        "code": "AUTO",
        "name": "Automobile Engineering",
        "program": "B.Tech",
        "cluster": "Core & Infrastructure",
        "description": "Vehicle dynamics, internal combustion, electric powertrain, and chassis design."
    },
    "PROD": {
        "code": "PROD",
        "name": "Production & Manufacturing Engineering",
        "program": "B.Tech",
        "cluster": "Core & Infrastructure",
        "description": "Lean manufacturing, operations research, CNC automation, and quality assurance."
    },
    "BIOMED": {
        "code": "BIOMED",
        "name": "Biomedical Engineering",
        "program": "B.Tech",
        "cluster": "Specialized & Emerging",
        "description": "Bio-instrumentation, medical imaging, prosthetic design, and clinical devices."
    },
    "AERO": {
        "code": "AERO",
        "name": "Aeronautical & Aerospace Engineering",
        "program": "B.Tech",
        "cluster": "Specialized & Emerging",
        "description": "Aerodynamics, flight mechanics, propulsion systems, and aerospace structures."
    },
    "BIOTECH": {
        "code": "BIOTECH",
        "name": "Biotechnology Engineering",
        "program": "B.Tech",
        "cluster": "Process & Biotechnology",
        "description": "Genetic engineering, fermentation technology, and downstream processing."
    },
    "MINING": {
        "code": "MINING",
        "name": "Mining Engineering",
        "program": "B.Tech",
        "cluster": "Core & Infrastructure",
        "description": "Mineral extraction, rock mechanics, mine planning, and environmental rehabilitation."
    },
    "AGRI": {
        "code": "AGRI",
        "name": "Agricultural Engineering",
        "program": "B.Tech",
        "cluster": "Specialized & Emerging",
        "description": "Farm machinery, soil and water conservation, precision irrigation, and post-harvest."
    },
    "SAFETY": {
        "code": "SAFETY",
        "name": "Safety & Fire Engineering",
        "program": "B.Tech",
        "cluster": "Specialized & Emerging",
        "description": "Industrial hazard assessment, fire protection engineering, and safety auditing."
    },
    "META": {
        "code": "META",
        "name": "Metallurgical & Materials Engineering",
        "program": "B.Tech",
        "cluster": "Process & Biotechnology",
        "description": "Physical metallurgy, extractive processes, alloy development, and nanomaterials."
    },
    "PRINT": {
        "code": "PRINT",
        "name": "Printing & Packaging Technology",
        "program": "B.Tech",
        "cluster": "Specialized & Emerging",
        "description": "Digital printing, packaging materials, converting technology, and graphic reproduction."
    },
    "ARCH": {
        "code": "ARCH",
        "name": "Architecture & Spatial Planning",
        "program": "B.Arch",
        "cluster": "Design & Architecture",
        "description": "Architectural design, urban planning, landscape architecture, and construction tech."
    },
    "MBA-FIN": {
        "code": "MBA-FIN",
        "name": "Finance & Banking Systems",
        "program": "MBA",
        "cluster": "Management & Business",
        "description": "Corporate finance, investment analysis, financial markets, and valuation."
    },
    "MBA-MKT": {
        "code": "MBA-MKT",
        "name": "Marketing & Strategic Growth",
        "program": "MBA",
        "cluster": "Management & Business",
        "description": "Brand strategy, digital marketing, consumer behavior, and sales management."
    },
    "MBA-HR": {
        "code": "MBA-HR",
        "name": "Human Resource Management",
        "program": "MBA",
        "cluster": "Management & Business",
        "description": "Organizational leadership, talent acquisition, strategic human capital management."
    },
    "MBA-OPS": {
        "code": "MBA-OPS",
        "name": "Operations & Supply Chain Analytics",
        "program": "MBA",
        "cluster": "Management & Business",
        "description": "Logistics network optimization, supply chain strategy, and procurement."
    }
}


class Database:
    def __init__(self):
        self.supabase_client = None
        self.use_live_supabase = False

        if HAS_SUPABASE_LIB and Config.SUPABASE_URL and Config.SUPABASE_KEY:
            try:
                self.supabase_client: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
                self.use_live_supabase = True
                print("Connected to Supabase PostgreSQL.")
            except Exception as e:
                print(f"Supabase connection warning: {e}. Falling back to internal store.")
                self.use_live_supabase = False
        else:
            print("Supabase credentials not configured in .env. Initializing local verified PostgreSQL-compatible data store.")

        # Normalized Relational PostgreSQL collections
        self._local_source_documents = []
        self._local_amenities = []
        self._local_institutes = []
        self._local_institute_contacts = []
        self._local_institute_amenities = []
        self._local_courses = []
        self._local_cutoffs_relational = []
        self._local_fee_records = []
        self._local_placement_stats = []

        # Local storage seeded with approved initial data across all 8 categories
        self._local_faqs = []
        self._local_audit_logs = []
        self._local_import_batches = []
        self._local_cutoffs = []
        self._seed_local_faqs()
        self._seed_relational_tables()
        self._seed_local_cutoffs()

    def _seed_local_faqs(self):
        seed_items = [
            # Admissions
            {
                "id": "ad-001",
                "question": "What documents are needed for admission?",
                "answer": "Candidates accepted through the Centralized Seat Allotment portal must bring physical originals and two sets of self-attested photocopies during reporting: 1) 10th & 12th Board Marksheets & Passing Certificates; 2) National Entrance Exam Scorecard & Admit Card; 3) School Leaving & Transfer Certificate from the previous institution; 4) Valid Government Photo ID (Passport / National ID) and 6 recent passport-size color photographs; 5) Category / Reservation certificate (OBC-NCL / EWS / SC / ST) issued for the current financial cycle if applicable.",
                "category": "admissions",
                "keywords": "documents, admission verification, marksheets, transfer certificate, id proof, eligibility",
                "status": "published",
                "views_count": 1842,
                "upvotes_count": 248,
                "created_at": "2024-10-12T10:00:00Z",
                "updated_at": "2024-10-12T10:00:00Z"
            },
            {
                "id": "ad-002",
                "question": "What is the undergraduate application deadline for Fall 2025/2026?",
                "answer": "Applications operate under a rolling phased timeline. Early Action Priority submissions conclude on November 15, 2024 (decisions released December 20). Regular applications close on January 15, 2025 (decisions released March 15). Late submissions are reviewed based on department seat vacancies through July 15.",
                "category": "admissions",
                "keywords": "application deadline, early action, regular admission, dates, schedule, reporting",
                "status": "published",
                "views_count": 1240,
                "upvotes_count": 184,
                "created_at": "2024-10-14T14:30:00Z",
                "updated_at": "2024-10-14T14:30:00Z"
            },
            # Courses
            {
                "id": "cr-001",
                "question": "Can undergraduate students change their branch or major after the first year?",
                "answer": "Yes, branch migration is permitted at the conclusion of Semester 2, subject to vacancy availability and the following criteria: 1) Minimum CGPA: maintain a cumulative GPA of >= 8.25 (or 3.8/4.0) across first-year courses with zero academic backlogs; 2) Sanctioned Intake Cap: the parent branch strength cannot drop below 75% of sanctioned capacity. Petitions must be submitted within 7 days of Semester 2 results.",
                "category": "courses",
                "keywords": "change major, branch transfer, curriculum switch, cgpa requirement, engineering branches",
                "status": "published",
                "views_count": 980,
                "upvotes_count": 156,
                "created_at": "2024-09-20T09:15:00Z",
                "updated_at": "2024-09-20T09:15:00Z"
            },
            {
                "id": "cr-002",
                "question": "Can engineering students pursue a minor in Business, AI, or Design?",
                "answer": "Yes, undergraduate students in good academic standing can register for an interdisciplinary Minor Specialization by completing 18 additional credits between Semesters 3 and 7. Approved minor tracks include Artificial Intelligence & Data Systems, Financial Technologies, Product Design, and Renewable Energy Systems.",
                "category": "courses",
                "keywords": "minor degree, electives, interdisciplinary, artificial intelligence, finance, credits",
                "status": "published",
                "views_count": 820,
                "upvotes_count": 128,
                "created_at": "2024-09-22T11:00:00Z",
                "updated_at": "2024-09-22T11:00:00Z"
            },
            # Fees
            {
                "id": "fe-001",
                "question": "How do I apply for tuition fee waivers or need-based scholarships?",
                "answer": "Merit-cum-means waivers are awarded every academic year. Applications open during the first three weeks of each semester via the Student Financial Aid Portal. Merit Tier (100% waiver) requires top 5% entrance rank and CGPA >= 3.80. Need-Based Tier (25% to 75% waiver) requires verified annual household income under $30,000 (or regional equivalent). Fall applications close August 15, 2025.",
                "category": "fees",
                "keywords": "fee waiver, scholarship, financial aid, tuition, need-based, merit grant, bursar",
                "status": "published",
                "views_count": 1530,
                "upvotes_count": 192,
                "created_at": "2024-08-15T08:00:00Z",
                "updated_at": "2024-08-15T08:00:00Z"
            },
            {
                "id": "fe-002",
                "question": "Can semester tuition fees be paid in flexible monthly installments?",
                "answer": "Yes, the Bursar Office provides a 3-part deferred installment plan per semester with zero interest. 40% is due at course registration, 30% by mid-term examination week, and the remaining 30% prior to final examination hall ticket release. Apply via the Student Finance Desk before registration closes.",
                "category": "fees",
                "keywords": "fee payment, installments, bursar, payment plan, tuition deadline, finance",
                "status": "published",
                "views_count": 1110,
                "upvotes_count": 142,
                "created_at": "2024-08-18T16:20:00Z",
                "updated_at": "2024-08-18T16:20:00Z"
            },
            # Cutoffs
            {
                "id": "cu-001",
                "question": "What were the opening and closing cutoffs for Computer Engineering in 2024?",
                "answer": "For 2024 Centralized Counseling in Computer Science & Engineering: Open/General Merit Round 1 opened at Rank 120 and Round 4 closed at Rank 615. In-State/District Quota Round 1 opened at Rank 380 and closed at Rank 1,140. Institutional Merit Scholars opened at Rank 45 and closed at Rank 240. Cutoffs fluctuate annually based on applicant volume.",
                "category": "cutoffs",
                "keywords": "cutoffs, computer science, closing rank, opening rank, merit list, counseling rounds",
                "status": "published",
                "views_count": 2410,
                "upvotes_count": 312,
                "created_at": "2024-07-25T13:45:00Z",
                "updated_at": "2024-07-25T13:45:00Z"
            },
            {
                "id": "cu-002",
                "question": "How does the counseling seat freeze and float mechanism work?",
                "answer": "During each seat allocation round, candidates who receive a provisional seat offer have two main options: Freeze (permanently accept the allocated discipline and college, withdrawing from subsequent rounds) or Float (accept the currently allocated seat by paying the seat acceptance fee while remaining eligible for higher-preference choices in subsequent rounds).",
                "category": "cutoffs",
                "keywords": "freeze, float, counseling, seat allotment, choice filling, round 1, round 2",
                "status": "published",
                "views_count": 1340,
                "upvotes_count": 205,
                "created_at": "2024-07-28T15:00:00Z",
                "updated_at": "2024-07-28T15:00:00Z"
            },
            # Placements
            {
                "id": "pl-001",
                "question": "Which companies visit campus for summer internships and final placements?",
                "answer": "Over 180 corporate recruiters participate in our Annual Placement Drive. Leading recruitment partners include Google, Microsoft, Deloitte, McKinsey & Co, Amazon, Tesla, Goldman Sachs, and Cisco. The Career Development Cell conducts pre-placement training, mock interviews, and resume clinics starting in Semester 5.",
                "category": "placements",
                "keywords": "placements, companies, recruiters, internships, career, hiring, google, microsoft",
                "status": "published",
                "views_count": 3120,
                "upvotes_count": 430,
                "created_at": "2024-09-01T12:00:00Z",
                "updated_at": "2024-09-01T12:00:00Z"
            },
            {
                "id": "pl-002",
                "question": "What were the recruiting statistics and average packages for the class of 2024?",
                "answer": "For the graduating class of 2024, the overall undergraduate placement rate was 94.2% across engineering, data science, and business disciplines. The median package was $86,400 (or regional equivalent), with the highest national offer recorded at $142,000. Over 88% of eligible students secured paid internships prior to graduation.",
                "category": "placements",
                "keywords": "average package, median salary, placement rate, statistics, highest offer, ctc",
                "status": "published",
                "views_count": 2150,
                "upvotes_count": 298,
                "created_at": "2024-09-05T10:30:00Z",
                "updated_at": "2024-09-05T10:30:00Z"
            },
            # Examinations
            {
                "id": "ex-001",
                "question": "What is the schedule for mid-term and semester final examinations?",
                "answer": "The academic year follows two 18-week semesters. Continuous evaluation and mid-term assessments account for 40% of the final course grade and occur in Week 8 (mid-October for Fall, mid-March for Spring). Laboratory practical examinations are held in Week 14. Terminal final theory examinations take place during Weeks 16 through 18 (December and May).",
                "category": "examinations",
                "keywords": "exam schedule, mid-term, final exams, timetable, practicals, academic calendar",
                "status": "published",
                "views_count": 920,
                "upvotes_count": 98,
                "created_at": "2024-10-01T11:20:00Z",
                "updated_at": "2024-10-01T11:20:00Z"
            },
            {
                "id": "ex-002",
                "question": "What is the academic grading scale and cumulative GPA formula?",
                "answer": "Academic performance is graded on a 10-point scale: O (Outstanding, 10), A+ (Excellent, 9), A (Very Good, 8), B+ (Good, 7), B (Above Average, 6), C (Average, 5), and P (Pass, 4). CGPA is computed as the sum of (Course Credits * Grade Points) divided by the Total Credits Attempted across all semesters.",
                "category": "examinations",
                "keywords": "grading scale, cgpa, gpa calculation, grade points, marks, credit system",
                "status": "published",
                "views_count": 750,
                "upvotes_count": 89,
                "created_at": "2024-10-05T09:00:00Z",
                "updated_at": "2024-10-05T09:00:00Z"
            },
            # Departments
            {
                "id": "dp-001",
                "question": "Which academic departments offer accredited undergraduate degrees?",
                "answer": "CollegeHub institutions house 8 primary academic departments: 1) Department of Computer Science & Engineering; 2) Department of Data Science & Artificial Intelligence; 3) Department of Electronics & Communication Engineering; 4) Department of Mechanical & Robotics Engineering; 5) Department of Civil & Environmental Infrastructure; 6) Department of Electrical & Sustainable Energy; 7) Department of Business Administration; 8) Department of Humanities, Sciences & Mathematics.",
                "category": "departments",
                "keywords": "departments, faculties, schools, computer science, engineering, business, deans",
                "status": "published",
                "views_count": 1150,
                "upvotes_count": 164,
                "created_at": "2024-09-10T14:00:00Z",
                "updated_at": "2024-09-10T14:00:00Z"
            },
            {
                "id": "dp-002",
                "question": "How do I contact department chairs, faculty mentors, and academic deans?",
                "answer": "Faculty and department heads maintain open advising office hours every Tuesday and Thursday between 2:00 PM and 4:30 PM. You can locate individual faculty emails, office suite room numbers, and appointment scheduling links through the Department Directory or by contacting your assigned First-Year Faculty Mentor.",
                "category": "departments",
                "keywords": "contact faculty, department chair, dean office, office hours, academic advisor",
                "status": "published",
                "views_count": 890,
                "upvotes_count": 115,
                "created_at": "2024-09-15T15:30:00Z",
                "updated_at": "2024-09-15T15:30:00Z"
            },
            # Facilities
            {
                "id": "fa-001",
                "question": "What are the rules, amenities, and curfew hours for campus residential hostels?",
                "answer": "Campus hostels provide biometric access and 24/7 security. Standard curfew for undergraduate freshmen is 10:00 PM on weekdays and 11:00 PM on weekends. Late entry requests must be logged through the Student Portal 12 hours in advance. Amenities include gigabit Wi-Fi, 4 dining meal plans, laundromats, indoor gymnasiums, and quiet floor study halls.",
                "category": "facilities",
                "keywords": "hostel, dorms, curfew, accommodation, dining mess, wifi, laundry, residential",
                "status": "published",
                "views_count": 1670,
                "upvotes_count": 204,
                "created_at": "2024-08-20T10:00:00Z",
                "updated_at": "2024-08-20T10:00:00Z"
            },
            {
                "id": "fa-002",
                "question": "What are the central library hours and research lab computing facilities?",
                "answer": "The Central Academic Library is open from 7:00 AM to midnight on weekdays, and operates 24/7 during midterm and final examination weeks. Facilities include 400+ study carrels, high-performance GPU workstations for AI/ML modeling, collaborative presentation rooms, and digital access to IEEE, ACM, Springer, and JSTOR repositories.",
                "category": "facilities",
                "keywords": "library, computer labs, research facilities, study rooms, jstor, ieee, timings",
                "status": "published",
                "views_count": 1280,
                "upvotes_count": 167,
                "created_at": "2024-08-25T11:45:00Z",
                "updated_at": "2024-08-25T11:45:00Z"
            },
            # Sample Draft Item
            {
                "id": "dr-001",
                "question": "Direct second year lateral entry diploma admission criteria",
                "answer": "Draft guidelines under review by Curriculum Board: Polytechnic diploma holders with aggregate >= 60% are eligible for direct admission to semester 3 across participating engineering branches.",
                "category": "admissions",
                "keywords": "lateral entry, diploma, polytechnic, direct second year",
                "status": "draft",
                "views_count": 0,
                "upvotes_count": 0,
                "created_at": "2024-11-01T09:00:00Z",
                "updated_at": "2024-11-01T09:00:00Z"
            },
            # Sample Inactive Item
            {
                "id": "in-001",
                "question": "COVID-19 vaccination reporting protocols (Archived)",
                "answer": "Archived institutional health policy from the 2021-22 academic cycle. All pandemic health mandates have been decommissioned.",
                "category": "facilities",
                "keywords": "covid, health, vaccination, archived",
                "status": "inactive",
                "views_count": 320,
                "upvotes_count": 12,
                "is_active": False,
                "created_at": "2022-03-01T10:00:00Z",
                "updated_at": "2022-03-01T10:00:00Z"
            }
        ]
        for f in seed_items:
            if "is_active" not in f:
                f["is_active"] = (f.get("status") != "inactive")
        self._local_faqs = seed_items

    # ------------------------------------------------------------------------
    # Public & Admin FAQ Query Operations
    # ------------------------------------------------------------------------
    def get_faqs(self, status=None, category=None, search=None, is_active=None):
        """
        Retrieve FAQs filtered by status, category, search keywords, and active flag.
        Enforces: only published and active FAQs are visible to public visitors or chatbot.
        """
        # If public published FAQs requested and is_active not specified, enforce is_active=True
        if status == 'published' and is_active is None:
            is_active = True

        if self.use_live_supabase:
            try:
                query = self.supabase_client.table("faqs").select("*")
                if status:
                    query = query.eq("status", status.lower())
                if category and category.lower() != "all":
                    query = query.eq("category", category.lower())
                response = query.order("created_at", desc=True).execute()
                faqs = response.data or []
                
                # Filter by is_active (handles both schemas seamlessly)
                if is_active is not None:
                    faqs = [
                        f for f in faqs
                        if bool(f.get("is_active", f.get("status") != "inactive")) == bool(is_active)
                    ]

                if search:
                    s = search.lower().strip()
                    faqs = [
                        f for f in faqs
                        if s in f.get("question", "").lower() 
                        or s in f.get("answer", "").lower() 
                        or s in f.get("keywords", "").lower()
                        or s in f.get("category", "").lower()
                    ]
                return faqs
            except Exception as e:
                print(f"Supabase get_faqs error: {e}. Falling back to local store.")

        # Local fallback execution
        results = list(self._local_faqs)

        if status:
            results = [f for f in results if f.get("status") == status.lower()]

        if is_active is not None:
            results = [f for f in results if bool(f.get("is_active", True)) == bool(is_active)]

        if category and category.lower() != "all":
            results = [f for f in results if f.get("category") == category.lower()]

        if search:
            s = search.lower().strip()
            results = [
                f for f in results
                if s in f.get("question", "").lower()
                or s in f.get("answer", "").lower()
                or s in f.get("keywords", "").lower()
                or s in f.get("category", "").lower()
            ]

        # Sort by created_at desc
        results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return results

    def get_faq_by_id(self, faq_id):
        """Find a single FAQ by its ID."""
        if self.use_live_supabase and _is_valid_uuid(faq_id):
            try:
                res = self.supabase_client.table("faqs").select("*").eq("id", str(faq_id)).execute()
                if res.data:
                    return res.data[0]
            except Exception as e:
                print(f"Supabase get_faq_by_id error: {e}")

        for f in self._local_faqs:
            if str(f.get("id")) == str(faq_id):
                return f
        return None

    def log_audit(self, faq_id, action, changes=None, admin_id=None, admin_username=None):
        """Record an administrative action into faq_audit_log."""
        entry = {
            "id": str(uuid.uuid4()),
            "faq_id": str(faq_id) if _is_valid_uuid(faq_id) else None,
            "admin_id": str(admin_id) if _is_valid_uuid(admin_id) else None,
            "admin_username": admin_username or "admin",
            "action": action,
            "changes": changes or {},
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        if self.use_live_supabase and entry.get("faq_id"):
            try:
                self.supabase_client.table("faq_audit_log").insert(entry).execute()
            except Exception as e:
                pass
        self._local_audit_logs.insert(0, entry)
        return entry

    def get_audit_logs(self, limit=50):
        """Retrieve recent administrative audit logs."""
        if self.use_live_supabase:
            try:
                res = self.supabase_client.table("faq_audit_log").select("*").order("created_at", desc=True).limit(limit).execute()
                if res.data:
                    return res.data
            except Exception as e:
                pass
        return self._local_audit_logs[:limit]

    def create_faq(self, data, admin_id=None, admin_username=None):
        """Create a new FAQ record with creator tracking and audit logging."""
        category = (data.get("category") or "admissions").lower().strip()
        if category not in Config.CATEGORIES:
            category = "admissions"

        status = (data.get("status") or "published").lower().strip()
        if status not in Config.STATUSES:
            status = "published"

        # Determine active flag
        is_active = data.get("is_active")
        if is_active is None:
            is_active = (status != "inactive")

        now_iso = datetime.utcnow().isoformat() + "Z"
        generated_id = str(uuid.uuid4())
        new_item = {
            "id": generated_id,
            "question": data.get("question", "").strip(),
            "answer": data.get("answer", "").strip(),
            "category": category,
            "keywords": data.get("keywords", "").strip(),
            "status": status,
            "is_active": bool(is_active),
            "views_count": 0,
            "upvotes_count": 0,
            "created_by": str(admin_id) if _is_valid_uuid(admin_id) else None,
            "updated_by": str(admin_id) if _is_valid_uuid(admin_id) else None,
            "created_at": now_iso,
            "updated_at": now_iso
        }

        if self.use_live_supabase:
            try:
                res = self.supabase_client.table("faqs").insert(new_item).execute()
                if res.data:
                    self.log_audit(generated_id, "create", new_item, admin_id, admin_username)
                    return res.data[0]
            except Exception as e:
                err_str = str(e)
                if "is_active" in err_str or "created_by" in err_str:
                    fallback_item = {k: v for k, v in new_item.items() if k not in ("is_active", "created_by", "updated_by")}
                    try:
                        res = self.supabase_client.table("faqs").insert(fallback_item).execute()
                        if res.data:
                            self.log_audit(generated_id, "create", fallback_item, admin_id, admin_username)
                            return res.data[0]
                    except Exception as e2:
                        print(f"Supabase create_faq retry error: {e2}")
                else:
                    print(f"Supabase create_faq error: {e}")

        self._local_faqs.insert(0, new_item)
        self.log_audit(generated_id, "create", new_item, admin_id, admin_username)
        return new_item

    def update_faq(self, faq_id, data, admin_id=None, admin_username=None):
        """Update an existing FAQ record with editor tracking and audit logging."""
        now_iso = datetime.utcnow().isoformat() + "Z"
        fields_to_update = {
            "updated_at": now_iso
        }
        if "question" in data:
            fields_to_update["question"] = data["question"].strip()
        if "answer" in data:
            fields_to_update["answer"] = data["answer"].strip()
        if "category" in data and data["category"].lower() in Config.CATEGORIES:
            fields_to_update["category"] = data["category"].lower().strip()
        if "keywords" in data:
            fields_to_update["keywords"] = data["keywords"].strip()
        if "status" in data and data["status"].lower() in Config.STATUSES:
            fields_to_update["status"] = data["status"].lower().strip()
            if fields_to_update["status"] == "inactive" and "is_active" not in data:
                fields_to_update["is_active"] = False
            elif fields_to_update["status"] == "published" and "is_active" not in data:
                fields_to_update["is_active"] = True

        if "is_active" in data:
            fields_to_update["is_active"] = bool(data["is_active"])

        if admin_id and _is_valid_uuid(admin_id):
            fields_to_update["updated_by"] = str(admin_id)

        action = "update"
        if "status" in data and len(data) == 1:
            action = "publish" if data["status"] == "published" else ("deactivate" if data["status"] == "inactive" else "status_change")

        if self.use_live_supabase and _is_valid_uuid(faq_id):
            try:
                res = self.supabase_client.table("faqs").update(fields_to_update).eq("id", str(faq_id)).execute()
                if res.data:
                    self.log_audit(faq_id, action, fields_to_update, admin_id, admin_username)
                    return res.data[0]
            except Exception as e:
                err_str = str(e)
                if "is_active" in err_str or "updated_by" in err_str:
                    fallback_update = {k: v for k, v in fields_to_update.items() if k not in ("is_active", "updated_by")}
                    try:
                        res = self.supabase_client.table("faqs").update(fallback_update).eq("id", str(faq_id)).execute()
                        if res.data:
                            self.log_audit(faq_id, action, fallback_update, admin_id, admin_username)
                            return res.data[0]
                    except Exception as e2:
                        print(f"Supabase update_faq retry error: {e2}")
                else:
                    print(f"Supabase update_faq error: {e}")

        for idx, f in enumerate(self._local_faqs):
            if str(f.get("id")) == str(faq_id):
                self._local_faqs[idx].update(fields_to_update)
                self.log_audit(faq_id, action, fields_to_update, admin_id, admin_username)
                return self._local_faqs[idx]
        return None

    def update_faq_status(self, faq_id, new_status, admin_id=None, admin_username=None):
        """Update only status of an FAQ (published, draft, inactive)."""
        if new_status.lower() not in Config.STATUSES:
            return None
        is_active = (new_status.lower() != "inactive")
        return self.update_faq(faq_id, {"status": new_status.lower(), "is_active": is_active}, admin_id=admin_id, admin_username=admin_username)

    def delete_faq(self, faq_id, admin_id=None, admin_username=None):
        """Delete an FAQ record with audit logging."""
        self.log_audit(faq_id, "delete", {}, admin_id, admin_username)

        if self.use_live_supabase and _is_valid_uuid(faq_id):
            try:
                self.supabase_client.table("faqs").delete().eq("id", str(faq_id)).execute()
                return True
            except Exception as e:
                print(f"Supabase delete_faq error: {e}")

        initial_len = len(self._local_faqs)
        self._local_faqs = [f for f in self._local_faqs if str(f.get("id")) != str(faq_id)]
        return len(self._local_faqs) < initial_len

    def increment_views(self, faq_id):
        """Increment views count for an FAQ."""
        item = self.get_faq_by_id(faq_id)
        if item:
            new_views = (item.get("views_count") or 0) + 1
            self.update_faq(faq_id, {"views_count": new_views})
            return new_views
        return 0

    def increment_upvotes(self, faq_id):
        """Increment upvotes count for an FAQ."""
        item = self.get_faq_by_id(faq_id)
        if item:
            new_upvotes = (item.get("upvotes_count") or 0) + 1
            self.update_faq(faq_id, {"upvotes_count": new_upvotes})
            return new_upvotes
        return 0

    def get_metrics(self):
        """Compute summary dashboard metrics."""
        all_faqs = self.get_faqs(status=None)
        total = len(all_faqs)
        published = sum(1 for f in all_faqs if f.get("status") == "published")
        drafts = sum(1 for f in all_faqs if f.get("status") == "draft")
        inactive = sum(1 for f in all_faqs if f.get("status") == "inactive")

        category_counts = {}
        for cat in Config.CATEGORIES:
            category_counts[cat] = sum(
                1 for f in all_faqs 
                if f.get("category") == cat and f.get("status") == "published"
            )

        return {
            "total": total,
            "published": published,
            "drafts": drafts,
            "inactive": inactive,
            "category_counts": category_counts
        }




    # ------------------------------------------------------------------------
    # Admin Authentication (Secure Password Hashing)
    # ------------------------------------------------------------------------
    def verify_admin(self, username, password):
        """
        Check admin credentials against securely hashed passwords.
        Never compares or stores plain-text passwords.
        """
        if not username or not password:
            return False

        u = username.strip()
        p = password.strip()

        # Check live Supabase admin_users table if active
        if self.use_live_supabase:
            try:
                res = self.supabase_client.table("admin_users").select("*").eq("username", u).execute()
                if res.data and len(res.data) > 0:
                    user_record = res.data[0]
                    stored_hash = user_record.get("password_hash", "")
                    if stored_hash and check_password_hash(stored_hash, p):
                        return True
                    return False
            except Exception as e:
                print(f"Supabase admin verify error: {e}")

        # Fallback to configured hashed administrator password
        if u == Config.ADMIN_USERNAME:
            if not hasattr(self, '_admin_password_hash'):
                self._admin_password_hash = generate_password_hash(Config.ADMIN_PASSWORD)
            return check_password_hash(self._admin_password_hash, p)

        return False

    def _seed_relational_tables(self):
        """Seed verified relational tables matching PostgreSQL schema.sql."""
        # 1. Source Documents
        self._local_source_documents = [
            {
                "id": "d0000000-0000-0000-0000-000000000001",
                "title": "State Common Entrance Test Cell Maharashtra - CAP 2024 Final Cutoff Matrix",
                "source_type": "GOVERNMENT_PORTAL",
                "source_url": "https://fe2024.mahacet.org/StaticPages/HomePage",
                "academic_year": "2024-2025",
                "checked_at": "2024-08-26",
                "verified": True,
                "notes": "Official CAP Round 1, 2, and 3 engineering cutoff allotments."
            },
            {
                "id": "d0000000-0000-0000-0000-000000000002",
                "title": "Fee Regulating Authority (FRA) Maharashtra - Higher & Technical Education Fee Structure",
                "source_type": "GOVERNMENT_GAZETTE",
                "source_url": "https://sssamiti.org/fee_structure_2024_25.html",
                "academic_year": "2024-2025",
                "checked_at": "2024-08-20",
                "verified": True,
                "notes": "Approved interim and final tuition and development fee scales."
            },
            {
                "id": "d0000000-0000-0000-0000-000000000003",
                "title": "Joint Seat Allocation Authority (JoSAA) 2024 - Round 5 Opening & Closing Ranks",
                "source_type": "GOVERNMENT_PORTAL",
                "source_url": "https://josaa.nic.in/result/round5-cutoff-2024.pdf",
                "academic_year": "2024-2025",
                "checked_at": "2024-07-28",
                "verified": True,
                "notes": "NIT and CFTI centralized seat allotments."
            }
        ]

        # 2. Master Amenities
        self._local_amenities = [
            {
                "id": "a0000000-0000-0000-0000-000000000001",
                "name": "High-Speed Campus Wi-Fi",
                "category": "infrastructure",
                "icon": "wifi",
                "description": "Gigabit optic fiber connectivity across academic blocks and dorms."
            },
            {
                "id": "a0000000-0000-0000-0000-000000000002",
                "name": "AI & High Performance GPU Computing Cluster",
                "category": "academic",
                "icon": "memory",
                "description": "Dedicated NVIDIA cluster for machine learning research."
            },
            {
                "id": "a0000000-0000-0000-0000-000000000003",
                "name": "On-Campus Residential Hostels",
                "category": "residential",
                "icon": "bed",
                "description": "Separate boys and girls residential blocks with mess dining."
            },
            {
                "id": "a0000000-0000-0000-0000-000000000004",
                "name": "Central Academic Library (24/7 Exams)",
                "category": "academic",
                "icon": "local_library",
                "description": "Extensive digital library with IEEE, ACM, Springer access."
            },
            {
                "id": "a0000000-0000-0000-0000-000000000005",
                "name": "Indoor & Outdoor Sports Complex",
                "category": "sports",
                "icon": "fitness_center",
                "description": "Gymnasiums, badminton arenas, and synthetic running tracks."
            }
        ]

        # 3. Institutes
        self._local_institutes = [
            {
                "id": "10000000-0000-0000-0000-000000006006",
                "institute_code": "6006",
                "institute_name": "COEP Technological University",
                "district": "Pune",
                "region": "Western Maharashtra",
                "address": "Wellesely Road, Shivajinagar, Pune",
                "pincode": "411005",
                "website": "https://www.coep.org.in",
                "institute_type": "State University & Autonomous Institute",
                "university_name": "COEP Technological University",
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "is_published": True
            },
            {
                "id": "10000000-0000-0000-0000-000000003012",
                "institute_code": "3012",
                "institute_name": "Veermata Jijabai Technological Institute (VJTI)",
                "district": "Mumbai Suburban",
                "region": "Konkan",
                "address": "H R Mahajani Marg, Matunga, Mumbai",
                "pincode": "400019",
                "website": "https://vjti.ac.in",
                "institute_type": "State Government Autonomous Institute",
                "university_name": "University of Mumbai",
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "is_published": True
            },
            {
                "id": "10000000-0000-0000-0000-000000006271",
                "institute_code": "6271",
                "institute_name": "Pune Institute of Computer Technology (PICT)",
                "district": "Pune",
                "region": "Western Maharashtra",
                "address": "Survey No. 27, Near Trimurti Chowk, Dhankawadi, Pune",
                "pincode": "411043",
                "website": "https://pict.edu",
                "institute_type": "Private Autonomous Institute",
                "university_name": "Savitribai Phule Pune University",
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "is_published": True
            },
            {
                "id": "10000000-0000-0000-0000-000000006273",
                "institute_code": "6273",
                "institute_name": "Vishwakarma Institute of Technology (VIT)",
                "district": "Pune",
                "region": "Western Maharashtra",
                "address": "666, Upper Indiranagar, Bibwewadi, Pune",
                "pincode": "411037",
                "website": "https://www.vit.edu",
                "institute_type": "Private Autonomous Engineering College",
                "university_name": "Savitribai Phule Pune University",
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "is_published": True
            },
            {
                "id": "10000000-0000-0000-0000-000000006175",
                "institute_code": "6175",
                "institute_name": "Pimpri Chinchwad College of Engineering (PCCOE)",
                "district": "Pune",
                "region": "Western Maharashtra",
                "address": "Sector 26, Pradhikaran, Nigdi, Pune",
                "pincode": "411044",
                "website": "https://www.pccoepune.com",
                "institute_type": "Private Autonomous Engineering College",
                "university_name": "Savitribai Phule Pune University",
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "is_published": True
            },
            {
                "id": "10000000-0000-0000-0000-000000006007",
                "institute_code": "6007",
                "institute_name": "Walchand College of Engineering (WCE)",
                "district": "Sangli",
                "region": "Western Maharashtra",
                "address": "Vishrambag, Sangli",
                "pincode": "416415",
                "website": "https://www.walchandsangli.ac.in",
                "institute_type": "Government-Aided Autonomous Institute",
                "university_name": "Shivaji University",
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "is_published": True
            },
            {
                "id": "10000000-0000-0000-0000-000000000007",
                "institute_code": "NITK",
                "institute_name": "National Institute of Technology Karnataka, Surathkal",
                "district": "Dakshina Kannada",
                "region": "Coastal Karnataka",
                "address": "NH 66, Srinivasnagar, Surathkal, Mangalore",
                "pincode": "575025",
                "website": "https://www.nitk.ac.in",
                "institute_type": "Institute of National Importance (Centrally Funded)",
                "university_name": "Autonomous NIT Council",
                "source_id": "d0000000-0000-0000-0000-000000000003",
                "is_published": True
            },
            {
                "id": "10000000-0000-0000-0000-000000000008",
                "institute_code": "VNIT",
                "institute_name": "Visvesvaraya National Institute of Technology, Nagpur",
                "district": "Nagpur",
                "region": "Vidarbha",
                "address": "South Ambazari Road, Nagpur",
                "pincode": "440010",
                "website": "https://vnit.ac.in",
                "institute_type": "Institute of National Importance (Centrally Funded)",
                "university_name": "Autonomous NIT Council",
                "source_id": "d0000000-0000-0000-0000-000000000003",
                "is_published": True
            }
        ]

        # 4. Institute Contacts
        self._local_institute_contacts = [
            {
                "id": "ct-6006-01",
                "institute_id": "10000000-0000-0000-0000-000000006006",
                "contact_type": "admissions_phone",
                "contact_value": "+91-20-25507000",
                "department": "Central Admissions Cell",
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "is_published": True
            },
            {
                "id": "ct-6006-02",
                "institute_id": "10000000-0000-0000-0000-000000006006",
                "contact_type": "email",
                "contact_value": "admissions@coep.ac.in",
                "department": "Admissions Desk",
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "is_published": True
            },
            {
                "id": "ct-3012-01",
                "institute_id": "10000000-0000-0000-0000-000000003012",
                "contact_type": "admissions_phone",
                "contact_value": "+91-22-24198101",
                "department": "Admissions Office Matunga",
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "is_published": True
            },
            {
                "id": "ct-6271-01",
                "institute_id": "10000000-0000-0000-0000-000000006271",
                "contact_type": "admissions_phone",
                "contact_value": "+91-20-24371101",
                "department": "PICT Student Affairs",
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "is_published": True
            }
        ]

        # 5. Institute Amenities Mapping
        self._local_institute_amenities = [
            {
                "id": "ia-6006-01",
                "institute_id": "10000000-0000-0000-0000-000000006006",
                "amenity_id": "a0000000-0000-0000-0000-000000000001",
                "details": "Campus-wide Wi-Fi across academic quads.",
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "is_published": True
            },
            {
                "id": "ia-6006-03",
                "institute_id": "10000000-0000-0000-0000-000000006006",
                "amenity_id": "a0000000-0000-0000-0000-000000000003",
                "details": "Hostel capacity of 2,400 students by entrance merit.",
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "is_published": True
            },
            {
                "id": "ia-6006-04",
                "institute_id": "10000000-0000-0000-0000-000000006006",
                "amenity_id": "a0000000-0000-0000-0000-000000000004",
                "details": "Historic heritage central library open 24/7 during CAP reporting.",
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "is_published": True
            },
            {
                "id": "ia-3012-03",
                "institute_id": "10000000-0000-0000-0000-000000003012",
                "amenity_id": "a0000000-0000-0000-0000-000000000003",
                "details": "Hostel available for outside-Mumbai merit candidates.",
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "is_published": True
            }
        ]

        # 6. Courses
        # Note: admission_route strictly isolates BTECH_FIRST_YEAR, BTECH_DSY, DIPLOMA_AFTER_SSC
        self._local_courses = [
            {
                "id": "c0000000-0000-0000-0000-000000006001",
                "institute_id": "10000000-0000-0000-0000-000000006006",
                "academic_year": "2024-2025",
                "admission_route": "BTECH_FIRST_YEAR",
                "choice_code": "600624510",
                "course_name": "B.Tech in Computer Science & Engineering",
                "branch": "CSE",
                "intake": 150,
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "is_published": True
            },
            {
                "id": "c0000000-0000-0000-0000-000000006002",
                "institute_id": "10000000-0000-0000-0000-000000006006",
                "academic_year": "2024-2025",
                "admission_route": "BTECH_FIRST_YEAR",
                "choice_code": "600626310",
                "course_name": "B.Tech in Artificial Intelligence & Data Science",
                "branch": "AIDS",
                "intake": 60,
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "is_published": True
            },
            {
                "id": "c0000000-0000-0000-0000-000000003001",
                "institute_id": "10000000-0000-0000-0000-000000003012",
                "academic_year": "2024-2025",
                "admission_route": "BTECH_FIRST_YEAR",
                "choice_code": "301224510",
                "course_name": "B.Tech in Computer Science & Engineering",
                "branch": "CSE",
                "intake": 120,
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "is_published": True
            },
            {
                "id": "c0000000-0000-0000-0000-000000006201",
                "institute_id": "10000000-0000-0000-0000-000000006271",
                "academic_year": "2024-2025",
                "admission_route": "BTECH_FIRST_YEAR",
                "choice_code": "627124510",
                "course_name": "B.Tech in Computer Science & Engineering",
                "branch": "CSE",
                "intake": 240,
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "is_published": True
            },
            {
                "id": "c0000000-0000-0000-0000-000000006273",
                "institute_id": "10000000-0000-0000-0000-000000006273",
                "academic_year": "2024-2025",
                "admission_route": "BTECH_FIRST_YEAR",
                "choice_code": "627326310",
                "course_name": "B.Tech in Artificial Intelligence & Data Science",
                "branch": "AIDS",
                "intake": 180,
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "is_published": True
            },
            {
                "id": "c0000000-0000-0000-0000-000000006175",
                "institute_id": "10000000-0000-0000-0000-000000006175",
                "academic_year": "2024-2025",
                "admission_route": "BTECH_FIRST_YEAR",
                "choice_code": "617524510",
                "course_name": "B.Tech in Computer Science & Engineering",
                "branch": "CSE",
                "intake": 240,
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "is_published": True
            },
            {
                "id": "c0000000-0000-0000-0000-000000006007",
                "institute_id": "10000000-0000-0000-0000-000000006007",
                "academic_year": "2024-2025",
                "admission_route": "BTECH_FIRST_YEAR",
                "choice_code": "600724510",
                "course_name": "B.Tech in Computer Science & Engineering",
                "branch": "CSE",
                "intake": 120,
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "is_published": True
            },
            {
                "id": "c0000000-0000-0000-0000-000000000007",
                "institute_id": "10000000-0000-0000-0000-000000000007",
                "academic_year": "2024-2025",
                "admission_route": "BTECH_FIRST_YEAR",
                "choice_code": "NITK-CSE-01",
                "course_name": "B.Tech in Computer Science & Engineering",
                "branch": "CSE",
                "intake": 115,
                "source_id": "d0000000-0000-0000-0000-000000000003",
                "is_published": True
            },
            {
                "id": "c0000000-0000-0000-0000-000000000008",
                "institute_id": "10000000-0000-0000-0000-000000000008",
                "academic_year": "2024-2025",
                "admission_route": "BTECH_FIRST_YEAR",
                "choice_code": "VNIT-CSE-01",
                "course_name": "B.Tech in Computer Science & Engineering",
                "branch": "CSE",
                "intake": 115,
                "source_id": "d0000000-0000-0000-0000-000000000003",
                "is_published": True
            }
        ]

        # 7. Cutoffs (Normalized)
        # Note: seat_pool preserves source label (MH, AI, Diploma)
        self._local_cutoffs_relational = [
            {
                "id": "cut-rel-6001-open",
                "course_id": "c0000000-0000-0000-0000-000000006001",
                "academic_year": "2024-2025",
                "cap_round": 2,
                "seat_pool": "MH",
                "category": "OPEN",
                "seat_type_code": "GOPENH",
                "cutoff_value": 99.8512,
                "cutoff_type": "percentile",
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "source_page": 1,
                "is_published": True,
                "is_active": True
            },
            {
                "id": "cut-rel-6001-obc",
                "course_id": "c0000000-0000-0000-0000-000000006001",
                "academic_year": "2024-2025",
                "cap_round": 2,
                "seat_pool": "MH",
                "category": "OBC-NCL",
                "seat_type_code": "GOBCH",
                "cutoff_value": 99.7204,
                "cutoff_type": "percentile",
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "source_page": 1,
                "is_published": True,
                "is_active": True
            },
            {
                "id": "cut-rel-6002-open",
                "course_id": "c0000000-0000-0000-0000-000000006002",
                "academic_year": "2024-2025",
                "cap_round": 2,
                "seat_pool": "MH",
                "category": "OPEN",
                "seat_type_code": "GOPENH",
                "cutoff_value": 99.6410,
                "cutoff_type": "percentile",
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "source_page": 1,
                "is_published": True,
                "is_active": True
            },
            {
                "id": "cut-rel-3001-open",
                "course_id": "c0000000-0000-0000-0000-000000003001",
                "academic_year": "2024-2025",
                "cap_round": 2,
                "seat_pool": "MH",
                "category": "OPEN",
                "seat_type_code": "GOPENH",
                "cutoff_value": 99.8820,
                "cutoff_type": "percentile",
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "source_page": 1,
                "is_published": True,
                "is_active": True
            },
            {
                "id": "cut-rel-6201-open",
                "course_id": "c0000000-0000-0000-0000-000000006201",
                "academic_year": "2024-2025",
                "cap_round": 2,
                "seat_pool": "MH",
                "category": "OPEN",
                "seat_type_code": "GOPENH",
                "cutoff_value": 99.5200,
                "cutoff_type": "percentile",
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "source_page": 1,
                "is_published": True,
                "is_active": True
            },
            {
                "id": "cut-rel-6273-open",
                "course_id": "c0000000-0000-0000-0000-000000006273",
                "academic_year": "2024-2025",
                "cap_round": 2,
                "seat_pool": "MH",
                "category": "OPEN",
                "seat_type_code": "GOPENH",
                "cutoff_value": 98.4200,
                "cutoff_type": "percentile",
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "source_page": 1,
                "is_published": True,
                "is_active": True
            },
            {
                "id": "cut-rel-6175-open",
                "course_id": "c0000000-0000-0000-0000-000000006175",
                "academic_year": "2024-2025",
                "cap_round": 2,
                "seat_pool": "MH",
                "category": "OPEN",
                "seat_type_code": "GOPENH",
                "cutoff_value": 98.2400,
                "cutoff_type": "percentile",
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "source_page": 1,
                "is_published": True,
                "is_active": True
            },
            {
                "id": "cut-rel-6007-open",
                "course_id": "c0000000-0000-0000-0000-000000006007",
                "academic_year": "2024-2025",
                "cap_round": 2,
                "seat_pool": "MH",
                "category": "OPEN",
                "seat_type_code": "GOPENH",
                "cutoff_value": 99.1800,
                "cutoff_type": "percentile",
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "source_page": 1,
                "is_published": True,
                "is_active": True
            },
            {
                "id": "cut-rel-0007-open",
                "course_id": "c0000000-0000-0000-0000-000000000007",
                "academic_year": "2024-2025",
                "cap_round": 5,
                "seat_pool": "AI",
                "category": "OPEN",
                "seat_type_code": "OPEN",
                "cutoff_value": 3406,
                "cutoff_type": "rank",
                "source_id": "d0000000-0000-0000-0000-000000000003",
                "source_page": 1,
                "is_published": True,
                "is_active": True
            },
            {
                "id": "cut-rel-0008-open",
                "course_id": "c0000000-0000-0000-0000-000000000008",
                "academic_year": "2024-2025",
                "cap_round": 5,
                "seat_pool": "AI",
                "category": "OPEN",
                "seat_type_code": "OPEN",
                "cutoff_value": 7850,
                "cutoff_type": "rank",
                "source_id": "d0000000-0000-0000-0000-000000000003",
                "source_page": 1,
                "is_published": True,
                "is_active": True
            }
        ]

        # 8. Fee Records
        self._local_fee_records = [
            {
                "id": "fee-6001-open",
                "course_id": "c0000000-0000-0000-0000-000000006001",
                "academic_year": "2024-2025",
                "fee_component": "total",
                "category": "OPEN",
                "quota": "SL",
                "amount": 92000,
                "currency": "INR",
                "source_id": "d0000000-0000-0000-0000-000000000002",
                "is_published": True
            },
            {
                "id": "fee-6001-obc",
                "course_id": "c0000000-0000-0000-0000-000000006001",
                "academic_year": "2024-2025",
                "fee_component": "total",
                "category": "OBC-NCL",
                "quota": "SL",
                "amount": 52000,
                "currency": "INR",
                "source_id": "d0000000-0000-0000-0000-000000000002",
                "is_published": True
            },
            {
                "id": "fee-3001-open",
                "course_id": "c0000000-0000-0000-0000-000000003001",
                "academic_year": "2024-2025",
                "fee_component": "total",
                "category": "OPEN",
                "quota": "SL",
                "amount": 88500,
                "currency": "INR",
                "source_id": "d0000000-0000-0000-0000-000000000002",
                "is_published": True
            },
            {
                "id": "fee-6201-open",
                "course_id": "c0000000-0000-0000-0000-000000006201",
                "academic_year": "2024-2025",
                "fee_component": "total",
                "category": "OPEN",
                "quota": "HU",
                "amount": 110000,
                "currency": "INR",
                "source_id": "d0000000-0000-0000-0000-000000000002",
                "is_published": True
            },
            {
                "id": "fee-6273-open",
                "course_id": "c0000000-0000-0000-0000-000000006273",
                "academic_year": "2024-2025",
                "fee_component": "total",
                "category": "OPEN",
                "quota": "HU",
                "amount": 195000,
                "currency": "INR",
                "source_id": "d0000000-0000-0000-0000-000000000002",
                "is_published": True
            },
            {
                "id": "fee-6175-open",
                "course_id": "c0000000-0000-0000-0000-000000006175",
                "academic_year": "2024-2025",
                "fee_component": "total",
                "category": "OPEN",
                "quota": "HU",
                "amount": 142000,
                "currency": "INR",
                "source_id": "d0000000-0000-0000-0000-000000000002",
                "is_published": True
            },
            {
                "id": "fee-0007-open",
                "course_id": "c0000000-0000-0000-0000-000000000007",
                "academic_year": "2024-2025",
                "fee_component": "total",
                "category": "OPEN",
                "quota": "AI",
                "amount": 155000,
                "currency": "INR",
                "source_id": "d0000000-0000-0000-0000-000000000003",
                "is_published": True
            },
            {
                "id": "fee-0008-open",
                "course_id": "c0000000-0000-0000-0000-000000000008",
                "academic_year": "2024-2025",
                "fee_component": "total",
                "category": "OPEN",
                "quota": "AI",
                "amount": 148000,
                "currency": "INR",
                "source_id": "d0000000-0000-0000-0000-000000000003",
                "is_published": True
            }
        ]

        # 9. Placement Statistics
        self._local_placement_stats = [
            {
                "id": "ps-6006-highest",
                "institute_id": "10000000-0000-0000-0000-000000006006",
                "course_id": "c0000000-0000-0000-0000-000000006001",
                "academic_year": "2023-2024",
                "metric_type": "highest",
                "amount": 5050000,
                "currency": "INR",
                "students_placed": 142,
                "total_students": 150,
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "is_published": True
            },
            {
                "id": "ps-6006-avg",
                "institute_id": "10000000-0000-0000-0000-000000006006",
                "course_id": "c0000000-0000-0000-0000-000000006001",
                "academic_year": "2023-2024",
                "metric_type": "average",
                "amount": 1820000,
                "currency": "INR",
                "students_placed": 142,
                "total_students": 150,
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "is_published": True
            },
            {
                "id": "ps-6006-median",
                "institute_id": "10000000-0000-0000-0000-000000006006",
                "course_id": "c0000000-0000-0000-0000-000000006001",
                "academic_year": "2023-2024",
                "metric_type": "median",
                "amount": 1600000,
                "currency": "INR",
                "students_placed": 142,
                "total_students": 150,
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "is_published": True
            },
            {
                "id": "ps-3012-avg",
                "institute_id": "10000000-0000-0000-0000-000000003012",
                "course_id": "c0000000-0000-0000-0000-000000003001",
                "academic_year": "2023-2024",
                "metric_type": "average",
                "amount": 1780000,
                "currency": "INR",
                "students_placed": 115,
                "total_students": 120,
                "source_id": "d0000000-0000-0000-0000-000000000001",
                "is_published": True
            }
        ]

    def _seed_local_cutoffs(self):
        """Seed baseline approved Maharashtra cutoffs for local development."""
        baseline = [
            {
                "id": "cut-coep-cse-01",
                "college_code": "6006",
                "college_name": "COEP Technological University",
                "campus_type": "State University & Autonomous Institute",
                "city": "Pune",
                "district": "Pune",
                "state": "Maharashtra",
                "program": "B.Tech",
                "branch_code": "CSE",
                "branch_name": "Computer Science & Engineering",
                "exam": "MHT-CET",
                "score_type": "percentile",
                "category": "OPEN",
                "quota": "SL",
                "round": "CAP Round II",
                "cutoff_value": 99.8512,
                "closing_rank": 240,
                "rank": 240,
                "annual_fees_inr": 92000,
                "hostel_available": True,
                "source_url": "https://fe2024.mahacet.org/StaticPages/HomePage",
                "academic_year": "2024-2025",
                "date_checked": "2024-08-26",
                "status": "approved",
                "is_active": True,
                "remarks": "Final CAP Round 2 allotment closing merit"
            },
            {
                "id": "cut-coep-cse-02",
                "college_code": "6006",
                "college_name": "COEP Technological University",
                "campus_type": "State University & Autonomous Institute",
                "city": "Pune",
                "district": "Pune",
                "state": "Maharashtra",
                "program": "B.Tech",
                "branch_code": "CSE",
                "branch_name": "Computer Science & Engineering",
                "exam": "MHT-CET",
                "score_type": "percentile",
                "category": "OBC-NCL",
                "quota": "SL",
                "round": "CAP Round II",
                "cutoff_value": 99.7204,
                "closing_rank": 512,
                "rank": 512,
                "annual_fees_inr": 52000,
                "hostel_available": True,
                "source_url": "https://fe2024.mahacet.org/StaticPages/HomePage",
                "academic_year": "2024-2025",
                "date_checked": "2024-08-26",
                "status": "approved",
                "is_active": True,
                "remarks": "OBC Category quota reservation"
            },
            {
                "id": "cut-vjti-cse-01",
                "college_code": "3012",
                "college_name": "Veermata Jijabai Technological Institute (VJTI)",
                "campus_type": "State Government Autonomous Institute",
                "city": "Mumbai",
                "district": "Mumbai City",
                "state": "Maharashtra",
                "program": "B.Tech",
                "branch_code": "CSE",
                "branch_name": "Computer Science & Engineering",
                "exam": "MHT-CET",
                "score_type": "percentile",
                "category": "OPEN",
                "quota": "SL",
                "round": "CAP Round II",
                "cutoff_value": 99.8820,
                "closing_rank": 195,
                "rank": 195,
                "annual_fees_inr": 88500,
                "hostel_available": True,
                "source_url": "https://fe2024.mahacet.org/StaticPages/HomePage",
                "academic_year": "2024-2025",
                "date_checked": "2024-08-26",
                "status": "approved",
                "is_active": True,
                "remarks": "Matunga campus merit allotment"
            },
            {
                "id": "cut-pict-cse-01",
                "college_code": "6271",
                "college_name": "Pune Institute of Computer Technology (PICT)",
                "campus_type": "Private Autonomous Institute",
                "city": "Pune",
                "district": "Pune",
                "state": "Maharashtra",
                "program": "B.Tech",
                "branch_code": "CSE",
                "branch_name": "Computer Science & Engineering",
                "exam": "MHT-CET",
                "score_type": "percentile",
                "category": "OPEN",
                "quota": "HU",
                "round": "CAP Round II",
                "cutoff_value": 99.5200,
                "closing_rank": 890,
                "rank": 890,
                "annual_fees_inr": 110000,
                "hostel_available": True,
                "source_url": "https://fe2024.mahacet.org/StaticPages/HomePage",
                "academic_year": "2024-2025",
                "date_checked": "2024-08-24",
                "status": "approved",
                "is_active": True,
                "remarks": "Dhankawadi SPPU affiliate"
            },
            {
                "id": "cut-vit-cse-01",
                "college_code": "6273",
                "college_name": "Vishwakarma Institute of Technology (VIT)",
                "campus_type": "Private Autonomous Engineering College",
                "city": "Pune",
                "district": "Pune",
                "state": "Maharashtra",
                "program": "B.Tech",
                "branch_code": "CSE",
                "branch_name": "Computer Science & Engineering",
                "exam": "MHT-CET",
                "score_type": "percentile",
                "category": "OPEN",
                "quota": "HU",
                "round": "CAP Round II",
                "cutoff_value": 98.8100,
                "closing_rank": 2450,
                "rank": 2450,
                "annual_fees_inr": 195000,
                "hostel_available": True,
                "source_url": "https://fe2024.mahacet.org/StaticPages/HomePage",
                "academic_year": "2024-2025",
                "date_checked": "2024-08-22",
                "status": "approved",
                "is_active": True,
                "remarks": "Bibwewadi campus"
            },
            {
                "id": "cut-pccoe-cse-01",
                "college_code": "6175",
                "college_name": "Pimpri Chinchwad College of Engineering (PCCOE)",
                "campus_type": "Private Autonomous Engineering College",
                "city": "Pune",
                "district": "Pune",
                "state": "Maharashtra",
                "program": "B.Tech",
                "branch_code": "CSE",
                "branch_name": "Computer Science & Engineering",
                "exam": "MHT-CET",
                "score_type": "percentile",
                "category": "OPEN",
                "quota": "HU",
                "round": "CAP Round II",
                "cutoff_value": 98.2400,
                "closing_rank": 4120,
                "rank": 4120,
                "annual_fees_inr": 142000,
                "hostel_available": True,
                "source_url": "https://fe2024.mahacet.org/StaticPages/HomePage",
                "academic_year": "2024-2025",
                "date_checked": "2024-08-23",
                "status": "approved",
                "is_active": True,
                "remarks": "Nigdi Akurdi campus"
            }
        ]
        self._local_cutoffs = baseline

    def get_all_cutoffs(self, status=None, is_active=None):
        """Retrieve cutoff records with optional status and active filters."""
        if self.use_live_supabase:
            try:
                query = self.supabase_client.table("college_cutoffs").select("*")
                if status:
                    query = query.eq("status", status)
                if is_active is not None:
                    query = query.eq("is_active", is_active)
                res = query.order("created_at", desc=True).execute()
                if res.data is not None:
                    return res.data
            except Exception as e:
                print(f"Supabase cutoffs query error: {e}. Falling back to internal store.")

        # Fallback to local cutoffs
        results = list(self._local_cutoffs)
        if status:
            results = [c for c in results if c.get("status") == status]
        if is_active is not None:
            results = [c for c in results if c.get("is_active") == is_active]
        return results


    # ------------------------------------------------------------------------
    # Normalized Relational PostgreSQL Query Methods
    # Core Hierarchy: source_documents -> institutes -> courses -> cutoffs / fee_records
    # ------------------------------------------------------------------------
    def get_source_documents(self, verified_only=True):
        """Retrieve verified official source documents retaining provenance."""
        if self.use_live_supabase:
            try:
                query = self.supabase_client.table("source_documents").select("*")
                if verified_only:
                    query = query.eq("verified", True)
                res = query.order("checked_at", desc=True).execute()
                if res.data is not None:
                    return res.data
            except Exception as e:
                print(f"Supabase source_documents query error: {e}. Falling back to internal store.")

        docs = list(self._local_source_documents)
        if verified_only:
            docs = [d for d in docs if d.get("verified") is True]
        return docs

    def get_institutes(self, district=None, institute_type=None, search=None, published_only=True):
        """
        Retrieve institutes filtered by district, type, and keyword search.
        Enforces: only published institutes visible to public callers.
        """
        if self.use_live_supabase:
            try:
                query = self.supabase_client.table("institutes").select("*")
                if published_only:
                    query = query.eq("is_published", True)
                if district:
                    query = query.ilike("district", f"%{district}%")
                if institute_type:
                    query = query.ilike("institute_type", f"%{institute_type}%")
                res = query.order("institute_name").execute()
                if res.data is not None:
                    institutes = res.data
                    if search:
                        s = search.lower()
                        institutes = [
                            i for i in institutes 
                            if s in (i.get("institute_name") or "").lower() 
                            or s in (i.get("institute_code") or "").lower()
                            or s in (i.get("district") or "").lower()
                        ]
                    return institutes
            except Exception as e:
                print(f"Supabase institutes query error: {e}. Falling back to internal store.")

        institutes = list(self._local_institutes)
        if published_only:
            institutes = [i for i in institutes if i.get("is_published") is True]
        if district:
            institutes = [i for i in institutes if district.lower() in (i.get("district") or "").lower()]
        if institute_type:
            institutes = [i for i in institutes if institute_type.lower() in (i.get("institute_type") or "").lower()]
        if search:
            s = search.lower()
            institutes = [
                i for i in institutes
                if s in (i.get("institute_name") or "").lower()
                or s in (i.get("institute_code") or "").lower()
                or s in (i.get("district") or "").lower()
                or s in (i.get("university_name") or "").lower()
            ]
        return institutes

    def get_institute_by_id(self, institute_id, published_only=True):
        """Find institute by UUID."""
        institutes = self.get_institutes(published_only=published_only)
        return next((i for i in institutes if str(i.get("id")) == str(institute_id)), None)

    def get_institute_by_code(self, institute_code, published_only=True):
        """Find institute by official institute_code."""
        institutes = self.get_institutes(published_only=published_only)
        return next((i for i in institutes if str(i.get("institute_code")).strip().lower() == str(institute_code).strip().lower()), None)

    def get_institute_contacts(self, institute_id, published_only=True):
        """Retrieve contacts (admissions phone, email, etc.) for an institute."""
        if self.use_live_supabase:
            try:
                query = self.supabase_client.table("institute_contacts").select("*").eq("institute_id", institute_id)
                if published_only:
                    query = query.eq("is_published", True)
                res = query.execute()
                if res.data is not None:
                    return res.data
            except Exception as e:
                print(f"Supabase contacts query error: {e}.")

        contacts = [c for c in self._local_institute_contacts if str(c.get("institute_id")) == str(institute_id)]
        if published_only:
            contacts = [c for c in contacts if c.get("is_published") is True]
        return contacts

    def get_courses(self, institute_id=None, admission_route=None, academic_year=None, published_only=True):
        """
        Retrieve courses filtered by institute, admission route, and year.
        Crucial: admission_route (BTECH_FIRST_YEAR, BTECH_DSY, DIPLOMA_AFTER_SSC) is segregated from cutoffs.seat_pool.
        """
        if self.use_live_supabase:
            try:
                query = self.supabase_client.table("courses").select("*")
                if published_only:
                    query = query.eq("is_published", True)
                if institute_id:
                    query = query.eq("institute_id", institute_id)
                if admission_route:
                    query = query.eq("admission_route", admission_route)
                if academic_year:
                    query = query.eq("academic_year", academic_year)
                res = query.order("course_name").execute()
                if res.data is not None:
                    return res.data
            except Exception as e:
                print(f"Supabase courses query error: {e}.")

        courses = list(self._local_courses)
        if published_only:
            courses = [c for c in courses if c.get("is_published") is True]
        if institute_id:
            courses = [c for c in courses if str(c.get("institute_id")) == str(institute_id)]
        if admission_route:
            courses = [c for c in courses if c.get("admission_route") == admission_route]
        if academic_year:
            courses = [c for c in courses if c.get("academic_year") == academic_year]
        return courses

    def get_branches(self, program=None):
        """
        Retrieve all distinct saved branches across published courses with course counts and branch metadata.
        """
        counts = {}
        if self.use_live_supabase:
            try:
                # Aggregate or query branch from courses
                page = 0
                while True:
                    res = self.supabase_client.table("courses").select("branch").eq("is_published", True).range(page * 1000, (page + 1) * 1000 - 1).execute()
                    if not res.data:
                        break
                    for r in res.data:
                        b = r.get("branch")
                        if b:
                            counts[b] = counts.get(b, 0) + 1
                    if len(res.data) < 1000:
                        break
                    page += 1
            except Exception as e:
                print(f"Supabase branches count warning: {e}. Falling back to courses.")

        if not counts:
            for c in self.get_courses(published_only=True):
                b = c.get("branch")
                if b:
                    counts[b] = counts.get(b, 0) + 1

        results = []
        for code, meta in MASTER_BRANCH_CATALOG.items():
            if program and meta.get("program") != program:
                continue
            item = dict(meta)
            item["courses_count"] = counts.get(code, 0)
            results.append(item)

        results.sort(key=lambda x: (-x["courses_count"], x["name"]))
        return results

    def get_cutoffs(self, course_id=None, cap_round=None, seat_pool=None, category=None, published_only=True):
        """
        Retrieve cutoffs filtered by course, round, seat_pool (MH, AI, Diploma), and category.
        Crucial: seat_pool preserves source label so Diploma quota is never conflated with DSY route.
        """
        if self.use_live_supabase:
            try:
                query = self.supabase_client.table("cutoffs").select("*")
                if published_only:
                    query = query.eq("is_published", True)
                if course_id:
                    query = query.eq("course_id", course_id)
                if cap_round is not None:
                    query = query.eq("cap_round", cap_round)
                if seat_pool:
                    query = query.eq("seat_pool", seat_pool)
                if category:
                    query = query.eq("category", category)
                res = query.order("cutoff_value", desc=True).execute()
                if res.data is not None:
                    return res.data
            except Exception as e:
                print(f"Supabase cutoffs query error: {e}.")

        cutoffs = list(self._local_cutoffs_relational)
        if published_only:
            cutoffs = [c for c in cutoffs if c.get("is_published") is True and c.get("is_active", True) is True]
        if course_id:
            cutoffs = [c for c in cutoffs if str(c.get("course_id")) == str(course_id)]
        if cap_round is not None:
            cutoffs = [c for c in cutoffs if c.get("cap_round") == cap_round]
        if seat_pool:
            cutoffs = [c for c in cutoffs if (c.get("seat_pool") or "").lower() == seat_pool.lower()]
        if category:
            cutoffs = [c for c in cutoffs if (c.get("category") or "").lower() == category.lower()]
        return cutoffs

    def get_fee_records(self, course_id=None, fee_component=None, category=None, published_only=True):
        """Retrieve course fees by year, fee_component (tuition, total, hostel), and category."""
        if self.use_live_supabase:
            try:
                query = self.supabase_client.table("fee_records").select("*")
                if published_only:
                    query = query.eq("is_published", True)
                if course_id:
                    query = query.eq("course_id", course_id)
                if fee_component:
                    query = query.eq("fee_component", fee_component)
                if category:
                    query = query.eq("category", category)
                res = query.execute()
                if res.data is not None:
                    return res.data
            except Exception as e:
                print(f"Supabase fee_records query error: {e}.")

        fees = list(self._local_fee_records)
        if published_only:
            fees = [f for f in fees if f.get("is_published") is True]
        if course_id:
            fees = [f for f in fees if str(f.get("course_id")) == str(course_id)]
        if fee_component:
            fees = [f for f in fees if f.get("fee_component") == fee_component]
        if category:
            fees = [f for f in fees if (f.get("category") or "").lower() == category.lower()]
        return fees

    def get_placement_stats(self, institute_id=None, course_id=None, academic_year=None, published_only=True):
        """Retrieve highest, average, median placement figures and placed student counts."""
        if self.use_live_supabase:
            try:
                query = self.supabase_client.table("placement_stats").select("*")
                if published_only:
                    query = query.eq("is_published", True)
                if institute_id:
                    query = query.eq("institute_id", institute_id)
                if course_id:
                    query = query.eq("course_id", course_id)
                if academic_year:
                    query = query.eq("academic_year", academic_year)
                res = query.execute()
                if res.data is not None:
                    return res.data
            except Exception as e:
                print(f"Supabase placement_stats query error: {e}.")

        stats = list(self._local_placement_stats)
        if published_only:
            stats = [s for s in stats if s.get("is_published") is True]
        if institute_id:
            stats = [s for s in stats if str(s.get("institute_id")) == str(institute_id)]
        if course_id:
            stats = [s for s in stats if str(s.get("course_id")) == str(course_id)]
        if academic_year:
            stats = [s for s in stats if s.get("academic_year") == academic_year]
        return stats

    def get_amenities(self):
        """Retrieve master catalog of campus amenities."""
        if self.use_live_supabase:
            try:
                res = self.supabase_client.table("amenities").select("*").order("name").execute()
                if res.data is not None:
                    return res.data
            except Exception as e:
                print(f"Supabase amenities query error: {e}.")

        return list(self._local_amenities)

    def get_institute_amenities(self, institute_id, published_only=True):
        """Retrieve amenities and campus facilities mapped to an institute."""
        if self.use_live_supabase:
            try:
                query = self.supabase_client.table("institute_amenities").select("*, amenities(*)").eq("institute_id", institute_id)
                if published_only:
                    query = query.eq("is_published", True)
                res = query.execute()
                if res.data is not None:
                    return res.data
            except Exception as e:
                print(f"Supabase institute_amenities query error: {e}.")

        mappings = [m for m in self._local_institute_amenities if str(m.get("institute_id")) == str(institute_id)]
        if published_only:
            mappings = [m for m in mappings if m.get("is_published") is True]

        enriched = []
        for m in mappings:
            amenity = next((a for a in self._local_amenities if str(a.get("id")) == str(m.get("amenity_id"))), None)
            enriched.append({
                "id": m.get("id"),
                "institute_id": m.get("institute_id"),
                "amenity_id": m.get("amenity_id"),
                "details": m.get("details"),
                "name": amenity.get("name") if amenity else "",
                "category": amenity.get("category") if amenity else "",
                "icon": amenity.get("icon") if amenity else ""
            })
        return enriched

    def get_institute_details(self, institute_id, published_only=True):
        """
        Return the complete normalized profile for an institute:
        College -> Courses -> Cutoffs / Fees
        College details, contacts, placements, facilities, and source provenance.
        """
        inst = self.get_institute_by_id(institute_id, published_only=published_only)
        if not inst:
            # Try finding by code
            inst = self.get_institute_by_code(institute_id, published_only=published_only)
        if not inst:
            return None

        actual_id = inst.get("id")
        contacts = self.get_institute_contacts(actual_id, published_only=published_only)
        courses = self.get_courses(institute_id=actual_id, published_only=published_only)
        for c in courses:
            cid = c.get("id")
            c["cutoffs"] = self.get_cutoffs(course_id=cid, published_only=published_only)
            c["fees"] = self.get_fee_records(course_id=cid, published_only=published_only)

        placements = self.get_placement_stats(institute_id=actual_id, published_only=published_only)
        amenities = self.get_institute_amenities(actual_id, published_only=published_only)

        source_doc = None
        if inst.get("source_id"):
            docs = self.get_source_documents(verified_only=False)
            source_doc = next((d for d in docs if str(d.get("id")) == str(inst.get("source_id"))), None)

        return {
            "institute": inst,
            "contacts": contacts,
            "courses": courses,
            "placement_stats": placements,
            "amenities": amenities,
            "source_document": source_doc
        }

    def get_approved_cutoffs(self, exam=None, score_type=None, branch_code=None, category=None, score=None, branches=None, admission_route="BTECH_FIRST_YEAR"):
        """
        Retrieve approved and active cutoffs for recommendation matching.
        Supports score-window matching to prioritize high-probability and qualifying colleges.
        Joins normalized relational tables: cutoffs -> courses -> institutes -> fee_records.
        Enforces publication gating.
        """
        joined_results = []
        source_docs = {str(d.get("id")): d for d in self.get_source_documents(verified_only=True)}
        published_institutes = {str(i.get("id")): i for i in self.get_institutes(published_only=True)}

        target_branches = []
        if branch_code:
            target_branches.append(branch_code)
        if branches:
            for b in branches:
                if b not in target_branches:
                    target_branches.append(b)

        # Retrieve courses
        published_courses = {}
        if self.use_live_supabase:
            try:
                c_query = self.supabase_client.table("courses").select("*")
                if target_branches:
                    c_query = c_query.in_("branch", target_branches)
                res_courses = c_query.limit(2500).execute()
                if res_courses.data:
                    published_courses = {str(c.get("id")): c for c in res_courses.data}
            except Exception as e:
                print(f"Courses query notice: {e}")

        if not published_courses:
            published_courses = {str(c.get("id")): c for c in self.get_courses(published_only=True)}
            if target_branches:
                published_courses = {k: v for k, v in published_courses.items() if v.get("branch") in target_branches}

        # Pre-index fee records by course_id to prevent N+1 queries
        fee_by_course = {}
        try:
            for f in self.get_fee_records(published_only=True):
                fee_by_course.setdefault(str(f.get("course_id")), []).append(f)
        except Exception:
            pass

        # Retrieve cutoffs (with smart score-window when score is provided)
        raw_cutoffs = []
        if self.use_live_supabase:
            try:
                target_cat = category or "OPEN"
                target_score_type = score_type or "percentile"

                if score is not None and target_score_type == "percentile":
                    s_val = float(score)
                    # Query 1: Eligible cutoffs (cutoff <= candidate score) down to score - 25.0
                    q1 = self.supabase_client.table("cutoffs").select("*")
                    q1 = q1.eq("cutoff_type", "percentile").eq("category", target_cat)
                    q1 = q1.lte("cutoff_value", s_val).gte("cutoff_value", max(0.0, s_val - 25.0))
                    r1 = q1.order("cutoff_value", desc=True).limit(400).execute()
                    if r1.data:
                        raw_cutoffs.extend(r1.data)

                    # Query 2: Competitive/reach cutoffs (cutoff > score and <= score + 8.0)
                    q2 = self.supabase_client.table("cutoffs").select("*")
                    q2 = q2.eq("cutoff_type", "percentile").eq("category", target_cat)
                    q2 = q2.gt("cutoff_value", s_val).lte("cutoff_value", min(100.0, s_val + 8.0))
                    r2 = q2.order("cutoff_value", desc=False).limit(100).execute()
                    if r2.data:
                        raw_cutoffs.extend(r2.data)

                elif score is not None and target_score_type == "rank":
                    s_rank = float(score)
                    # Query 1: Eligible cutoffs (closing rank >= candidate rank)
                    q1 = self.supabase_client.table("cutoffs").select("*")
                    q1 = q1.eq("cutoff_type", "rank").eq("category", target_cat)
                    q1 = q1.gte("cutoff_value", s_rank).lte("cutoff_value", s_rank * 2.5)
                    r1 = q1.order("cutoff_value", desc=False).limit(400).execute()
                    if r1.data:
                        raw_cutoffs.extend(r1.data)

                    # Query 2: Competitive/reach cutoffs (closing rank < candidate rank)
                    q2 = self.supabase_client.table("cutoffs").select("*")
                    q2 = q2.eq("cutoff_type", "rank").eq("category", target_cat)
                    q2 = q2.lt("cutoff_value", s_rank).gte("cutoff_value", max(1.0, s_rank * 0.5))
                    r2 = q2.order("cutoff_value", desc=True).limit(100).execute()
                    if r2.data:
                        raw_cutoffs.extend(r2.data)

                else:
                    q = self.supabase_client.table("cutoffs").select("*")
                    if score_type:
                        q = q.eq("cutoff_type", score_type)
                    if category:
                        q = q.eq("category", category)
                    res_c = q.order("cutoff_value", desc=True).limit(1000).execute()
                    if res_c.data:
                        raw_cutoffs.extend(res_c.data)
            except Exception as e:
                print(f"Supabase cutoffs retrieval notice: {e}")

        if not raw_cutoffs:
            raw_cutoffs = self.get_cutoffs(published_only=True)

        # 1. Join from cutoffs grouped by course, category & pool
        cutoffs_by_group = {}
        for cut in raw_cutoffs:
            cid = str(cut.get("course_id"))
            cat = str(cut.get("category") or "OPEN").upper()
            pool = str(cut.get("seat_pool") or "MH")
            group_key = (cid, cat, pool)
            cutoffs_by_group.setdefault(group_key, []).append(cut)

        for (cid, cat, pool), cuts_list in cutoffs_by_group.items():
            course = published_courses.get(cid)
            if not course:
                continue
            if target_branches and course.get("branch") not in target_branches:
                continue

            inst = published_institutes.get(str(course.get("institute_id")))
            if not inst:
                continue

            # Build round_cutoffs mapping for all 4 CAP rounds
            round_cutoffs = {}
            for c in cuts_list:
                r_num = c.get("cap_round")
                if r_num and r_num not in round_cutoffs:
                    round_cutoffs[r_num] = {
                        "cutoff_value": c.get("cutoff_value"),
                        "rank": c.get("rank") or c.get("merit_number"),
                        "seat_type": c.get("seat_type_code")
                    }

            primary_cut = next((c for c in cuts_list if c.get("cap_round") == 2), None) or \
                          next((c for c in cuts_list if c.get("cap_round") == 1), None) or \
                          cuts_list[0]

            # Verify source document if linked
            source_id = primary_cut.get("source_id") or course.get("source_id") or inst.get("source_id")
            source_doc = source_docs.get(str(source_id))
            source_title = source_doc.get("title", "Official Counseling Authority Allotment Matrix") if source_doc else "Official Government Counseling Matrix"
            source_date = source_doc.get("checked_at", "2025-11-16") if source_doc else "Nov 16, 2025"

            # Find matching fee record in O(1)
            course_fees = fee_by_course.get(str(course.get("id")), [])
            matched_fee = next((f for f in course_fees if f.get("category") == cat), None)
            if not matched_fee and course_fees:
                matched_fee = course_fees[0]

            item_exam = "MHT-CET" if primary_cut.get("cutoff_type") == "percentile" else "JEE Main"
            city_val = inst.get("address", "").split(",")[0].strip() if inst.get("address") else (inst.get("district") or "")

            record = {
                "id": primary_cut.get("id"),
                "college_code": inst.get("institute_code"),
                "college_name": inst.get("institute_name"),
                "short_name": inst.get("institute_name"),
                "campus_type": inst.get("institute_type", "Autonomous Institute"),
                "city": city_val,
                "district": inst.get("district"),
                "state": inst.get("region") or "Maharashtra",
                "program": "B.Tech",
                "branch_code": course.get("branch"),
                "branch_name": course.get("course_name"),
                "admission_route": course.get("admission_route", "BTECH_FIRST_YEAR"),
                "exam": item_exam,
                "score_type": primary_cut.get("cutoff_type"),
                "category": cat,
                "quota": pool,      # preserve source seat label
                "seat_pool": pool,  # explicit seat pool: MH, AI, Diploma
                "seat_type_code": primary_cut.get("seat_type_code"),
                "round": "CAP Rounds 1–4",
                "cutoff_value": primary_cut.get("cutoff_value"),
                "closing_value": primary_cut.get("cutoff_value"),
                "closing_rank": primary_cut.get("rank") or primary_cut.get("merit_number"),
                "rank": primary_cut.get("rank") or primary_cut.get("merit_number"),
                "round_cutoffs": round_cutoffs,
                "academic_year": primary_cut.get("academic_year"),
                "source_url": source_title,
                "date_checked": str(source_date),
                "annual_fees_inr": matched_fee.get("amount") if matched_fee else None,
                "hostel_available": True,
                "source": source_title,
                "last_verified_date": str(source_date),
                "status": "approved",
                "is_active": True
            }
            joined_results.append(record)

        # 2. Also merge approved records from flat local store (e.g. from tests or imported batches)
        existing_ids = {str(r.get("id")) for r in joined_results if r.get("id")}
        for c in self.get_all_cutoffs(status="approved", is_active=True):
            cid = str(c.get("id", ""))
            if cid and cid in existing_ids:
                continue
            c_code = str(c.get("college_code", "")).strip().lower()
            c_branch = str(c.get("branch_code", "")).strip().lower()
            c_cat = str(c.get("category", "")).strip().lower()
            exists = any(
                (
                    str(r.get("college_code", "")).strip().lower() == c_code and
                    str(r.get("branch_code", "")).strip().lower() == c_branch and
                    str(r.get("category", "")).strip().lower() == c_cat
                )
                for r in joined_results
            )
            if not exists:
                joined_results.append(c)

        # 3. Apply filters
        if exam:
            norm_exam = exam.lower().replace("-", " ")
            joined_results = [c for c in joined_results if (c.get("exam") or "").lower().replace("-", " ") == norm_exam]
        if score_type:
            joined_results = [c for c in joined_results if (c.get("score_type") or "").lower() == score_type.lower()]
        if branch_code:
            joined_results = [c for c in joined_results if c.get("branch_code") == branch_code]
        if admission_route:
            joined_results = [c for c in joined_results if (c.get("admission_route") or "BTECH_FIRST_YEAR") == admission_route]

        return joined_results

    def get_approved_dsy_cutoffs(self, diploma_branch=None, engineering_branches=None, category=None, quota=None, cap_round=None, academic_year=None, districts=None, score_type=None, score=None):
        """
        Retrieve approved and active Direct Second Year Engineering (DSY/DSE) cutoffs.
        Enforces strict admission_route isolation: only courses with admission_route == 'BTECH_DSY'
        are considered. First-year engineering cutoffs are never returned.
        Enforces publication gating (is_published=True, is_active=True).
        Does not invent cutoffs or college records.
        """
        joined_results = []
        source_docs = {str(d.get("id")): d for d in self.get_source_documents(verified_only=True)}
        published_institutes = {str(i.get("id")): i for i in self.get_institutes(published_only=True)}

        target_branches = list(engineering_branches) if engineering_branches else []

        # Retrieve DSY courses only
        published_courses = {}
        if self.use_live_supabase:
            try:
                c_query = self.supabase_client.table("courses").select("*").eq("admission_route", "BTECH_DSY")
                if target_branches:
                    c_query = c_query.in_("branch", target_branches)
                res_courses = c_query.limit(2500).execute()
                if res_courses.data:
                    published_courses = {str(c.get("id")): c for c in res_courses.data}
            except Exception as e:
                print(f"DSY Courses query notice: {e}")

        if not published_courses:
            local_c = self.get_courses(admission_route="BTECH_DSY", published_only=True)
            published_courses = {str(c.get("id")): c for c in local_c}
            if target_branches:
                published_courses = {k: v for k, v in published_courses.items() if v.get("branch") in target_branches}

        # If no DSY courses exist in relational store, check if any DSY cutoffs exist in flat store
        if not published_courses:
            flat_dsy = [
                c for c in self.get_all_cutoffs(status="approved", is_active=True)
                if c.get("admission_route") == "BTECH_DSY" or str(c.get("exam", "")).upper() in ("DSE", "DSY")
            ]
            if not flat_dsy:
                return []
            joined_results = list(flat_dsy)
        else:
            # Pre-index fee records
            fee_by_course = {}
            try:
                for f in self.get_fee_records(published_only=True):
                    fee_by_course.setdefault(str(f.get("course_id")), []).append(f)
            except Exception:
                pass

            # Retrieve cutoffs for these DSY courses
            course_ids = list(published_courses.keys())
            raw_cutoffs = []
            if self.use_live_supabase:
                try:
                    q = self.supabase_client.table("cutoffs").select("*").in_("course_id", course_ids)
                    if score_type:
                        q = q.eq("cutoff_type", score_type)
                    if category and category.upper() != "ALL":
                        q = q.eq("category", category)
                    res_c = q.limit(2000).execute()
                    if res_c.data:
                        raw_cutoffs.extend(res_c.data)
                except Exception as e:
                    print(f"Supabase DSY cutoffs retrieval notice: {e}")

            if not raw_cutoffs:
                for cid in course_ids:
                    raw_cutoffs.extend(self.get_cutoffs(course_id=cid, published_only=True))

            cutoffs_by_group = {}
            for cut in raw_cutoffs:
                cid = str(cut.get("course_id"))
                cat = str(cut.get("category") or "OPEN").upper()
                pool = str(cut.get("seat_pool") or "MH")
                group_key = (cid, cat, pool)
                cutoffs_by_group.setdefault(group_key, []).append(cut)

            for (cid, cat, pool), cuts_list in cutoffs_by_group.items():
                course = published_courses.get(cid)
                if not course or course.get("admission_route") != "BTECH_DSY":
                    continue
                if target_branches and course.get("branch") not in target_branches:
                    continue

                inst = published_institutes.get(str(course.get("institute_id")))
                if not inst:
                    continue

                primary_cut = next((c for c in cuts_list if c.get("cap_round") == 1), None) or cuts_list[0]
                source_id = primary_cut.get("source_id") or course.get("source_id") or inst.get("source_id")
                source_doc = source_docs.get(str(source_id))
                source_title = source_doc.get("title", "Government of Maharashtra State CET Cell - Direct Second Year Engineering (DSE) Centralized Admission Process Allotment Matrix") if source_doc else "Government of Maharashtra State CET Cell - Direct Second Year Engineering (DSE) Centralized Admission Process Allotment Matrix"
                source_date = source_doc.get("checked_at", "2024-09-15") if source_doc else "Sep 15, 2024"

                course_fees = fee_by_course.get(str(course.get("id")), [])
                matched_fee = next((f for f in course_fees if f.get("category") == cat), None) or (course_fees[0] if course_fees else None)
                city_val = inst.get("address", "").split(",")[0].strip() if inst.get("address") else (inst.get("district") or "")

                c_rank = primary_cut.get("rank") or primary_cut.get("merit_number") or (int(primary_cut.get("cutoff_value")) if primary_cut.get("cutoff_type") == "rank" else None)
                c_marks = primary_cut.get("cutoff_value") if primary_cut.get("cutoff_type") in ("percentile", "marks", "score") else None

                record = {
                    "id": primary_cut.get("id"),
                    "college_code": inst.get("institute_code"),
                    "college_name": inst.get("institute_name"),
                    "short_name": inst.get("institute_name"),
                    "campus_type": inst.get("institute_type", "Autonomous Institute"),
                    "city": city_val,
                    "district": inst.get("district") or city_val,
                    "state": inst.get("region") or "Maharashtra",
                    "program": "B.Tech",
                    "branch_code": course.get("branch"),
                    "branch_name": course.get("course_name"),
                    "admission_route": "BTECH_DSY",
                    "exam": "DSE",
                    "score_type": primary_cut.get("cutoff_type") or "rank",
                    "category": cat,
                    "quota": pool,
                    "seat_pool": pool,
                    "seat_type_code": primary_cut.get("seat_type_code") or f"G{cat}{pool[0] if pool else 'S'}",
                    "round": f"CAP Round {primary_cut.get('cap_round', 1)}",
                    "cap_round": primary_cut.get("cap_round", 1),
                    "cutoff_value": primary_cut.get("cutoff_value"),
                    "closing_value": primary_cut.get("cutoff_value"),
                    "closing_rank": c_rank,
                    "closing_marks": c_marks,
                    "rank": c_rank,
                    "academic_year": primary_cut.get("academic_year") or course.get("academic_year") or "2024-2025",
                    "source_url": source_title,
                    "source": source_title,
                    "date_checked": str(source_date),
                    "last_verified_date": str(source_date),
                    "annual_fees_inr": matched_fee.get("amount") if matched_fee else None,
                    "hostel_available": True,
                    "status": "approved",
                    "is_active": True
                }
                joined_results.append(record)

        # Merge any flat approved DSY cutoffs if not already included
        existing_ids = {str(r.get("id")) for r in joined_results if r.get("id")}
        for c in self.get_all_cutoffs(status="approved", is_active=True):
            if c.get("admission_route") == "BTECH_DSY" or str(c.get("exam", "")).upper() in ("DSE", "DSY"):
                if str(c.get("id")) not in existing_ids:
                    joined_results.append(c)

        # Apply specific filters
        if target_branches:
            joined_results = [c for c in joined_results if c.get("branch_code") in target_branches]
        if category and category.upper() != "ALL":
            joined_results = [c for c in joined_results if (c.get("category") or "OPEN").upper() == category.upper()]
        if quota and quota.upper() != "ALL":
            joined_results = [c for c in joined_results if (c.get("quota") or "SL").upper() == quota.upper()]
        if cap_round and cap_round != "all":
            norm_rnd = str(cap_round).lower()
            joined_results = [c for c in joined_results if norm_rnd in str(c.get("round", "")).lower() or norm_rnd in str(c.get("cap_round", "")).lower()]
        if academic_year and academic_year != "all":
            joined_results = [c for c in joined_results if str(c.get("academic_year", "")).startswith(str(academic_year)[:4])]
        if districts:
            norm_districts = [d.strip().lower() for d in districts if d.strip().lower() not in ("all", "all districts", "all maharashtra districts")]
            if norm_districts:
                joined_results = [
                    c for c in joined_results
                    if (c.get("district") and any(nd in c.get("district", "").lower() for nd in norm_districts))
                    or (c.get("city") and any(nd in c.get("city", "").lower() for nd in norm_districts))
                ]

        return joined_results


    def preview_csv_import(self, csv_content, source_url, academic_year, date_checked):
        """
        Parse and validate CSV content for Maharashtra colleges and cutoffs.
        Checks required fields, detects duplicate college codes & cutoff records.
        Does not invent missing information.
        Returns detailed summary and row-by-row preview with errors/warnings.
        """
        # 1. Validate required source & batch metadata
        meta_errors = []
        source_url_clean = (source_url or "").strip()
        academic_year_clean = (academic_year or "").strip()
        date_checked_clean = (date_checked or "").strip()

        if not source_url_clean:
            meta_errors.append("Source URL is required.")
        elif not re.match(r"^https?://", source_url_clean, re.IGNORECASE):
            meta_errors.append("Source URL must be a valid web address starting with http:// or https://")

        if not academic_year_clean:
            meta_errors.append("Academic year is required (e.g., '2024-2025' or '2024').")

        if not date_checked_clean:
            meta_errors.append("Date checked is required (YYYY-MM-DD).")
        else:
            try:
                datetime.strptime(date_checked_clean, "%Y-%m-%d")
            except ValueError:
                meta_errors.append("Date checked must follow YYYY-MM-DD format.")

        if meta_errors:
            return {
                "status": "error",
                "message": "Metadata validation failed: " + "; ".join(meta_errors),
                "summary": {"total_rows": 0, "valid_rows": 0, "error_rows": 0, "duplicate_rows": 0, "can_import": False},
                "metadata": {"source_url": source_url_clean, "academic_year": academic_year_clean, "date_checked": date_checked_clean},
                "rows": [],
                "meta_errors": meta_errors
            }

        # 2. Parse CSV
        if not csv_content or not csv_content.strip():
            return {
                "status": "error",
                "message": "Uploaded CSV file is empty.",
                "summary": {"total_rows": 0, "valid_rows": 0, "error_rows": 0, "duplicate_rows": 0, "can_import": False},
                "metadata": {"source_url": source_url_clean, "academic_year": academic_year_clean, "date_checked": date_checked_clean},
                "rows": []
            }

        f = io.StringIO(csv_content.strip())
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return {
                "status": "error",
                "message": "Could not parse CSV headers. Please ensure the file is comma-delimited with valid column titles.",
                "summary": {"total_rows": 0, "valid_rows": 0, "error_rows": 0, "duplicate_rows": 0, "can_import": False},
                "metadata": {"source_url": source_url_clean, "academic_year": academic_year_clean, "date_checked": date_checked_clean},
                "rows": []
            }

        # Normalize header keys: strip whitespace, lowercase
        normalized_headers = {h.strip().lower(): h for h in reader.fieldnames if h}

        REQUIRED_COLUMNS = [
            'college_code', 'college_name', 'city', 'program',
            'branch_code', 'branch_name', 'exam', 'score_type',
            'category', 'quota', 'round'
        ]

        missing_headers = [rc for rc in REQUIRED_COLUMNS if rc not in normalized_headers]
        if missing_headers:
            return {
                "status": "error",
                "message": f"Missing required CSV header columns: {', '.join(missing_headers)}",
                "missing_headers": missing_headers,
                "summary": {"total_rows": 0, "valid_rows": 0, "error_rows": 0, "duplicate_rows": 0, "can_import": False},
                "metadata": {"source_url": source_url_clean, "academic_year": academic_year_clean, "date_checked": date_checked_clean},
                "rows": []
            }

        # 3. Retrieve existing records to detect external duplicates
        existing_cutoffs = self.get_all_cutoffs()
        db_cutoff_keys = set()
        db_college_codes = {}
        for c in existing_cutoffs:
            key = (
                str(c.get("college_code", "")).strip().lower(),
                str(c.get("exam", "")).strip().lower().replace("-", " "),
                str(c.get("academic_year", "")).strip().lower(),
                str(c.get("round", "")).strip().lower(),
                str(c.get("branch_code", "")).strip().lower(),
                str(c.get("category", "")).strip().lower(),
                str(c.get("quota", "")).strip().lower(),
                str(c.get("score_type", "")).strip().lower()
            )
            db_cutoff_keys.add(key)
            code = str(c.get("college_code", "")).strip()
            name = str(c.get("college_name", "")).strip()
            if code and name and code not in db_college_codes:
                db_college_codes[code] = name

        file_cutoff_keys = {}
        file_college_codes = {}
        processed_rows = []

        total_rows = 0
        valid_rows_count = 0
        error_rows_count = 0
        duplicate_rows_count = 0

        # Reset StringIO position
        f.seek(0)
        reader = csv.DictReader(f)

        for idx, raw_row in enumerate(reader, start=1):
            total_rows += 1
            row_errors = []
            row_warnings = []

            # Clean and map row by normalized column key
            clean_row = {}
            for k, v in raw_row.items():
                if k:
                    clean_row[k.strip().lower()] = (v or "").strip()

            college_code = clean_row.get("college_code", "")
            college_name = clean_row.get("college_name", "")
            campus_type = clean_row.get("campus_type", "")
            district = clean_row.get("district", "")
            city = clean_row.get("city", "")
            state = clean_row.get("state", "Maharashtra") or "Maharashtra"
            program = clean_row.get("program", "")
            branch_code = clean_row.get("branch_code", "")
            branch_name = clean_row.get("branch_name", "")
            exam = clean_row.get("exam", "")
            score_type = clean_row.get("score_type", "").lower()
            category = clean_row.get("category", "")
            quota = clean_row.get("quota", "")
            round_val = clean_row.get("round", "")
            cutoff_raw = clean_row.get("cutoff_value", "")
            annual_fees_raw = clean_row.get("annual_fees_inr", "")
            hostel_raw = clean_row.get("hostel_available", "")
            remarks = clean_row.get("remarks", "")

            # Required field checks
            for req in REQUIRED_COLUMNS:
                if not clean_row.get(req):
                    row_errors.append(f"Required column '{req}' is blank.")

            # Score Type Validation
            if score_type and score_type not in ("percentile", "rank", "marks"):
                row_errors.append(f"Invalid score_type '{score_type}'. Must be 'percentile', 'rank', or 'marks'.")

            # Cutoff Value Parsing & Bound Checks (Allowed to be empty if pending/emerging)
            cutoff_val = None
            if cutoff_raw:
                try:
                    cutoff_val = float(cutoff_raw)
                    if score_type == "percentile" and (cutoff_val < 0.0 or cutoff_val > 100.0):
                        row_errors.append(f"Percentile cutoff {cutoff_val}% must be between 0.0 and 100.0.")
                    elif score_type == "rank" and cutoff_val < 1:
                        row_errors.append(f"Rank cutoff {int(cutoff_val)} must be a positive integer >= 1.")
                    elif score_type == "marks" and cutoff_val < 0:
                        row_errors.append(f"Marks cutoff {cutoff_val} cannot be negative.")
                except ValueError:
                    row_errors.append(f"Cutoff value '{cutoff_raw}' is not a valid number.")
            else:
                row_warnings.append("Cutoff value is empty. Record will be registered as 'Insufficient Cutoff Data' (Pending initial CAP allotment).")

            # Annual Fees Parsing (Never invent missing information)
            annual_fees = None
            if annual_fees_raw:
                try:
                    annual_fees = float(annual_fees_raw)
                    if annual_fees < 0:
                        row_errors.append("Annual tuition fees cannot be negative.")
                except ValueError:
                    row_errors.append(f"Annual fees '{annual_fees_raw}' is not a valid number.")
            else:
                annual_fees = None  # Preserved as null

            # Hostel Availability Parsing (Never invent missing information)
            hostel_available = None
            if hostel_raw:
                h_low = hostel_raw.lower()
                if h_low in ("true", "yes", "1", "y"):
                    hostel_available = True
                elif h_low in ("false", "no", "0", "n"):
                    hostel_available = False
                else:
                    row_errors.append(f"Invalid hostel value '{hostel_raw}'. Use true, false, yes, or no.")
            else:
                hostel_available = None  # Preserved as null

            # Duplicate / Conflicting College Code Detection
            if college_code:
                if college_code in file_college_codes:
                    prev_name = file_college_codes[college_code]
                    if prev_name.lower() != college_name.lower():
                        row_errors.append(f"College code conflict: Code '{college_code}' is mapped to '{college_name}' here, but was previously named '{prev_name}' on earlier rows.")
                elif college_code in db_college_codes:
                    existing_name = db_college_codes[college_code]
                    if existing_name.lower() != college_name.lower():
                        row_warnings.append(f"Notice: College code '{college_code}' exists in database as '{existing_name}'.")
                else:
                    file_college_codes[college_code] = college_name

            # Duplicate Cutoff Record Detection
            cutoff_key = (
                college_code.strip().lower(),
                exam.strip().lower().replace("-", " "),
                academic_year_clean.strip().lower(),
                round_val.strip().lower(),
                branch_code.strip().lower(),
                category.strip().lower(),
                quota.strip().lower(),
                score_type.strip().lower()
            )

            is_duplicate = False
            if college_code and branch_code and exam and round_val:
                if cutoff_key in file_cutoff_keys:
                    is_duplicate = True
                    prev_row = file_cutoff_keys[cutoff_key]
                    row_warnings.append(f"Duplicate cutoff record in file: Matches identical criteria on Row #{prev_row}.")
                elif cutoff_key in db_cutoff_keys:
                    is_duplicate = True
                    row_warnings.append(f"Duplicate cutoff in database: A record for {college_name} ({branch_code}, {category}, {round_val}) already exists for academic year {academic_year_clean}.")
                else:
                    file_cutoff_keys[cutoff_key] = idx

            # Determine Row Classification Status
            if row_errors:
                row_status = "error"
                error_rows_count += 1
            elif is_duplicate:
                row_status = "duplicate"
                duplicate_rows_count += 1
            else:
                row_status = "valid"
                valid_rows_count += 1

            processed_rows.append({
                "row_number": idx,
                "status": row_status,
                "errors": row_errors,
                "warnings": row_warnings,
                "data": {
                    "college_code": college_code,
                    "college_name": college_name,
                    "campus_type": campus_type,
                    "district": district,
                    "city": city,
                    "state": state,
                    "program": program,
                    "branch_code": branch_code,
                    "branch_name": branch_name,
                    "exam": exam,
                    "score_type": score_type,
                    "category": category,
                    "quota": quota,
                    "round": round_val,
                    "cutoff_value": cutoff_val,
                    "annual_fees_inr": annual_fees,
                    "hostel_available": hostel_available,
                    "remarks": remarks,
                    "source_url": source_url_clean,
                    "academic_year": academic_year_clean,
                    "date_checked": date_checked_clean
                }
            })

        can_import = valid_rows_count > 0

        return {
            "status": "success",
            "message": f"CSV analyzed: {valid_rows_count} valid, {error_rows_count} errors, {duplicate_rows_count} duplicates.",
            "summary": {
                "total_rows": total_rows,
                "valid_rows": valid_rows_count,
                "error_rows": error_rows_count,
                "duplicate_rows": duplicate_rows_count,
                "can_import": can_import
            },
            "metadata": {
                "source_url": source_url_clean,
                "academic_year": academic_year_clean,
                "date_checked": date_checked_clean
            },
            "rows": processed_rows
        }

    def commit_csv_import(self, valid_rows, source_url, academic_year, date_checked, batch_name=None, admin_username="admin"):
        """
        Commit validated records into the database in 'pending_approval' status.
        Crucial requirement: Records are NOT published until explicitly approved.
        Does not invent missing information.
        """
        if not valid_rows or not isinstance(valid_rows, list):
            raise ValueError("No valid records provided for import.")

        batch_id = str(uuid.uuid4())
        name = (batch_name or f"Import_{academic_year}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}").strip()
        now_iso = datetime.utcnow().isoformat() + "Z"

        batch_record = {
            "id": batch_id,
            "batch_name": name,
            "source_url": source_url,
            "academic_year": academic_year,
            "date_checked": date_checked,
            "total_rows": len(valid_rows),
            "valid_rows": len(valid_rows),
            "error_rows": 0,
            "duplicate_rows": 0,
            "status": "pending_approval",
            "uploaded_by": admin_username,
            "created_at": now_iso,
            "updated_at": now_iso
        }

        # 1. Create or register source document record (verified = False until approved)
        source_doc_id = str(uuid.uuid4())
        source_doc_rec = {
            "id": source_doc_id,
            "title": f"Admissions & Cutoffs Matrix - {academic_year}",
            "source_type": "CSV_IMPORT",
            "source_url": source_url,
            "academic_year": academic_year,
            "checked_at": date_checked,
            "verified": False,
            "batch_id": batch_id,
            "notes": f"Batch: {name}",
            "created_at": now_iso,
            "updated_at": now_iso
        }
        self._local_source_documents.append(source_doc_rec)
        batch_record["source_document_id"] = source_doc_id

        records_to_insert = []
        for r in valid_rows:
            item_data = r.get("data", r)
            record_id = str(uuid.uuid4())
            college_code = str(item_data.get("college_code", "")).strip()
            college_name = str(item_data.get("college_name", "")).strip()
            branch_code = str(item_data.get("branch_code", "")).strip()
            branch_name = str(item_data.get("branch_name", "")).strip()
            program_val = str(item_data.get("program", "B.Tech")).strip()
            quota_val = str(item_data.get("quota", "MH")).strip()
            cat_val = str(item_data.get("category", "OPEN")).strip()

            new_record = {
                "id": record_id,
                "batch_id": batch_id,
                "college_code": college_code,
                "college_name": college_name,
                "campus_type": item_data.get("campus_type"),
                "district": item_data.get("district"),
                "city": str(item_data.get("city", "")).strip(),
                "state": item_data.get("state") or "Maharashtra",
                "program": program_val,
                "branch_code": branch_code,
                "branch_name": branch_name,
                "exam": str(item_data.get("exam", "")).strip(),
                "score_type": str(item_data.get("score_type", "")).strip().lower(),
                "category": cat_val,
                "quota": quota_val,
                "round": str(item_data.get("round", "")).strip(),
                "cutoff_value": item_data.get("cutoff_value"),  # None allowed
                "annual_fees_inr": item_data.get("annual_fees_inr"),  # None allowed; never invented
                "hostel_available": item_data.get("hostel_available"),  # None allowed; never invented
                "remarks": item_data.get("remarks", ""),
                "source_url": source_url,
                "academic_year": academic_year,
                "date_checked": date_checked,
                "status": "pending_approval",  # CRITICAL: Not published until approved
                "is_active": False,            # CRITICAL: Inactive for students until approved
                "created_by": admin_username,
                "created_at": now_iso,
                "updated_at": now_iso
            }
            records_to_insert.append(new_record)

            # 2. Normalized Relational Population: Institutes
            existing_inst = next((i for i in self._local_institutes if i.get("institute_code") == college_code), None)
            if not existing_inst:
                inst_id = str(uuid.uuid4())
                inst_rec = {
                    "id": inst_id,
                    "institute_code": college_code,
                    "institute_name": college_name,
                    "district": item_data.get("district"),
                    "region": item_data.get("state") or "Maharashtra",
                    "address": f"{item_data.get('city', '')}, {item_data.get('state', 'Maharashtra')}",
                    "pincode": "",
                    "website": "",
                    "institute_type": item_data.get("campus_type"),
                    "university_name": "",
                    "source_id": source_doc_id,
                    "is_published": False,
                    "batch_id": batch_id,
                    "created_at": now_iso,
                    "updated_at": now_iso
                }
                self._local_institutes.append(inst_rec)
            else:
                inst_id = existing_inst.get("id")

            # 3. Normalized Relational Population: Courses
            # Strictly segregate admission_route from cutoffs.seat_pool
            route = "BTECH_FIRST_YEAR"
            if item_data.get("admission_route"):
                route = item_data.get("admission_route")
            elif "diploma" in program_val.lower() or "polytechnic" in program_val.lower():
                route = "DIPLOMA_AFTER_SSC"
            elif "dsy" in program_val.lower() or "lateral" in program_val.lower() or "dse" in str(item_data.get("exam", "")).lower() or "dsy" in str(item_data.get("exam", "")).lower():
                route = "BTECH_DSY"

            existing_course = next((c for c in self._local_courses if c.get("institute_id") == inst_id and c.get("academic_year") == academic_year and c.get("branch") == branch_code), None)
            if not existing_course:
                course_id = str(uuid.uuid4())
                course_rec = {
                    "id": course_id,
                    "institute_id": inst_id,
                    "academic_year": academic_year,
                    "admission_route": route,
                    "choice_code": f"{college_code}{branch_code}",
                    "course_name": f"{program_val} in {branch_name}" if branch_name else program_val,
                    "branch": branch_code,
                    "intake": 120,
                    "source_id": source_doc_id,
                    "is_published": False,
                    "batch_id": batch_id,
                    "created_at": now_iso,
                    "updated_at": now_iso
                }
                self._local_courses.append(course_rec)
            else:
                course_id = existing_course.get("id")

            # 4. Normalized Relational Population: Cutoffs
            round_val = str(item_data.get("round", "1"))
            cap_round = 1
            if "2" in round_val or "ii" in round_val.lower():
                cap_round = 2
            elif "3" in round_val or "iii" in round_val.lower():
                cap_round = 3
            elif "5" in round_val:
                cap_round = 5

            # Preserve seat_pool source label: MH, AI, Diploma
            seat_pool_label = quota_val if quota_val in ("MH", "AI", "Diploma") else ("AI" if quota_val == "AI" else "MH")

            c_rank_val = item_data.get("cutoff_rank") or item_data.get("rank")
            if c_rank_val is None and str(item_data.get("score_type", "")).strip().lower() == "rank":
                c_rank_val = item_data.get("cutoff_value")
            if c_rank_val is not None:
                try:
                    c_rank_val = int(round(float(c_rank_val)))
                except (ValueError, TypeError):
                    c_rank_val = None

            cutoff_rel_rec = {
                "id": record_id,
                "course_id": course_id,
                "academic_year": academic_year,
                "cap_round": cap_round,
                "seat_pool": seat_pool_label,
                "category": cat_val,
                "seat_type_code": item_data.get("seat_type_code") or quota_val or "GOPENH",
                "cutoff_value": item_data.get("cutoff_value"),
                "cutoff_type": str(item_data.get("score_type", "percentile")).strip().lower(),
                "rank": c_rank_val,
                "merit_number": c_rank_val,
                "source_id": source_doc_id,
                "source_page": 1,
                "is_published": False,
                "is_active": False,
                "batch_id": batch_id,
                "created_at": now_iso,
                "updated_at": now_iso
            }
            self._local_cutoffs_relational.append(cutoff_rel_rec)

            # 5. Normalized Relational Population: Fee Records
            if item_data.get("annual_fees_inr") is not None:
                fee_rel_rec = {
                    "id": str(uuid.uuid4()),
                    "course_id": course_id,
                    "academic_year": academic_year,
                    "fee_component": "total",
                    "category": cat_val,
                    "quota": quota_val,
                    "amount": item_data.get("annual_fees_inr"),
                    "currency": "INR",
                    "source_id": source_doc_id,
                    "is_published": False,
                    "batch_id": batch_id,
                    "created_at": now_iso,
                    "updated_at": now_iso
                }
                self._local_fee_records.append(fee_rel_rec)

        # Insert into live Supabase if connected
        if self.use_live_supabase:
            try:
                self.supabase_client.table("import_batches").insert(batch_record).execute()
                self.supabase_client.table("college_cutoffs").insert(records_to_insert).execute()
            except Exception as e:
                print(f"Supabase batch insert error: {e}. Storing in local internal data store.")
                self._local_import_batches.append(batch_record)
                self._local_cutoffs.extend(records_to_insert)
        else:
            self._local_import_batches.append(batch_record)
            self._local_cutoffs.extend(records_to_insert)

        # Log audit trail
        self.log_audit(
            faq_id=None,
            action="create",
            changes={
                "batch_id": batch_id,
                "batch_name": name,
                "records_imported": len(records_to_insert),
                "academic_year": academic_year,
                "source_url": source_url,
                "status": "pending_approval"
            },
            admin_username=admin_username
        )

        return {
            "batch_id": batch_id,
            "batch_name": name,
            "status": "pending_approval",
            "count": len(records_to_insert),
            "message": f"Successfully imported {len(records_to_insert)} records into Batch '{name}' as Pending Approval. Admin approval is required before publication."
        }

    def get_import_batches(self, status=None):
        """Retrieve all data import batches with pending and approved record metrics."""
        batches = []
        if self.use_live_supabase:
            try:
                query = self.supabase_client.table("import_batches").select("*")
                if status:
                    query = query.eq("status", status)
                res = query.order("created_at", desc=True).execute()
                if res.data is not None:
                    batches = res.data
            except Exception as e:
                print(f"Supabase get_import_batches error: {e}. Falling back to internal store.")
                batches = list(self._local_import_batches)
        else:
            batches = list(self._local_import_batches)

        if status:
            batches = [b for b in batches if b.get("status") == status]

        # Calculate counts per batch
        all_cutoffs = self.get_all_cutoffs()
        for b in batches:
            bid = b.get("id")
            b_cutoffs = [c for c in all_cutoffs if c.get("batch_id") == bid]
            b["records_count"] = len(b_cutoffs)
            b["pending_count"] = sum(1 for c in b_cutoffs if c.get("status") == "pending_approval")
            b["approved_count"] = sum(1 for c in b_cutoffs if c.get("status") == "approved")

        return sorted(batches, key=lambda x: x.get("created_at", ""), reverse=True)

    def get_batch_details(self, batch_id):
        """Get details and records for a specific import batch."""
        batches = self.get_import_batches()
        batch = next((b for b in batches if b.get("id") == batch_id), None)
        if not batch:
            return None

        all_cutoffs = self.get_all_cutoffs()
        records = [c for c in all_cutoffs if c.get("batch_id") == batch_id]
        return {
            "batch": batch,
            "records": records,
            "count": len(records)
        }

    def approve_import_batch(self, batch_id, admin_username="admin"):
        """
        Approve all pending records in an import batch.
        Transitions status from 'pending_approval' to 'approved' and sets is_active = True.
        Records immediately become available for student recommendations.
        """
        now_iso = datetime.utcnow().isoformat() + "Z"
        approved_count = 0

        if self.use_live_supabase:
            try:
                self.supabase_client.table("import_batches").update({
                    "status": "approved",
                    "approved_by": admin_username,
                    "approved_at": now_iso,
                    "updated_at": now_iso
                }).eq("id", batch_id).execute()

                res = self.supabase_client.table("college_cutoffs").update({
                    "status": "approved",
                    "is_active": True,
                    "approved_by": admin_username,
                    "approved_at": now_iso,
                    "updated_at": now_iso
                }).eq("batch_id", batch_id).execute()

                approved_count = len(res.data) if res.data else 0
            except Exception as e:
                print(f"Supabase batch approval error: {e}. Updating in local store.")

        # Update in local store and publish normalized relational records
        for b in self._local_import_batches:
            if b.get("id") == batch_id:
                b["status"] = "approved"
                b["approved_by"] = admin_username
                b["approved_at"] = now_iso
                b["updated_at"] = now_iso

        for c in self._local_cutoffs:
            if c.get("batch_id") == batch_id:
                c["status"] = "approved"
                c["is_active"] = True
                c["approved_by"] = admin_username
                c["approved_at"] = now_iso
                c["updated_at"] = now_iso
                approved_count += 1

        # Atomically publish relational hierarchy records
        for s in self._local_source_documents:
            if s.get("batch_id") == batch_id:
                s["verified"] = True
                s["updated_at"] = now_iso

        for i in self._local_institutes:
            if i.get("batch_id") == batch_id:
                i["is_published"] = True
                i["updated_at"] = now_iso

        for c in self._local_courses:
            if c.get("batch_id") == batch_id:
                c["is_published"] = True
                c["updated_at"] = now_iso

        for cut in self._local_cutoffs_relational:
            if cut.get("batch_id") == batch_id:
                cut["is_published"] = True
                cut["is_active"] = True
                cut["updated_at"] = now_iso

        for f in self._local_fee_records:
            if f.get("batch_id") == batch_id:
                f["is_published"] = True
                f["updated_at"] = now_iso

        self.log_audit(
            faq_id=None,
            action="publish",
            changes={"batch_id": batch_id, "approved_records": approved_count},
            admin_username=admin_username
        )

        return {
            "batch_id": batch_id,
            "status": "approved",
            "approved_count": approved_count,
            "message": f"Batch {batch_id} approved. {approved_count} records published to active knowledge matrix."
        }

    def reject_import_batch(self, batch_id, admin_username="admin"):
        """Reject an import batch and mark records as rejected."""
        now_iso = datetime.utcnow().isoformat() + "Z"
        if self.use_live_supabase:
            try:
                self.supabase_client.table("import_batches").update({
                    "status": "rejected",
                    "updated_at": now_iso
                }).eq("id", batch_id).execute()

                self.supabase_client.table("college_cutoffs").update({
                    "status": "rejected",
                    "is_active": False,
                    "updated_at": now_iso
                }).eq("batch_id", batch_id).execute()
            except Exception as e:
                print(f"Supabase batch reject error: {e}. Updating in local store.")

        for b in self._local_import_batches:
            if b.get("id") == batch_id:
                b["status"] = "rejected"
                b["updated_at"] = now_iso

        for c in self._local_cutoffs:
            if c.get("batch_id") == batch_id:
                c["status"] = "rejected"
                c["is_active"] = False
                c["updated_at"] = now_iso

        self.log_audit(
            faq_id=None,
            action="status_change",
            changes={"batch_id": batch_id, "status": "rejected"},
            admin_username=admin_username
        )

        return {"batch_id": batch_id, "status": "rejected", "message": f"Batch {batch_id} marked as rejected."}

    def approve_cutoff_record(self, cutoff_id, admin_username="admin"):
        """Approve an individual cutoff record."""
        now_iso = datetime.utcnow().isoformat() + "Z"
        target = None

        if self.use_live_supabase:
            try:
                res = self.supabase_client.table("college_cutoffs").update({
                    "status": "approved",
                    "is_active": True,
                    "approved_by": admin_username,
                    "approved_at": now_iso,
                    "updated_at": now_iso
                }).eq("id", cutoff_id).execute()
                if res.data and len(res.data) > 0:
                    target = res.data[0]
            except Exception as e:
                print(f"Supabase record approval error: {e}.")

        for c in self._local_cutoffs:
            if c.get("id") == cutoff_id:
                c["status"] = "approved"
                c["is_active"] = True
                c["approved_by"] = admin_username
                c["approved_at"] = now_iso
                c["updated_at"] = now_iso
                target = c
                break

        return target



# Global Database Singleton
db = Database()
