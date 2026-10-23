from backend.blueprints.admin import bp as admin_bp
from backend.blueprints.alerts import bp as alerts_bp
from backend.blueprints.analytics import bp as analytics_bp
from backend.blueprints.api_v1 import bp as api_bp
from backend.blueprints.assessments import bp as assessments_bp
from backend.blueprints.auth import bp as auth_bp
from backend.blueprints.game import bp as game_bp
from backend.blueprints.main import bp as main_bp
from backend.blueprints.puzzles import bp as puzzles_bp
from backend.blueprints.screening import bp as screening_bp
from backend.blueprints.sessions import bp as sessions_bp
from backend.blueprints.students import bp as students_bp
from backend.blueprints.wellness import bp as wellness_bp

ALL_BLUEPRINTS = (
    auth_bp, main_bp, students_bp, assessments_bp, screening_bp, puzzles_bp, game_bp,
    alerts_bp, sessions_bp, wellness_bp, analytics_bp, admin_bp, api_bp,
)
