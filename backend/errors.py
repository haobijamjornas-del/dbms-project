import logging
import sqlite3

from flask import current_app, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

log = logging.getLogger("mindcare")


class AppError(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, details=None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.details = details or {}


class ValidationError(AppError):
    status_code = 422


class NotFoundError(AppError):
    status_code = 404


class PermissionError_(AppError):
    status_code = 403


def wants_json():
    if request.path.startswith(current_app.config["API_PREFIX"]):
        return True
    return request.accept_mimetypes.best == "application/json"


def _payload(code, message, details=None):
    body = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return body


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(exc):
        if wants_json():
            return jsonify(_payload(exc.status_code, exc.message, exc.details)), \
                   exc.status_code
        return render_template("error.html", code=exc.status_code,
                               message=exc.message), exc.status_code

    @app.errorhandler(sqlite3.IntegrityError)
    def handle_integrity(exc):
        message = str(exc)
        log.warning("Integrity error: %s", message)
        if wants_json():
            return jsonify(_payload(409, "The database rejected this change.",
                                    {"constraint": message})), 409
        return render_template("error.html", code=409,
                               message=f"The database rejected this change: "
                                       f"{message}"), 409

    @app.errorhandler(HTTPException)
    def handle_http(exc):
        if wants_json():
            return jsonify(_payload(exc.code, exc.description)), exc.code
        return render_template("error.html", code=exc.code,
                               message=exc.description), exc.code

    @app.errorhandler(Exception)
    def handle_unexpected(exc):
        log.exception("Unhandled exception")
        if current_app.config["DEBUG"]:
            raise exc
        if wants_json():
            return jsonify(_payload(500, "Internal server error.")), 500
        return render_template("error.html", code=500,
                               message="Something went wrong on our side."), 500
