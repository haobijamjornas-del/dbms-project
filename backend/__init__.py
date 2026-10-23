import logging
import os

from flask import Flask

from backend.config import get_config
from backend.database import close_db
from backend.errors import register_error_handlers
from backend.security import load_current_user


def create_app(config_name=None):
    app = Flask(__name__,
                template_folder="templates",
                static_folder="static",
                static_url_path="/static")
    app.config.from_object(get_config(config_name))

    _configure_logging(app)
    _register_blueprints(app)
    _register_hooks(app)
    _register_template_helpers(app)
    register_error_handlers(app)

    return app


def _configure_logging(app):
    level = logging.DEBUG if app.config["DEBUG"] else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
        datefmt="%H:%M:%S")
    logging.getLogger("werkzeug").setLevel(logging.WARNING)


def _register_blueprints(app):
    from backend.blueprints import ALL_BLUEPRINTS
    for bp in ALL_BLUEPRINTS:
        app.register_blueprint(bp)


def _register_hooks(app):
    app.teardown_appcontext(close_db)
    app.before_request(load_current_user)

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        return response


def _register_template_helpers(app):
    from datetime import datetime

    from backend.database import scalar
    from backend.security import current_user
    from backend.services.daily_service import thought_for_today

    LEVEL_NAMES = {0: "Low", 1: "Medium", 2: "High"}
    LEVEL_COLORS = {0: "#2E9E5B", 1: "#E8A33D", 2: "#D64545"}

    @app.template_filter("dt")
    def fmt_dt(value, fmt="%d %b %Y, %H:%M"):
        if not value:
            return "-"
        if isinstance(value, str):
            for f in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    value = datetime.strptime(value, f)
                    break
                except ValueError:
                    continue
        return value.strftime(fmt) if isinstance(value, datetime) else str(value)

    @app.template_filter("ago")
    def fmt_ago(value):
        if not value:
            return "-"
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return value
        delta = datetime.now() - value
        if delta.days > 1:
            return f"{delta.days} days ago"
        if delta.days == 1:
            return "yesterday"
        hours = delta.seconds // 3600
        if hours:
            return f"{hours}h ago"
        return f"{max(1, delta.seconds // 60)}m ago"

    honorifics = {"dr", "dr.", "mr", "mr.", "ms", "ms.", "mrs", "mrs.", "prof", "prof."}

    def _name_parts(name):
        return [p for p in str(name or "").split() if p.lower() not in honorifics]

    @app.template_filter("firstname")
    def first_name(name):
        parts = _name_parts(name)
        return parts[0] if parts else (name or "")

    @app.template_filter("initials")
    def initials(name):
        parts = _name_parts(name)
        if not parts:
            return "?"
        return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()

    @app.context_processor
    def inject_globals():
        user = current_user()
        open_alerts = 0
        if user and user["role"] in ("counsellor", "admin"):
            open_alerts = scalar("SELECT COUNT(*) FROM alert WHERE status = 'OPEN'")
        return {
            "g_user": user,
            "LEVEL_NAMES": LEVEL_NAMES,
            "LEVEL_COLORS": LEVEL_COLORS,
            "open_alert_count": open_alerts,
            "thought": thought_for_today(),
            "now": datetime.now(),
            "greeting": ("Good morning" if datetime.now().hour < 12
                         else "Good afternoon" if datetime.now().hour < 17
                         else "Good evening"),
        }
