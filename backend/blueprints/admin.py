import json
import os
import time

from flask import (Blueprint, current_app, flash, redirect, render_template,
                   request, url_for)

from backend.database import run_readonly_sql
from backend.repositories import admin_repo
from backend.security import login_required
from backend.sql_samples import SAMPLE_QUERIES

bp = Blueprint("admin", __name__)


@bp.route("/models")
@login_required("admin")
def models():
    meta_path = os.path.join(current_app.config["MODEL_DIR"], "metadata.json")
    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path) as fh:
            meta = json.load(fh)
    return render_template("models.html", rows=admin_repo.models(), meta=meta,
                           usage=admin_repo.model_usage(),
                           corpus_stats=admin_repo.corpus_stats())


@bp.route("/models/<int:model_id>/activate", methods=["POST"])
@login_required("admin")
def model_activate(model_id):
    admin_repo.activate_model(model_id)
    flash(f"Model #{model_id} is now the active model (trigger T7 deactivated "
          f"the previous one).", "success")
    return redirect(url_for("admin.models"))


@bp.route("/sql", methods=["GET", "POST"])
@login_required("admin")
def sql_console():
    sql = (request.form.get("sql", "") if request.method == "POST"
           else request.args.get("sql", ""))
    cols, rows, error, truncated, elapsed = [], [], None, False, None
    if sql.strip():
        t0 = time.time()
        try:
            cols, rows, truncated = run_readonly_sql(sql)
            elapsed = round((time.time() - t0) * 1000, 2)
        except Exception as exc:
            error = str(exc)
    return render_template("sql_console.html", sql=sql, cols=cols, rows=rows,
                           error=error, truncated=truncated, elapsed=elapsed,
                           samples=SAMPLE_QUERIES)


@bp.route("/schema")
@login_required("admin")
def schema():
    return render_template("schema.html", **admin_repo.schema_objects())
