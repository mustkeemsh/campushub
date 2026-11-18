import re
from flask import Blueprint, request, jsonify
from database import db
from config import Config
from routes.chatbot_service import (
    MAX_MESSAGE_CHARS, ai_enabled, build_context, generate_ai_answer,
    rate_limited, database_summary_answer, _top_faqs
)
from routes import local_advisor

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


def _faq_only_response(user_message, ai_unavailable=False, context_text="", meta=None):
    """Original behaviour: answer strictly from administrator-approved FAQs."""
    published_faqs = db.get_faqs(status='published')
    scored_faqs = []
    for faq in published_faqs:
        score = calculate_match_score(user_message, faq)
        if score > 0:
            scored_faqs.append((score, faq))
    scored_faqs.sort(key=lambda x: x[0], reverse=True)

    CONFIDENCE_THRESHOLD = 3.0

    # Key-free advisor: colleges from the CAP institute list + admissions primer
    try:
        local = local_advisor.answer(user_message)
    except Exception as exc:
        print(f"[chatbot] local advisor error: {exc}")
        local = None
    if local:
        return jsonify({
            "status": "matched",
            "matched": True,
            "source": "local",
            "answer": local["text"],
            "related": [],
            "disclaimer": "Based on the CAP institute list and verified CollegeHub records."
        })

    if scored_faqs and scored_faqs[0][0] >= CONFIDENCE_THRESHOLD:
        best_score, best_faq = scored_faqs[0]
        db.increment_views(best_faq.get('id'))
        related = [
            {"id": f.get("id"), "question": f.get("question"), "category": f.get("category")}
            for sc, f in scored_faqs[1:4] if sc >= (CONFIDENCE_THRESHOLD * 0.7)
        ]
        return jsonify({
            "status": "matched",
            "matched": True,
            "source": "faq",
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

    summary = database_summary_answer(context_text, meta or {})
    if summary:
        return jsonify({
            "status": "matched",
            "matched": True,
            "source": "database",
            "answer": summary,
            "related": [],
            "disclaimer": "Summary of verified CollegeHub records."
        })

    return jsonify({
        "status": "fallback",
        "matched": False,
        "ai_unavailable": ai_unavailable,
        "answer": (
            "I couldn't find an answer to that. I can help with Maharashtra engineering colleges: try a college name "
            "(e.g. \"COEP\" or \"Zeal College\"), a place (e.g. \"colleges in Sangli\"), or topics like CAP rounds, TFWS, "
            "documents and cutoffs."
        ),
        "disclaimer": "CollegeHub Assistant uses verified administrator entries only. No speculative information is generated.",
        "suggested_categories": Config.CATEGORIES
    })


@faqs_bp.route('/chat', methods=['POST'])
def chat_assistant():
    """
    "Ask CollegeHub" chatbot endpoint.

    Request JSON: {"message": "...", "history": [{"role": "user"|"assistant", "content": "..."}]}

    With ANTHROPIC_API_KEY configured, the question is answered by an AI model that is
    grounded in verified CollegeHub database records and approved FAQs (see
    routes/chatbot_service.py). Without a key, or if the AI call fails, the endpoint
    falls back to the approved-FAQ matcher so the chatbot keeps working.
    """
    data = request.get_json(silent=True) or {}
    user_message = str(data.get('message', '')).strip()

    if not user_message:
        return jsonify({"status": "error", "message": "Message parameter is required."}), 400
    if len(user_message) > MAX_MESSAGE_CHARS:
        user_message = user_message[:MAX_MESSAGE_CHARS]

    client_id = request.headers.get('X-Forwarded-For', request.remote_addr or 'unknown').split(',')[0].strip()
    if rate_limited(client_id):
        return jsonify({
            "status": "error",
            "message": "You're sending messages too quickly. Please wait a moment and try again."
        }), 429

    context_text, meta = build_context(user_message)
    try:
        extra = local_advisor.context_for_ai(user_message)
        if extra:
            context_text = (context_text + "\n\nCAP INSTITUTE LIST (official institute data):\n" + extra).strip()
    except Exception as exc:
        print(f"[chatbot] local context error: {exc}")

    if not ai_enabled():
        return _faq_only_response(user_message, ai_unavailable=True, context_text=context_text, meta=meta)

    try:
        answer = generate_ai_answer(user_message, data.get('history'), context_text)
    except Exception as exc:
        print(f"[chatbot] AI call failed, using fallback: {exc}")
        return _faq_only_response(user_message, ai_unavailable=True, context_text=context_text, meta=meta)

    related = []
    for sc, f in _top_faqs(user_message, limit=4):
        if sc >= 3.0 * 0.7:
            related.append({"id": f.get("id"), "question": f.get("question"), "category": f.get("category")})

    return jsonify({
        "status": "matched",
        "matched": True,
        "source": "ai",
        "answer": answer,
        "colleges": meta.get("institutes", []),
        "related": related[:3],
        "disclaimer": "AI-generated using CollegeHub data. Please verify important details on the official CET Cell / college website."
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
