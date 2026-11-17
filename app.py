import os
from flask import Flask, jsonify, request
from config import Config
from routes.views import views_bp
from routes.api_faqs import faqs_bp
from routes.api_admin import admin_bp
from routes.api_recommendations import recommendations_bp
from routes.api_colleges import colleges_bp
from routes.api_auth import auth_bp


def create_app():
    app = Flask(__name__, static_folder=None)
    app.config.from_object(Config)

    # Ensure secret key is set
    app.secret_key = Config.SECRET_KEY

    # Register application blueprints
    app.register_blueprint(views_bp)
    app.register_blueprint(faqs_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(recommendations_bp)
    app.register_blueprint(colleges_bp)
    app.register_blueprint(auth_bp)

    @app.errorhandler(404)
    def handle_not_found(e):
        if request.path.startswith('/api/'):
            return jsonify({
                "status": "error",
                "message": "Resource or endpoint not found."
            }), 404
        return (
            "<!DOCTYPE html><html><head><title>404 Not Found - CollegeHub</title>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<style>body{font-family:sans-serif;background:#F9F9F8;color:#0F1E36;text-align:center;padding:10vh 20px;}"
            "a{color:#216963;text-decoration:none;font-weight:bold;border-bottom:2px solid #216963;}</style></head>"
            "<body><h1>404 - Page Not Found</h1>"
            "<p>The requested page does not exist on CollegeHub.</p>"
            "<p><a href='/'>&larr; Return to CollegeHub Homepage</a></p></body></html>"
        ), 404

    @app.errorhandler(500)
    def handle_server_error(e):
        if request.path.startswith('/api/'):
            return jsonify({
                "status": "error",
                "message": "Internal server error occurred."
            }), 500
        return (
            "<!DOCTYPE html><html><head><title>500 Error - CollegeHub</title>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<style>body{font-family:sans-serif;background:#F9F9F8;color:#0F1E36;text-align:center;padding:10vh 20px;}"
            "a{color:#216963;text-decoration:none;font-weight:bold;border-bottom:2px solid #216963;}</style></head>"
            "<body><h1>500 - Server Error</h1>"
            "<p>An unexpected error occurred while processing your request.</p>"
            "<p><a href='/'>&larr; Return to CollegeHub Homepage</a></p></body></html>"
        ), 500

    return app


app = create_app()

def start_fallback_port_3000_forwarder():
    """
    Supabase projects default their Site URL to http://localhost:3000.
    If port 3000 is free, start a lightweight HTTP redirector in a background thread
    that automatically bounces incoming requests (including hash tokens) to port 5000.
    """
    try:
        import threading
        from http.server import HTTPServer, BaseHTTPRequestHandler

        class PortForwardHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                html = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Redirecting to CollegeHub...</title>
  <script>
    var currentPath = window.location.pathname;
    if (currentPath === '/' && window.location.hash.includes('type=recovery')) {
      currentPath = '/reset-password';
    }
    var target = 'http://localhost:5000' + currentPath + window.location.search + window.location.hash;
    window.location.replace(target);
  </script>
</head>
<body style="font-family:sans-serif;text-align:center;padding:40px;color:#1e293b;">
  <p>Forwarding to CollegeHub on port 5000...</p>
</body>
</html>"""
                self.wfile.write(html.encode('utf-8'))

            def log_message(self, format, *args):
                pass

        server_3000 = HTTPServer(('0.0.0.0', 3000), PortForwardHandler)
        t = threading.Thread(target=server_3000.serve_forever, daemon=True)
        t.start()
        print("Fallback forwarder running on http://127.0.0.1:3000 -> http://127.0.0.1:5000")
    except Exception:
        pass


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    start_fallback_port_3000_forwarder()
    print(f"Starting CollegeHub on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)
