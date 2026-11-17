import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'collegehub-super-secret-key-2025')
    SUPABASE_URL = os.getenv('SUPABASE_URL', '').strip()
    SUPABASE_KEY = os.getenv('SUPABASE_KEY', '').strip()

    # Pre-configured authorized admin credentials
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin').strip()
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admincollegehub').strip()

    # The 8 authorized FAQ categories required by CollegeHub
    CATEGORIES = [
        'admissions',
        'courses',
        'fees',
        'cutoffs',
        'placements',
        'examinations',
        'departments',
        'facilities'
    ]

    STATUSES = ['published', 'draft', 'inactive']
