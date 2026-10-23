from flask import Blueprint, render_template

from backend.security import login_required
from backend.services import analytics_service

bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@bp.route("/")
@login_required("counsellor", "admin")
def index():
    return render_template("analytics.html", **analytics_service.full_report())
