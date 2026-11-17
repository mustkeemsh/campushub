import os
from functools import wraps
from flask import Blueprint, request, jsonify, session, send_file
from database import db
from config import Config

admin_bp = Blueprint('admin_bp', __name__, url_prefix='/api/admin')


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return jsonify({
                "status": "error",
                "message": "Authentication required. Please log in as an administrator."
            }), 401
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/login', methods=['POST'])
def admin_login():
    """Authenticate administrator credentials and initialize session."""
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({
            "status": "error",
            "message": "Username and password are required."
        }), 400

    if db.verify_admin(username, password):
        session['admin_logged_in'] = True
        session['admin_username'] = username
        return jsonify({
            "status": "success",
            "message": "Authentication successful. Welcome to the Admin Console.",
            "username": username
        })
    else:
        return jsonify({
            "status": "error",
            "message": "Invalid administrator username or password. Please verify your credentials."
        }), 401


@admin_bp.route('/logout', methods=['POST'])
def admin_logout():
    """Terminate administrator session."""
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    return jsonify({
        "status": "success",
        "message": "Logged out successfully."
    })


@admin_bp.route('/me', methods=['GET'])
@admin_bp.route('/session', methods=['GET'])
def admin_session_status():
    """Return current admin authentication status."""
    is_authenticated = bool(session.get('admin_logged_in'))
    username = session.get('admin_username', '') if is_authenticated else ''
    return jsonify({
        "status": "success",
        "authenticated": is_authenticated,
        "username": username,
        "user": {
            "username": username,
            "role": "admin"
        } if is_authenticated else None
    })


@admin_bp.route('/metrics', methods=['GET'])
@admin_required
def admin_metrics():
    """Retrieve summary dashboard counts and statistics."""
    metrics = db.get_metrics()
    return jsonify({
        "status": "success",
        "data": metrics
    })


@admin_bp.route('/faqs', methods=['GET'])
@admin_required
def admin_list_faqs():
    """List all FAQs with optional filters for category, status, and search query."""
    status = request.args.get('status', '').strip().lower()
    category = request.args.get('category', '').strip().lower()
    search = request.args.get('q', '').strip()

    status_filter = status if status and status != 'all' else None
    category_filter = category if category and category != 'all' else None

    faqs = db.get_faqs(status=status_filter, category=category_filter, search=search)
    return jsonify({
        "status": "success",
        "data": faqs,
        "count": len(faqs)
    })


@admin_bp.route('/faqs', methods=['POST'])
@admin_required
def admin_create_faq():
    """Create a new FAQ record."""
    data = request.get_json(silent=True) or {}
    question = data.get('question', '').strip()
    answer = data.get('answer', '').strip()
    category = data.get('category', 'admissions').strip().lower()
    keywords = data.get('keywords', '').strip()
    status = data.get('status', 'published').strip().lower()

    if not question:
        return jsonify({
            "status": "error",
            "message": "Question field is required and cannot be empty."
        }), 400

    if not answer:
        return jsonify({
            "status": "error",
            "message": "Answer field is required and cannot be empty."
        }), 400

    if category not in Config.CATEGORIES:
        return jsonify({
            "status": "error",
            "message": f"Invalid category. Must be one of: {', '.join(Config.CATEGORIES)}"
        }), 400

    if status not in Config.STATUSES:
        return jsonify({
            "status": "error",
            "message": f"Invalid status. Must be one of: {', '.join(Config.STATUSES)}"
        }), 400

    created = db.create_faq({
        "question": question,
        "answer": answer,
        "category": category,
        "keywords": keywords,
        "status": status,
        "is_active": data.get("is_active", status != "inactive")
    }, admin_id=session.get('admin_id'), admin_username=session.get('admin_username', 'admin'))

    return jsonify({
        "status": "success",
        "message": f"FAQ '{question[:40]}...' created successfully.",
        "data": created
    }), 201


@admin_bp.route('/faqs/<faq_id>', methods=['PATCH', 'PUT'])
@admin_required
def admin_update_faq(faq_id):
    """Update an existing FAQ entry."""
    data = request.get_json(silent=True) or {}
    faq = db.get_faq_by_id(faq_id)
    if not faq:
        return jsonify({
            "status": "error",
            "message": "FAQ entry not found."
        }), 404

    question = data.get('question', '').strip()
    answer = data.get('answer', '').strip()
    category = data.get('category', '').strip().lower()
    keywords = data.get('keywords', '').strip()
    status = data.get('status', '').strip().lower()

    if 'question' in data and not question:
        return jsonify({
            "status": "error",
            "message": "Question cannot be empty."
        }), 400

    if 'answer' in data and not answer:
        return jsonify({
            "status": "error",
            "message": "Answer cannot be empty."
        }), 400

    if category and category not in Config.CATEGORIES:
        return jsonify({
            "status": "error",
            "message": f"Invalid category. Must be one of: {', '.join(Config.CATEGORIES)}"
        }), 400

    if status and status not in Config.STATUSES:
        return jsonify({
            "status": "error",
            "message": f"Invalid status. Must be one of: {', '.join(Config.STATUSES)}"
        }), 400

    update_payload = {}
    if question:
        update_payload['question'] = question
    if answer:
        update_payload['answer'] = answer
    if category:
        update_payload['category'] = category
    if 'keywords' in data:
        update_payload['keywords'] = keywords
    if status:
        update_payload['status'] = status
    if 'is_active' in data:
        update_payload['is_active'] = bool(data['is_active'])

    updated = db.update_faq(faq_id, update_payload, admin_id=session.get('admin_id'), admin_username=session.get('admin_username', 'admin'))
    return jsonify({
        "status": "success",
        "message": "FAQ updated successfully.",
        "data": updated
    })


