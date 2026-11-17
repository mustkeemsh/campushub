import os
from flask import Blueprint, send_from_directory, session, redirect, url_for, current_app

views_bp = Blueprint('views_bp', __name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')


@views_bp.route('/')
def home():
    """Serve the public Home page."""
    return send_from_directory(BASE_DIR, 'index.html')


@views_bp.route('/index.html')
def home_alias():
    return redirect(url_for('views_bp.home'))


@views_bp.route('/faqs')
def faqs():
    """Serve the public FAQs and Chatbot page."""
    return send_from_directory(BASE_DIR, 'faqs.html')


@views_bp.route('/faqs.html')
def faqs_alias():
    return redirect(url_for('views_bp.faqs'))


@views_bp.route('/about')
def about():
    """Serve the About page."""
    return send_from_directory(BASE_DIR, 'about.html')


@views_bp.route('/about.html')
def about_alias():
    return redirect(url_for('views_bp.about'))


@views_bp.route('/admin-login')
def admin_login():
    """Serve the Administrator Sign-In page."""
    if session.get('admin_logged_in'):
        return redirect(url_for('views_bp.admin'))
    return send_from_directory(BASE_DIR, 'admin-login.html')


@views_bp.route('/admin-login.html')
def admin_login_alias():
    return redirect(url_for('views_bp.admin_login'))


@views_bp.route('/admin')
def admin():
    """Serve the Protected Admin Dashboard page."""
    # Check if admin session exists
    if not session.get('admin_logged_in'):
        return redirect(url_for('views_bp.admin_login'))
    return send_from_directory(BASE_DIR, 'admin.html')


@views_bp.route('/admin.html')
def admin_alias():
    return redirect(url_for('views_bp.admin'))


@views_bp.route('/login')
@views_bp.route('/login.html')
@views_bp.route('/signin')
@views_bp.route('/signin.html')
def login():
    """Serve the unified Login and Sign In page."""
    # If login.html exists serve it, otherwise signin.html
    target = 'login.html' if os.path.exists(os.path.join(BASE_DIR, 'login.html')) else 'signin.html'
    return send_from_directory(BASE_DIR, target)


@views_bp.route('/signup')
@views_bp.route('/signup.html')
def signup():
    """Serve the Sign Up demo page."""
    return send_from_directory(BASE_DIR, 'signup.html')


@views_bp.route('/reset-password')
@views_bp.route('/reset-password.html')
def reset_password():
    """Serve the dedicated Reset Password page."""
    return send_from_directory(BASE_DIR, 'reset-password.html')


@views_bp.route('/profile')
@views_bp.route('/profile.html')
def profile():
    """Serve the Student Profile / Application Hub demo page."""
    return send_from_directory(BASE_DIR, 'profile.html')


@views_bp.route('/vault')
@views_bp.route('/vault.html')
def vault_redirect():
    """Redirect retired document vault page to student profile."""
    return redirect(url_for('views_bp.profile'))


@views_bp.route('/saved')
@views_bp.route('/saved.html')
def saved():
    """Serve the Saved FAQs & Counselor Chats demo page."""
    return send_from_directory(BASE_DIR, 'saved.html')


@views_bp.route('/recommendations')
@views_bp.route('/recommendations.html')
@views_bp.route('/predictor')
@views_bp.route('/predictor.html')
@views_bp.route('/college-predictor')
def recommendations():
    """Serve the Student Profile -> College Predictor flow."""
    return send_from_directory(BASE_DIR, 'recommendations.html')


@views_bp.route('/settings')
@views_bp.route('/settings.html')
def settings():
    """Serve the Account Settings & Security demo page."""
    return send_from_directory(BASE_DIR, 'settings.html')


@views_bp.route('/assets/<path:filename>')
def serve_assets(filename):
    """Serve static media, logos, and stylesheets."""
    return send_from_directory(ASSETS_DIR, filename)
