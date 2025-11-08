from flask import Flask
from flask_cors import CORS
from .config import Config


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    # CORS
    CORS(app, resources={r"/*": {"origins": app.config.get("CORS_ORIGINS", "*")}})

    # Blueprints
    from .routes import bp as api_bp  # noqa: WPS433 (import within function)
    app.register_blueprint(api_bp, url_prefix="/api")

    return app
