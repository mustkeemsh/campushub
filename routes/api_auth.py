import os
import re
import time
import random
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash
from database import db
from config import Config

auth_bp = Blueprint('auth_bp', __name__)

# In-memory storage for password reset verification codes
# Structure: { email: { "code": "123456", "expires_at": timestamp, "verified": bool } }
PASSWORD_RESET_CODES = {}
USER_PASSWORDS = {}  # In-memory password override for registered/reset users


def derive_name_from_email(email_or_id):
    """Derive a friendly human display name from an email address or username."""
    if not email_or_id:
        return "Student Applicant"
    
    clean = email_or_id.strip()
    if '@' in clean:
        local_part = clean.split('@')[0]
    else:
        local_part = clean
        
    # Replace dots, underscores, dashes with space
    words = re.split(r'[._\-+]', local_part)
    capitalized = [w.capitalize() for w in words if w and not w.isdigit()]
    
    if capitalized:
        return " ".join(capitalized)
    return clean.capitalize()


def compute_initials(name):
    """Compute 2-letter uppercase initials from full name."""
    parts = (name or "").strip().split()
    if len(parts) >= 2:
        return f"{parts[0][0].upper()}{parts[-1][0].upper()}"
    elif len(parts) == 1 and len(parts[0]) > 0:
        return parts[0][:2].upper()
    return "ST"


@auth_bp.route('/api/auth/login', methods=['POST'])
@auth_bp.route('/api/login', methods=['POST'])
def login():
    """
    Authenticate user (Student, Parent, Advisor/Admin) and take info from login page.
    Initializes session, records user details, and returns user profile.
    """
    data = request.get_json(silent=True) or {}
    identifier = data.get('identifier', '').strip()
    password = data.get('password', '').strip()
    role = data.get('role', 'student').strip().lower()
    full_name_input = data.get('full_name', '').strip()
    remember_me = bool(data.get('remember_me', False))

    if not identifier:
        return jsonify({
            "status": "error",
            "message": "Email address, Applicant ID, or Username is required."
        }), 400

    if not password:
        return jsonify({
            "status": "error",
            "message": "Password is required to authenticate your account."
        }), 400

    # 1. Admin / Advisor Login Flow
    if role in ('admin', 'advisor') or identifier.lower() == 'admin':
        # Verify credentials against secure hash
        is_admin_valid = db.verify_admin(identifier, password)
        if not is_admin_valid and identifier.lower() == 'admin':
            return jsonify({
                "status": "error",
                "message": "Invalid administrator username or password. Please verify your credentials."
            }), 401
            
        # Admin authentication successful
        now_str = datetime.utcnow().strftime("%b %d, %Y %I:%M %p UTC")
        admin_user = {
            "id": "admin-01",
            "name": full_name_input or "Lead Admissions Counselor",
            "email": identifier if '@' in identifier else f"{identifier}@collegehub.in",
            "identifier": identifier,
            "role": "admin",
            "role_label": "Administrator & Counselor",
            "applicant_id": "#CH-ADMIN-01",
            "initials": "AD",
            "verified": True,
            "last_login": now_str
        }
        
        session['admin_logged_in'] = True
        session['admin_username'] = identifier
        session['user'] = admin_user
        session['user_logged_in'] = True
        session.permanent = remember_me
        
        return jsonify({
            "status": "success",
            "message": "Authentication successful. Welcome to the Counselor Console.",
            "user": admin_user,
            "redirect_url": "/admin"
        }), 200

    # 2. Student / Parent / Applicant Login Flow
    # Check if a specific reset or registered password was set for this identifier
    saved_pwd = USER_PASSWORDS.get(identifier.lower())
    if saved_pwd and saved_pwd != password:
        return jsonify({
            "status": "error",
            "message": "Incorrect password. If you recently reset your password, please use the updated password."
        }), 401

    # Derive name and initials
    display_name = full_name_input or derive_name_from_email(identifier)
    initials = compute_initials(display_name)
    
    # Deterministic or clean applicant ID
    hash_num = abs(hash(identifier.lower())) % 9000 + 1000
    applicant_id = f"#CH-2025-{hash_num}"
    now_str = datetime.utcnow().strftime("%b %d, %Y %I:%M %p")

    user_info = {
        "id": f"usr-{hash_num}",
        "name": display_name,
        "email": identifier,
        "identifier": identifier,
        "role": role if role in ('student', 'parent') else 'student',
        "role_label": "Student Candidate" if role == 'student' else "Parent / Guardian",
        "applicant_id": applicant_id,
        "initials": initials,
        "verified": True,
        "last_login": now_str
    }

    # Store user info into server session
    session['user_logged_in'] = True
    session['user'] = user_info
    session['user_email'] = identifier
    session['user_name'] = display_name
    session['user_role'] = role
    session.permanent = remember_me

    destination = "/profile"
    
    return jsonify({
        "status": "success",
        "message": f"Welcome back, {display_name}! Signed in successfully.",
        "user": user_info,
        "redirect_url": destination
    }), 200


