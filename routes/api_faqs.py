import re
from flask import Blueprint, request, jsonify
from database import db
from config import Config

faqs_bp = Blueprint('faqs_bp', __name__, url_prefix='/api')

CATEGORY_METADATA = {
    "admissions": {
        "title": "Admissions",
        "description": "Application deadlines, eligibility criteria, required documents, and verification protocols.",
        "icon": "school"
    },
    "courses": {
        "title": "Courses",
        "description": "Degree programs, major switches, credit systems, and interdisciplinary minors.",
        "icon": "menu_book"
    },
    "fees": {
        "title": "Fees",
        "description": "Tuition structures, installment plans, need-based fee waivers, and merit scholarships.",
        "icon": "payments"
    },
    "cutoffs": {
        "title": "Cutoffs",
        "description": "Historical opening and closing merit ranks, counseling round scores, and quotas.",
        "icon": "analytics"
    },
    "placements": {
        "title": "Placements",
        "description": "On-campus recruitment statistics, average packages, top recruiters, and internships.",
        "icon": "work"
    },
    "examinations": {
        "title": "Examinations",
        "description": "Semester exam schedules, hall tickets, grading scales, re-evaluations, and backlogs.",
        "icon": "assignment"
    },
    "departments": {
        "title": "Departments",
        "description": "Academic engineering and science faculties, chair contacts, deans, and advising hours.",
        "icon": "domain"
    },
    "facilities": {
        "title": "Facilities",
        "description": "Campus residential hostels, dining messes, 24/7 central library, and computing labs.",
        "icon": "apartment"
    }
}

STOPWORDS = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'aren',
    'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by',
    'can', 'could', 'did', 'do', 'does', 'doing', 'down', 'during', 'each', 'few', 'for', 'from',
    'further', 'had', 'has', 'have', 'having', 'he', 'her', 'here', 'hers', 'herself', 'him', 'himself',
    'his', 'how', 'i', 'if', 'in', 'into', 'is', 'it', 'its', 'itself', 'just', 'me', 'more', 'most',
    'my', 'myself', 'no', 'nor', 'not', 'now', 'of', 'off', 'on', 'once', 'only', 'or', 'other', 'our',
    'ours', 'ourselves', 'out', 'over', 'own', 'same', 'she', 'should', 'so', 'some', 'such', 'than',
    'that', 'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there', 'these', 'they', 'this',
    'those', 'through', 'to', 'too', 'under', 'until', 'up', 'very', 'was', 'we', 'were', 'what',
    'when', 'where', 'which', 'while', 'who', 'whom', 'why', 'will', 'with', 'would', 'you', 'your',
    'yours', 'yourself', 'yourselves', 'tell', 'show', 'give', 'know', 'want', 'please', 'college', 'collegehub'
}


