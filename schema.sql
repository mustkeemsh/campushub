-- ============================================================================
-- CollegeHub: Smart College Inquiry and Assistance System
-- Comprehensive Normalized Relational Schema & Security Policies
-- ============================================================================
--
-- Core Relational Hierarchy:
--   source_documents (Official PDF/page URL, academic year, date checked, verification)
--       │
--       ├── institutes (College code, name, district, address, website, type)
--       │       │
--       │       ├── institute_contacts (Admissions phone/email and contact details)
--       │       │
--       │       ├── placement_stats (Highest, average, median CTC & placements)
--       │       │
--       │       ├── institute_amenities (Facilities & features mapped to institutes)
--       │       │
--       │       ├── faqs (Institutional knowledge base entries for AI Copilot)
--       │       │
--       │       └── courses (Course, branch, choice code, route, intake, year)
--       │               │
--       │               ├── cutoffs (Round, MH/AI/Diploma seat pool, category, cutoff value & type)
--       │               │
--       │               └── fee_records (Course fees by year, component, category/quota)
--       │
--       └── import_batches (Uploaded PDF/CSV audit metadata, status, row counts)
--
-- Key Rules:
-- 1. Preserve source seat label (MH, AI, Diploma) in cutoffs.seat_pool.
-- 2. Keep admission route (BTECH_FIRST_YEAR, BTECH_DSY, DIPLOMA_AFTER_SSC) in courses.admission_route.
-- 3. Recommendation engine evaluates candidate scores in memory without persisting student data.
-- 4. Row Level Security (RLS) ensures public users ONLY see published, verified records.
-- ============================================================================

-- 0. Required Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- 1. Source Documents Table (source_documents)
-- ============================================================================
-- Stores official provenance (PDF or web URL, academic year, check date, verification)
CREATE TABLE IF NOT EXISTS public.source_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    source_type TEXT DEFAULT 'GOVERNMENT_PORTAL', -- PDF, WEB_PAGE, GOVERNMENT_GAZETTE, NOTIFICATION
    source_url TEXT NOT NULL,
    academic_year TEXT,
    checked_at DATE,
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);



-- ============================================================================
-- 2. Institutes Table (institutes)
-- ============================================================================
-- College code, name, district, region, address, pincode, website, type, university
CREATE TABLE IF NOT EXISTS public.institutes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institute_code TEXT UNIQUE NOT NULL,
    institute_name TEXT NOT NULL,
    district TEXT,
    region TEXT,
    address TEXT,
    pincode TEXT,
    website TEXT,
    institute_type TEXT, -- State University, Government Autonomous, Private Autonomous, Centrally Funded
    university_name TEXT,
    source_id UUID REFERENCES public.source_documents(id) ON DELETE SET NULL,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);



-- ============================================================================
-- 3. Institute Contacts Table (institute_contacts)
-- ============================================================================
-- Admissions phone/email, counseling desk, and departmental contact points
CREATE TABLE IF NOT EXISTS public.institute_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institute_id UUID NOT NULL REFERENCES public.institutes(id) ON DELETE CASCADE,
    contact_type TEXT NOT NULL, -- admissions_phone, general_phone, email, counseling_desk
    contact_value TEXT NOT NULL,
    department TEXT,
    source_id UUID REFERENCES public.source_documents(id) ON DELETE SET NULL,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);



-- ============================================================================
-- 4. Courses Table (courses)
-- ============================================================================
-- Course, branch, choice code, admission route, intake capacity, academic year
-- Note: admission_route strictly isolates BTECH_FIRST_YEAR, BTECH_DSY, DIPLOMA_AFTER_SSC
CREATE TABLE IF NOT EXISTS public.courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institute_id UUID NOT NULL REFERENCES public.institutes(id) ON DELETE CASCADE,
    academic_year TEXT NOT NULL,
    admission_route TEXT NOT NULL, -- DIPLOMA_AFTER_SSC, BTECH_FIRST_YEAR, BTECH_DSY
    choice_code TEXT,
    course_name TEXT NOT NULL,
    branch TEXT,
    intake INTEGER,
    source_id UUID REFERENCES public.source_documents(id) ON DELETE SET NULL,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (academic_year, choice_code)
);

-- ============================================================================
-- 5. Cutoffs Table (cutoffs)
-- ============================================================================
-- Round, seat pool (MH, AI, Diploma), category, printed seat type code, cutoff value & type
-- Note: seat_pool preserves source label so Diploma quota is never conflated with DSY route
CREATE TABLE IF NOT EXISTS public.cutoffs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES public.courses(id) ON DELETE CASCADE,
    academic_year TEXT NOT NULL,
    cap_round INTEGER,
    seat_pool TEXT NOT NULL, -- keep the source label: MH, AI, Diploma, Home_Univ, Other_Than_Home
    category TEXT,
    seat_type_code TEXT, -- preserve the official code as printed: GOPENH, GOBCH, LOPENH, TFWS
    cutoff_value NUMERIC,
    cutoff_type TEXT, -- percentile, rank, merit_number, score, marks
    source_id UUID REFERENCES public.source_documents(id) ON DELETE SET NULL,
    source_page INTEGER,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);



-- ============================================================================
-- 6. Fee Records Table (fee_records)
-- ============================================================================
-- Course fees by year, fee component (tuition, development, total, hostel), category/quota
CREATE TABLE IF NOT EXISTS public.fee_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES public.courses(id) ON DELETE CASCADE,
    academic_year TEXT NOT NULL,
    fee_component TEXT NOT NULL, -- tuition, development, total, hostel
    category TEXT,
    quota TEXT,
    amount NUMERIC NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR',
    source_id UUID REFERENCES public.source_documents(id) ON DELETE SET NULL,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);



-- ============================================================================
-- 7. Placement Stats Table (placement_stats)
-- ============================================================================
-- Highest, average, median CTC and placements kept as separate metrics and years
CREATE TABLE IF NOT EXISTS public.placement_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institute_id UUID NOT NULL REFERENCES public.institutes(id) ON DELETE CASCADE,
    course_id UUID REFERENCES public.courses(id) ON DELETE SET NULL,
    academic_year TEXT NOT NULL,
    metric_type TEXT NOT NULL, -- highest, average, median
    amount NUMERIC NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR',
    students_placed INTEGER,
    total_students INTEGER,
    source_id UUID REFERENCES public.source_documents(id) ON DELETE SET NULL,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);