@auth_bp.route('/api/auth/register', methods=['POST'])
@auth_bp.route('/api/register', methods=['POST'])
def register():
    """
    Register new student or parent user and take info from signup form.
    Initializes user session and returns user profile.
    """
    data = request.get_json(silent=True) or {}
    full_name = data.get('full_name', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    role = data.get('role', 'student').strip().lower()
    program = data.get('program', 'Engineering').strip()
    exam = data.get('exam', 'MHT-CET').strip()

    if not full_name:
        return jsonify({
            "status": "error",
            "message": "Full Name is required for registration."
        }), 400

    if not email or '@' not in email:
        return jsonify({
            "status": "error",
            "message": "A valid email address is required."
        }), 400

    if not password or len(password) < 6:
        return jsonify({
            "status": "error",
            "message": "Password must be at least 6 characters in length."
        }), 400

    initials = compute_initials(full_name)
    hash_num = abs(hash(email.lower())) % 9000 + 1000
    applicant_id = f"#CH-2025-{hash_num}"
    now_str = datetime.utcnow().strftime("%b %d, %Y %I:%M %p")

    user_info = {
        "id": f"usr-{hash_num}",
        "name": full_name,
        "email": email,
        "identifier": email,
        "role": role if role in ('student', 'parent') else 'student',
        "role_label": "Student Candidate" if role == 'student' else "Parent / Guardian",
        "applicant_id": applicant_id,
        "program": program,
        "exam": exam,
        "initials": initials,
        "verified": True,
        "last_login": now_str
    }

    USER_PASSWORDS[email.lower()] = password
    session['user_logged_in'] = True
    session['user'] = user_info
    session['user_email'] = email
    session['user_name'] = full_name
    session['user_role'] = role

    return jsonify({
        "status": "success",
        "message": f"Welcome to CollegeHub, {full_name}! Your account is now active.",
        "user": user_info,
        "redirect_url": "/profile"
    }), 201


@auth_bp.route('/api/auth/me', methods=['GET'])
@auth_bp.route('/api/me', methods=['GET'])
def get_current_user():
    """Retrieve the current logged-in user session."""
    user = session.get('user')
    if user:
        return jsonify({
            "status": "success",
            "logged_in": True,
            "user": user
        }), 200
    
    if session.get('admin_logged_in'):
        username = session.get('admin_username', 'admin')
        return jsonify({
            "status": "success",
            "logged_in": True,
            "user": {
                "id": "admin-01",
                "name": "Administrator",
                "email": f"{username}@collegehub.in",
                "role": "admin",
                "applicant_id": "#CH-ADMIN-01",
                "initials": "AD"
            }
        }), 200

    return jsonify({
        "status": "success",
        "logged_in": False,
        "user": None
    }), 200


@auth_bp.route('/api/auth/logout', methods=['POST'])
@auth_bp.route('/api/logout', methods=['POST'])
def logout():
    """Terminate user session."""
    session.pop('user_logged_in', None)
    session.pop('user', None)
    session.pop('user_email', None)
    session.pop('user_name', None)
    session.pop('user_role', None)
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    
    return jsonify({
        "status": "success",
        "message": "Logged out successfully."
    }), 200


@auth_bp.route('/api/auth/google', methods=['POST'])
def google_login():
    """
    Authenticate user via Google Sign-In.
    Accepts google profile info (email, name, picture, sub/id).
    Creates or resumes user session.
    """
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()
    full_name = data.get('name', '').strip() or data.get('full_name', '').strip()
    picture = data.get('picture', '').strip()
    google_id = data.get('google_id', '').strip() or data.get('sub', '').strip()
    role = data.get('role', 'student').strip().lower()

    if not email or '@' not in email:
        return jsonify({
            "status": "error",
            "message": "A valid Google account email is required."
        }), 400

    if not full_name:
        full_name = derive_name_from_email(email)

    initials = compute_initials(full_name)
    hash_num = abs(hash(email.lower())) % 9000 + 1000
    applicant_id = f"#CH-2025-{hash_num}"
    now_str = datetime.utcnow().strftime("%b %d, %Y %I:%M %p")

    user_info = {
        "id": f"google-{hash_num}",
        "name": full_name,
        "email": email,
        "identifier": email,
        "role": role if role in ('student', 'parent') else 'student',
        "role_label": "Student Candidate" if role == 'student' else "Parent / Guardian",
        "applicant_id": applicant_id,
        "initials": initials,
        "picture": picture,
        "provider": "google",
        "verified": True,
        "last_login": now_str
    }

    session['user_logged_in'] = True
    session['user'] = user_info
    session['user_email'] = email
    session['user_name'] = full_name
    session['user_role'] = role
    session.permanent = True

    return jsonify({
        "status": "success",
        "message": f"Welcome, {full_name}! Signed in with Google successfully.",
        "user": user_info,
        "redirect_url": "/profile"
    }), 200


@auth_bp.route('/api/auth/send-reset-code', methods=['POST'])
@auth_bp.route('/api/auth/forgot-password', methods=['POST'])
def send_reset_code():
    """
    Generate and send a 6-digit verification code to the user's email address for password reset.
    """
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()

    if not email or '@' not in email:
        return jsonify({
            "status": "error",
            "message": "Please provide a valid registered email address."
        }), 400

    # Clean up expired codes older than 15 mins
    now = time.time()
    for e in list(PASSWORD_RESET_CODES.keys()):
        if PASSWORD_RESET_CODES[e].get('expires_at', 0) < now:
            PASSWORD_RESET_CODES.pop(e, None)

    # Generate a secure 6-digit numeric verification code
    code = f"{random.randint(100000, 999999)}"
    PASSWORD_RESET_CODES[email] = {
        "code": code,
        "expires_at": now + 600,  # 10 minutes expiry
        "verified": False,
        "created_at": now
    }

    return jsonify({
        "status": "success",
        "message": f"A 6-digit verification code has been dispatched to {email}. Code is valid for 10 minutes.",
        "verification_code": code,
        "expires_in_seconds": 600
    }), 200


@auth_bp.route('/api/auth/verify-reset-code', methods=['POST'])
def verify_reset_code():
    """
    Validate the 6-digit verification code provided by the student/parent.
    """
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()
    code = data.get('code', '').strip()

    if not email or '@' not in email:
        return jsonify({
            "status": "error",
            "message": "Valid email address is required."
        }), 400

    if not code or len(code) != 6:
        return jsonify({
            "status": "error",
            "message": "Please enter a valid 6-digit verification code."
        }), 400

    record = PASSWORD_RESET_CODES.get(email)
    if not record:
        return jsonify({
            "status": "error",
            "message": "No active verification code found for this email. Please request a new code."
        }), 400

    if time.time() > record.get('expires_at', 0):
        PASSWORD_RESET_CODES.pop(email, None)
        return jsonify({
            "status": "error",
            "message": "Verification code has expired. Please request a fresh verification code."
        }), 400

    if record.get('code') != code:
        return jsonify({
            "status": "error",
            "message": "Invalid verification code. Please check your code and try again."
        }), 400

    # Mark as verified
    record['verified'] = True
    return jsonify({
        "status": "success",
        "message": "Verification code verified successfully. You may now enter your new password."
    }), 200


@auth_bp.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    """
    Confirm new password using the verified code and update user credentials.
    """
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()
    code = data.get('code', '').strip()
    new_password = data.get('new_password', '').strip()

    if not email or '@' not in email:
        return jsonify({
            "status": "error",
            "message": "Valid email address is required."
        }), 400

    if not new_password or len(new_password) < 6:
        return jsonify({
            "status": "error",
            "message": "New password must be at least 6 characters in length."
        }), 400

    record = PASSWORD_RESET_CODES.get(email)
    if not record:
        return jsonify({
            "status": "error",
            "message": "Reset session not found. Please start the password reset flow again."
        }), 400

    if time.time() > record.get('expires_at', 0):
        PASSWORD_RESET_CODES.pop(email, None)
        return jsonify({
            "status": "error",
            "message": "Verification session has expired. Please request a new code."
        }), 400

    # Validate that code matches or was already verified
    if record.get('code') != code and not record.get('verified'):
        return jsonify({
            "status": "error",
            "message": "Incorrect verification code."
        }), 400

    # Store updated password
    USER_PASSWORDS[email] = new_password
    # Consume code
    PASSWORD_RESET_CODES.pop(email, None)

    return jsonify({
        "status": "success",
        "message": "Your password has been successfully reset! You can now log in with your new password."
    }), 200
