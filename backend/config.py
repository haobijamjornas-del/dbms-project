import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class BaseConfig:
    SECRET_KEY = os.environ.get("MINDCARE_SECRET_KEY",
                                "mindcare-dbms-project-secret-key")
    DATABASE_PATH = os.path.join(BASE_DIR, "mindcare.db")
    MODEL_DIR = os.path.join(BASE_DIR, "ml", "models")

    JSON_SORT_KEYS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8

    PAGE_SIZE = 15
    MAX_PAGE_SIZE = 100
    SQL_CONSOLE_ROW_LIMIT = 200

    API_PREFIX = "/api/v1"
    API_TOKEN_TTL = 60 * 60 * 12

    DEBUG = False
    TESTING = False


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False


class ProductionConfig(BaseConfig):
    SECRET_KEY = os.environ.get("MINDCARE_SECRET_KEY")
    SESSION_COOKIE_SECURE = True


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(name=None):
    name = name or os.environ.get("MINDCARE_ENV", "development")
    if name not in CONFIGS:
        raise ValueError(f"Unknown config '{name}'. Choose from {list(CONFIGS)}.")
    cfg = CONFIGS[name]
    if name == "production" and not cfg.SECRET_KEY:
        raise RuntimeError("MINDCARE_SECRET_KEY must be set in production.")
    return cfg
