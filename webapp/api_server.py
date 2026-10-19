from flask import Flask

try:
    from flask_cors import CORS
except ImportError:  # pragma: no cover - dependency is declared in requirements.txt
    CORS = None

from webapp.config import load_config
from webapp.errors import register_error_handlers
from webapp.routes.api import api_bp


def create_app() -> Flask:
    config = load_config()
    app = Flask(__name__)
    app.config["APP_ENV"] = config.env
    app.config["QUOTE_HISTORY_DB"] = str(config.quote_history_db)

    register_error_handlers(app)
    app.register_blueprint(api_bp)

    if config.cors_origins and CORS is not None:
        CORS(app, resources={r"/api/*": {"origins": list(config.cors_origins)}})

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5055, debug=False)