-- ============================================================================
-- 8. Amenities Master & Institute Amenities (amenities, institute_amenities)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.amenities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    category TEXT, -- academic, residential, sports, infrastructure, medical
    icon TEXT,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.institute_amenities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institute_id UUID NOT NULL REFERENCES public.institutes(id) ON DELETE CASCADE,
    amenity_id UUID NOT NULL REFERENCES public.amenities(id) ON DELETE CASCADE,
    details TEXT,
    source_id UUID REFERENCES public.source_documents(id) ON DELETE SET NULL,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (institute_id, amenity_id)
);

-- ============================================================================
-- 9. Admin Profiles & Users (admin_profiles, admin_users)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.admin_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(150),
    role VARCHAR(50) NOT NULL DEFAULT 'admin' CHECK (role IN ('superadmin', 'admin', 'editor')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);



CREATE TABLE IF NOT EXISTS public.admin_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    role TEXT NOT NULL DEFAULT 'admin',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Ensure is_active column exists if admin_users was previously created
ALTER TABLE public.admin_users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

-- ============================================================================
-- 10. Import Batches Table (import_batches)
-- ============================================================================
-- Tracks uploaded PDF/CSV file name, provenance, status, and validation counts
CREATE TABLE IF NOT EXISTS public.import_batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_name VARCHAR(150) NOT NULL,
    source_document_id UUID REFERENCES public.source_documents(id) ON DELETE SET NULL,
    source_url TEXT NOT NULL,
    academic_year TEXT NOT NULL,
    date_checked DATE NOT NULL,
    file_type TEXT DEFAULT 'CSV', -- CSV, PDF
    total_rows INTEGER NOT NULL DEFAULT 0,
    valid_rows INTEGER NOT NULL DEFAULT 0,
    error_rows INTEGER NOT NULL DEFAULT 0,
    duplicate_rows INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(30) NOT NULL DEFAULT 'pending_approval' CHECK (
        status IN ('pending_approval', 'approved', 'partially_approved', 'rejected')
    ),
    uploaded_by TEXT,
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    notes TEXT DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);



