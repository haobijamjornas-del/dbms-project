from flask import (Blueprint, flash, redirect, render_template, request,
                   url_for)

from backend.repositories import alert_repo, lookup_repo
from backend.schemas import AlertUpdateSchema
from backend.security import current_user, login_required
from backend.services import alert_service

bp = Blueprint("alerts", __name__, url_prefix="/alerts")


@bp.route("/")
@login_required("counsellor", "admin")
def index():
    user = current_user()
    mine = request.args.get("mine") == "1"
    rows, total = alert_service.search(
        status=request.args.get("status", "OPEN"),
        priority=request.args.get("priority") or None,
        counsellor_id=user["counsellor_id"] if mine else None,
        page=max(1, request.args.get("page", 1, type=int)),
        per_page=100)
    return render_template("alerts.html", rows=rows, total=total,
                           status=request.args.get("status", "OPEN"),
                           priority=request.args.get("priority", ""),
                           mine=mine, counts=alert_repo.status_counts(),
                           counsellors=lookup_repo.counsellors())


@bp.route("/<int:alert_id>/update", methods=["POST"])
@login_required("counsellor", "admin")
def update(alert_id):
    data = AlertUpdateSchema.load(request.form)
    alert_service.update(alert_id, status=data["status"],
                         assigned_to=data["assigned_to"],
                         remarks=data["remarks"])
    if data["status"]:
        flash(f"Alert #{alert_id} set to {data['status']}.", "success")
    return redirect(request.referrer or url_for("alerts.index"))
