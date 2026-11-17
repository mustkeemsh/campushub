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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting CollegeHub on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