-- ============================================================================
-- 11. FAQs Knowledge Base Table (faqs)
-- ============================================================================
-- Verified answers for the college inquiry chatbot; links back to institute if specific
CREATE TABLE IF NOT EXISTS public.faqs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institute_id UUID REFERENCES public.institutes(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category TEXT NOT NULL CHECK (
        category IN (
            'admissions', 
            'courses', 
            'fees', 
            'cutoffs', 
            'placements', 
            'examinations', 
            'departments', 
            'facilities'
        )
    ),
    keywords TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'published' CHECK (
        status IN ('published', 'draft', 'archived', 'inactive')
    ),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    views_count INTEGER NOT NULL DEFAULT 0,
    upvotes_count INTEGER NOT NULL DEFAULT 0,
    source_id UUID REFERENCES public.source_documents(id) ON DELETE SET NULL,
    created_by UUID REFERENCES public.admin_profiles(id) ON DELETE SET NULL,
    updated_by UUID REFERENCES public.admin_profiles(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Ensure relational foreign keys and columns exist on faqs even if faqs was previously created
ALTER TABLE public.faqs ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE public.faqs ADD COLUMN IF NOT EXISTS institute_id UUID REFERENCES public.institutes(id) ON DELETE CASCADE;
ALTER TABLE public.faqs ADD COLUMN IF NOT EXISTS source_id UUID REFERENCES public.source_documents(id) ON DELETE SET NULL;
ALTER TABLE public.faqs ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES public.admin_profiles(id) ON DELETE SET NULL;
ALTER TABLE public.faqs ADD COLUMN IF NOT EXISTS updated_by UUID REFERENCES public.admin_profiles(id) ON DELETE SET NULL;



-- ============================================================================
-- 12. FAQ Audit Log (faq_audit_log)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.faq_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    faq_id UUID REFERENCES public.faqs(id) ON DELETE CASCADE,
    admin_id UUID REFERENCES public.admin_profiles(id) ON DELETE SET NULL,
    admin_username VARCHAR(100),
    action VARCHAR(50) NOT NULL CHECK (
        action IN ('create', 'update', 'status_change', 'publish', 'deactivate', 'delete')
    ),
    changes JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 13. Automatic updated_at Trigger
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_source_documents_updated_at ON public.source_documents;
CREATE TRIGGER trigger_source_documents_updated_at
    BEFORE UPDATE ON public.source_documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_institutes_updated_at ON public.institutes;
CREATE TRIGGER trigger_institutes_updated_at
    BEFORE UPDATE ON public.institutes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_institute_contacts_updated_at ON public.institute_contacts;
CREATE TRIGGER trigger_institute_contacts_updated_at
    BEFORE UPDATE ON public.institute_contacts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_courses_updated_at ON public.courses;
CREATE TRIGGER trigger_courses_updated_at
    BEFORE UPDATE ON public.courses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_cutoffs_updated_at ON public.cutoffs;
CREATE TRIGGER trigger_cutoffs_updated_at
    BEFORE UPDATE ON public.cutoffs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_fee_records_updated_at ON public.fee_records;
CREATE TRIGGER trigger_fee_records_updated_at
    BEFORE UPDATE ON public.fee_records
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_placement_stats_updated_at ON public.placement_stats;
CREATE TRIGGER trigger_placement_stats_updated_at
    BEFORE UPDATE ON public.placement_stats
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_faqs_updated_at ON public.faqs;
CREATE TRIGGER trigger_faqs_updated_at
    BEFORE UPDATE ON public.faqs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_import_batches_updated_at ON public.import_batches;
CREATE TRIGGER trigger_import_batches_updated_at
    BEFORE UPDATE ON public.import_batches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_admin_profiles_updated_at ON public.admin_profiles;
CREATE TRIGGER trigger_admin_profiles_updated_at
    BEFORE UPDATE ON public.admin_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 14. Performance Indexes for Relational Traversal
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_institutes_code ON public.institutes(institute_code);
CREATE INDEX IF NOT EXISTS idx_institutes_district ON public.institutes(district);
CREATE INDEX IF NOT EXISTS idx_institutes_published ON public.institutes(is_published);
CREATE INDEX IF NOT EXISTS idx_institute_contacts_inst ON public.institute_contacts(institute_id);
CREATE INDEX IF NOT EXISTS idx_courses_institute ON public.courses(institute_id);
CREATE INDEX IF NOT EXISTS idx_courses_route ON public.courses(admission_route);
CREATE INDEX IF NOT EXISTS idx_courses_branch ON public.courses(branch);
CREATE INDEX IF NOT EXISTS idx_courses_year ON public.courses(academic_year);
CREATE INDEX IF NOT EXISTS idx_cutoffs_course ON public.cutoffs(course_id);
CREATE INDEX IF NOT EXISTS idx_cutoffs_round_pool ON public.cutoffs(cap_round, seat_pool);
CREATE INDEX IF NOT EXISTS idx_cutoffs_category ON public.cutoffs(category);
CREATE INDEX IF NOT EXISTS idx_cutoffs_published ON public.cutoffs(is_published);
CREATE INDEX IF NOT EXISTS idx_fee_records_course ON public.fee_records(course_id);
CREATE INDEX IF NOT EXISTS idx_fee_records_comp ON public.fee_records(fee_component);
CREATE INDEX IF NOT EXISTS idx_placement_stats_inst ON public.placement_stats(institute_id);
CREATE INDEX IF NOT EXISTS idx_faqs_category ON public.faqs(category);
CREATE INDEX IF NOT EXISTS idx_faqs_institute ON public.faqs(institute_id);
CREATE INDEX IF NOT EXISTS idx_faqs_public_active ON public.faqs(status, is_active);
CREATE INDEX IF NOT EXISTS idx_import_batches_status ON public.import_batches(status);

-- ============================================================================
-- 15. Row Level Security (RLS) Configuration
-- ============================================================================
-- Enable RLS across every table
ALTER TABLE public.source_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.institutes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.institute_contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.courses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cutoffs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fee_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.placement_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.amenities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.institute_amenities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.faq_audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.admin_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.admin_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.import_batches ENABLE ROW LEVEL SECURITY;

-- ----------------------------------------------------------------------------
-- Public Visitors: Read Access to Checked & Published Records Only
-- ----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Public can view verified sources" ON public.source_documents;
CREATE POLICY "Public can view verified sources"
    ON public.source_documents FOR SELECT
    TO anon, authenticated
    USING (verified = TRUE);

DROP POLICY IF EXISTS "Public can view published institutes" ON public.institutes;
CREATE POLICY "Public can view published institutes"
    ON public.institutes FOR SELECT
    TO anon, authenticated
    USING (is_published = TRUE);

DROP POLICY IF EXISTS "Public can view published contacts" ON public.institute_contacts;
CREATE POLICY "Public can view published contacts"
    ON public.institute_contacts FOR SELECT
    TO anon, authenticated
    USING (is_published = TRUE);

DROP POLICY IF EXISTS "Public can view published courses" ON public.courses;
CREATE POLICY "Public can view published courses"
    ON public.courses FOR SELECT
    TO anon, authenticated
    USING (is_published = TRUE);

DROP POLICY IF EXISTS "Public can view published cutoffs" ON public.cutoffs;
CREATE POLICY "Public can view published cutoffs"
    ON public.cutoffs FOR SELECT
    TO anon, authenticated
    USING (is_published = TRUE);

DROP POLICY IF EXISTS "Public can view published fee records" ON public.fee_records;
CREATE POLICY "Public can view published fee records"
    ON public.fee_records FOR SELECT
    TO anon, authenticated
    USING (is_published = TRUE);

DROP POLICY IF EXISTS "Public can view published placement stats" ON public.placement_stats;
CREATE POLICY "Public can view published placement stats"
    ON public.placement_stats FOR SELECT
    TO anon, authenticated
    USING (is_published = TRUE);

DROP POLICY IF EXISTS "Public can view amenities master" ON public.amenities;
CREATE POLICY "Public can view amenities master"
    ON public.amenities FOR SELECT
    TO anon, authenticated
    USING (TRUE);

DROP POLICY IF EXISTS "Public can view published institute amenities" ON public.institute_amenities;
CREATE POLICY "Public can view published institute amenities"
    ON public.institute_amenities FOR SELECT
    TO anon, authenticated
    USING (is_published = TRUE);

DROP POLICY IF EXISTS "Public can view published active FAQs" ON public.faqs;
CREATE POLICY "Public can view published active FAQs"
    ON public.faqs FOR SELECT
    TO anon, authenticated
    USING (status = 'published' AND is_active = TRUE);

-- ----------------------------------------------------------------------------
-- Active Admins: Full Management Access
-- ----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Admins manage source documents" ON public.source_documents;
CREATE POLICY "Admins manage source documents"
    ON public.source_documents FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM public.admin_profiles WHERE user_id = auth.uid() AND is_active = TRUE))
    WITH CHECK (EXISTS (SELECT 1 FROM public.admin_profiles WHERE user_id = auth.uid() AND is_active = TRUE));

DROP POLICY IF EXISTS "Admins manage institutes" ON public.institutes;
CREATE POLICY "Admins manage institutes"
    ON public.institutes FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM public.admin_profiles WHERE user_id = auth.uid() AND is_active = TRUE))
    WITH CHECK (EXISTS (SELECT 1 FROM public.admin_profiles WHERE user_id = auth.uid() AND is_active = TRUE));

DROP POLICY IF EXISTS "Admins manage contacts" ON public.institute_contacts;
CREATE POLICY "Admins manage contacts"
    ON public.institute_contacts FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM public.admin_profiles WHERE user_id = auth.uid() AND is_active = TRUE))
    WITH CHECK (EXISTS (SELECT 1 FROM public.admin_profiles WHERE user_id = auth.uid() AND is_active = TRUE));

