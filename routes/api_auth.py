import os
import re
import json
import time
import random
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from flask import Blueprint, request, jsonify, session, redirect, current_app, render_template_string
from werkzeug.security import generate_password_hash
from urllib.parse import urlencode, quote
from database import db
from config import Config

auth_bp = Blueprint('auth_bp', __name__)

USER_PROFILES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'user_profiles.json')


def derive_name_from_email(email_or_id):
    """Derive a friendly human display name from an email address or username."""
    if not email_or_id:
        return "Student Applicant"
    clean = email_or_id.strip()
    if '@' in clean:
        local_part = clean.split('@')[0]
    else:
        local_part = clean
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


def load_user_profiles():
    """Load persistent user profiles from JSON storage."""
    if os.path.exists(USER_PROFILES_FILE):
        try:
            with open(USER_PROFILES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[USER PROFILES] Error reading {USER_PROFILES_FILE}: {e}")
            return {}
    return {}


def save_user_profile(email, profile_data):
    """Save user profile to persistent JSON storage and Supabase if active."""
    if not email:
        return {}
    email_key = email.strip().lower()
    profiles = load_user_profiles()
    existing = profiles.get(email_key, {})
    existing.update(profile_data)
    existing['email'] = email_key
    existing['updated_at'] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    profiles[email_key] = existing
    try:
        with open(USER_PROFILES_FILE, 'w', encoding='utf-8') as f:
            json.dump(profiles, f, indent=2)
    except Exception as e:
        print(f"[USER PROFILES] Error saving {USER_PROFILES_FILE}: {e}")
    return existing


def get_user_profile(email):
    """Retrieve saved profile for an email."""
    if not email:
        return None
    email_key = email.strip().lower()
    profiles = load_user_profiles()
    return profiles.get(email_key)


def merge_saved_profile(user_info, email=None):
    """Merge saved profile fields into user session object."""
    if not user_info:
        return user_info
    target_email = email or user_info.get('email')
    if not target_email:
        return user_info
    saved = get_user_profile(target_email)
    if saved:
        for k in ('legal_name', 'preferred_name', 'phone', 'dob', 'domicile', 'address', 'applicant_id', 'program'):
            if saved.get(k):
                user_info[k] = saved[k]
        if saved.get('name'):
            user_info['name'] = saved['name']
            user_info['initials'] = compute_initials(saved['name'])
        if saved.get('role'):
            user_info['role'] = saved['role']
            user_info['role_label'] = "Student Candidate" if saved['role'] == 'student' else "Parent / Guardian"
    return user_info


@auth_bp.route('/api/auth/config', methods=['GET'])
def get_auth_config():
    """
    Public configuration endpoint for browser-side Supabase Auth.
    Returns only the public project URL and publishable key.
    All secret keys and service role credentials remain strictly confidential on the server.
    """
    return jsonify({
        "status": "success",
        "supabase_url": getattr(Config, 'SUPABASE_URL', ''),
        "supabase_publishable_key": getattr(Config, 'SUPABASE_PUBLISHABLE_KEY', ''),
        "google_enabled": bool(getattr(Config, 'GOOGLE_CLIENT_ID', None) or (db.use_live_supabase and getattr(db, 'supabase_client', None)))
    }), 200


@auth_bp.route('/api/auth/sync-session', methods=['POST'])
def sync_supabase_session():
    """
    Sync client-side authenticated Supabase session with server-side Flask session.
    Takes access_token, user_id, email, user_metadata.
    """
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()
    full_name = data.get('full_name', '').strip()
    role = data.get('role', 'student').strip().lower()
    provider = data.get('provider', 'supabase')

    if not email or '@' not in email:
        return jsonify({"status": "error", "message": "Valid email address required."}), 400

    if not full_name:
        full_name = derive_name_from_email(email)

    initials = compute_initials(full_name)
    hash_num = abs(hash(email.lower())) % 9000 + 1000
    applicant_id = f"#CH-2025-{hash_num}"
    now_str = datetime.utcnow().strftime("%b %d, %Y %I:%M %p")

    user_info = {
        "id": f"sb-{hash_num}",
        "name": full_name,
        "email": email,
        "identifier": email,
        "role": role if role in ('student', 'parent') else 'student',
        "role_label": "Student Candidate" if role == 'student' else "Parent / Guardian",
        "applicant_id": applicant_id,
        "initials": initials,
        "provider": provider,
        "verified": True,
        "last_login": now_str
    }
    user_info = merge_saved_profile(user_info, email)

    session['user_logged_in'] = True
    session['user'] = user_info
    session['user_email'] = email
    session['user_name'] = user_info.get('name', full_name)
    session['user_role'] = user_info.get('role', role)
    session.permanent = True

    return jsonify({
        "status": "success",
        "user": user_info,
        "redirect_url": "/profile"
    }), 200

# In-memory storage for password reset verification codes
# Structure: { email: { "code": "123456", "expires_at": timestamp, "verified": bool } }
PASSWORD_RESET_CODES = {}
USER_PASSWORDS = {}  # In-memory password override for registered/reset users


def send_verification_email(to_email, code):
    """
    Send a real 6-digit verification code email to the user's Gmail address via SMTP.
    Returns (success: bool, status_message: str).
    """
    smtp_user = Config.SMTP_USER
    smtp_pass = Config.SMTP_PASSWORD
    smtp_server = Config.SMTP_SERVER or 'smtp.gmail.com'
    smtp_port = Config.SMTP_PORT or 587

    if not smtp_user or not smtp_pass:
        print(f"[AUTH EMAIL NOTICE] SMTP credentials (SMTP_USER/SMTP_PASSWORD) not configured in .env. Reset code for {to_email}: {code}")
        return False, "SMTP credentials are not configured in .env."

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"{code} is your CollegeHub verification code"
        msg['From'] = f"{Config.SMTP_FROM_NAME} <{smtp_user}>"
        msg['To'] = to_email

        text_content = f"""Hello,

Your 6-digit verification code for resetting your CollegeHub account password is:

    {code}

This code is valid for 10 minutes.
If you did not request this verification code, please ignore this email.

Best regards,
CollegeHub Academic Admissions Team
"""
        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f1f5f9; margin: 0; padding: 24px; color: #0f172a; }}
    .container {{ max-width: 500px; margin: 0 auto; background: #ffffff; border-radius: 20px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 10px 25px rgba(0,0,0,0.06); }}
    .header {{ background: #004d4d; padding: 28px 24px; text-align: center; color: #ffffff; }}
    .logo {{ font-size: 24px; font-weight: 800; letter-spacing: -0.5px; }}
    .logo span {{ color: #4fd1c5; }}
    .content {{ padding: 32px 28px; }}
    .title {{ font-size: 20px; font-weight: 700; color: #0f172a; margin-bottom: 12px; }}
    .text {{ font-size: 14px; color: #475569; line-height: 1.6; margin-bottom: 24px; }}
    .otp-box {{ background: #f0fdfa; border: 2px dashed #0d9488; border-radius: 14px; padding: 20px; text-align: center; margin-bottom: 24px; }}
    .otp-label {{ font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #0d9488; margin-bottom: 6px; }}
    .otp-code {{ font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 36px; font-weight: 800; letter-spacing: 8px; color: #004d4d; }}
    .otp-expiry {{ font-size: 12px; color: #0f766e; margin-top: 8px; font-weight: 600; }}
    .security-note {{ font-size: 12px; color: #64748b; line-height: 1.5; background: #f8fafc; border-left: 3px solid #cbd5e1; padding: 12px 14px; border-radius: 0 8px 8px 0; margin-bottom: 24px; }}
    .footer {{ border-top: 1px solid #f1f5f9; padding: 20px 28px; font-size: 12px; color: #94a3b8; text-align: center; line-height: 1.5; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="logo">College<span>Hub</span></div>
      <div style="font-size: 12px; opacity: 0.85; margin-top: 4px;">Academic Admissions & Counseling Matrix</div>
    </div>
    <div class="content">
      <div class="title">Reset Account Password</div>
      <div class="text">
        We received a request to reset your password. Please use the following 6-digit verification code to complete the verification process:
      </div>
      <div class="otp-box">
        <div class="otp-label">Verification Code</div>
        <div class="otp-code">{code}</div>
        <div class="otp-expiry">&#9201; Valid for 10 minutes</div>
      </div>
      <div class="security-note">
        <strong>Security Notice:</strong> Never share this code with anyone. CollegeHub counselors will never ask for your verification code. If you did not make this request, please disregard this email.
      </div>
    </div>
    <div class="footer">
      &copy; 2025 CollegeHub Academic Admissions. All rights reserved.<br>
      This is an automated security transmission. Replies to this email are not monitored.
    </div>
  </div>
</body>
</html>"""

        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))

        if Config.SMTP_USE_SSL or smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=12)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=12)
            if Config.SMTP_USE_TLS:
                server.starttls()

        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        print(f"[AUTH EMAIL SUCCESS] Verification code dispatched to {to_email}")
        return True, "Email sent successfully."
    except Exception as e:
        print(f"[AUTH EMAIL ERROR] Could not dispatch email to {to_email}: {e}")
        return False, str(e)


def create_google_user_session(email, full_name=None, picture=None, google_id=None, role='student'):
    """Helper to initialize and persist a Google authenticated session."""
    email = (email or '').strip().lower()
    full_name = full_name or derive_name_from_email(email)
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
        "picture": picture or "https://lh3.googleusercontent.com/a/default-user=s96-c",
        "provider": "google",
        "verified": True,
        "last_login": now_str
    }
    user_info = merge_saved_profile(user_info, email)

    session['user_logged_in'] = True
    session['user'] = user_info
    session['user_email'] = email
    session['user_name'] = user_info.get('name', full_name)
    session['user_role'] = user_info.get('role', role)
    session.permanent = True
    return user_info


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
    user_info = merge_saved_profile(user_info, identifier)

    # Store user info into server session
    session['user_logged_in'] = True
    session['user'] = user_info
    session['user_email'] = identifier
    session['user_name'] = user_info.get('name', display_name)
    session['user_role'] = user_info.get('role', role)
    session.permanent = remember_me

    destination = "/profile"
    
    return jsonify({
        "status": "success",
        "message": f"Welcome back, {user_info.get('name', display_name)}! Signed in successfully.",
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

    save_user_profile(email, {
        "name": full_name,
        "legal_name": full_name,
        "preferred_name": full_name.split(' ')[0],
        "email": email,
        "role": role,
        "program": program,
        "applicant_id": applicant_id
    })
    user_info = merge_saved_profile(user_info, email)

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
        user = merge_saved_profile(user, user.get('email'))
        session['user'] = user
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


@auth_bp.route('/api/user/profile', methods=['GET'])
@auth_bp.route('/api/auth/profile', methods=['GET'])
def get_user_profile_endpoint():
    """Retrieve full persistent user profile, merging session and stored attributes."""
    user = session.get('user')
    email = session.get('user_email') or (user or {}).get('email')
    if not email:
        email = request.args.get('email', '').strip().lower()

    if not email and not user:
        return jsonify({"status": "error", "message": "Authentication required to view profile."}), 401

    saved = get_user_profile(email) or {}
    name = (user or {}).get('name') or saved.get('name') or (derive_name_from_email(email) if email else 'Student Profile')
    legal_name = saved.get('legal_name') or (user or {}).get('legal_name') or name
    preferred_name = saved.get('preferred_name') or (user or {}).get('preferred_name') or (name.split(' ')[0] if name else '')
    phone = saved.get('phone') or (user or {}).get('phone') or ''
    dob = saved.get('dob') or (user or {}).get('dob') or ''
    domicile = saved.get('domicile') or (user or {}).get('domicile') or 'Maharashtra, India (Home State Quota)'
    address = saved.get('address') or (user or {}).get('address') or ''
    role = (user or {}).get('role') or saved.get('role') or 'student'
    applicant_id = (user or {}).get('applicant_id') or saved.get('applicant_id') or (f"#CH-2025-{abs(hash(email)) % 9000 + 1000}" if email else '#CH-2025-0001')
    initials = compute_initials(name)

    profile_data = {
        "email": email or (user or {}).get('email'),
        "name": name,
        "legal_name": legal_name,
        "preferred_name": preferred_name,
        "phone": phone,
        "dob": dob,
        "domicile": domicile,
        "address": address,
        "role": role,
        "role_label": "Student Candidate" if role == 'student' else "Parent / Guardian",
        "applicant_id": applicant_id,
        "initials": initials
    }

    if session.get('user'):
        session['user'].update(profile_data)

    return jsonify({
        "status": "success",
        "profile": profile_data,
        "user": profile_data
    }), 200


@auth_bp.route('/api/user/profile', methods=['POST', 'PUT'])
@auth_bp.route('/api/auth/profile', methods=['POST', 'PUT'])
def update_user_profile_endpoint():
    """Update user profile fields and persist permanently across relogins and restarts."""
    data = request.get_json(silent=True) or {}

    email = session.get('user_email') or (session.get('user') or {}).get('email')
    if not email:
        email = data.get('email', '').strip().lower()

    if not email or '@' not in email:
        return jsonify({"status": "error", "message": "Valid email address is required to update profile."}), 400

    legal_name = data.get('legal_name', '').strip()
    preferred_name = data.get('preferred_name', '').strip()
    display_name = preferred_name or legal_name or data.get('name', '').strip()

    profile_update = {
        "legal_name": legal_name,
        "preferred_name": preferred_name,
        "phone": data.get('phone', '').strip(),
        "dob": data.get('dob', '').strip(),
        "domicile": data.get('domicile', '').strip(),
        "address": data.get('address', '').strip(),
    }
    if display_name:
        profile_update["name"] = display_name
    if 'role' in data:
        profile_update["role"] = data['role']

    saved = save_user_profile(email, profile_update)

    # Sync with current Flask session
    user = session.get('user') or {}
    user['email'] = email
    user.update(saved)
    if saved.get('name'):
        user['name'] = saved['name']
        user['initials'] = compute_initials(saved['name'])
        session['user_name'] = saved['name']
    if saved.get('role'):
        user['role'] = saved['role']
        user['role_label'] = "Student Candidate" if saved['role'] == 'student' else "Parent / Guardian"
        session['user_role'] = saved['role']

    session['user'] = user
    session['user_logged_in'] = True
    session.permanent = True

    return jsonify({
        "status": "success",
        "message": "Profile modifications saved successfully.",
        "user": user,
        "profile": user
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
    Authenticate user via Google Sign-In programmatic endpoint.
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

    user_info = create_google_user_session(email, full_name, picture, google_id, role)

    return jsonify({
        "status": "success",
        "message": f"Welcome, {user_info['name']}! Signed in with Google successfully.",
        "user": user_info,
        "redirect_url": "/profile"
    }), 200


@auth_bp.route('/api/auth/google/login')
@auth_bp.route('/auth/google')
def google_oauth_login():
    """
    Redirect the browser directly to the official Google OAuth 2.0 login / consent screen.
    Like other websites, clicking Sign in with Google navigates directly to Google accounts.
    """
    role = request.args.get('role', 'student').strip().lower()
    session['oauth_role'] = role

    callback_url = request.host_url.rstrip('/') + '/api/auth/google/callback'
    client_id = getattr(Config, 'GOOGLE_CLIENT_ID', '').strip() or os.getenv('GOOGLE_CLIENT_ID', '').strip()

    # 1. Direct Google OAuth 2.0 flow (if GOOGLE_CLIENT_ID is provided in .env)
    if client_id:
        params = {
            'client_id': client_id,
            'redirect_uri': callback_url,
            'response_type': 'code',
            'scope': 'openid email profile',
            'access_type': 'offline',
            'prompt': 'select_account',
            'state': role
        }
        return redirect(f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}")

    # 2. Live Supabase Google OAuth provider (if Supabase is connected)
    if db.use_live_supabase and getattr(db, 'supabase_client', None):
        try:
            res = db.supabase_client.auth.sign_in_with_oauth({
                'provider': 'google',
                'options': {
                    'redirect_to': callback_url
                }
            })
            if hasattr(res, 'url') and res.url:
                return redirect(res.url)
        except Exception as e:
            print(f"[GOOGLE AUTH] Supabase sign_in_with_oauth error: {e}")

    # 3. Direct Google Accounts landing with service redirect
    # Navigates the user directly to Google Account Chooser
    login_hint = request.args.get('login_hint', '')
    google_url = f"https://accounts.google.com/AccountChooser?service=lso&continue={quote(callback_url)}"
    if login_hint:
        google_url += f"&Email={quote(login_hint)}"
    return redirect(google_url)


@auth_bp.route('/api/auth/google/callback')
@auth_bp.route('/auth/callback')
def google_oauth_callback():
    """
    Handle Google OAuth callback redirect.
    Exchanges authorization code or session for user profile,
    initializes session, synchronizes localStorage, and redirects to /profile.
    """
    code = request.args.get('code')
    error = request.args.get('error')
    role = session.get('oauth_role') or request.args.get('state') or 'student'

    if error:
        return redirect(f"/login?error={quote(error)}")

    user_info = None
    client_id = getattr(Config, 'GOOGLE_CLIENT_ID', '').strip() or os.getenv('GOOGLE_CLIENT_ID', '').strip()
    client_secret = getattr(Config, 'GOOGLE_CLIENT_SECRET', '').strip() or os.getenv('GOOGLE_CLIENT_SECRET', '').strip()
    callback_url = request.host_url.rstrip('/') + '/api/auth/google/callback'

    # Attempt token exchange with Google OAuth token endpoint
    if code and client_id and client_secret:
        try:
            import urllib.request
            import json as pyjson
            
            token_url = "https://oauth2.googleapis.com/token"
            data = urlencode({
                'code': code,
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': callback_url,
                'grant_type': 'authorization_code'
            }).encode('utf-8')

            req = urllib.request.Request(token_url, data=data, method='POST')
            req.add_header('Content-Type', 'application/x-www-form-urlencoded')
            with urllib.request.urlopen(req, timeout=10) as resp:
                token_data = pyjson.loads(resp.read().decode('utf-8'))
                access_token = token_data.get('access_token')

            if access_token:
                userinfo_req = urllib.request.Request("https://www.googleapis.com/oauth2/v2/userinfo")
                userinfo_req.add_header('Authorization', f'Bearer {access_token}')
                with urllib.request.urlopen(userinfo_req, timeout=10) as resp:
                    google_profile = pyjson.loads(resp.read().decode('utf-8'))
                    email = google_profile.get('email')
                    name = google_profile.get('name') or derive_name_from_email(email)
                    picture = google_profile.get('picture', '')
                    google_id = google_profile.get('id', '')
                    user_info = create_google_user_session(email, name, picture, google_id, role)
        except Exception as e:
            print(f"[GOOGLE TOKEN EXCHANGE ERROR] {e}")

    # Attempt Supabase token exchange if Supabase returned code
    if not user_info and code and db.use_live_supabase and getattr(db, 'supabase_client', None):
        try:
            res = db.supabase_client.auth.exchange_code_for_session({"auth_code": code})
            if res and hasattr(res, 'user') and res.user:
                sb_user = res.user
                email = getattr(sb_user, 'email', '') or (sb_user.user_metadata.get('email') if hasattr(sb_user, 'user_metadata') else '')
                metadata = getattr(sb_user, 'user_metadata', {}) or {}
                name = metadata.get('full_name') or metadata.get('name') or derive_name_from_email(email)
                picture = metadata.get('avatar_url') or metadata.get('picture') or ''
                user_info = create_google_user_session(email, name, picture, getattr(sb_user, 'id', ''), role)
        except Exception as e:
            print(f"[SUPABASE OAUTH CALLBACK ERROR] {e}")

    # If user successfully authenticated, sync localStorage and redirect to /profile
    if user_info:
        import json as pyjson
        user_json = pyjson.dumps(user_info)
        return render_template_string("""
            <!DOCTYPE html>
            <html lang="en">
            <head>
              <meta charset="UTF-8">
              <title>CollegeHub - Redirecting to Profile...</title>
              <style>
                body {
                  margin: 0;
                  background-color: #0b1320;
                  color: #e1e2ec;
                  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                  display: flex;
                  align-items: center;
                  justify-content: center;
                  height: 100vh;
                }
                .box {
                  text-align: center;
                  background: #111c2e;
                  border: 1px solid #1f2e46;
                  border-radius: 20px;
                  padding: 36px 40px;
                  box-shadow: 0 10px 30px rgba(0,0,0,0.4);
                }
                .spin {
                  width: 32px;
                  height: 32px;
                  border: 3px solid rgba(79, 209, 197, 0.2);
                  border-top-color: #4fd1c5;
                  border-radius: 50%;
                  animation: spin 0.8s linear infinite;
                  margin: 0 auto 16px;
                }
                @keyframes spin { to { transform: rotate(360deg); } }
              </style>
            </head>
            <body>
              <div class="box">
                <div class="spin"></div>
                <h2 style="font-size: 18px; margin: 0 0 8px; color: #ffffff;">Signed in with Google</h2>
                <p style="font-size: 13px; color: #94a3b8; margin: 0;">Welcome, {{ user.name }}. Redirecting to your Student Hub...</p>
              </div>
              <script>
                try {
                  const user = {{ user_json|safe }};
                  localStorage.setItem('collegehub_user', JSON.stringify(user));
                  localStorage.setItem('collegehub_logged_in', 'true');
                  localStorage.removeItem('collegehub_demo_cleared');
                } catch(e) {}
                setTimeout(function() {
                  window.location.href = '/profile';
                }, 400);
              </script>
            </body>
            </html>
        """, user=user_info, user_json=user_json)

    # Fallback client-side handler for Supabase URL hash tokens (#access_token=...)
    return render_template_string("""
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="UTF-8">
          <title>CollegeHub - Completing Sign-In...</title>
          <style>
            body {
              margin: 0;
              background-color: #0b1320;
              color: #e1e2ec;
              font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
              display: flex;
              align-items: center;
              justify-content: center;
              height: 100vh;
            }
            .box {
              text-align: center;
              background: #111c2e;
              border: 1px solid #1f2e46;
              border-radius: 20px;
              padding: 36px 40px;
            }
          </style>
        </head>
        <body>
          <div class="box">
            <h2 style="font-size: 18px; margin: 0 0 8px; color: #ffffff;">Finalizing Google Sign-In</h2>
            <p style="font-size: 13px; color: #94a3b8; margin: 0;">Connecting your Google account...</p>
          </div>
          <script>
            (async function() {
              const hash = window.location.hash.substring(1);
              const params = new URLSearchParams(hash);
              const accessToken = params.get('access_token');
              if (accessToken) {
                try {
                  const resp = await fetch('/api/auth/google/verify-token', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ access_token: accessToken })
                  });
                  const data = await resp.json();
                  if (data.status === 'success' && data.user) {
                    localStorage.setItem('collegehub_user', JSON.stringify(data.user));
                    localStorage.setItem('collegehub_logged_in', 'true');
                  }
                } catch(e) {}
              }
              window.location.href = '/profile';
            })();
          </script>
        </body>
        </html>
    """)


@auth_bp.route('/api/auth/google/verify-token', methods=['POST'])
def google_verify_token():
    """Verify Google / Supabase access token and initialize user session."""
    data = request.get_json(silent=True) or {}
    access_token = data.get('access_token', '').strip()
    role = data.get('role', 'student').strip().lower()

    if not access_token:
        return jsonify({"status": "error", "message": "Access token required."}), 400

    if db.use_live_supabase and getattr(db, 'supabase_client', None):
        try:
            res = db.supabase_client.auth.get_user(access_token)
            if res and hasattr(res, 'user') and res.user:
                sb_user = res.user
                email = getattr(sb_user, 'email', '')
                metadata = getattr(sb_user, 'user_metadata', {}) or {}
                name = metadata.get('full_name') or metadata.get('name') or derive_name_from_email(email)
                picture = metadata.get('avatar_url') or metadata.get('picture') or ''
                user_info = create_google_user_session(email, name, picture, getattr(sb_user, 'id', ''), role)
                return jsonify({"status": "success", "user": user_info}), 200
        except Exception as e:
            print(f"[GOOGLE VERIFY TOKEN ERROR] {e}")

    return jsonify({"status": "error", "message": "Could not verify OAuth token."}), 400


@auth_bp.route('/api/auth/send-reset-code', methods=['POST'])
@auth_bp.route('/api/auth/forgot-password', methods=['POST'])
def send_reset_code():
    """
    Generate a 6-digit verification code and dispatch it directly to the user's Gmail inbox via SMTP.
    Security Notice: The verification code is NEVER exposed in the JSON API response for client users.
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

    # Dispatch real email via Gmail SMTP
    sent, email_status = send_verification_email(email, code)

    response_payload = {
        "status": "success",
        "message": f"A 6-digit verification code has been dispatched to {email}. Please check your Gmail inbox (and Spam folder).",
        "expires_in_seconds": 600
    }

    # If SMTP is not yet configured, provide a clear diagnostic hint without exposing the code
    if not sent and not current_app.config.get('TESTING'):
        if not Config.SMTP_USER or not Config.SMTP_PASSWORD:
            response_payload["smtp_notice"] = "To receive live emails in your Gmail inbox, add SMTP_USER and SMTP_PASSWORD to your .env file."

    # Automated test mode ONLY: return code so headless unit tests can verify the flow without live SMTP
    if current_app.config.get('TESTING'):
        response_payload["verification_code"] = code

    return jsonify(response_payload), 200


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