@admin_bp.route('/faqs/<faq_id>/status', methods=['PATCH'])
@admin_required
def admin_update_faq_status(faq_id):
    """Update only the status of an FAQ (published, draft, inactive)."""
    data = request.get_json(silent=True) or {}
    new_status = data.get('status', '').strip().lower()

    if new_status not in Config.STATUSES:
        return jsonify({
            "status": "error",
            "message": f"Invalid status '{new_status}'. Allowed: {', '.join(Config.STATUSES)}"
        }), 400

    faq = db.get_faq_by_id(faq_id)
    if not faq:
        return jsonify({
            "status": "error",
            "message": "FAQ entry not found."
        }), 404

    updated = db.update_faq_status(faq_id, new_status, admin_id=session.get('admin_id'), admin_username=session.get('admin_username', 'admin'))
    return jsonify({
        "status": "success",
        "message": f"Status updated to '{new_status}'.",
        "data": updated
    })


@admin_bp.route('/faqs/<faq_id>', methods=['DELETE'])
@admin_required
def admin_delete_faq(faq_id):
    """Delete an FAQ record."""
    faq = db.get_faq_by_id(faq_id)
    if not faq:
        return jsonify({
            "status": "error",
            "message": "FAQ entry not found."
        }), 404

    success = db.delete_faq(faq_id, admin_id=session.get('admin_id'), admin_username=session.get('admin_username', 'admin'))
    if success:
        return jsonify({
            "status": "success",
            "message": "FAQ entry successfully removed."
        })
    else:
        return jsonify({
            "status": "error",
            "message": "Could not remove FAQ entry."
        }), 500


@admin_bp.route('/audit-logs', methods=['GET'])
@admin_required
def admin_audit_logs():
    """Retrieve audit history of administrative changes."""
    logs = db.get_audit_logs()
    return jsonify({
        "status": "success",
        "data": logs,
        "count": len(logs)
    })


# ============================================================================
# Maharashtra Colleges & Cutoffs Data Import Endpoints
# ============================================================================

@admin_bp.route('/import/template', methods=['GET'])
def admin_download_import_template():
    """Download blank CSV template for Maharashtra colleges, courses, fees, and cutoffs."""
    template_path = os.path.join(os.getcwd(), 'templates', 'maharashtra_colleges_cutoffs_template.csv')
    if not os.path.exists(template_path):
        template_path = os.path.join(os.getcwd(), 'assets', 'data', 'maharashtra_colleges_cutoffs_template.csv')
    return send_file(
        template_path,
        mimetype='text/csv',
        as_attachment=True,
        download_name='maharashtra_colleges_cutoffs_template.csv'
    )


@admin_bp.route('/import/sample', methods=['GET'])
def admin_download_import_sample():
    """Download pre-populated sample CSV of authentic Maharashtra colleges and cutoffs."""
    sample_path = os.path.join(os.getcwd(), 'assets', 'data', 'maharashtra_colleges_cutoffs_sample.csv')
    return send_file(
        sample_path,
        mimetype='text/csv',
        as_attachment=True,
        download_name='maharashtra_colleges_cutoffs_sample.csv'
    )


@admin_bp.route('/import/dsy-template', methods=['GET'])
def admin_download_dsy_template():
    """Download official blank CSV template for Direct Second Year Engineering (DSY/DSE) cutoffs."""
    template_path = os.path.join(os.getcwd(), 'assets', 'data', 'maharashtra_dse_cutoffs_template.csv')
    return send_file(
        template_path,
        mimetype='text/csv',
        as_attachment=True,
        download_name='maharashtra_dse_cutoffs_template.csv'
    )


@admin_bp.route('/import/dsy-sample', methods=['GET'])
def admin_download_dsy_sample():
    """Download sample CSV with authentic Maharashtra Direct Second Year Engineering (DSY/DSE) format."""
    sample_path = os.path.join(os.getcwd(), 'assets', 'data', 'maharashtra_dse_cutoffs_sample.csv')
    return send_file(
        sample_path,
        mimetype='text/csv',
        as_attachment=True,
        download_name='maharashtra_dse_cutoffs_sample.csv'
    )


