from flask import Blueprint

bp = Blueprint("shared", __name__)

from app.blueprints.shared import routes  # noqa: E402, F401
