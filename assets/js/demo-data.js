/**
 * CollegeHub - Centralized Demo Data & Shared Client State
 * 
 * NOTE: This is a front-end demo data store. No live database or backend connection
 * is implied. All updates, edits, and state changes persist only within the browser's
 * current session or localStorage.
 */

const CollegeHubData = (function () {
  'use strict';

  // 1. The 8 Approved FAQ Categories
  const categories = [
    {
      key: 'admissions',
      title: 'Admissions',
      badge: '32 FAQs',
      icon: 'assignment_turned_in',
      description: 'Application deadlines, entrance eligibility, verification workflows, and reporting quotas.'
    },
    {
      key: 'courses',
      title: 'Courses & Majors',
      badge: '28 FAQs',
      icon: 'school',
      description: 'Undergraduate degrees, branch transfer rules, interdisciplinary minors, and credit systems.'
    },
    {
      key: 'fees',
      title: 'Fees & Financial Aid',
      badge: '19 FAQs',
      icon: 'payments',
      description: 'Tuition structures, merit scholarships, interest-free installment plans, and fee waivers.'
    },
    {
      key: 'cutoffs',
      title: 'Cutoffs & Merit Lists',
      badge: '24 FAQs',
      icon: 'leaderboard',
      description: 'Previous year rank trends, branch opening/closing counseling ranks, and reservation quotas.'
    },
    {
      key: 'placements',
      title: 'Placements & Careers',
      badge: '22 FAQs',
      icon: 'work',
      description: 'Top recruiting partners, median packages, international internships, and career training.'
    },
    {
      key: 'exams',
      title: 'Examinations',
      badge: '16 FAQs',
      icon: 'calendar_month',
      description: 'Midterm timetables, hall ticket releases, 10-point GPA grading, and re-evaluation rules.'
    },
    {
      key: 'departments',
      title: 'Departments',
      badge: '18 FAQs',
      icon: 'domain',
      description: 'Faculties of Engineering, Computing, Sciences, and Business, dean offices, and chair advising.'
    },
    {
      key: 'facilities',
      title: 'Campus & Facilities',
      badge: '26 FAQs',
      icon: 'apartment',
      description: 'Hostel allotment guidelines, high-tech engineering labs, 24/7 central library, and dining plans.'
    }
  ];

  // 2. Approved Knowledge Base FAQs (Neutral & India-appropriate guidelines)
  const initialFaqs = [
    {
      id: 'ad-001',
      question: 'What documents are needed for admission reporting?',
      category: 'admissions',
      status: 'published',
      views: 1842,
      upvotes: 248,
      updated: '2024-10-12',
      author: 'Lead Admissions Advisor',
      keywords: 'documents, verification, marksheets, transfer certificate, id proof, eligibility',
      answer: `Candidates accepted through the Centralized Counseling and Seat Allotment portal must bring physical originals and two sets of self-attested photocopies during reporting:
1. Class 10 & Class 12 Board Marksheets & Passing Certificates
2. National / State Entrance Examination Rank Card & Admit Card
3. School Leaving / Transfer Certificate and Character Certificate from the previous institution
4. Valid Government Photo ID (Aadhaar / Passport / National ID) and 6 recent passport-size color photographs
5. Category / Reservation certificate (OBC-NCL / EWS / SC / ST) issued for the current financial cycle if applicable.`
    },
    {
      id: 'ad-002',
      question: 'What is the undergraduate application deadline for Fall 2025/2026?',
      category: 'admissions',
      status: 'published',
      views: 1240,
      upvotes: 184,
      updated: '2024-10-14',
      author: 'Admissions Desk',
      keywords: 'application deadline, priority intake, regular admission, dates, schedule, reporting',
      answer: `Applications operate under a rolling phased timeline:
• Early Action Priority submissions conclude on November 15, 2024 (decision released December 20).
• Regular applications close on January 15, 2025 (decision released March 15).
• Late submissions are reviewed based on department seat vacancies through July 15.`
    },
    {
      id: 'cr-001',
      question: 'Can undergraduate students change their branch or major after the first year?',
      category: 'courses',
      status: 'published',
      views: 980,
      upvotes: 156,
      updated: '2024-09-20',
      author: 'Dean of Academic Affairs',
      keywords: 'change major, branch transfer, curriculum switch, cgpa requirement, engineering branches',
      answer: `Yes, branch migration is permitted at the conclusion of Semester 2, subject to vacancy availability and the following criteria:
1. Minimum CGPA: maintain a cumulative GPA of >= 8.25 across first-year common courses with zero academic backlogs.
2. Sanctioned Intake Cap: parent branch strength cannot drop below 75% of sanctioned capacity.
Petitions must be submitted within 7 days of Semester 2 results publication.`
    },
    {
      id: 'cr-002',
      question: 'Can engineering students pursue an interdisciplinary minor in AI, Business, or Design?',
      category: 'courses',
      status: 'published',
      views: 820,
      upvotes: 128,
      updated: '2024-09-22',
      author: 'Curriculum Board',
      keywords: 'minor degree, electives, interdisciplinary, artificial intelligence, finance, credits',
      answer: `Yes, undergraduate students in good academic standing can register for an interdisciplinary Minor Specialization by completing 18 additional credits between Semesters 3 and 7. Approved minor tracks include Artificial Intelligence & Data Systems, Financial Technologies, Product Design, and Renewable Energy Systems.`
    },
    {
      id: 'fe-001',
      question: 'How do I apply for tuition fee waivers or need-based scholarships?',
      category: 'fees',
      status: 'published',
      views: 1530,
      upvotes: 192,
      updated: '2024-08-15',
      author: 'Financial Aid Office',
      keywords: 'fee waiver, scholarship, financial aid, tuition, need-based, merit grant, bursar',
      answer: `Merit-cum-means waivers are awarded every academic year. Applications open during the first three weeks of each semester via the Student Financial Aid Portal:
• Merit Tier (100% tuition waiver): Top 5% entrance rank maintainer with CGPA >= 8.50.
• Need-Based Tier (25% to 75% waiver): Verified annual household income certificate under ₹3,00,000 / $30,000 equivalent.
Fall semester applications close August 15, 2025.`
    },
    {
      id: 'fe-002',
      question: 'Can semester tuition fees be paid in flexible monthly installments?',
      category: 'fees',
      status: 'published',
      views: 1110,
      upvotes: 142,
      updated: '2024-08-18',
      author: 'Bursar Office',
      keywords: 'fee payment, installments, bursar, payment plan, tuition deadline, finance',
      answer: `Yes, the Bursar Office provides a 3-part deferred installment plan per semester with zero interest:
• 40% due at course registration
• 30% due by mid-term examination week
• 30% prior to final examination hall ticket release.
Apply via the Student Finance Desk before registration closes.`
    },
    {
      id: 'cu-001',
      question: 'What were the opening and closing cutoffs for Computer Engineering in 2024?',
      category: 'cutoffs',
      status: 'published',
      views: 2410,
      upvotes: 312,
      updated: '2024-09-01',
      author: 'Counseling Cell',
      keywords: 'cutoffs, computer science, closing rank, opening rank, merit list, counseling rounds',
      answer: `For 2024 Centralized Counseling in Computer Science & Engineering:
• Open / General Merit: Round 1 opened at Rank 120 and Round 4 closed at Rank 615.
• In-State / Regional Quota: Round 1 opened at Rank 380 and closed at Rank 1,140.
• Institutional Merit Scholars: opened at Rank 45 and closed at Rank 240.
Cutoffs fluctuate annually based on applicant volume and seat matrix.`
    },
    {
      id: 'pl-001',
      question: 'Which companies visit campus for summer internships and final placements?',
      category: 'placements',
      status: 'published',
      views: 2150,
      upvotes: 430,
      updated: '2024-09-05',
      author: 'Career & Placement Cell',
      keywords: 'placements, companies, recruiters, internships, highest package, average package',
      answer: `Over 180+ tier-1 recruiters participate in our Annual Placement Drive:
• 2024 Placement Rate: 94.2% across engineering, business, and data science.
• Median Package: $18,500 / ₹12.5 LPA; Highest Package: $54,000 / ₹45 LPA.
• Visiting recruiters include Google, Microsoft, Deloitte, Amazon, McKinsey & Co, Tesla, and Goldman Sachs.`
    },
    {
      id: 'ex-001',
      question: 'What is the schedule for mid-term and semester final examinations?',
      category: 'exams',
      status: 'published',
      views: 750,
      upvotes: 98,
      updated: '2024-10-05',
      author: 'Registrar Evaluation Division',
      keywords: 'exam schedule, midterms, finals, hall tickets, timetable, backlogs, grading',
      answer: `The academic year follows a twin-semester structure. Continuous internal assessment accounts for 40% of the grade, while the terminal exam represents 60%:
• Mid-Semester Evaluations: Week 8 (Mid-October / Mid-March)
• Practical Laboratory Vivas: Week 14 (Late November / Late April)
• Final Semester Theory Exams: Week 16 to 18 (December / May).`
    },
    {
      id: 'dp-001',
      question: 'Which academic departments offer accredited undergraduate degrees?',
      category: 'departments',
      status: 'published',
      views: 1150,
      upvotes: 164,
      updated: '2024-09-10',
      author: 'Office of Academic Affairs',
      keywords: 'departments, faculties, schools, computer science, engineering, business, deans',
      answer: `CollegeHub institutions house 8 primary accredited academic departments:
1. Department of Computer Science & Engineering
2. Department of Data Science & Artificial Intelligence
3. Department of Electronics & Communication Engineering
4. Department of Mechanical & Robotics Engineering
5. Department of Civil & Environmental Infrastructure
6. Department of Electrical & Sustainable Energy
7. Department of Business Administration
8. Department of Humanities, Sciences & Mathematics.`
    },
    {
      id: 'dp-002',
      question: 'How do I contact department chairs, faculty mentors, and academic deans?',
      category: 'departments',
      status: 'published',
      views: 890,
      upvotes: 115,
      updated: '2024-09-15',
      author: 'Student Advising Network',
      keywords: 'contact faculty, department chair, dean office, office hours, academic advisor',
      answer: `Faculty and department heads maintain open advising office hours every Tuesday and Thursday between 2:00 PM and 4:30 PM. You can locate individual faculty emails, office suite numbers, and appointment scheduling links through the Department Directory or by contacting your assigned First-Year Faculty Mentor.`
    },
    {
      id: 'fa-001',
      question: 'What are the rules, amenities, and curfew hours for campus residential hostels?',
      category: 'facilities',
      status: 'published',
      views: 1670,
      upvotes: 204,
      updated: '2024-08-20',
      author: 'Campus Housing Authority',
      keywords: 'hostel, dorms, curfew, accommodation, dining mess, wifi, laundry, residential',
      answer: `Campus hostels provide biometric access and 24/7 security:
• Standard Curfew: 10:00 PM on weekdays; 11:00 PM on Fridays and Saturdays. Late pass requests can be submitted via the student portal 12 hours prior.
• Amenities: Gigabit Wi-Fi, 4 dining meal plans, laundromats, indoor gymnasiums, and quiet study lounges.
• Allocation: Double occupancy for freshmen; single or double occupancy studio choices for 2nd through 4th-year students.`
    },
    {
      id: 'fa-002',
      question: 'What are the central library hours and research lab computing facilities?',
      category: 'facilities',
      status: 'published',
      views: 1280,
      upvotes: 167,
      updated: '2024-08-25',
      author: 'Library Operations',
      keywords: 'library, computer labs, research facilities, study rooms, jstor, ieee, timings',
      answer: `The Central Academic Library is open from 7:00 AM to midnight on weekdays, and operates 24/7 during midterm and final examination weeks. Facilities include 400+ study carrels, high-performance GPU workstations for AI/ML modeling, collaborative presentation rooms, and digital access to IEEE, ACM, Springer, and JSTOR repositories.`
    },
    {
      id: 'dr-001',
      question: 'Direct second year lateral entry diploma admission criteria (Under Review)',
      category: 'admissions',
      status: 'draft',
      views: 0,
      upvotes: 0,
      updated: '2024-11-01',
      author: 'Curriculum Board',
      keywords: 'lateral entry, diploma, polytechnic, direct second year',
      answer: `Draft guidelines under review: Polytechnic diploma holders with aggregate >= 60% are eligible for direct admission to semester 3 across participating engineering branches.`
    },
    {
      id: 'in-001',
      question: 'Archived Health Protocols & Vaccination Reporting (Historical Cycle)',
      category: 'facilities',
      status: 'inactive',
      views: 320,
      upvotes: 12,
      updated: '2022-03-01',
      author: 'Health Center',
      keywords: 'covid, health, vaccination, archived',
      answer: `Archived institutional health policy from the 2021-22 academic cycle. All pandemic health mandates have been decommissioned.`
    }
  ];

  // 3. Fallback Response for Chatbot
  const CHATBOT_FALLBACK = "I couldn't find a reliable answer to that question in the approved college FAQs. Please try rephrasing your question, searching our FAQ directory, or contacting college administrative staff directly.";

  // 4. Student Applicant Profile (Demo user removed)
  const applicantProfile = null;

  // 5. Local Storage & In-Memory State
  const FAQ_STORAGE_KEY = 'collegehub_demo_faqs';
  const THEME_STORAGE_KEY = 'collegehub-theme';

  function getStoredFaqs() {
    try {
      const stored = localStorage.getItem(FAQ_STORAGE_KEY);
      if (stored) {
        return JSON.parse(stored);
      }
    } catch (e) {
      console.warn('LocalStorage error, using initial FAQs:', e);
    }
    return initialFaqs.map(f => Object.assign({}, f));
  }

  function saveStoredFaqs(faqs) {
    try {
      localStorage.setItem(FAQ_STORAGE_KEY, JSON.stringify(faqs));
    } catch (e) {
      console.warn('Failed to save to localStorage:', e);
    }
  }

  // 6. Theme Engine
  function applyTheme(theme) {
    const isDark = (theme === 'dark');
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }

    // Update all theme toggle icons across the page
    const icons = document.querySelectorAll('#theme-toggle-icon, #themeToggleIcon, .theme-toggle-icon');
    icons.forEach(icon => {
      icon.textContent = isDark ? 'light_mode' : 'dark_mode';
    });

    // Also update any material icons inside theme toggle buttons
    const btns = document.querySelectorAll('#theme-toggle-btn, #themeToggleBtn, [aria-label*="Theme" i], [title*="Light/Dark" i]');
    btns.forEach(btn => {
      const matIcon = btn.querySelector('.material-symbols-outlined');
      if (matIcon && !matIcon.classList.contains('dark:hidden') && !matIcon.classList.contains('dark:inline')) {
        matIcon.textContent = isDark ? 'light_mode' : 'dark_mode';
      }
    });
  }

  function toggleTheme() {
    const current = localStorage.getItem(THEME_STORAGE_KEY) ||
      (document.documentElement.classList.contains('dark') ? 'dark' : 'light');
    const newTheme = current === 'dark' ? 'light' : 'dark';
    try {
      localStorage.setItem(THEME_STORAGE_KEY, newTheme);
    } catch (e) { }
    applyTheme(newTheme);
    window.dispatchEvent(new CustomEvent('themechange', { detail: { theme: newTheme } }));
  }

  function bindThemeButtons() {
    const selector = '#theme-toggle-btn, #themeToggleBtn, [aria-label*="Theme" i], [title*="Light/Dark" i], .theme-toggle-btn';
    const buttons = document.querySelectorAll(selector);
    buttons.forEach(btn => {
      // Avoid duplicate binding
      if (!btn.dataset.themeBound) {
        btn.dataset.themeBound = 'true';
        btn.addEventListener('click', function (e) {
          // If button already has inline onclick="toggleTheme()", let it run; otherwise trigger toggleTheme
          if (!btn.getAttribute('onclick') || !btn.getAttribute('onclick').includes('toggleTheme')) {
            e.preventDefault();
            toggleTheme();
          }
        });
      }
    });
  }

  function initTheme() {
    const saved = localStorage.getItem(THEME_STORAGE_KEY);
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = saved || (prefersDark ? 'dark' : 'light');
    applyTheme(theme);
    bindThemeButtons();

    window.addEventListener('storage', function (e) {
      if (e.key === THEME_STORAGE_KEY) {
        applyTheme(e.newValue || 'light');
      }
    });
  }

  // 7. Chatbot Query Matching
  function matchChatQuery(userQuery) {
    if (!userQuery || !userQuery.trim()) {
      return { matched: false, answer: CHATBOT_FALLBACK };
    }

    const q = userQuery.toLowerCase().trim();
    const faqs = getStoredFaqs().filter(f => f.status === 'published');

    // Tokenization and stopword elimination
    const stopWords = new Set(['a', 'an', 'the', 'is', 'are', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'what', 'how', 'do', 'can', 'college', 'i', 'my', 'please', 'tell', 'me']);
    const tokens = q.replace(/[^a-z0-9 ]/g, ' ').split(/\s+/).filter(w => w.length > 1 && !stopWords.has(w));

    let bestScore = 0;
    let bestFaq = null;

    for (let faq of faqs) {
      let score = 0;
      const qText = faq.question.toLowerCase();
      const aText = faq.answer.toLowerCase();
      const kText = (faq.keywords || '').toLowerCase();
      const cText = faq.category.toLowerCase();

      if (qText.includes(q)) score += 8.0;
      if (kText.includes(q)) score += 6.0;

      for (let t of tokens) {
        if (qText.includes(t)) score += 3.5;
        if (kText.includes(t)) score += 3.0;
        if (cText === t) score += 2.5;
        if (aText.includes(t)) score += 1.0;
      }

      if (score > bestScore) {
        bestScore = score;
        bestFaq = faq;
      }
    }

    if (bestScore >= 3.0 && bestFaq) {
      return {
        matched: true,
        answer: bestFaq.answer,
        faq: bestFaq,
        score: bestScore
      };
    }

    return {
      matched: false,
      answer: CHATBOT_FALLBACK
    };
  }

  // Expose toggleTheme and applyTheme to window for inline onclick handlers
  if (typeof window !== 'undefined') {
    window.toggleTheme = toggleTheme;
    window.applyTheme = applyTheme;
  }

  // Auto-initialize theme on DOM load
  if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', initTheme);
    } else {
      initTheme();
    }
  }

  return {
    categories: categories,
    getFaqs: getStoredFaqs,
    saveFaqs: saveStoredFaqs,
    profile: applicantProfile,
    fallbackText: CHATBOT_FALLBACK,
    matchChat: matchChatQuery,
    applyTheme: applyTheme,
    toggleTheme: toggleTheme
  };
})();

// Attach globally
if (typeof window !== 'undefined') {
  window.CollegeHubData = CollegeHubData;
}

// Export for module systems if present
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CollegeHubData;
}
