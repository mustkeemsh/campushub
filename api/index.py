import os
import sys

# Add the project root directory to the Python path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import app


class VercelPathMiddleware:
    """
    WSGI middleware for Vercel Serverless Functions.
    When Vercel rewrites incoming traffic through /api/index, PATH_INFO in the
    WSGI environment may be set to '/api/index'.
    This middleware restores the client's actual request path from HTTP_X_MATCHED_PATH
    or REQUEST_URI so Flask routes like '/', '/faqs', '/recommendations', etc. match cleanly.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        matched_path = (
            environ.get('HTTP_X_MATCHED_PATH') or
            environ.get('REQUEST_URI') or
            environ.get('HTTP_X_FORWARDED_URI') or
            ''
        )
        if matched_path:
            clean_path = matched_path.split('?')[0]
            if clean_path and clean_path not in ('/api/index', '/api/index.py'):
                environ['PATH_INFO'] = clean_path
        elif environ.get('PATH_INFO', '') in ('/api/index', '/api/index.py'):
            environ['PATH_INFO'] = '/'
        elif environ.get('PATH_INFO', '').startswith('/api/index/'):
            environ['PATH_INFO'] = environ['PATH_INFO'][len('/api/index'):] or '/'

        return self.wsgi_app(environ, start_response)


app.wsgi_app = VercelPathMiddleware(app.wsgi_app)

# Vercel's Python runtime discovers and serves the `app` WSGI callable
if __name__ == "__main__":
    app.run()
