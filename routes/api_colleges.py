from flask import Blueprint, request, jsonify
from database import db

colleges_bp = Blueprint('colleges_bp', __name__, url_prefix='/api')


@colleges_bp.route('/institutes', methods=['GET'])
def list_institutes():
    """
    List published institutes with optional district, type, and keyword search filters.
    Enforces Row Level Security: only published institutes (is_published = true) are visible.
    """
    district = request.args.get('district', '').strip() or None
    institute_type = request.args.get('type', '').strip() or None
    search = request.args.get('q', '').strip() or request.args.get('search', '').strip() or None

    institutes = db.get_institutes(
        district=district,
        institute_type=institute_type,
        search=search,
        published_only=True
    )

    # Enrich with summary counts
    enriched = []
    for inst in institutes:
        inst_id = inst.get("id")
        contacts = db.get_institute_contacts(inst_id, published_only=True)
        courses = db.get_courses(institute_id=inst_id, published_only=True)
        amenities = db.get_institute_amenities(inst_id, published_only=True)
        item = dict(inst)
        item["contacts_count"] = len(contacts)
        item["courses_count"] = len(courses)
        item["amenities_count"] = len(amenities)
        enriched.append(item)

    return jsonify({
        "status": "success",
        "count": len(enriched),
        "data": enriched
    }), 200


@colleges_bp.route('/institutes/<institute_id>', methods=['GET'])
def get_institute(institute_id):
    """
    Retrieve comprehensive normalized relational profile for an institute:
    College -> Courses -> Cutoffs / Fees
    Contacts, placements, facilities, and source provenance.
    Enforces publication gating: unpublished institutes return 404 to public visitors.
    """
    profile = db.get_institute_details(institute_id, published_only=True)
    if not profile:
        return jsonify({
            "status": "error",
            "message": f"Institute '{institute_id}' not found or has not yet been published by an administrator."
        }), 404

    return jsonify({
        "status": "success",
        "data": profile
    }), 200


@colleges_bp.route('/courses', methods=['GET'])
def list_courses():
    """
    List published courses filtered by institute, admission route, or academic year.
    Crucial: admission_route (BTECH_FIRST_YEAR, BTECH_DSY, DIPLOMA_AFTER_SSC) is segregated from cutoffs.seat_pool.
    """
    institute_id = request.args.get('institute_id', '').strip() or None
    admission_route = request.args.get('route', '').strip() or request.args.get('admission_route', '').strip() or None
    academic_year = request.args.get('academic_year', '').strip() or None

    courses = db.get_courses(
        institute_id=institute_id,
        admission_route=admission_route,
        academic_year=academic_year,
        published_only=True
    )

    # Attach parent institute basic info for each course
    enriched = []
    for c in courses:
        item = dict(c)
        inst = db.get_institute_by_id(c.get("institute_id"), published_only=True)
        if inst:
            item["institute_code"] = inst.get("institute_code")
            item["institute_name"] = inst.get("institute_name")
            item["district"] = inst.get("district")
        enriched.append(item)

    return jsonify({
        "status": "success",
        "count": len(enriched),
        "data": enriched
    }), 200


@colleges_bp.route('/amenities', methods=['GET'])
def list_amenities():
    """Retrieve master catalog of campus amenities and academic infrastructure."""
    amenities = db.get_amenities()
    return jsonify({
        "status": "success",
        "count": len(amenities),
        "data": amenities
    }), 200


@colleges_bp.route('/sources', methods=['GET'])
def list_sources():
    """
    Retrieve verified official source documents retaining origin, checked date, and URL.
    Only administrator-verified sources (verified = true) are displayed.
    """
    sources = db.get_source_documents(verified_only=True)
    return jsonify({
        "status": "success",
        "count": len(sources),
        "data": sources
    }), 200


@colleges_bp.route('/branches', methods=['GET'])
def list_branches():
    """
    Retrieve all distinct academic branches saved across published courses.
    Includes course counts, degree programs, cluster tags, and descriptions.
    """
    program = request.args.get('program', '').strip() or None
    branches = db.get_branches(program=program)
    return jsonify({
        "status": "success",
        "count": len(branches),
        "data": branches
    }), 200