def tokenize(text):
    """Normalize and tokenize text into informative search tokens."""
    if not text:
        return []
    words = re.findall(r'[a-zA-Z0-9]+', text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


def calculate_match_score(query, faq):
    """
    Score relevance of a user query against an approved published FAQ.
    Returns a score between 0.0 and positive infinity.
    Never invents or searches unapproved data.
    """
    query_clean = query.lower().strip()
    query_tokens = tokenize(query)
    if not query_tokens:
        # Fall back to raw tokens if all were filtered out
        query_tokens = [w for w in re.findall(r'[a-zA-Z0-9]+', query_clean) if len(w) > 1]
    
    if not query_tokens:
        return 0.0

    score = 0.0
    q_text = faq.get("question", "").lower()
    a_text = faq.get("answer", "").lower()
    kw_text = faq.get("keywords", "").lower()
    cat_text = faq.get("category", "").lower()

    # 1. Exact phrase substring match in question or keywords
    if query_clean in q_text:
        score += 8.0
    if query_clean in kw_text:
        score += 6.0

    # 2. Token matches across distinct fields with specific weights
    matched_tokens = 0
    for token in query_tokens:
        token_found = False
        # Question token match
        if re.search(r'\b' + re.escape(token) + r'\b', q_text):
            score += 3.5
            token_found = True
        elif token in q_text:
            score += 2.0
            token_found = True

        # Keywords token match
        if re.search(r'\b' + re.escape(token) + r'\b', kw_text):
            score += 3.0
            token_found = True
        elif token in kw_text:
            score += 1.5
            token_found = True

        # Category match
        if token == cat_text:
            score += 2.5
            token_found = True

        # Answer body match (less weighted to avoid spurious matches)
        if re.search(r'\b' + re.escape(token) + r'\b', a_text):
            score += 1.0
            token_found = True

        if token_found:
            matched_tokens += 1

    # Token coverage calculation
    coverage = matched_tokens / len(query_tokens)

    # Spurious match prevention:
    # If no tokens match, or if in a multi-token query only a single isolated token matched with low coverage, reject
    if matched_tokens == 0:
        return 0.0

    if len(query_tokens) >= 3 and matched_tokens < 2 and coverage < 0.4:
        return 0.0

    # Scale score with coverage
    score = score * (coverage ** 1.5)
    return score


@faqs_bp.route('/faqs', methods=['GET'])
def list_faqs():
    """Public FAQ listing: retrieves approved, published, and active FAQs only."""
    category = request.args.get('category', '').strip().lower()
    search = request.args.get('q', '').strip()

    faqs = db.get_faqs(status='published', category=category if category != 'all' else None, search=search, is_active=True)
    return jsonify({
        "status": "success",
        "data": faqs,
        "count": len(faqs)
    })


@faqs_bp.route('/faqs/<faq_id>', methods=['GET'])
def get_faq_detail(faq_id):
    """Retrieve single approved FAQ and increment its view counter."""
    faq = db.get_faq_by_id(faq_id)
    if not faq or faq.get('status') != 'published' or not faq.get('is_active', True):
        return jsonify({
            "status": "error",
            "message": "FAQ not found or not published."
        }), 404

    db.increment_views(faq_id)
    return jsonify({
        "status": "success",
        "data": faq
    })


@faqs_bp.route('/categories', methods=['GET'])
def get_categories():
    """Retrieve all 8 approved categories with active published counts."""
    metrics = db.get_metrics()
    counts = metrics.get("category_counts", {})

    categories_list = []
    for cat_key in Config.CATEGORIES:
        meta = CATEGORY_METADATA.get(cat_key, {
            "title": cat_key.capitalize(),
            "description": f"Approved {cat_key} details.",
            "icon": "folder"
        })
        categories_list.append({
            "key": cat_key,
            "title": meta["title"],
            "description": meta["description"],
            "icon": meta["icon"],
            "count": counts.get(cat_key, 0)
        })

    return jsonify({
        "status": "success",
        "data": categories_list
    })


@faqs_bp.route('/chat', methods=['POST'])
def chat_assistant():
    """
    Text-based chatbot endpoint answering strictly from administrator-approved FAQs.
    Never invents college fees, cutoffs, placements, dates, facilities, or contact details.
    When a reliable match cannot be confirmed, returns explicit fallback message.
    """
    data = request.get_json(silent=True) or {}
    user_message = data.get('message', '').strip()

    if not user_message:
        return jsonify({
            "status": "error",
            "message": "Message parameter is required."
        }), 400

    # Retrieve only approved published FAQs
    published_faqs = db.get_faqs(status='published')

    # Score each FAQ against the user's message
    scored_faqs = []
    for faq in published_faqs:
        score = calculate_match_score(user_message, faq)
        if score > 0:
            scored_faqs.append((score, faq))

    scored_faqs.sort(key=lambda x: x[0], reverse=True)

    # Explicit fallback message as required by CollegeHub policy
    FALLBACK_RESPONSE = (
        "I couldn't find a reliable answer to that question in the approved college FAQs. "
        "Please try rephrasing your question, searching our FAQ directory, or contacting "
        "college administrative staff directly."
    )

    # Threshold for a confident, reliable match
    CONFIDENCE_THRESHOLD = 3.0

    if not scored_faqs or scored_faqs[0][0] < CONFIDENCE_THRESHOLD:
        return jsonify({
            "status": "fallback",
            "matched": False,
            "answer": FALLBACK_RESPONSE,
            "disclaimer": "CollegeHub Assistant uses verified administrator entries only. No speculative information is generated.",
            "suggested_categories": Config.CATEGORIES
        })

    best_score, best_faq = scored_faqs[0]

    # Increment view count for the matched FAQ
    db.increment_views(best_faq.get('id'))

    # Provide related verified questions if available with decent scores
    related = []
    for sc, f in scored_faqs[1:4]:
        if sc >= (CONFIDENCE_THRESHOLD * 0.7):
            related.append({
                "id": f.get("id"),
                "question": f.get("question"),
                "category": f.get("category")
            })

    return jsonify({
        "status": "matched",
        "matched": True,
        "answer": best_faq.get("answer"),
        "faq": {
            "id": best_faq.get("id"),
            "question": best_faq.get("question"),
            "category": best_faq.get("category"),
            "keywords": best_faq.get("keywords")
        },
        "score": round(best_score, 2),
        "related": related,
        "disclaimer": "This answer is verified and approved by the college administration."
    })


@faqs_bp.route('/faqs/<faq_id>/vote', methods=['POST'])
def vote_faq(faq_id):
    """Increment upvote count for a helpful FAQ."""
    faq = db.get_faq_by_id(faq_id)
    if not faq:
        return jsonify({
            "status": "error",
            "message": "FAQ not found."
        }), 404

    new_upvotes = db.increment_upvotes(faq_id)
    return jsonify({
        "status": "success",
        "upvotes_count": new_upvotes
    })
