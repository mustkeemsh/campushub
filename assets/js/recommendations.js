/**
 * CollegeHub - College Recommendation & Cutoff Matching Engine
 * 
 * Part of Student Profile -> College Recommendations Flow.
 * Strictly separates recommendation logic and data from UI components.
 * Ready to connect with Flask backend and Supabase.
 */

(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.CollegeHubRecommender = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {

  // =========================================================================
  // 1. Entrance Exam & Admission Configurations
  // =========================================================================
  const EXAM_CONFIGS = {
    'MHT-CET': {
      code: 'MHT-CET',
      name: 'Maharashtra Common Entrance Test (MHT-CET)',
      supportedScoreTypes: ['percentile', 'rank'],
      defaultScoreType: 'percentile',
      scoreRanges: {
        percentile: { min: 0.0, max: 100.0, step: 0.0001, unit: '%', hint: 'Enter normalized CET percentile (e.g., 97.8540)' },
        rank: { min: 1, max: 200000, step: 1, unit: 'Rank', hint: 'Enter General State Merit List Rank (SMLR)' }
      },
      categories: [
        { code: 'OPEN', label: 'OPEN / General (GOPEN)' },
        { code: 'OBC-NCL', label: 'Other Backward Class (OBC-NCL)' },
        { code: 'EWS', label: 'Economically Weaker Section (EWS - 10%)' },
        { code: 'SC', label: 'Scheduled Caste (SC)' },
        { code: 'ST', label: 'Scheduled Tribe (ST)' },
        { code: 'TFWS', label: 'Tuition Fee Waiver Scheme (TFWS - 5%)' },
        { code: 'VJNT', label: 'VJ / NT (A/B/C/D Categories)' }
      ],
      quotas: [
        { code: 'HU', label: 'Home University Quota (GOPENH / GOBCH)' },
        { code: 'OHU', label: 'Other than Home University (GOPENO)' },
        { code: 'SL', label: 'State Level Quota (Autonomous Institutes)' }
      ],
      defaultState: 'Maharashtra'
    },
    'JEE-Main': {
      code: 'JEE-Main',
      name: 'Joint Entrance Examination (JEE Main)',
      supportedScoreTypes: ['percentile', 'rank'],
      defaultScoreType: 'rank',
      scoreRanges: {
        percentile: { min: 0.0, max: 100.0, step: 0.0001, unit: '%', hint: 'NTA Total Score / Percentile (e.g., 98.4210)' },
        rank: { min: 1, max: 1500000, step: 1, unit: 'AIR', hint: 'All India CRL or Category Rank' }
      },
      categories: [
        { code: 'OPEN', label: 'OPEN / General (CRL)' },
        { code: 'EWS', label: 'GEN-EWS' },
        { code: 'OBC-NCL', label: 'OBC-NCL (Central List)' },
        { code: 'SC', label: 'Scheduled Caste (SC)' },
        { code: 'ST', label: 'Scheduled Tribe (ST)' }
      ],
      quotas: [
        { code: 'AI', label: 'All India Quota (AI)' },
        { code: 'HS', label: 'Home State Quota (HS)' },
        { code: 'OS', label: 'Other State Quota (OS)' }
      ],
      defaultState: 'All India'
    },
    'KCET': {
      code: 'KCET',
      name: 'Karnataka Common Entrance Test (KCET)',
      supportedScoreTypes: ['rank'],
      defaultScoreType: 'rank',
      scoreRanges: {
        rank: { min: 1, max: 250000, step: 1, unit: 'Rank', hint: 'Enter Karnataka State Engineering Rank' }
      },
      categories: [
        { code: 'GM', label: 'General Merit (GM)' },
        { code: '2A', label: 'Category 2A' },
        { code: '2B', label: 'Category 2B' },
        { code: '3A', label: 'Category 3A' },
        { code: '3B', label: 'Category 3B' },
        { code: 'SC', label: 'Scheduled Caste' },
        { code: 'ST', label: 'Scheduled Tribe' }
      ],
      quotas: [
        { code: 'GM', label: 'Karnataka State General Quota' },
        { code: 'HK', label: 'Hyderabad-Karnataka (Article 371J)' }
      ],
      defaultState: 'Karnataka'
    }
  };

  // =========================================================================
  // 2. Academic Program & Branch Catalog
  // =========================================================================
  const COURSE_BRANCH_CATALOG = {
    'B.Tech': {
      name: 'B.Tech / B.E. (Bachelor of Technology / Engineering)',
      branches: [
        { code: 'CSE', name: 'Computer Science & Engineering', cluster: 'computing' },
        { code: 'AIDS', name: 'Artificial Intelligence & Data Science', cluster: 'computing' },
        { code: 'IT', name: 'Information Technology', cluster: 'computing' },
        { code: 'ENTC', name: 'Electronics & Telecommunication Engineering', cluster: 'circuital' },
        { code: 'ELECT', name: 'Electrical Engineering', cluster: 'circuital' },
        { code: 'MECH', name: 'Mechanical Engineering', cluster: 'core' },
        { code: 'CIVIL', name: 'Civil & Infrastructure Engineering', cluster: 'core' },
        { code: 'CHEM', name: 'Chemical & Polymer Engineering', cluster: 'process' },
        { code: 'ROBO', name: 'Robotics, Automation & Mechatronics', cluster: 'specialized' },
        { code: 'INST', name: 'Instrumentation & Control Engineering', cluster: 'circuital' },
        { code: 'FOOD', name: 'Food Technology & Engineering', cluster: 'process' },
        { code: 'TEXT', name: 'Textile Engineering & Technology', cluster: 'process' },
        { code: 'AUTO', name: 'Automobile Engineering', cluster: 'core' },
        { code: 'PROD', name: 'Production & Manufacturing Engineering', cluster: 'core' },
        { code: 'BIOMED', name: 'Biomedical Engineering', cluster: 'specialized' },
        { code: 'AERO', name: 'Aeronautical & Aerospace Engineering', cluster: 'specialized' },
        { code: 'BIOTECH', name: 'Biotechnology Engineering', cluster: 'process' },
        { code: 'MINING', name: 'Mining Engineering', cluster: 'core' },
        { code: 'AGRI', name: 'Agricultural Engineering', cluster: 'specialized' },
        { code: 'SAFETY', name: 'Safety & Fire Engineering', cluster: 'specialized' },
        { code: 'META', name: 'Metallurgical & Materials Engineering', cluster: 'process' },
        { code: 'PRINT', name: 'Printing & Packaging Technology', cluster: 'specialized' }
      ]
    },
    'B.Arch': {
      name: 'B.Arch (Bachelor of Architecture)',
      branches: [
        { code: 'ARCH', name: 'Architecture & Spatial Planning', cluster: 'design' }
      ]
    },
    'MBA': {
      name: 'MBA (Master of Business Administration)',
      branches: [
        { code: 'MBA-FIN', name: 'Finance & Banking Systems', cluster: 'business' },
        { code: 'MBA-MKT', name: 'Marketing & Strategic Growth', cluster: 'business' },
        { code: 'MBA-HR', name: 'Human Resource Management', cluster: 'business' },
        { code: 'MBA-OPS', name: 'Operations & Supply Chain Analytics', cluster: 'business' }
      ]
    }
  };

  // =========================================================================
  // 3. Verified Historical Cutoff Knowledge Matrix (Illustrative Demo Data)
  // =========================================================================
  // Note: All records correspond to historical counseling outcomes and
  // are stamped with source, round, score type, and audit timestamps.
  const HISTORICAL_CUTOFFS = [
    // -----------------------------------------------------------------------
    // COEP Technological University, Pune (College Code: 6006)
    // -----------------------------------------------------------------------
    {
      id: 'cut-coep-cse-01',
      collegeCode: '6006',
      collegeName: 'COEP Technological University',
      shortName: 'COEP Pune',
      campusType: 'State University & Autonomous Institute',
      city: 'Pune',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'CSE',
      branchName: 'Computer Science & Engineering',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OPEN',
      quota: 'SL',
      year: 2024,
      round: 'CAP Round II',
      closingValue: 99.8512,
      openingValue: 99.9820,
      annualFeesINR: 92000,
      hostelAvailable: true,
      hostelNote: 'Hostel seats available based on entrance merit rank',
      source: 'State Common Entrance Test Cell, Maharashtra - 2024 Final Allotment Matrix',
      lastVerifiedDate: 'Aug 26, 2024',
      status: 'verified'
    },
    {
      id: 'cut-coep-cse-02',
      collegeCode: '6006',
      collegeName: 'COEP Technological University',
      shortName: 'COEP Pune',
      campusType: 'State University & Autonomous Institute',
      city: 'Pune',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'CSE',
      branchName: 'Computer Science & Engineering',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OBC-NCL',
      quota: 'SL',
      year: 2024,
      round: 'CAP Round II',
      closingValue: 99.7204,
      openingValue: 99.8450,
      annualFeesINR: 52000,
      hostelAvailable: true,
      hostelNote: 'Hostel seats available based on entrance merit rank',
      source: 'State Common Entrance Test Cell, Maharashtra - 2024 Final Allotment Matrix',
      lastVerifiedDate: 'Aug 26, 2024',
      status: 'verified'
    },
    {
      id: 'cut-coep-aids-01',
      collegeCode: '6006',
      collegeName: 'COEP Technological University',
      shortName: 'COEP Pune',
      campusType: 'State University & Autonomous Institute',
      city: 'Pune',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'AIDS',
      branchName: 'Artificial Intelligence & Data Science',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OPEN',
      quota: 'SL',
      year: 2024,
      round: 'CAP Round II',
      closingValue: 99.6410,
      openingValue: 99.8100,
      annualFeesINR: 92000,
      hostelAvailable: true,
      hostelNote: 'On-campus hostel allotted by merit quota',
      source: 'State Common Entrance Test Cell, Maharashtra - 2024 Final Allotment Matrix',
      lastVerifiedDate: 'Aug 26, 2024',
      status: 'verified'
    },
    {
      id: 'cut-coep-entc-01',
      collegeCode: '6006',
      collegeName: 'COEP Technological University',
      shortName: 'COEP Pune',
      campusType: 'State University & Autonomous Institute',
      city: 'Pune',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'ENTC',
      branchName: 'Electronics & Telecommunication Engineering',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OPEN',
      quota: 'SL',
      year: 2024,
      round: 'CAP Round II',
      closingValue: 99.3800,
      openingValue: 99.6100,
      annualFeesINR: 92000,
      hostelAvailable: true,
      hostelNote: 'On-campus hostel allotted by merit quota',
      source: 'State Common Entrance Test Cell, Maharashtra - 2024 Final Allotment Matrix',
      lastVerifiedDate: 'Aug 26, 2024',
      status: 'verified'
    },
    {
      id: 'cut-coep-mech-01',
      collegeCode: '6006',
      collegeName: 'COEP Technological University',
      shortName: 'COEP Pune',
      campusType: 'State University & Autonomous Institute',
      city: 'Pune',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'MECH',
      branchName: 'Mechanical & Robotics Engineering',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OPEN',
      quota: 'SL',
      year: 2024,
      round: 'CAP Round II',
      closingValue: 98.4500,
      openingValue: 99.2100,
      annualFeesINR: 92000,
      hostelAvailable: true,
      hostelNote: 'On-campus hostel allotted by merit quota',
      source: 'State Common Entrance Test Cell, Maharashtra - 2024 Final Allotment Matrix',
      lastVerifiedDate: 'Aug 26, 2024',
      status: 'verified'
    },

    // -----------------------------------------------------------------------
    // VJTI (Veermata Jijabai Technological Institute), Mumbai (Code: 3012)
    // -----------------------------------------------------------------------
    {
      id: 'cut-vjti-cse-01',
      collegeCode: '3012',
      collegeName: 'Veermata Jijabai Technological Institute (VJTI)',
      shortName: 'VJTI Mumbai',
      campusType: 'State Government Autonomous Institute',
      city: 'Mumbai',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'CSE',
      branchName: 'Computer Science & Engineering',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OPEN',
      quota: 'SL',
      year: 2024,
      round: 'CAP Round II',
      closingValue: 99.8820,
      openingValue: 99.9910,
      annualFeesINR: 88500,
      hostelAvailable: true,
      hostelNote: 'Limited hostel quota reserved for non-Mumbai candidates',
      source: 'State Common Entrance Test Cell, Maharashtra - 2024 CAP Round II',
      lastVerifiedDate: 'Aug 26, 2024',
      status: 'verified'
    },
    {
      id: 'cut-vjti-it-01',
      collegeCode: '3012',
      collegeName: 'Veermata Jijabai Technological Institute (VJTI)',
      shortName: 'VJTI Mumbai',
      campusType: 'State Government Autonomous Institute',
      city: 'Mumbai',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'IT',
      branchName: 'Information Technology',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OPEN',
      quota: 'SL',
      year: 2024,
      round: 'CAP Round II',
      closingValue: 99.7100,
      openingValue: 99.8800,
      annualFeesINR: 88500,
      hostelAvailable: true,
      hostelNote: 'Limited hostel quota for outside-Mumbai residents',
      source: 'State Common Entrance Test Cell, Maharashtra - 2024 CAP Round II',
      lastVerifiedDate: 'Aug 26, 2024',
      status: 'verified'
    },
    {
      id: 'cut-vjti-entc-01',
      collegeCode: '3012',
      collegeName: 'Veermata Jijabai Technological Institute (VJTI)',
      shortName: 'VJTI Mumbai',
      campusType: 'State Government Autonomous Institute',
      city: 'Mumbai',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'ENTC',
      branchName: 'Electronics & Telecommunication Engineering',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OPEN',
      quota: 'SL',
      year: 2024,
      round: 'CAP Round II',
      closingValue: 99.3100,
      openingValue: 99.6800,
      annualFeesINR: 88500,
      hostelAvailable: true,
      hostelNote: 'Hostel allotted by merit',
      source: 'State Common Entrance Test Cell, Maharashtra - 2024 CAP Round II',
      lastVerifiedDate: 'Aug 26, 2024',
      status: 'verified'
    },

    // -----------------------------------------------------------------------
    // PICT (Pune Institute of Computer Technology), Pune (Code: 6271)
    // -----------------------------------------------------------------------
    {
      id: 'cut-pict-cse-01',
      collegeCode: '6271',
      collegeName: 'Pune Institute of Computer Technology (PICT)',
      shortName: 'PICT Pune',
      campusType: 'Private Autonomous Institute (SPPU Affiliated)',
      city: 'Pune',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'CSE',
      branchName: 'Computer Science & Engineering',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OPEN',
      quota: 'HU',
      year: 2024,
      round: 'CAP Round II',
      closingValue: 99.5200,
      openingValue: 99.8200,
      annualFeesINR: 110000,
      hostelAvailable: true,
      hostelNote: 'Private campus hostel and nearby verified PG accommodation',
      source: 'State Common Entrance Test Cell, Maharashtra - 2024 CAP Cutoff Matrix',
      lastVerifiedDate: 'Aug 24, 2024',
      status: 'verified'
    },
    {
      id: 'cut-pict-aids-01',
      collegeCode: '6271',
      collegeName: 'Pune Institute of Computer Technology (PICT)',
      shortName: 'PICT Pune',
      campusType: 'Private Autonomous Institute (SPPU Affiliated)',
      city: 'Pune',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'AIDS',
      branchName: 'Artificial Intelligence & Data Science',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OPEN',
      quota: 'HU',
      year: 2024,
      round: 'CAP Round II',
      closingValue: 99.3400,
      openingValue: 99.5100,
      annualFeesINR: 110000,
      hostelAvailable: true,
      hostelNote: 'Hostel facilities for boys and girls',
      source: 'State Common Entrance Test Cell, Maharashtra - 2024 CAP Cutoff Matrix',
      lastVerifiedDate: 'Aug 24, 2024',
      status: 'verified'
    },
    {
      id: 'cut-pict-it-01',
      collegeCode: '6271',
      collegeName: 'Pune Institute of Computer Technology (PICT)',
      shortName: 'PICT Pune',
      campusType: 'Private Autonomous Institute (SPPU Affiliated)',
      city: 'Pune',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'IT',
      branchName: 'Information Technology',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OPEN',
      quota: 'HU',
      year: 2024,
      round: 'CAP Round II',
      closingValue: 99.2800,
      openingValue: 99.4900,
      annualFeesINR: 110000,
      hostelAvailable: true,
      hostelNote: 'Campus hostel and student residential wings',
      source: 'State Common Entrance Test Cell, Maharashtra - 2024 CAP Cutoff Matrix',
      lastVerifiedDate: 'Aug 24, 2024',
      status: 'verified'
    },

    // -----------------------------------------------------------------------
    // SPIT (Sardar Patel Institute of Technology), Mumbai (Code: 3014)
    // -----------------------------------------------------------------------
    {
      id: 'cut-spit-cse-01',
      collegeCode: '3014',
      collegeName: 'Sardar Patel Institute of Technology (SPIT)',
      shortName: 'SPIT Mumbai',
      campusType: 'Autonomous Institute (Bhavans Campus)',
      city: 'Mumbai',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'CSE',
      branchName: 'Computer Science & Engineering',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OPEN',
      quota: 'SL',
      year: 2024,
      round: 'CAP Round II',
      closingValue: 99.6100,
      openingValue: 99.8900,
      annualFeesINR: 172000,
      hostelAvailable: true,
      hostelNote: 'Limited on-campus hostel housing',
      source: 'State CET Cell Maharashtra - CAP Round II 2024 Allotment',
      lastVerifiedDate: 'Aug 25, 2024',
      status: 'verified'
    },
    {
      id: 'cut-spit-aids-01',
      collegeCode: '3014',
      collegeName: 'Sardar Patel Institute of Technology (SPIT)',
      shortName: 'SPIT Mumbai',
      campusType: 'Autonomous Institute (Bhavans Campus)',
      city: 'Mumbai',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'AIDS',
      branchName: 'Artificial Intelligence & Data Science',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OPEN',
      quota: 'SL',
      year: 2024,
      round: 'CAP Round II',
      closingValue: 99.4500,
      openingValue: 99.6200,
      annualFeesINR: 172000,
      hostelAvailable: true,
      hostelNote: 'Hostel facility available',
      source: 'State CET Cell Maharashtra - CAP Round II 2024 Allotment',
      lastVerifiedDate: 'Aug 25, 2024',
      status: 'verified'
    },

    // -----------------------------------------------------------------------
    // Walchand College of Engineering, Sangli (Code: 6007)
    // -----------------------------------------------------------------------
    {
      id: 'cut-wce-cse-01',
      collegeCode: '6007',
      collegeName: 'Walchand College of Engineering',
      shortName: 'WCE Sangli',
      campusType: 'Government-Aided Autonomous Institute',
      city: 'Sangli',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'CSE',
      branchName: 'Computer Science & Engineering',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OPEN',
      quota: 'SL',
      year: 2024,
      round: 'CAP Round II',
      closingValue: 99.1800,
      openingValue: 99.5500,
      annualFeesINR: 85000,
      hostelAvailable: true,
      hostelNote: 'Extensive on-campus residential hostels with 1000+ beds',
      source: 'State Common Entrance Test Cell, Maharashtra - 2024 CAP Round II',
      lastVerifiedDate: 'Aug 24, 2024',
      status: 'verified'
    },
    {
      id: 'cut-wce-it-01',
      collegeCode: '6007',
      collegeName: 'Walchand College of Engineering',
      shortName: 'WCE Sangli',
      campusType: 'Government-Aided Autonomous Institute',
      city: 'Sangli',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'IT',
      branchName: 'Information Technology',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OPEN',
      quota: 'SL',
      year: 2024,
      round: 'CAP Round II',
      closingValue: 98.9200,
      openingValue: 99.2500,
      annualFeesINR: 85000,
      hostelAvailable: true,
      hostelNote: '100% hostel allotment priority for outstation students',
      source: 'State Common Entrance Test Cell, Maharashtra - 2024 CAP Round II',
      lastVerifiedDate: 'Aug 24, 2024',
      status: 'verified'
    },

    // -----------------------------------------------------------------------
    // VIT (Vishwakarma Institute of Technology), Pune (Code: 6273)
    // -----------------------------------------------------------------------
    {
      id: 'cut-vit-cse-01',
      collegeCode: '6273',
      collegeName: 'Vishwakarma Institute of Technology (VIT)',
      shortName: 'VIT Pune',
      campusType: 'Private Autonomous Engineering College',
      city: 'Pune',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'CSE',
      branchName: 'Computer Science & Engineering',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OPEN',
      quota: 'HU',
      year: 2024,
      round: 'CAP Round II',
      closingValue: 98.8100,
      openingValue: 99.3000,
      annualFeesINR: 195000,
      hostelAvailable: true,
      hostelNote: 'Partner hostels and verified private accommodations nearby',
      source: 'State CET Cell Maharashtra - 2024 Allotment Matrix',
      lastVerifiedDate: 'Aug 22, 2024',
      status: 'verified'
    },
    {
      id: 'cut-vit-aids-01',
      collegeCode: '6273',
      collegeName: 'Vishwakarma Institute of Technology (VIT)',
      shortName: 'VIT Pune',
      campusType: 'Private Autonomous Engineering College',
      city: 'Pune',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'AIDS',
      branchName: 'Artificial Intelligence & Data Science',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OPEN',
      quota: 'HU',
      year: 2024,
      round: 'CAP Round II',
      closingValue: 98.4200,
      openingValue: 98.9500,
      annualFeesINR: 195000,
      hostelAvailable: true,
      hostelNote: 'Partner hostels available with Wi-Fi and mess',
      source: 'State CET Cell Maharashtra - 2024 Allotment Matrix',
      lastVerifiedDate: 'Aug 22, 2024',
      status: 'verified'
    },
    {
      id: 'cut-vit-entc-01',
      collegeCode: '6273',
      collegeName: 'Vishwakarma Institute of Technology (VIT)',
      shortName: 'VIT Pune',
      campusType: 'Private Autonomous Engineering College',
      city: 'Pune',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'ENTC',
      branchName: 'Electronics & Telecommunication Engineering',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OPEN',
      quota: 'HU',
      year: 2024,
      round: 'CAP Round II',
      closingValue: 97.6500,
      openingValue: 98.3500,
      annualFeesINR: 195000,
      hostelAvailable: true,
      hostelNote: 'Hostel facilities available',
      source: 'State CET Cell Maharashtra - 2024 Allotment Matrix',
      lastVerifiedDate: 'Aug 22, 2024',
      status: 'verified'
    },

    // -----------------------------------------------------------------------
    // PCCOE (Pimpri Chinchwad College of Engineering), Pune (Code: 6175)
    // -----------------------------------------------------------------------
    {
      id: 'cut-pccoe-cse-01',
      collegeCode: '6175',
      collegeName: 'Pimpri Chinchwad College of Engineering (PCCOE)',
      shortName: 'PCCOE Pune',
      campusType: 'Private Autonomous Engineering College',
      city: 'Pune',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'CSE',
      branchName: 'Computer Science & Engineering',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OPEN',
      quota: 'HU',
      year: 2024,
      round: 'CAP Round II',
      closingValue: 98.2400,
      openingValue: 98.8000,
      annualFeesINR: 142000,
      hostelAvailable: true,
      hostelNote: 'On-campus separate boy and girl hostels with dining',
      source: 'State CET Cell Maharashtra - 2024 Allotment Matrix',
      lastVerifiedDate: 'Aug 23, 2024',
      status: 'verified'
    },
    {
      id: 'cut-pccoe-it-01',
      collegeCode: '6175',
      collegeName: 'Pimpri Chinchwad College of Engineering (PCCOE)',
      shortName: 'PCCOE Pune',
      campusType: 'Private Autonomous Engineering College',
      city: 'Pune',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'IT',
      branchName: 'Information Technology',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OPEN',
      quota: 'HU',
      year: 2024,
      round: 'CAP Round II',
      closingValue: 97.9100,
      openingValue: 98.3500,
      annualFeesINR: 142000,
      hostelAvailable: true,
      hostelNote: 'Hostel facilities available',
      source: 'State CET Cell Maharashtra - 2024 Allotment Matrix',
      lastVerifiedDate: 'Aug 23, 2024',
      status: 'verified'
    },

    // -----------------------------------------------------------------------
    // Government College of Engineering, Chhatrapati Sambhajinagar (Aurangabad) (Code: 2008)
    // -----------------------------------------------------------------------
    {
      id: 'cut-geca-cse-01',
      collegeCode: '2008',
      collegeName: 'Government College of Engineering, Chhatrapati Sambhajinagar',
      shortName: 'GECA Aurangabad',
      campusType: 'Government Autonomous Institute',
      city: 'Chhatrapati Sambhajinagar',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'CSE',
      branchName: 'Computer Science & Engineering',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OPEN',
      quota: 'SL',
      year: 2024,
      round: 'CAP Round II',
      closingValue: 97.4500,
      openingValue: 98.3000,
      annualFeesINR: 32000,
      hostelAvailable: true,
      hostelNote: 'Low-cost government hostel facility on premises',
      source: 'State CET Cell Maharashtra - 2024 CAP Allotment Data',
      lastVerifiedDate: 'Aug 21, 2024',
      status: 'verified'
    },
    {
      id: 'cut-geca-entc-01',
      collegeCode: '2008',
      collegeName: 'Government College of Engineering, Chhatrapati Sambhajinagar',
      shortName: 'GECA Aurangabad',
      campusType: 'Government Autonomous Institute',
      city: 'Chhatrapati Sambhajinagar',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'ENTC',
      branchName: 'Electronics & Telecommunication Engineering',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OPEN',
      quota: 'SL',
      year: 2024,
      round: 'CAP Round II',
      closingValue: 95.8000,
      openingValue: 97.1000,
      annualFeesINR: 32000,
      hostelAvailable: true,
      hostelNote: 'Government hostel accommodation available',
      source: 'State CET Cell Maharashtra - 2024 CAP Allotment Data',
      lastVerifiedDate: 'Aug 21, 2024',
      status: 'verified'
    },

    // -----------------------------------------------------------------------
    // D.J. Sanghvi College of Engineering, Mumbai (Code: 3199)
    // -----------------------------------------------------------------------
    {
      id: 'cut-djsce-cse-01',
      collegeCode: '3199',
      collegeName: 'Dwarkadas J. Sanghvi College of Engineering (DJSCE)',
      shortName: 'DJ Sanghvi Mumbai',
      campusType: 'Private Autonomous Linguistic Minority College',
      city: 'Mumbai',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'CSE',
      branchName: 'Computer Science & Engineering',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OPEN',
      quota: 'SL',
      year: 2024,
      round: 'CAP Round II',
      closingValue: 99.1500,
      openingValue: 99.6800,
      annualFeesINR: 235000,
      hostelAvailable: false,
      hostelNote: 'No on-campus hostel; student PGs available across Vile Parle West',
      source: 'State CET Cell Maharashtra - CAP Round II 2024',
      lastVerifiedDate: 'Aug 23, 2024',
      status: 'verified'
    },

    // -----------------------------------------------------------------------
    // JEE Main All-India Cutoff Records (AIR Rank-Based Comparison)
    // -----------------------------------------------------------------------
    {
      id: 'cut-nitk-cse-01',
      collegeCode: 'NITK',
      collegeName: 'National Institute of Technology Karnataka, Surathkal',
      shortName: 'NIT Surathkal',
      campusType: 'Institute of National Importance (Centrally Funded)',
      city: 'Surathkal',
      state: 'Karnataka',
      program: 'B.Tech',
      branchCode: 'CSE',
      branchName: 'Computer Science & Engineering',
      exam: 'JEE-Main',
      scoreType: 'rank',
      category: 'OPEN',
      quota: 'AI',
      year: 2024,
      round: 'JoSAA Round 5',
      closingValue: 3406,
      openingValue: 840,
      annualFeesINR: 155000,
      hostelAvailable: true,
      hostelNote: '100% residential campus with mandatory hostel allocation',
      source: 'Joint Seat Allocation Authority (JoSAA) 2024 Round 5 Opening and Closing Ranks',
      lastVerifiedDate: 'Jul 28, 2024',
      status: 'verified'
    },
    {
      id: 'cut-vnit-cse-01',
      collegeCode: 'VNIT',
      collegeName: 'Visvesvaraya National Institute of Technology, Nagpur',
      shortName: 'VNIT Nagpur',
      campusType: 'Institute of National Importance (Centrally Funded)',
      city: 'Nagpur',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'CSE',
      branchName: 'Computer Science & Engineering',
      exam: 'JEE-Main',
      scoreType: 'rank',
      category: 'OPEN',
      quota: 'HS',
      year: 2024,
      round: 'JoSAA Round 5',
      closingValue: 7850,
      openingValue: 2400,
      annualFeesINR: 148000,
      hostelAvailable: true,
      hostelNote: 'Full hostel amenities and campus dining',
      source: 'Joint Seat Allocation Authority (JoSAA) 2024 Round 5 Closing Ranks',
      lastVerifiedDate: 'Jul 28, 2024',
      status: 'verified'
    },
    {
      id: 'cut-vnit-entc-01',
      collegeCode: 'VNIT',
      collegeName: 'Visvesvaraya National Institute of Technology, Nagpur',
      shortName: 'VNIT Nagpur',
      campusType: 'Institute of National Importance (Centrally Funded)',
      city: 'Nagpur',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'ENTC',
      branchName: 'Electronics & Telecommunication Engineering',
      exam: 'JEE-Main',
      scoreType: 'rank',
      category: 'OPEN',
      quota: 'HS',
      year: 2024,
      round: 'JoSAA Round 5',
      closingValue: 14200,
      openingValue: 6800,
      annualFeesINR: 148000,
      hostelAvailable: true,
      hostelNote: 'Full hostel amenities and campus dining',
      source: 'Joint Seat Allocation Authority (JoSAA) 2024 Round 5 Closing Ranks',
      lastVerifiedDate: 'Jul 28, 2024',
      status: 'verified'
    },

    // -----------------------------------------------------------------------
    // Representative State Engineering Colleges (75% - 90% Percentile Range)
    // -----------------------------------------------------------------------
    {
      id: 'cut-mmit-cse-01',
      collegeCode: '6203',
      collegeName: "Marathwada Mitra Mandal's Institute of Technology (MMIT)",
      shortName: 'MMIT Pune',
      campusType: 'Private Autonomous Engineering College',
      city: 'Pune',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'CSE',
      branchName: 'Computer Science & Engineering',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OPEN',
      quota: 'HU',
      year: 2024,
      round: 'CAP Rounds 1–4',
      closingValue: 86.3500,
      annualFeesINR: 105000,
      hostelAvailable: true,
      source: 'State CET Cell Maharashtra - 2024 Final Allotment Matrix',
      lastVerifiedDate: 'Aug 26, 2024',
      status: 'verified'
    },
    {
      id: 'cut-mgm-cse-01',
      collegeCode: '2127',
      collegeName: "MGM's College of Engineering",
      shortName: 'MGM Nanded',
      campusType: 'Approved Autonomous Institute',
      city: 'Nanded',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'CSE',
      branchName: 'Computer Science & Engineering',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OPEN',
      quota: 'SL',
      year: 2024,
      round: 'CAP Rounds 1–4',
      closingValue: 85.9900,
      annualFeesINR: 98000,
      hostelAvailable: true,
      source: 'State CET Cell Maharashtra - 2024 Final Allotment Matrix',
      lastVerifiedDate: 'Aug 26, 2024',
      status: 'verified'
    },
    {
      id: 'cut-ghr-aids-01',
      collegeCode: '4115',
      collegeName: 'G H Raisoni College of Engineering',
      shortName: 'GHRCEN Nagpur',
      campusType: 'Autonomous Engineering College',
      city: 'Nagpur',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'AIDS',
      branchName: 'Artificial Intelligence & Data Science',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OPEN',
      quota: 'SL',
      year: 2024,
      round: 'CAP Rounds 1–4',
      closingValue: 84.5000,
      annualFeesINR: 128000,
      hostelAvailable: true,
      source: 'State CET Cell Maharashtra - 2024 Final Allotment Matrix',
      lastVerifiedDate: 'Aug 26, 2024',
      status: 'verified'
    },
    {
      id: 'cut-scoe-it-01',
      collegeCode: '6178',
      collegeName: 'Sinhgad College of Engineering (SCOE)',
      shortName: 'SCOE Pune',
      campusType: 'Private Engineering College',
      city: 'Pune',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'IT',
      branchName: 'Information Technology',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OPEN',
      quota: 'HU',
      year: 2024,
      round: 'CAP Rounds 1–4',
      closingValue: 88.2000,
      annualFeesINR: 115000,
      hostelAvailable: true,
      source: 'State CET Cell Maharashtra - 2024 Final Allotment Matrix',
      lastVerifiedDate: 'Aug 26, 2024',
      status: 'verified'
    },
    {
      id: 'cut-thakur-entc-01',
      collegeCode: '3176',
      collegeName: 'Thakur College of Engineering and Technology',
      shortName: 'TCET Mumbai',
      campusType: 'Autonomous Engineering College',
      city: 'Mumbai',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'ENTC',
      branchName: 'Electronics & Telecommunication Engineering',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OPEN',
      quota: 'SL',
      year: 2024,
      round: 'CAP Rounds 1–4',
      closingValue: 86.4000,
      annualFeesINR: 140000,
      hostelAvailable: true,
      source: 'State CET Cell Maharashtra - 2024 Final Allotment Matrix',
      lastVerifiedDate: 'Aug 26, 2024',
      status: 'verified'
    },
    {
      id: 'cut-dyp-cse-01',
      collegeCode: '6272',
      collegeName: 'Dr. D.Y. Patil Institute of Technology',
      shortName: 'DYPIT Pimpri',
      campusType: 'Private Autonomous Institute',
      city: 'Pune',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'CSE',
      branchName: 'Computer Science & Engineering',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OPEN',
      quota: 'HU',
      year: 2024,
      round: 'CAP Rounds 1–4',
      closingValue: 82.5000,
      annualFeesINR: 125000,
      hostelAvailable: true,
      source: 'State CET Cell Maharashtra - 2024 Final Allotment Matrix',
      lastVerifiedDate: 'Aug 26, 2024',
      status: 'verified'
    },

    // -----------------------------------------------------------------------
    // Illustrative Insufficient Cutoff Data Record (Brand New Emerging Course)
    // -----------------------------------------------------------------------
    {
      id: 'cut-sample-emerging-01',
      collegeCode: '9999',
      collegeName: 'State Institute of Advanced Computing & Quantum Technologies',
      shortName: 'SIACQT Pune',
      campusType: 'New State Emerging Research Center',
      city: 'Pune',
      state: 'Maharashtra',
      program: 'B.Tech',
      branchCode: 'QUANT',
      branchName: 'Quantum Computing & Neuromorphic Systems',
      exam: 'MHT-CET',
      scoreType: 'percentile',
      category: 'OPEN',
      quota: 'SL',
      year: 2024,
      round: 'Pending Initial Allotment',
      closingValue: null, // Deliberately missing historical data
      openingValue: null,
      annualFeesINR: 105000,
      hostelAvailable: true,
      hostelNote: 'Hostel facilities underway',
      source: 'AICTE Approval Matrix 2024-25 (New Sanctioned Intake)',
      lastVerifiedDate: 'Jul 15, 2024',
      status: 'insufficient_data',
      dataMissingReason: 'Newly sanctioned undergraduate program for 2024-25. No historical centralized counseling CAP cutoff archive exists.'
    }
  ];

  // =========================================================================
  // 3.1 University & Affiliation Knowledge Resolution
  // =========================================================================
  const KNOWN_UNIV_MAP = {
    '6006': 'COEP Technological University',
    '16006': 'COEP Technological University',
    '3012': 'University of Mumbai',
    '03012': 'University of Mumbai',
    '6271': 'Savitribai Phule Pune University',
    '06271': 'Savitribai Phule Pune University',
    '6273': 'Savitribai Phule Pune University',
    '06273': 'Savitribai Phule Pune University',
    '6175': 'Savitribai Phule Pune University',
    '06175': 'Savitribai Phule Pune University',
    '6007': 'Shivaji University',
    '06007': 'Shivaji University',
    'NITK': 'Autonomous NIT Council',
    'VNIT': 'Autonomous NIT Council',
    '3014': 'University of Mumbai',
    '03014': 'University of Mumbai',
    '1002': 'Sant Gadge Baba Amravati University',
    '01002': 'Sant Gadge Baba Amravati University',
    '2008': 'Dr. Babasaheb Ambedkar Marathwada University',
    '02008': 'Dr. Babasaheb Ambedkar Marathwada University',
    '5004': 'Kavayitri Bahinabai Chaudhari North Maharashtra University',
    '05004': 'Kavayitri Bahinabai Chaudhari North Maharashtra University'
  };

  function resolveUniversity(record) {
    if (!record) return 'State Affiliated / Autonomous University';
    if (record.university) return record.university;
    if (record.universityName) return record.universityName;
    if (record.university_name) return record.university_name;
    if (record.affiliatedUniversity) return record.affiliatedUniversity;
    if (record.affiliated_university) return record.affiliated_university;
    if (record.home_university) return record.home_university;

    const code = String(record.collegeCode || record.college_code || '').trim();
    const cleanCode = code.replace(/^0+/, '');
    if (KNOWN_UNIV_MAP[code]) return KNOWN_UNIV_MAP[code];
    if (KNOWN_UNIV_MAP[cleanCode]) return KNOWN_UNIV_MAP[cleanCode];

    const name = String(record.collegeName || record.college_name || record.shortName || '').trim();
    const campus = String(record.campusType || record.campus_type || '').trim();

    if (/COEP|Technological University/i.test(name)) return 'COEP Technological University';
    if (/VJTI|Mumbai/i.test(name) || /Mumbai/i.test(campus)) return 'University of Mumbai';
    if (/PICT|VIT|PCCOE|Pune/i.test(name)) return 'Savitribai Phule Pune University';
    if (/Walchand|WCE|Shivaji|Sangli|Kolhapur/i.test(name)) return 'Shivaji University';
    if (/NIT|National Institute of Technology/i.test(name)) return 'Autonomous NIT Council';
    if (/Nagpur|RTMNU/i.test(name)) return /VNIT/i.test(name) ? 'Autonomous NIT Council' : 'Rashtrasant Tukadoji Maharaj Nagpur University';
    if (/Amravati|SGBAU/i.test(name)) return 'Sant Gadge Baba Amravati University';
    if (/Aurangabad|Sambhajinagar|BAMU/i.test(name)) return 'Dr. Babasaheb Ambedkar Marathwada University';
    if (/Nanded|SRTMU|Latur/i.test(name)) return 'Swami Ramanand Teerth Marathwada University';
    if (/Solapur|PAHSU/i.test(name)) return 'Punyashlok Ahilyadevi Holkar Solapur University';
    if (/Jalgaon|KBCNMU|North Maharashtra/i.test(name)) return 'Kavayitri Bahinabai Chaudhari North Maharashtra University';

    if (cleanCode.length >= 4 && /^\d+$/.test(cleanCode)) {
      const d = cleanCode[0];
      if (d === '1') return 'Sant Gadge Baba Amravati University';
      if (d === '2') return 'Dr. Babasaheb Ambedkar Marathwada University';
      if (d === '3') return 'University of Mumbai';
      if (d === '4') return 'Rashtrasant Tukadoji Maharaj Nagpur University';
      if (d === '5') return 'Kavayitri Bahinabai Chaudhari North Maharashtra University';
      if (d === '6') return 'Savitribai Phule Pune University';
    }

    return 'State Affiliated / Autonomous University';
  }

  // =========================================================================
  // 4. Recommendation Engine Core Logic
  // =========================================================================
  class RecommenderEngine {
    constructor(cutoffs = HISTORICAL_CUTOFFS) {
      this.cutoffs = cutoffs;
    }

    /**
     * Generate 4 CAP round cutoff progression
     */
    generateRoundCutoffs(record) {
      if (record.roundCutoffs) return record.roundCutoffs;
      if (record.round_cutoffs) return record.round_cutoffs;
      const cv = record.closingValue;
      if (cv === null || cv === undefined) {
        return { 1: null, 2: null, 3: null, 4: null };
      }
      const st = record.scoreType || 'percentile';
      if (st === 'percentile') {
        return {
          1: { cutoff_value: Math.min(99.99, Math.round((cv + 0.08) * 10000) / 10000), rank: null },
          2: { cutoff_value: Math.round(cv * 10000) / 10000, rank: null },
          3: { cutoff_value: Math.max(0.0, Math.round((cv - 0.07) * 10000) / 10000), rank: null },
          4: { cutoff_value: Math.max(0.0, Math.round((cv - 0.18) * 10000) / 10000), rank: null }
        };
      } else if (st === 'rank') {
        return {
          1: { cutoff_value: Math.max(1, Math.round(cv * 0.92)), rank: Math.max(1, Math.round(cv * 0.92)) },
          2: { cutoff_value: Math.round(cv), rank: Math.round(cv) },
          3: { cutoff_value: Math.round(cv * 1.08), rank: Math.round(cv * 1.08) },
          4: { cutoff_value: Math.round(cv * 1.18), rank: Math.round(cv * 1.18) }
        };
      } else {
        return {
          1: { cutoff_value: Math.round(cv + 3), rank: null },
          2: { cutoff_value: Math.round(cv), rank: null },
          3: { cutoff_value: Math.max(0, Math.round(cv - 2)), rank: null },
          4: { cutoff_value: Math.max(0, Math.round(cv - 5)), rank: null }
        };
      }
    }

    /**
     * Validate student input profile
     */
    validateProfile(profile) {
      const errors = {};

      if (!profile.exam || !EXAM_CONFIGS[profile.exam]) {
        errors.exam = 'Please select a valid entrance exam.';
      }

      if (!profile.scoreType) {
        errors.scoreType = 'Please select an exam score type.';
      } else if (profile.scoreType === 'marks') {
        errors.scoreType = 'Marks scoring has been discontinued. Cutoff allotments strictly evaluate Percentile or Rank.';
      } else {
        const examConf = EXAM_CONFIGS[profile.exam];
        if (examConf && examConf.supportedScoreTypes && !examConf.supportedScoreTypes.includes(profile.scoreType)) {
          errors.scoreType = `Score type "${profile.scoreType}" is not supported for ${profile.exam}.`;
        }
      }

      const scoreVal = parseFloat(profile.score);
      if (isNaN(scoreVal)) {
        errors.score = 'Please enter a valid numeric score.';
      } else {
        const examConf = EXAM_CONFIGS[profile.exam];
        if (examConf && examConf.scoreRanges[profile.scoreType]) {
          const range = examConf.scoreRanges[profile.scoreType];
          if (scoreVal < range.min || scoreVal > range.max) {
            errors.score = `For ${profile.scoreType}, value must be between ${range.min} and ${range.max}.`;
          }
        }
      }

      // Class 10 & 12 validation
      const tenthVal = parseFloat(profile.class10Percentage);
      if (isNaN(tenthVal) || tenthVal < 35 || tenthVal > 100) {
        errors.class10Percentage = 'Enter valid Class 10 percentage (between 35% and 100%).';
      }

      const twelfthVal = parseFloat(profile.class12Percentage);
      if (isNaN(twelfthVal) || twelfthVal < 35 || twelfthVal > 100) {
        errors.class12Percentage = 'Enter valid Class 12 percentage (between 35% and 100%).';
      }

      if (!profile.category) {
        errors.category = 'Please select your admission category.';
      }

      if (!profile.preferredCourse) {
        errors.preferredCourse = 'Please select your preferred degree course.';
      }

      if (!profile.preferredBranches || profile.preferredBranches.length === 0) {
        errors.preferredBranches = 'Please select at least one preferred academic branch in priority order.';
      }

      return {
        isValid: Object.keys(errors).length === 0,
        errors
      };
    }

    /**
     * Compute matches strictly respecting exam, score type, category, and branch priority
     */
    getRecommendations(profile) {
      const validation = this.validateProfile(profile);
      if (!validation.isValid) {
        return {
          status: 'error',
          errors: validation.errors,
          recommendations: []
        };
      }

      const studentScore = parseFloat(profile.score);
      const studentExam = profile.exam;
      const studentScoreType = profile.scoreType;
      const studentCategory = profile.category;
      const studentBranches = Array.isArray(profile.preferredBranches)
        ? profile.preferredBranches
        : [profile.preferredBranches];
      const preferredCities = profile.preferredCities || [];
      const budgetMax = profile.budgetMax ? parseFloat(profile.budgetMax) : null;
      const hostelPref = profile.hostelPreference || 'any'; // 'required', 'day_scholar', 'any'

      const results = [];

      for (const record of this.cutoffs) {
        // Rule 1: STRICT Exam Matching. Never compare MHT-CET with JEE Main
        if (record.exam !== studentExam) {
          continue;
        }

        // Rule 2: Score Type Evaluation (Percentile vs Rank)
        let recordRank = record.closingRank || record.rank;
        if (!recordRank && record.roundCutoffs) {
          const r2 = record.roundCutoffs[2] || record.roundCutoffs['2'] || record.roundCutoffs[1] || record.roundCutoffs['1'];
          if (r2 && r2.rank) recordRank = r2.rank;
        }
        if (!recordRank) {
          if (record.scoreType === 'rank') {
            recordRank = record.closingValue;
          } else if (record.closingValue !== null && record.closingValue !== undefined) {
            recordRank = Math.max(1, Math.round((100.0 - record.closingValue) * 3500.0));
          }
        }

        let recordPercentile = record.scoreType === 'percentile' ? record.closingValue : null;
        if (recordPercentile === null && record.roundCutoffs) {
          const r2 = record.roundCutoffs[2] || record.roundCutoffs['2'] || record.roundCutoffs[1] || record.roundCutoffs['1'];
          if (r2 && r2.cutoff_value) recordPercentile = r2.cutoff_value;
        }

        // If searching with rank, record must have valid rank
        if (studentScoreType === 'rank' && !recordRank) {
          continue;
        }
        // If searching with percentile, record must have valid percentile
        if (studentScoreType === 'percentile' && recordPercentile === null && record.closingValue === null) {
          continue;
        }

        // Rule 3: Branch Matching against student's priority list
        const branchPriorityIndex = studentBranches.indexOf(record.branchCode);
        const matchesBranch = branchPriorityIndex !== -1;

        // If student filtered for specific branches and record is not in list, skip
        if (!matchesBranch) {
          continue;
        }

        // Rule 4: Course match
        if (profile.preferredCourse && record.program !== profile.preferredCourse) {
          continue;
        }

        // Rule 5: City preference soft matching
        const matchesCity = preferredCities.length === 0 || preferredCities.includes(record.city);

        // Rule 6: Handle Insufficient Cutoff Data
        if (record.status === 'insufficient_data' || (studentScoreType === 'percentile' ? recordPercentile === null : !recordRank)) {
          results.push({
            record,
            matchLabel: 'Insufficient cutoff data',
            matchType: 'insufficient_data',
            matchPercentage: null,
            badgeClass: 'bg-surface-container text-on-surface-variant border-outline-variant',
            badgeIcon: 'help_outline',
            priorityRank: branchPriorityIndex + 1,
            explanation: record.dataMissingReason || 'Historical cutoff records are unverified or pending publication for this program.',
            diffValue: null,
            scoreConfidence: 'unverified',
            cityMatch: matchesCity
          });
          continue;
        }

        // Rule 7: Category matching (Use specific category if record matches, or evaluate General/OPEN)
        const isCategoryMatch = (record.category === studentCategory) || (record.category === 'OPEN');

        // Evaluate historical score match
        let isHistoricalMatch = false;
        let isMoreCompetitive = false;
        let diff = 0;
        let explanation = '';

        if (studentScoreType === 'percentile') {
          // In Percentiles: higher is better.
          const targetVal = recordPercentile !== null ? recordPercentile : record.closingValue;
          diff = studentScore - targetVal;
          if (diff >= 0.0) {
            isHistoricalMatch = true;
            explanation = `Historical Match: Your ${record.exam} score of ${studentScore.toFixed(2)}% meets or exceeds the closing cutoff of ${targetVal.toFixed(2)}% (${record.category} category).`;
          } else if (diff >= -2.0) {
            isMoreCompetitive = true;
            explanation = `More Competitive: The closing cutoff was ${targetVal.toFixed(2)}% (${record.category}). Your score of ${studentScore.toFixed(2)}% is within competitive striking distance (${Math.abs(diff).toFixed(2)}% difference).`;
          } else {
            isMoreCompetitive = true;
            explanation = `More Competitive: Historical closing cutoff stood at ${targetVal.toFixed(2)}%. Your score of ${studentScore.toFixed(2)}% is ${Math.abs(diff).toFixed(2)}% below the historical cutoff threshold.`;
          }
        } else if (studentScoreType === 'rank') {
          // In Ranks: lower number is better! (e.g. Rank 1000 is better than Rank 5000)
          diff = recordRank - studentScore;
          if (studentScore <= recordRank) {
            isHistoricalMatch = true;
            explanation = `Historical Match: Your ${record.exam} Rank of #${Math.round(studentScore)} is comfortably within the closing rank cutoff of #${Math.round(recordRank)} (${record.category} category).`;
          } else {
            isMoreCompetitive = true;
            explanation = `More Competitive: Allotments closed at rank #${Math.round(recordRank)}. Your rank #${Math.round(studentScore)} is higher than the historical closing rank.`;
          }
        }

        // Budget consideration
        let budgetMatch = true;
        if (budgetMax && record.annualFeesINR > budgetMax) {
          budgetMatch = false;
        }

        // Hostel consideration
        let hostelMatch = true;
        if (hostelPref === 'required' && !record.hostelAvailable) {
          hostelMatch = false;
        }

        const matchLabel = isHistoricalMatch ? 'Historical match' : 'More competitive';
        const matchType = isHistoricalMatch ? 'historical_match' : 'more_competitive';
        const badgeClass = isHistoricalMatch
          ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30'
          : 'bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/30';
        const badgeIcon = isHistoricalMatch ? 'check_circle' : 'trending_up';

        // Calculate user match percentage and admission probability percentage
        let matchPercentage = null;
        let admissionProbability = null;
        let probabilityTier = null;

        if (studentScoreType === 'percentile') {
          const targetVal = recordPercentile !== null ? recordPercentile : record.closingValue;
          if (targetVal !== null && targetVal !== undefined) {
            if (isHistoricalMatch) {
              matchPercentage = studentScore > 0 ? (targetVal / studentScore) * 100 : 100;
            } else {
              matchPercentage = targetVal > 0 ? (studentScore / targetVal) * 100 : 0;
            }
            const d = studentScore - targetVal;
            if (d >= 0) {
              admissionProbability = 75.0 + 24.0 * Math.min(1.0, d / 3.0);
            } else if (d >= -2.0) {
              admissionProbability = 75.0 - 45.0 * (Math.abs(d) / 2.0);
            } else if (d >= -5.0) {
              admissionProbability = 30.0 - 20.0 * ((Math.abs(d) - 2.0) / 3.0);
            } else {
              admissionProbability = Math.max(5.0, 10.0 - (Math.abs(d) - 5.0));
            }
          }
        } else if (studentScoreType === 'rank' && recordRank) {
          diff = recordRank - studentScore;
          if (isHistoricalMatch) {
            const ratio = diff / recordRank;
            admissionProbability = 75.0 + 24.0 * Math.min(1.0, ratio / 0.30);
            matchPercentage = 75.0 + 25.0 * Math.min(1.0, ratio / 0.50);
          } else {
            const def = Math.abs(diff) / recordRank;
            if (def <= 0.15) {
              admissionProbability = 75.0 - 45.0 * (def / 0.15);
            } else if (def <= 0.40) {
              admissionProbability = 30.0 - 20.0 * ((def - 0.15) / 0.25);
            } else {
              admissionProbability = Math.max(5.0, 10.0 - (def - 0.40) * 10);
            }
            matchPercentage = Math.max(0.0, 70.0 - 70.0 * Math.min(1.0, def / 0.50));
          }
        }

        if (matchPercentage !== null) {
          matchPercentage = Math.min(100.0, Math.max(0.0, Math.round(matchPercentage * 10) / 10));
        }
        if (admissionProbability !== null) {
          admissionProbability = Math.min(99.0, Math.max(5.0, Math.round(admissionProbability * 10) / 10));

          if (admissionProbability >= 85.0) {
            probabilityTier = "Very High (Safe)";
          } else if (admissionProbability >= 70.0) {
            probabilityTier = "High (Target)";
          } else if (admissionProbability >= 50.0) {
            probabilityTier = "Moderate (CAP 2–4 Possibility)";
          } else if (admissionProbability >= 25.0) {
            probabilityTier = "Low (Reach)";
          } else {
            probabilityTier = "Very Low (Ambitious)";
          }
        }

        const roundCutoffs = record.roundCutoffs || record.round_cutoffs || this.generateRoundCutoffs(record);

        results.push({
          record: {
            ...record,
            roundCutoffs,
            university: record.university || record.universityName || resolveUniversity(record)
          },
          roundCutoffs,
          matchLabel,
          matchType,
          matchPercentage,
          admissionProbability,
          probabilityTier,
          badgeClass,
          badgeIcon,
          priorityRank: branchPriorityIndex + 1,
          explanation,
          diffValue: diff,
          cityMatch: matchesCity,
          budgetMatch,
          hostelMatch
        });
      }

      // Sort results by default:
      // 1. Branch priority order first (Priority 1 branches first)
      // 2. Historical matches before competitive
      // 3. Closeness of score
      results.sort((a, b) => {
        // Priority rank first
        if (a.priorityRank !== b.priorityRank) {
          return a.priorityRank - b.priorityRank;
        }
        // Historical matches first
        if (a.matchType === 'historical_match' && b.matchType !== 'historical_match') return -1;
        if (b.matchType === 'historical_match' && a.matchType !== 'historical_match') return 1;
        // City match boost
        if (a.cityMatch && !b.cityMatch) return -1;
        if (!a.cityMatch && b.cityMatch) return 1;
        return 0;
      });

      return {
        status: 'success',
        studentProfile: {
          ...profile,
          scoreFormatted: `${studentScore} ${EXAM_CONFIGS[studentExam].scoreRanges[studentScoreType]?.unit || ''}`,
          examName: EXAM_CONFIGS[studentExam].name
        },
        count: results.length,
        recommendations: results
      };
    }

    /**
     * Filter recommendations by UI criteria
     */
    filterRecommendations(results, filters = {}) {
      return results.filter(item => {
        if (filters.matchType && filters.matchType !== 'all') {
          if (item.matchType !== filters.matchType) return false;
        }
        if (filters.city && filters.city !== 'all') {
          if (item.record.city !== filters.city) return false;
        }
        if (filters.branch && filters.branch !== 'all') {
          if (item.record.branchCode !== filters.branch) return false;
        }
        if (filters.hostelRequired && !item.record.hostelAvailable) {
          return false;
        }
        return true;
      });
    }

    /**
     * Sort recommendations cleanly by selected criterion
     */
    sortRecommendations(results, sortBy = 'probability') {
      const copy = [...results];

      const getRank = item => {
        const r = item.record || {};
        if (typeof item.closingRank === 'number' && item.closingRank > 0) return item.closingRank;
        if (typeof r.closingRank === 'number' && r.closingRank > 0) return r.closingRank;
        if (typeof r.closing_rank === 'number' && r.closing_rank > 0) return r.closing_rank;
        if (typeof r.rank === 'number' && r.rank > 0) return r.rank;
        const roundsMap = r.roundCutoffs || r.round_cutoffs || item.roundCutoffs || item.round_cutoffs || {};
        for (const rnd of [1, 2, 3, 4]) {
          const rd = roundsMap[rnd] || roundsMap[String(rnd)];
          if (rd && typeof rd === 'object' && rd.rank) return Number(rd.rank);
        }
        const valStr = String(item.cutoffValueDisplay || item.cutoff_value || r.closingValue || '');
        if (valStr.startsWith('#')) {
          const num = parseFloat(valStr.replace('#', ''));
          if (!isNaN(num) && num > 0) return num;
        }
        if (r.scoreType === 'rank' && typeof r.closingValue === 'number' && r.closingValue > 0) {
          return r.closingValue;
        }
        return Infinity;
      };

      const getCutoffVal = item => {
        const r = item.record || {};
        const v = item.cutoffValueDisplay || item.cutoff_value || r.closingValue;
        if (typeof v === 'number') return v;
        const num = parseFloat(String(v || '').replace('#', ''));
        return isNaN(num) ? 0 : num;
      };

      switch (sortBy) {
        case 'rank_asc':
        case 'merit_rank':
        case 'rank':
          return copy.sort((a, b) => {
            // 1. Eligible matches (within cutoff range) first
            const typeScore = t => (t === 'historical_match' || t === 'within_cutoff_range') ? 0 : (t === 'more_competitive' ? 1 : 2);
            const scoreDiff = typeScore(a.matchType) - typeScore(b.matchType);
            if (scoreDiff !== 0) return scoreDiff;

            // 2. Best merit rank first (lower rank number is better: #248, #312, #845...)
            const rankA = getRank(a);
            const rankB = getRank(b);
            if (rankA !== rankB) return rankA - rankB;

            return (a.priorityRank || 99) - (b.priorityRank || 99);
          });

        case 'rank_desc':
          return copy.sort((a, b) => {
            const typeScore = t => (t === 'historical_match' || t === 'within_cutoff_range') ? 0 : (t === 'more_competitive' ? 1 : 2);
            const scoreDiff = typeScore(a.matchType) - typeScore(b.matchType);
            if (scoreDiff !== 0) return scoreDiff;

            const rankA = getRank(a);
            const rankB = getRank(b);
            if (rankA !== rankB) return rankB - rankA;

            return (a.priorityRank || 99) - (b.priorityRank || 99);
          });

        case 'cutoff_desc':
          return copy.sort((a, b) => {
            const typeScore = t => (t === 'historical_match' || t === 'within_cutoff_range') ? 0 : (t === 'more_competitive' ? 1 : 2);
            const scoreDiff = typeScore(a.matchType) - typeScore(b.matchType);
            if (scoreDiff !== 0) return scoreDiff;

            return getCutoffVal(b) - getCutoffVal(a);
          });

        case 'cutoff_asc':
          return copy.sort((a, b) => {
            const typeScore = t => (t === 'historical_match' || t === 'within_cutoff_range') ? 0 : (t === 'more_competitive' ? 1 : 2);
            const scoreDiff = typeScore(a.matchType) - typeScore(b.matchType);
            if (scoreDiff !== 0) return scoreDiff;

            return getCutoffVal(a) - getCutoffVal(b);
          });

        case 'city':
          return copy.sort((a, b) => {
            const cityA = (a.record?.city || a.district || '').trim();
            const cityB = (b.record?.city || b.district || '').trim();
            const cDiff = cityA.localeCompare(cityB, undefined, { sensitivity: 'base' });
            if (cDiff !== 0) return cDiff;
            return (a.priorityRank || 99) - (b.priorityRank || 99);
          });

        case 'name_asc':
        case 'alphabetical':
          return copy.sort((a, b) => {
            const nameA = (a.record?.collegeName || a.record?.college_name || a.record?.shortName || '').trim();
            const nameB = (b.record?.collegeName || b.record?.college_name || b.record?.shortName || '').trim();
            const cDiff = nameA.localeCompare(nameB, undefined, { sensitivity: 'base' });
            if (cDiff !== 0) return cDiff;
            return (a.priorityRank || 99) - (b.priorityRank || 99);
          });

        case 'priority':
          return copy.sort((a, b) => {
            // 1. Branch priority order first (#1 branch first, then #2, #3...)
            const pDiff = (a.priorityRank || 99) - (b.priorityRank || 99);
            if (pDiff !== 0) return pDiff;

            // 2. Within same branch preference, eligible colleges first
            const typeScore = t => (t === 'historical_match' || t === 'within_cutoff_range') ? 0 : (t === 'more_competitive' ? 1 : 2);
            const scoreDiff = typeScore(a.matchType) - typeScore(b.matchType);
            if (scoreDiff !== 0) return scoreDiff;

            // 3. Highest probability first
            const probA = typeof a.admissionProbability === 'number' ? a.admissionProbability : 0;
            const probB = typeof b.admissionProbability === 'number' ? b.admissionProbability : 0;
            return probB - probA;
          });

        case 'university':
          return copy.sort((a, b) => {
            const getUniv = item => {
              const r = item.record || {};
              return (r.university || r.universityName || r.university_name || r.affiliatedUniversity || resolveUniversity(r) || '').trim();
            };
            const univA = getUniv(a);
            const univB = getUniv(b);
            const uDiff = univA.localeCompare(univB, undefined, { sensitivity: 'base' });
            if (uDiff !== 0) return uDiff;

            // Within same university: eligible colleges first
            const typeScore = t => (t === 'historical_match' || t === 'within_cutoff_range') ? 0 : (t === 'more_competitive' ? 1 : 2);
            const scoreDiff = typeScore(a.matchType) - typeScore(b.matchType);
            if (scoreDiff !== 0) return scoreDiff;

            // Highest probability first
            const probA = typeof a.admissionProbability === 'number' ? a.admissionProbability : 0;
            const probB = typeof b.admissionProbability === 'number' ? b.admissionProbability : 0;
            if (probB !== probA) return probB - probA;

            // College name A-Z
            const nameA = (a.record?.collegeName || a.record?.college_name || a.record?.shortName || '').trim();
            const nameB = (b.record?.collegeName || b.record?.college_name || b.record?.shortName || '').trim();
            return nameA.localeCompare(nameB, undefined, { sensitivity: 'base' });
          });

        case 'fees_low_high':
          return copy.sort((a, b) => {
            const getFee = item => {
              const f = item.record?.annualFeesINR ?? item.record?.annual_fees_inr;
              return (typeof f === 'number' && f > 0) ? f : Infinity;
            };
            const feeA = getFee(a);
            const feeB = getFee(b);
            if (feeA !== feeB) return feeA - feeB;

            // Tie-breaker: eligible first
            const typeScore = t => (t === 'historical_match' || t === 'within_cutoff_range') ? 0 : (t === 'more_competitive' ? 1 : 2);
            return typeScore(a.matchType) - typeScore(b.matchType);
          });

        case 'probability':
        default:
          return copy.sort((a, b) => {
            // 1. Historical matches (colleges student qualifies for) MUST be shown first!
            const typeScore = t => (t === 'historical_match' || t === 'within_cutoff_range') ? 0 : (t === 'more_competitive' ? 1 : 2);
            const scoreDiff = typeScore(a.matchType) - typeScore(b.matchType);
            if (scoreDiff !== 0) return scoreDiff;

            // 2. Sort by admission probability descending
            const probA = typeof a.admissionProbability === 'number' ? a.admissionProbability : 0;
            const probB = typeof b.admissionProbability === 'number' ? b.admissionProbability : 0;
            if (probB !== probA) {
              return probB - probA;
            }

            // 3. Tie-breaker: match percentage descending
            const matchA = typeof a.matchPercentage === 'number' ? a.matchPercentage : 0;
            const matchB = typeof b.matchPercentage === 'number' ? b.matchPercentage : 0;
            if (matchB !== matchA) {
              return matchB - matchA;
            }

            // 4. Branch priority rank tie-breaker
            return (a.priorityRank || 99) - (b.priorityRank || 99);
          });
      }
    }
  }

  // Export engine and configurations
  return {
    EXAM_CONFIGS,
    COURSE_BRANCH_CATALOG,
    HISTORICAL_CUTOFFS,
    RecommenderEngine,
    resolveUniversity,
    engine: new RecommenderEngine()
  };
});
