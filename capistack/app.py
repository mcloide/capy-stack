# capistack/app.py
from pathlib import Path
from flask import Flask
from capistack.core.settings import get_config
from capistack.web.routes import web_bp
# from capistack.api.routes import api_bp 

BASE_DIR = Path(__file__).resolve().parent

def create_app():
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "web" / "templates"),
        static_folder=str(BASE_DIR / "web" / "static"),
        static_url_path="/static",
    )
    app.config.from_object(get_config())  # your existing config loader

    # Blueprints
    app.register_blueprint(web_bp)              # site pages
    # app.register_blueprint(api_bp, url_prefix="/api")  # JSON endpoints

    return app

# Keep this so `flask --app capistack.app run --debug` works
app = create_app()