DROP POLICY IF EXISTS "Admins manage courses" ON public.courses;
CREATE POLICY "Admins manage courses"
    ON public.courses FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM public.admin_profiles WHERE user_id = auth.uid() AND is_active = TRUE))
    WITH CHECK (EXISTS (SELECT 1 FROM public.admin_profiles WHERE user_id = auth.uid() AND is_active = TRUE));

DROP POLICY IF EXISTS "Admins manage cutoffs" ON public.cutoffs;
CREATE POLICY "Admins manage cutoffs"
    ON public.cutoffs FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM public.admin_profiles WHERE user_id = auth.uid() AND is_active = TRUE))
    WITH CHECK (EXISTS (SELECT 1 FROM public.admin_profiles WHERE user_id = auth.uid() AND is_active = TRUE));

DROP POLICY IF EXISTS "Admins manage fee records" ON public.fee_records;
CREATE POLICY "Admins manage fee records"
    ON public.fee_records FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM public.admin_profiles WHERE user_id = auth.uid() AND is_active = TRUE))
    WITH CHECK (EXISTS (SELECT 1 FROM public.admin_profiles WHERE user_id = auth.uid() AND is_active = TRUE));

DROP POLICY IF EXISTS "Admins manage placement stats" ON public.placement_stats;
CREATE POLICY "Admins manage placement stats"
    ON public.placement_stats FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM public.admin_profiles WHERE user_id = auth.uid() AND is_active = TRUE))
    WITH CHECK (EXISTS (SELECT 1 FROM public.admin_profiles WHERE user_id = auth.uid() AND is_active = TRUE));

DROP POLICY IF EXISTS "Admins manage amenities" ON public.amenities;
CREATE POLICY "Admins manage amenities"
    ON public.amenities FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM public.admin_profiles WHERE user_id = auth.uid() AND is_active = TRUE))
    WITH CHECK (EXISTS (SELECT 1 FROM public.admin_profiles WHERE user_id = auth.uid() AND is_active = TRUE));

DROP POLICY IF EXISTS "Admins manage institute amenities" ON public.institute_amenities;
CREATE POLICY "Admins manage institute amenities"
    ON public.institute_amenities FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM public.admin_profiles WHERE user_id = auth.uid() AND is_active = TRUE))
    WITH CHECK (EXISTS (SELECT 1 FROM public.admin_profiles WHERE user_id = auth.uid() AND is_active = TRUE));

DROP POLICY IF EXISTS "Admins manage faqs" ON public.faqs;
CREATE POLICY "Admins manage faqs"
    ON public.faqs FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM public.admin_profiles WHERE user_id = auth.uid() AND is_active = TRUE))
    WITH CHECK (EXISTS (SELECT 1 FROM public.admin_profiles WHERE user_id = auth.uid() AND is_active = TRUE));

DROP POLICY IF EXISTS "Admins manage import batches" ON public.import_batches;
CREATE POLICY "Admins manage import batches"
    ON public.import_batches FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM public.admin_profiles WHERE user_id = auth.uid() AND is_active = TRUE))
    WITH CHECK (EXISTS (SELECT 1 FROM public.admin_profiles WHERE user_id = auth.uid() AND is_active = TRUE));

DROP POLICY IF EXISTS "Admins view audit logs" ON public.faq_audit_log;
CREATE POLICY "Admins view audit logs"
    ON public.faq_audit_log FOR SELECT TO authenticated
    USING (EXISTS (SELECT 1 FROM public.admin_profiles WHERE user_id = auth.uid() AND is_active = TRUE));

-- ----------------------------------------------------------------------------
-- Service Role: Full Unrestricted Access (Used by Flask backend)
-- ----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Service role access source_documents" ON public.source_documents;
CREATE POLICY "Service role access source_documents" ON public.source_documents FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);

DROP POLICY IF EXISTS "Service role access institutes" ON public.institutes;
CREATE POLICY "Service role access institutes" ON public.institutes FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);

DROP POLICY IF EXISTS "Service role access institute_contacts" ON public.institute_contacts;
CREATE POLICY "Service role access institute_contacts" ON public.institute_contacts FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);

DROP POLICY IF EXISTS "Service role access courses" ON public.courses;
CREATE POLICY "Service role access courses" ON public.courses FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);

DROP POLICY IF EXISTS "Service role access cutoffs" ON public.cutoffs;
CREATE POLICY "Service role access cutoffs" ON public.cutoffs FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);

DROP POLICY IF EXISTS "Service role access fee_records" ON public.fee_records;
CREATE POLICY "Service role access fee_records" ON public.fee_records FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);

DROP POLICY IF EXISTS "Service role access placement_stats" ON public.placement_stats;
CREATE POLICY "Service role access placement_stats" ON public.placement_stats FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);

DROP POLICY IF EXISTS "Service role access amenities" ON public.amenities;
CREATE POLICY "Service role access amenities" ON public.amenities FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);

DROP POLICY IF EXISTS "Service role access institute_amenities" ON public.institute_amenities;
CREATE POLICY "Service role access institute_amenities" ON public.institute_amenities FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);

DROP POLICY IF EXISTS "Service role access faqs" ON public.faqs;
CREATE POLICY "Service role access faqs" ON public.faqs FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);

DROP POLICY IF EXISTS "Service role access import_batches" ON public.import_batches;
CREATE POLICY "Service role access import_batches" ON public.import_batches FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);

DROP POLICY IF EXISTS "Service role access admin_profiles" ON public.admin_profiles;
CREATE POLICY "Service role access admin_profiles" ON public.admin_profiles FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);

DROP POLICY IF EXISTS "Service role access admin_users" ON public.admin_users;
CREATE POLICY "Service role access admin_users" ON public.admin_users FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);

DROP POLICY IF EXISTS "Service role access faq_audit_log" ON public.faq_audit_log;
CREATE POLICY "Service role access faq_audit_log" ON public.faq_audit_log FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);


-- ============================================================================
-- 16. Seed Data: Comprehensive Relational Hierarchy
-- ============================================================================

