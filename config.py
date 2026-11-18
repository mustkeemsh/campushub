import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'collegehub-super-secret-key-2025')
    SUPABASE_URL = os.getenv('SUPABASE_URL', '').strip()
    SUPABASE_KEY = os.getenv('SUPABASE_KEY', '').strip()
    SUPABASE_PUBLISHABLE_KEY = os.getenv('SUPABASE_PUBLISHABLE_KEY', '').strip()

    # Pre-configured authorized admin credentials
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin').strip()
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admincollegehub').strip()

    # Google OAuth 2.0 Credentials
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '').strip()
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '').strip()

    # Mail & Gmail SMTP Configuration
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com').strip()
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USER = os.getenv('SMTP_USER', '').strip()
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '').strip()
    SMTP_FROM_NAME = os.getenv('SMTP_FROM_NAME', 'CollegeHub Admissions').strip()
    SMTP_USE_TLS = os.getenv('SMTP_USE_TLS', 'true').strip().lower() in ('true', '1', 'yes')
    SMTP_USE_SSL = os.getenv('SMTP_USE_SSL', 'false').strip().lower() in ('true', '1', 'yes')

    # AI chatbot. Set ONE key. With no key the chatbot runs in key-free mode (CAP data + FAQs only).
    # CHATBOT_PROVIDER: auto | gemini | anthropic | openai  (auto = first key found)
    CHATBOT_PROVIDER = os.getenv('CHATBOT_PROVIDER', 'auto').strip().lower()
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '').strip()
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash').strip()
    # Any OpenAI-compatible service (Groq, OpenRouter, a local Ollama server, ...)
    OPENAI_COMPAT_BASE_URL = os.getenv('OPENAI_COMPAT_BASE_URL', '').strip().rstrip('/')
    OPENAI_COMPAT_API_KEY = os.getenv('OPENAI_COMPAT_API_KEY', '').strip()
    OPENAI_COMPAT_MODEL = os.getenv('OPENAI_COMPAT_MODEL', '').strip()
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '').strip()
    CHATBOT_MODEL = os.getenv('CHATBOT_MODEL', 'claude-haiku-5-5').strip()
    CHATBOT_MAX_TOKENS = int(os.getenv('CHATBOT_MAX_TOKENS', '700'))
    CHATBOT_RATE_LIMIT_PER_MIN = int(os.getenv('CHATBOT_RATE_LIMIT_PER_MIN', '15'))

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