@admin_bp.route('/import/preview', methods=['POST'])
@admin_required
def admin_import_preview():
    """
    Parse and validate uploaded CSV of Maharashtra colleges, courses, and cutoffs.
    Checks required fields, detects duplicate college codes and duplicate cutoffs.
    Returns preview summary and row-by-row validation results.
    """
    csv_text = ""
    source_url = ""
    academic_year = ""
    date_checked = ""

    # Support multipart file upload or JSON payload
    if request.content_type and 'multipart/form-data' in request.content_type:
        uploaded_file = request.files.get('file')
        if not uploaded_file:
            return jsonify({
                "status": "error",
                "message": "No CSV file uploaded. Please select a valid .csv file."
            }), 400
        try:
            csv_text = uploaded_file.read().decode('utf-8', errors='replace')
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Error reading CSV file: {str(e)}"
            }), 400

        source_url = request.form.get('source_url', '')
        academic_year = request.form.get('academic_year', '')
        date_checked = request.form.get('date_checked', '')
    else:
        data = request.get_json(silent=True) or {}
        csv_text = data.get('csv_text', '')
        source_url = data.get('source_url', '')
        academic_year = data.get('academic_year', '')
        date_checked = data.get('date_checked', '')

    if not csv_text:
        return jsonify({
            "status": "error",
            "message": "CSV content is required."
        }), 400

    result = db.preview_csv_import(
        csv_content=csv_text,
        source_url=source_url,
        academic_year=academic_year,
        date_checked=date_checked
    )

    status_code = 200 if result.get("status") == "success" else 400
    return jsonify(result), status_code


@admin_bp.route('/import/commit', methods=['POST'])
@admin_required
def admin_import_commit():
    """
    Commit validated records into the database in 'pending_approval' status.
    Imported records are NOT published until explicitly approved by an administrator.
    """
    data = request.get_json(silent=True) or {}
    valid_rows = data.get('valid_rows', [])
    source_url = data.get('source_url', '').strip()
    academic_year = data.get('academic_year', '').strip()
    date_checked = data.get('date_checked', '').strip()
    batch_name = data.get('batch_name', '').strip()

    if not valid_rows or not isinstance(valid_rows, list):
        return jsonify({
            "status": "error",
            "message": "No valid rows provided for import."
        }), 400

    if not source_url or not academic_year or not date_checked:
        return jsonify({
            "status": "error",
            "message": "Source URL, academic year, and date checked are required metadata."
        }), 400

    admin_username = session.get('admin_username', 'admin')

    try:
        commit_res = db.commit_csv_import(
            valid_rows=valid_rows,
            source_url=source_url,
            academic_year=academic_year,
            date_checked=date_checked,
            batch_name=batch_name,
            admin_username=admin_username
        )
        return jsonify({
            "status": "success",
            "data": commit_res
        }), 201
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to commit import: {str(e)}"
        }), 500


@admin_bp.route('/import/batches', methods=['GET'])
@admin_required
def admin_list_import_batches():
    """List all CSV import batches and their status."""
    status_filter = request.args.get('status', '').strip().lower() or None
    batches = db.get_import_batches(status=status_filter)
    return jsonify({
        "status": "success",
        "data": batches,
        "count": len(batches)
    })


@admin_bp.route('/import/batches/<batch_id>', methods=['GET'])
@admin_required
def admin_get_import_batch(batch_id):
    """Get details and records for an import batch."""
    details = db.get_batch_details(batch_id)
    if not details:
        return jsonify({
            "status": "error",
            "message": f"Import batch '{batch_id}' not found."
        }), 404
    return jsonify({
        "status": "success",
        "data": details
    })


@admin_bp.route('/import/batches/<batch_id>/approve', methods=['POST'])
@admin_required
def admin_approve_import_batch(batch_id):
    """
    Approve all records in an import batch.
    Publishes records to active student recommendations.
    """
    admin_username = session.get('admin_username', 'admin')
    res = db.approve_import_batch(batch_id, admin_username=admin_username)
    return jsonify({
        "status": "success",
        "data": res
    })


@admin_bp.route('/import/batches/<batch_id>/reject', methods=['POST'])
@admin_required
def admin_reject_import_batch(batch_id):
    """Reject an import batch and mark records as rejected."""
    admin_username = session.get('admin_username', 'admin')
    res = db.reject_import_batch(batch_id, admin_username=admin_username)
    return jsonify({
        "status": "success",
        "data": res
    })


@admin_bp.route('/import/cutoffs/<cutoff_id>/approve', methods=['PATCH'])
@admin_required
def admin_approve_single_cutoff(cutoff_id):
    """Approve an individual cutoff record."""
    admin_username = session.get('admin_username', 'admin')
    target = db.approve_cutoff_record(cutoff_id, admin_username=admin_username)
    if not target:
        return jsonify({
            "status": "error",
            "message": f"Cutoff record '{cutoff_id}' not found."
        }), 404
    return jsonify({
        "status": "success",
        "data": target,
        "message": "Cutoff record approved and published."
    })