-- 16.1 Official Source Documents
INSERT INTO public.source_documents (id, title, source_type, source_url, academic_year, checked_at, verified, notes)
VALUES
    ('d0000000-0000-0000-0000-000000000001', 'State Common Entrance Test Cell Maharashtra - CAP 2024 Final Cutoff Matrix', 'GOVERNMENT_PORTAL', 'https://fe2024.mahacet.org/StaticPages/HomePage', '2024-2025', '2024-08-26', TRUE, 'Official CAP Round 1, 2, and 3 engineering cutoff allotments.'),
    ('d0000000-0000-0000-0000-000000000002', 'Fee Regulating Authority (FRA) Maharashtra - Higher & Technical Education Fee Structure', 'GOVERNMENT_GAZETTE', 'https://sssamiti.org/fee_structure_2024_25.html', '2024-2025', '2024-08-20', TRUE, 'Approved interim and final tuition and development fee scales.'),
    ('d0000000-0000-0000-0000-000000000003', 'Joint Seat Allocation Authority (JoSAA) 2024 - Round 5 Opening & Closing Ranks', 'GOVERNMENT_PORTAL', 'https://josaa.nic.in/result/round5-cutoff-2024.pdf', '2024-2025', '2024-07-28', TRUE, 'NIT and CFTI centralized seat allotments.')
ON CONFLICT (id) DO NOTHING;

-- 16.2 Amenities Master List
INSERT INTO public.amenities (id, name, category, icon, description)
VALUES
    ('a0000000-0000-0000-0000-000000000001', 'High-Speed Campus Wi-Fi', 'infrastructure', 'wifi', 'Gigabit optic fiber connectivity across academic blocks and dorms.'),
    ('a0000000-0000-0000-0000-000000000002', 'AI & High Performance GPU Computing Cluster', 'academic', 'memory', 'Dedicated NVIDIA cluster for machine learning research.'),
    ('a0000000-0000-0000-0000-000000000003', 'On-Campus Residential Hostels', 'residential', 'bed', 'Separate boys and girls residential blocks with mess dining.'),
    ('a0000000-0000-0000-0000-000000000004', 'Central Academic Library (24/7 Exams)', 'academic', 'local_library', 'Extensive digital library with IEEE, ACM, Springer access.'),
    ('a0000000-0000-0000-0000-000000000005', 'Indoor & Outdoor Sports Complex', 'sports', 'fitness_center', 'Gymnasiums, badminton arenas, and synthetic running tracks.')
ON CONFLICT (name) DO NOTHING;

-- 16.3 Institutes
INSERT INTO public.institutes (id, institute_code, institute_name, district, region, address, pincode, website, institute_type, university_name, source_id, is_published)
VALUES
    ('10000000-0000-0000-0000-000000006006', '6006', 'COEP Technological University', 'Pune', 'Western Maharashtra', 'Wellesely Road, Shivajinagar, Pune', '411005', 'https://www.coep.org.in', 'State University & Autonomous Institute', 'COEP Technological University', 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('10000000-0000-0000-0000-000000003012', '3012', 'Veermata Jijabai Technological Institute (VJTI)', 'Mumbai Suburban', 'Konkan', 'H R Mahajani Marg, Matunga, Mumbai', '400019', 'https://vjti.ac.in', 'State Government Autonomous Institute', 'University of Mumbai', 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('10000000-0000-0000-0000-000000006271', '6271', 'Pune Institute of Computer Technology (PICT)', 'Pune', 'Western Maharashtra', 'Survey No. 27, Near Trimurti Chowk, Dhankawadi, Pune', '411043', 'https://pict.edu', 'Private Autonomous Institute', 'Savitribai Phule Pune University', 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('10000000-0000-0000-0000-000000006273', '6273', 'Vishwakarma Institute of Technology (VIT)', 'Pune', 'Western Maharashtra', '666, Upper Indiranagar, Bibwewadi, Pune', '411037', 'https://www.vit.edu', 'Private Autonomous Engineering College', 'Savitribai Phule Pune University', 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('10000000-0000-0000-0000-000000006175', '6175', 'Pimpri Chinchwad College of Engineering (PCCOE)', 'Pune', 'Western Maharashtra', 'Sector 26, Pradhikaran, Nigdi, Pune', '411044', 'https://www.pccoepune.com', 'Private Autonomous Engineering College', 'Savitribai Phule Pune University', 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('10000000-0000-0000-0000-000000006007', '6007', 'Walchand College of Engineering (WCE)', 'Sangli', 'Western Maharashtra', 'Vishrambag, Sangli', '416415', 'https://www.walchandsangli.ac.in', 'Government-Aided Autonomous Institute', 'Shivaji University', 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('10000000-0000-0000-0000-000000000007', 'NITK', 'National Institute of Technology Karnataka, Surathkal', 'Dakshina Kannada', 'Coastal Karnataka', 'NH 66, Srinivasnagar, Surathkal, Mangalore', '575025', 'https://www.nitk.ac.in', 'Institute of National Importance (Centrally Funded)', 'Autonomous NIT Council', 'd0000000-0000-0000-0000-000000000003', TRUE),
    ('10000000-0000-0000-0000-000000000008', 'VNIT', 'Visvesvaraya National Institute of Technology, Nagpur', 'Nagpur', 'Vidarbha', 'South Ambazari Road, Nagpur', '440010', 'https://vnit.ac.in', 'Institute of National Importance (Centrally Funded)', 'Autonomous NIT Council', 'd0000000-0000-0000-0000-000000000003', TRUE)
ON CONFLICT (institute_code) DO NOTHING;

-- 16.4 Institute Contacts
INSERT INTO public.institute_contacts (institute_id, contact_type, contact_value, department, source_id, is_published)
VALUES
    ('10000000-0000-0000-0000-000000006006', 'admissions_phone', '+91-20-25507000', 'Central Admissions Cell', 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('10000000-0000-0000-0000-000000006006', 'email', 'admissions@coep.ac.in', 'Admissions Desk', 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('10000000-0000-0000-0000-000000003012', 'admissions_phone', '+91-22-24198101', 'Admissions Office Matunga', 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('10000000-0000-0000-0000-000000006271', 'admissions_phone', '+91-20-24371101', 'PICT Student Affairs', 'd0000000-0000-0000-0000-000000000001', TRUE)
ON CONFLICT DO NOTHING;

-- 16.5 Institute Amenities Mapping
INSERT INTO public.institute_amenities (institute_id, amenity_id, details, source_id, is_published)
VALUES
    ('10000000-0000-0000-0000-000000006006', 'a0000000-0000-0000-0000-000000000001', 'Campus-wide Wi-Fi across academic quads.', 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('10000000-0000-0000-0000-000000006006', 'a0000000-0000-0000-0000-000000000003', 'Hostel capacity of 2,400 students by entrance merit.', 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('10000000-0000-0000-0000-000000006006', 'a0000000-0000-0000-0000-000000000004', 'Historic heritage central library open 24/7 during CAP reporting.', 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('10000000-0000-0000-0000-000000003012', 'a0000000-0000-0000-0000-000000000003', 'Hostel available for outside-Mumbai merit candidates.', 'd0000000-0000-0000-0000-000000000001', TRUE)
ON CONFLICT DO NOTHING;

-- 16.6 Courses
-- Note: admission_route is strictly separated from seat quota labels
INSERT INTO public.courses (id, institute_id, academic_year, admission_route, choice_code, course_name, branch, intake, source_id, is_published)
VALUES
    ('c0000000-0000-0000-0000-000000006001', '10000000-0000-0000-0000-000000006006', '2024-2025', 'BTECH_FIRST_YEAR', '600624510', 'B.Tech in Computer Science & Engineering', 'CSE', 150, 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('c0000000-0000-0000-0000-000000006002', '10000000-0000-0000-0000-000000006006', '2024-2025', 'BTECH_FIRST_YEAR', '600626310', 'B.Tech in Artificial Intelligence & Data Science', 'AIDS', 60, 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('c0000000-0000-0000-0000-000000003001', '10000000-0000-0000-0000-000000003012', '2024-2025', 'BTECH_FIRST_YEAR', '301224510', 'B.Tech in Computer Science & Engineering', 'CSE', 120, 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('c0000000-0000-0000-0000-000000006201', '10000000-0000-0000-0000-000000006271', '2024-2025', 'BTECH_FIRST_YEAR', '627124510', 'B.Tech in Computer Science & Engineering', 'CSE', 240, 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('c0000000-0000-0000-0000-000000006273', '10000000-0000-0000-0000-000000006273', '2024-2025', 'BTECH_FIRST_YEAR', '627326310', 'B.Tech in Artificial Intelligence & Data Science', 'AIDS', 180, 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('c0000000-0000-0000-0000-000000006175', '10000000-0000-0000-0000-000000006175', '2024-2025', 'BTECH_FIRST_YEAR', '617524510', 'B.Tech in Computer Science & Engineering', 'CSE', 240, 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('c0000000-0000-0000-0000-000000006007', '10000000-0000-0000-0000-000000006007', '2024-2025', 'BTECH_FIRST_YEAR', '600724510', 'B.Tech in Computer Science & Engineering', 'CSE', 120, 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('c0000000-0000-0000-0000-000000000007', '10000000-0000-0000-0000-000000000007', '2024-2025', 'BTECH_FIRST_YEAR', 'NITK-CSE-01', 'B.Tech in Computer Science & Engineering', 'CSE', 115, 'd0000000-0000-0000-0000-000000000003', TRUE),
    ('c0000000-0000-0000-0000-000000000008', '10000000-0000-0000-0000-000000000008', '2024-2025', 'BTECH_FIRST_YEAR', 'VNIT-CSE-01', 'B.Tech in Computer Science & Engineering', 'CSE', 115, 'd0000000-0000-0000-0000-000000000003', TRUE)
ON CONFLICT (academic_year, choice_code) DO NOTHING;

-- 16.7 Cutoffs
-- Note: seat_pool preserves source label (MH, AI, Diploma)
INSERT INTO public.cutoffs (course_id, academic_year, cap_round, seat_pool, category, seat_type_code, cutoff_value, cutoff_type, source_id, is_published)
VALUES
    ('c0000000-0000-0000-0000-000000006001', '2024-2025', 2, 'MH', 'OPEN', 'GOPENH', 99.8512, 'percentile', 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('c0000000-0000-0000-0000-000000006001', '2024-2025', 2, 'MH', 'OBC-NCL', 'GOBCH', 99.7204, 'percentile', 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('c0000000-0000-0000-0000-000000006002', '2024-2025', 2, 'MH', 'OPEN', 'GOPENH', 99.6410, 'percentile', 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('c0000000-0000-0000-0000-000000003001', '2024-2025', 2, 'MH', 'OPEN', 'GOPENH', 99.8820, 'percentile', 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('c0000000-0000-0000-0000-000000006201', '2024-2025', 2, 'MH', 'OPEN', 'GOPENH', 99.5200, 'percentile', 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('c0000000-0000-0000-0000-000000006273', '2024-2025', 2, 'MH', 'OPEN', 'GOPENH', 98.4200, 'percentile', 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('c0000000-0000-0000-0000-000000006175', '2024-2025', 2, 'MH', 'OPEN', 'GOPENH', 98.2400, 'percentile', 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('c0000000-0000-0000-0000-000000006007', '2024-2025', 2, 'MH', 'OPEN', 'GOPENH', 99.1800, 'percentile', 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('c0000000-0000-0000-0000-000000000007', '2024-2025', 5, 'AI', 'OPEN', 'OPEN', 3406, 'rank', 'd0000000-0000-0000-0000-000000000003', TRUE),
    ('c0000000-0000-0000-0000-000000000008', '2024-2025', 5, 'AI', 'OPEN', 'OPEN', 7850, 'rank', 'd0000000-0000-0000-0000-000000000003', TRUE)
ON CONFLICT DO NOTHING;

-- 16.8 Fee Records
INSERT INTO public.fee_records (course_id, academic_year, fee_component, category, quota, amount, currency, source_id, is_published)
VALUES
    ('c0000000-0000-0000-0000-000000006001', '2024-2025', 'total', 'OPEN', 'SL', 92000, 'INR', 'd0000000-0000-0000-0000-000000000002', TRUE),
    ('c0000000-0000-0000-0000-000000006001', '2024-2025', 'total', 'OBC-NCL', 'SL', 52000, 'INR', 'd0000000-0000-0000-0000-000000000002', TRUE),
    ('c0000000-0000-0000-0000-000000003001', '2024-2025', 'total', 'OPEN', 'SL', 88500, 'INR', 'd0000000-0000-0000-0000-000000000002', TRUE),
    ('c0000000-0000-0000-0000-000000006201', '2024-2025', 'total', 'OPEN', 'HU', 110000, 'INR', 'd0000000-0000-0000-0000-000000000002', TRUE),
    ('c0000000-0000-0000-0000-000000006273', '2024-2025', 'total', 'OPEN', 'HU', 195000, 'INR', 'd0000000-0000-0000-0000-000000000002', TRUE),
    ('c0000000-0000-0000-0000-000000006175', '2024-2025', 'total', 'OPEN', 'HU', 142000, 'INR', 'd0000000-0000-0000-0000-000000000002', TRUE),
    ('c0000000-0000-0000-0000-000000000007', '2024-2025', 'total', 'OPEN', 'AI', 155000, 'INR', 'd0000000-0000-0000-0000-000000000003', TRUE),
    ('c0000000-0000-0000-0000-000000000008', '2024-2025', 'total', 'OPEN', 'AI', 148000, 'INR', 'd0000000-0000-0000-0000-000000000003', TRUE)
ON CONFLICT DO NOTHING;

-- 16.9 Placement Stats
INSERT INTO public.placement_stats (institute_id, course_id, academic_year, metric_type, amount, currency, students_placed, total_students, source_id, is_published)
VALUES
    ('10000000-0000-0000-0000-000000006006', 'c0000000-0000-0000-0000-000000006001', '2023-2024', 'highest', 5050000, 'INR', 142, 150, 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('10000000-0000-0000-0000-000000006006', 'c0000000-0000-0000-0000-000000006001', '2023-2024', 'average', 1820000, 'INR', 142, 150, 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('10000000-0000-0000-0000-000000006006', 'c0000000-0000-0000-0000-000000006001', '2023-2024', 'median', 1600000, 'INR', 142, 150, 'd0000000-0000-0000-0000-000000000001', TRUE),
    ('10000000-0000-0000-0000-000000003012', 'c0000000-0000-0000-0000-000000003001', '2023-2024', 'average', 1780000, 'INR', 115, 120, 'd0000000-0000-0000-0000-000000000001', TRUE)
ON CONFLICT DO NOTHING;

-- 16.10 Knowledge Base FAQs (Linking back to Institute or General Process)
INSERT INTO public.faqs (question, answer, category, keywords, status, is_active, views_count, upvotes_count) 
SELECT 
    'What documents are needed for admission?',
    'Candidates accepted through the Centralized Seat Allotment portal must bring physical originals and two sets of self-attested photocopies during reporting: 1) 10th & 12th Board Marksheets & Passing Certificates; 2) National Entrance Exam Scorecard & Admit Card; 3) School Leaving & Transfer Certificate from the previous institution; 4) Valid Government Photo ID (Passport / National ID) and 6 recent passport-size color photographs; 5) Category / Reservation certificate (OBC-NCL / EWS / SC / ST) issued for the current financial cycle if applicable.',
    'admissions',
    'documents, admission verification, marksheets, transfer certificate, id proof, eligibility',
    'published',
    TRUE,
    1842,
    248
WHERE NOT EXISTS (SELECT 1 FROM public.faqs WHERE question = 'What documents are needed for admission?');

INSERT INTO public.faqs (question, answer, category, keywords, status, is_active, views_count, upvotes_count) 
SELECT 
    'What is the undergraduate application deadline for Fall 2025/2026?',
    'Applications operate under a rolling phased timeline. Early Action Priority submissions conclude on November 15, 2024 (decisions released December 20). Regular applications close on January 15, 2025 (decisions released March 15). Late submissions are reviewed based on department seat vacancies through July 15.',
    'admissions',
    'application deadline, early action, regular admission, dates, schedule, reporting',
    'published',
    TRUE,
    1240,
    184
WHERE NOT EXISTS (SELECT 1 FROM public.faqs WHERE question = 'What is the undergraduate application deadline for Fall 2025/2026?');

INSERT INTO public.faqs (question, answer, category, keywords, status, is_active, views_count, upvotes_count) 
SELECT 
    'Can undergraduate students change their branch or major after the first year?',
    'Yes, branch migration is permitted at the conclusion of Semester 2, subject to vacancy availability and the following criteria: 1) Minimum CGPA: maintain a cumulative GPA of >= 8.25 (or 3.8/4.0) across first-year courses with zero academic backlogs; 2) Sanctioned Intake Cap: the parent branch strength cannot drop below 75% of sanctioned capacity. Petitions must be submitted within 7 days of Semester 2 results.',
    'courses',
    'change major, branch transfer, curriculum switch, cgpa requirement, engineering branches',
    'published',
    TRUE,
    980,
    156
WHERE NOT EXISTS (SELECT 1 FROM public.faqs WHERE question = 'Can undergraduate students change their branch or major after the first year?');

INSERT INTO public.faqs (question, answer, category, keywords, status, is_active, views_count, upvotes_count) 
SELECT 
    'Can engineering students pursue a minor in Business, AI, or Design?',
    'Yes, undergraduate students in good academic standing can register for an interdisciplinary Minor Specialization by completing 18 additional credits between Semesters 3 and 7. Approved minor tracks include Artificial Intelligence & Data Systems, Financial Technologies, Product Design, and Renewable Energy Systems.',
    'courses',
    'minor degree, electives, interdisciplinary, artificial intelligence, finance, credits',
    'published',
    TRUE,
    820,
    128
WHERE NOT EXISTS (SELECT 1 FROM public.faqs WHERE question = 'Can engineering students pursue a minor in Business, AI, or Design?');

INSERT INTO public.faqs (question, answer, category, keywords, status, is_active, views_count, upvotes_count) 
SELECT 
    'How do I apply for tuition fee waivers or need-based scholarships?',
    'Merit-cum-means waivers are awarded every academic year. Applications open during the first three weeks of each semester via the Student Financial Aid Portal. Merit Tier (100% waiver) requires top 5% entrance rank and CGPA >= 3.80. Need-Based Tier (25% to 75% waiver) requires verified annual household income under $30,000 (or regional equivalent). Fall applications close August 15, 2025.',
    'fees',
    'fee waiver, scholarship, financial aid, tuition, need-based, merit grant, bursar',
    'published',
    TRUE,
    1530,
    192
WHERE NOT EXISTS (SELECT 1 FROM public.faqs WHERE question = 'How do I apply for tuition fee waivers or need-based scholarships?');

INSERT INTO public.faqs (question, answer, category, keywords, status, is_active, views_count, upvotes_count) 
SELECT 
    'Can semester tuition fees be paid in flexible monthly installments?',
    'Yes, the Bursar Office provides a 3-part deferred installment plan per semester with zero interest. 40% is due at course registration, 30% by mid-term examination week, and the remaining 30% prior to final examination hall ticket release. Apply via the Student Finance Desk before registration closes.',
    'fees',
    'fee payment, installments, bursar, payment plan, tuition deadline, finance',
    'published',
    TRUE,
    1110,
    142
WHERE NOT EXISTS (SELECT 1 FROM public.faqs WHERE question = 'Can semester tuition fees be paid in flexible monthly installments?');

INSERT INTO public.faqs (question, answer, category, keywords, status, is_active, views_count, upvotes_count) 
SELECT 
    'What were the opening and closing cutoffs for Computer Engineering in 2024?',
    'Centralized allotment outcomes for Computer Science and Engineering closed as follows: State General Merit Round 1 closed at 99.85 percentile (SMLR Rank #210); Round 2 closed at 99.64 percentile (Rank #342); Round 3 final spot round closed at 99.45 percentile. Category quotas (OBC/EWS/SC/ST) and domicile reservation seats closed between 96.20 and 99.10 percentile.',
    'cutoffs',
    'cutoffs, closing rank, computer science, mht-cet, percentile, opening rank, merit list',
    'published',
    TRUE,
    2450,
    312
WHERE NOT EXISTS (SELECT 1 FROM public.faqs WHERE question = 'What were the opening and closing cutoffs for Computer Engineering in 2024?');

INSERT INTO public.faqs (question, answer, category, keywords, status, is_active, views_count, upvotes_count) 
SELECT 
    'What was the median placement CTC and top hiring partners for the class of 2024?',
    'The 2023-2024 graduating cohort attained a 94.6% placement rate across 180 visiting hiring partners. Key metrics: Highest International Package: $148,000 USD (Software Infrastructure); Highest Domestic Package: 52.5 LPA; Overall Cohort Average CTC: 14.8 LPA; Engineering Median CTC: 12.4 LPA. Top recruiters included Google, Microsoft, Amazon AWS, Barclays, Texas Instruments, and Nvidia.',
    'placements',
    'placements, ctc, highest package, average package, companies, recruiters, statistics',
    'published',
    TRUE,
    3120,
    440
WHERE NOT EXISTS (SELECT 1 FROM public.faqs WHERE question = 'What was the median placement CTC and top hiring partners for the class of 2024?');

INSERT INTO public.faqs (question, answer, category, keywords, status, is_active, views_count, upvotes_count) 
SELECT 
    'What is the academic semester grading policy and relative GPA scale?',
    'Academics operate on a 10-point Letter Grade Scale: Outstanding (O, 10.0, >=90%), Excellent (A+, 9.0, 80-89%), Very Good (A, 8.0, 70-79%), Good (B+, 7.0, 60-69%), Above Average (B, 6.0, 50-59%), Pass (C, 5.0, 40-49%), and Fail (F, 0.0, <40%). Relative grading applies to core courses with enrollments exceeding 60 students.',
    'examinations',
    'grading scale, relative grading, gpa calculation, gpa, examination rules, credits',
    'published',
    TRUE,
    890,
    112
WHERE NOT EXISTS (SELECT 1 FROM public.faqs WHERE question = 'What is the academic semester grading policy and relative GPA scale?');

INSERT INTO public.faqs (question, answer, category, keywords, status, is_active, views_count, upvotes_count) 
SELECT 
    'What are the rules, amenities, and curfew hours for campus residential hostels?',
    'Campus hostels provide biometric access and 24/7 security. Standard curfew for undergraduate freshmen is 10:00 PM on weekdays and 11:00 PM on weekends. Late entry requests must be logged through the Student Portal 12 hours in advance. Amenities include gigabit Wi-Fi, 4 dining meal plans, laundromats, indoor gymnasiums, and quiet floor study halls.',
    'facilities',
    'hostel, dorms, curfew, accommodation, dining mess, wifi, laundry, residential',
    'published',
    TRUE,
    1670,
    204
WHERE NOT EXISTS (SELECT 1 FROM public.faqs WHERE question = 'What are the rules, amenities, and curfew hours for campus residential hostels?');

INSERT INTO public.faqs (question, answer, category, keywords, status, is_active, views_count, upvotes_count) 
SELECT 
    'What are the central library hours and research lab computing facilities?',
    'The Central Academic Library is open from 7:00 AM to midnight on weekdays, and operates 24/7 during midterm and final examination weeks. Facilities include 400+ study carrels, high-performance GPU workstations for AI/ML modeling, collaborative presentation rooms, and digital access to IEEE, ACM, Springer, and JSTOR repositories.',
    'facilities',
    'library, computer labs, research facilities, study rooms, jstor, ieee, timings',
    'published',
    TRUE,
    1280,
    167
WHERE NOT EXISTS (SELECT 1 FROM public.faqs WHERE question = 'What are the central library hours and research lab computing facilities?');